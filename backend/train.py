"""
🧠 Training Script — Plant Disease Detection Model
TRANSFER LEARNING approach: Freeze pretrained backbone, train only classifier.

Uses MobileNetV2 (fast on CPU) + frozen feature extractor = trains in minutes, not hours.
Dataset: vipoooool/new-plant-diseases-dataset (Kaggle)
"""

import os
import sys
import time
import json
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms, models
import numpy as np

# ===== Configuration =====
EPOCHS = 3              # Few epochs needed with transfer learning
BATCH_SIZE = 64         # Larger batch = faster on CPU
LEARNING_RATE = 0.001
NUM_WORKERS = 0         # 0 for macOS compatibility
MODEL_SAVE_PATH = "plant_disease_model.pth"
CLASS_MAP_PATH = "class_mapping.json"
USE_SUBSET = True       # Use subset for fast hackathon training
SUBSET_PER_CLASS = 200  # Images per class (200 × 38 = 7,600 total)


def get_dataset_path():
    """Download multiple datasets using kagglehub and merge them via symlinks."""
    print("[DATA] Downloading Primary Dataset (Kaggle)...")
    import kagglehub
    base1 = kagglehub.dataset_download("vipoooool/new-plant-diseases-dataset")
    data_dir1 = os.path.join(base1, "New Plant Diseases Dataset(Augmented)", "New Plant Diseases Dataset(Augmented)")

    print("[DATA] Downloading Secondary Dataset (Flowers)...")
    data_dir2 = kagglehub.dataset_download("shuvokumarbasak4004/flower-leaf-diseases-dataset-new-and-update")

    merged_dir = os.path.abspath(".merged_dataset")
    merged_train = os.path.join(merged_dir, "train")
    merged_valid = os.path.join(merged_dir, "valid")
    os.makedirs(merged_train, exist_ok=True)
    os.makedirs(merged_valid, exist_ok=True)

    def symlink_classes(src_dir, dest_dir, require_split=False):
        if not os.path.exists(src_dir): return
        for cls_name in os.listdir(src_dir):
            cls_path = os.path.join(src_dir, cls_name)
            if os.path.isdir(cls_path):
                dest_path = os.path.join(dest_dir, cls_name)
                if not os.path.exists(dest_path):
                    os.symlink(cls_path, dest_path)

    print("[DATA] Unifying datasets into a single master dataset...")
    # Add crops dataset (it has train/valid splits)
    symlink_classes(os.path.join(data_dir1, "train"), merged_train)
    symlink_classes(os.path.join(data_dir1, "valid"), merged_valid)
    
    # Add flowers dataset (it might just contain class folders directly, or have splits)
    if os.path.exists(os.path.join(data_dir2, "train")):
        symlink_classes(os.path.join(data_dir2, "train"), merged_train)
        if os.path.exists(os.path.join(data_dir2, "valid")):
            symlink_classes(os.path.join(data_dir2, "valid"), merged_valid)
        else:
            symlink_classes(os.path.join(data_dir2, "train"), merged_valid) # Fallback
    else:
        # If no splits, use the root directory for both train and valid
        symlink_classes(data_dir2, merged_train)
        symlink_classes(data_dir2, merged_valid)

    print(f"[DATA] ✓ Unified dataset path: {merged_dir}")
    return merged_dir


def create_subset(dataset, per_class: int):
    """Create a balanced subset with `per_class` samples per class."""
    targets = np.array(dataset.targets)
    indices = []
    for class_idx in range(len(dataset.classes)):
        class_indices = np.where(targets == class_idx)[0]
        if len(class_indices) == 0: continue
        selected = np.random.choice(
            class_indices, size=min(per_class, len(class_indices)), replace=False
        )
        indices.extend(selected.tolist())
    np.random.shuffle(indices)
    return Subset(dataset, indices)


def build_mobilenet_v2(num_classes: int):
    """
    Transfer Learning with MobileNetV2:
    - Load pretrained ImageNet weights (feature extractor)
    - FREEZE entire backbone (no gradient computation = fast)
    - Replace only the classifier head (trains in minutes)
    """
    print("[MODEL] Loading MobileNetV2 (pretrained on ImageNet)...")
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)

    # ★ FREEZE all backbone parameters — this is the key to speed
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace classifier (only this part trains)
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(model.last_channel, num_classes),  # 1280 → 38
    )

    # Count parameters
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    frozen = total - trainable
    print(f"[MODEL] ✓ MobileNetV2 loaded")
    print(f"[MODEL]   Total params:     {total:>10,}")
    print(f"[MODEL]   Frozen (backbone): {frozen:>10,}  ← pretrained, not updated")
    print(f"[MODEL]   Trainable (head):  {trainable:>10,}  ← only this trains!")

    return model


def build_resnet18(num_classes: int):
    """
    Transfer Learning with ResNet18:
    - Load pretrained ImageNet weights
    - FREEZE entire backbone
    - Replace only the fc layer
    """
    print("[MODEL] Loading ResNet18 (pretrained on ImageNet)...")
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)

    # ★ FREEZE all layers except the final fc
    for name, param in model.named_parameters():
        if "fc" not in name:
            param.requires_grad = False

    # Replace classifier
    num_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(num_features, num_classes),  # 512 → 38
    )

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    frozen = total - trainable
    print(f"[MODEL] ✓ ResNet18 loaded")
    print(f"[MODEL]   Total params:     {total:>10,}")
    print(f"[MODEL]   Frozen (backbone): {frozen:>10,}")
    print(f"[MODEL]   Trainable (head):  {trainable:>10,}")

    return model


def train(model_type: str = "mobilenet"):
    """
    Main training function using Transfer Learning.

    Args:
        model_type: 'mobilenet' (faster) or 'resnet' (slightly more accurate)
    """
    print("\n" + "=" * 60)
    print("🌱 Plant Disease Model — Transfer Learning Training")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[TRAIN] Device: {device}")
    print(f"[TRAIN] Model: {model_type.upper()}")
    print(f"[TRAIN] Strategy: Frozen backbone + trainable classifier head")

    # Get dataset
    data_dir = get_dataset_path()
    train_dir = os.path.join(data_dir, "train")
    valid_dir = os.path.join(data_dir, "valid")

    # Data transforms
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # Load datasets
    print("[DATA] Loading datasets...")
    full_train_dataset = datasets.ImageFolder(train_dir, transform=train_transform)
    val_dataset = datasets.ImageFolder(valid_dir, transform=val_transform)
    num_classes = len(full_train_dataset.classes)

    # Use subset for faster training on CPU
    if USE_SUBSET:
        print(f"[DATA] Creating balanced subset ({SUBSET_PER_CLASS} per class)...")
        train_dataset = create_subset(full_train_dataset, SUBSET_PER_CLASS)
        val_subset = create_subset(val_dataset, 50)  # 50 per class for validation
        print(f"[DATA] Training subset:   {len(train_dataset):,} images")
        print(f"[DATA] Validation subset: {len(val_subset):,} images")
    else:
        train_dataset = full_train_dataset
        val_subset = val_dataset
        print(f"[DATA] Training:   {len(train_dataset):,} images")
        print(f"[DATA] Validation: {len(val_subset):,} images")

    print(f"[DATA] Classes: {num_classes}")

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=NUM_WORKERS, pin_memory=False
    )
    val_loader = DataLoader(
        val_subset, batch_size=BATCH_SIZE, shuffle=False,
        num_workers=NUM_WORKERS, pin_memory=False
    )

    # Save class mapping
    class_to_idx = full_train_dataset.class_to_idx
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    with open(CLASS_MAP_PATH, "w") as f:
        json.dump({
            "class_to_idx": class_to_idx,
            "idx_to_class": idx_to_class,
            "num_classes": num_classes,
            "model_type": model_type,
        }, f, indent=2)
    print(f"[DATA] ✓ Class mapping saved to: {CLASS_MAP_PATH}")

    # Build model
    if model_type == "mobilenet":
        model = build_mobilenet_v2(num_classes)
    else:
        model = build_resnet18(num_classes)

    model = model.to(device)

    # Loss & optimizer (only trainable params)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
    )
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)

    # Training loop
    best_acc = 0.0
    total_start = time.time()
    print(f"\n[TRAIN] Starting training — {EPOCHS} epochs, {len(train_loader)} batches/epoch")
    print("-" * 60)

    for epoch in range(EPOCHS):
        epoch_start = time.time()

        # ---- Train ----
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            # Progress every 20 batches
            if (batch_idx + 1) % 20 == 0:
                print(f"  Epoch {epoch+1}/{EPOCHS} | "
                      f"Batch {batch_idx+1}/{len(train_loader)} | "
                      f"Loss: {running_loss/(batch_idx+1):.4f} | "
                      f"Acc: {100*correct/total:.1f}%")

        train_loss = running_loss / len(train_loader)
        train_acc = 100 * correct / total

        # ---- Validate ----
        model.eval()
        val_correct = 0
        val_total = 0
        val_loss = 0.0

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        val_loss /= len(val_loader)
        val_acc = 100 * val_correct / val_total
        epoch_time = time.time() - epoch_start

        print(f"\n📊 Epoch [{epoch+1}/{EPOCHS}] ({epoch_time:.0f}s)")
        print(f"   Train — Loss: {train_loss:.4f} | Acc: {train_acc:.1f}%")
        print(f"   Valid — Loss: {val_loss:.4f} | Acc: {val_acc:.1f}%")

        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"   ✅ Best model saved! (Val Acc: {val_acc:.1f}%)")

        print("-" * 60)
        scheduler.step()

    total_time = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"🎉 Training Complete in {total_time:.0f}s ({total_time/60:.1f} min)!")
    print(f"   Best Validation Accuracy: {best_acc:.1f}%")
    print(f"   Model saved to: {MODEL_SAVE_PATH}")
    print(f"   Class mapping:  {CLASS_MAP_PATH}")
    print(f"{'=' * 60}")
    print(f"\n▶ Restart the backend to use the trained model:")
    print(f"   python main.py")


if __name__ == "__main__":
    # Use 'mobilenet' (fast on CPU) or 'resnet' 
    train(model_type="mobilenet")
