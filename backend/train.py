"""
🧠 Training Script — Plant Disease Detection Model
Dataset:  abdallahalidev/plantvillage-dataset
          https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset

TRANSFER LEARNING approach:
  - MobileNetV2 backbone (pretrained on ImageNet)
  - Freeze feature extractor, train only classifier head
  - 38 plant disease classes (color images)
  - Trains in minutes on CPU, ~30s/epoch on GPU

Usage:
  python train.py                       # default: mobilenet, 5 epochs
  python train.py --model resnet        # ResNet18 backbone
  python train.py --model efficientnet  # EfficientNet-B0 (best accuracy)
  python train.py --epochs 10           # more epochs
  python train.py --full                # use full dataset (slower but more accurate)
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms, models
import numpy as np

# ===== Configuration =====
EPOCHS           = 5              # More epochs = better accuracy
BATCH_SIZE       = 64
LEARNING_RATE    = 0.001
NUM_WORKERS      = 0              # 0 for macOS compatibility
MODEL_SAVE_PATH  = "plant_disease_model.pth"
CLASS_MAP_PATH   = "class_mapping.json"
USE_SUBSET       = True           # Set False to train on full dataset
SUBSET_PER_CLASS = 200            # Images per class for subset training


def get_dataset_path():
    """
    Locate the PlantVillage dataset (abdallahalidev/plantvillage-dataset).
    URL: https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset

    Dataset structure:
      plantvillage dataset/
        color/         ← 38 class folders with color images  ✅ we use this
        grayscale/     ← same images in grayscale
        segmented/     ← segmented versions
    """
    print("[DATA] Locating abdallahalidev/plantvillage-dataset ...")

    # ── 1. Check if dataset is already extracted (kagglehub cache) ────────────
    KNOWN_PATH = os.path.expanduser(
        "~/.cache/kagglehub/datasets/abdallahalidev/"
        "plantvillage-dataset/versions/3/plantvillage dataset/color"
    )
    if os.path.isdir(KNOWN_PATH):
        n = len([d for d in os.listdir(KNOWN_PATH)
                 if os.path.isdir(os.path.join(KNOWN_PATH, d))])
        print(f"[DATA] ✓ Found pre-extracted dataset ({n} classes)")
        print(f"[DATA] ✓ Using: {KNOWN_PATH}")
        return KNOWN_PATH

    # ── 2. Also check any version in the kagglehub cache ─────────────────────
    cache_base = os.path.expanduser(
        "~/.cache/kagglehub/datasets/abdallahalidev/plantvillage-dataset/versions"
    )
    if os.path.isdir(cache_base):
        for ver in sorted(os.listdir(cache_base), reverse=True):
            candidate = os.path.join(cache_base, ver, "plantvillage dataset", "color")
            if os.path.isdir(candidate):
                n = len([d for d in os.listdir(candidate)
                         if os.path.isdir(os.path.join(candidate, d))])
                print(f"[DATA] ✓ Found cached dataset v{ver} ({n} classes)")
                print(f"[DATA] ✓ Using: {candidate}")
                return candidate

    # ── 3. Download via kagglehub if not cached ───────────────────────────────
    print("[DATA] Not cached — downloading from Kaggle ...")
    try:
        import kagglehub
    except ImportError:
        print("[ERROR] kagglehub not installed. Run: pip install kagglehub")
        sys.exit(1)

    try:
        base = kagglehub.dataset_download("abdallahalidev/plantvillage-dataset")
    except Exception as e:
        print(f"\n[ERROR] Failed to download dataset: {e}")
        print()
        print("  ▸ Set up your Kaggle API key:")
        print("    1. Visit https://www.kaggle.com → Account → API → Create New Token")
        print("    2. Move kaggle.json to: ~/.kaggle/kaggle.json")
        print("    3. Run: chmod 600 ~/.kaggle/kaggle.json")
        print("    4. Re-run: python train.py")
        sys.exit(1)

    # ── 4. Locate the color/ folder inside the download ───────────────────────
    color_dir = None
    for candidate in [
        os.path.join(base, "plantvillage dataset", "color"),
        os.path.join(base, "color"),
    ]:
        if os.path.isdir(candidate):
            color_dir = candidate
            break

    if color_dir is None:
        for root, dirs, _ in os.walk(base):
            if "color" in dirs:
                candidate = os.path.join(root, "color")
                subdirs = [d for d in os.listdir(candidate)
                           if os.path.isdir(os.path.join(candidate, d))]
                if len(subdirs) > 5:
                    color_dir = candidate
                    break

    if color_dir is None:
        print(f"[ERROR] Could not find color/ folder under: {base}")
        sys.exit(1)

    n = len([d for d in os.listdir(color_dir)
             if os.path.isdir(os.path.join(color_dir, d))])
    print(f"[DATA] ✓ Using: {color_dir}")
    print(f"[DATA] ✓ Found {n} class folders")
    return color_dir


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


def _print_model_stats(model, name: str):
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    frozen    = total - trainable
    print(f"[MODEL] ✓ {name} loaded")
    print(f"[MODEL]   Total params:      {total:>12,}")
    print(f"[MODEL]   Frozen (backbone): {frozen:>12,}  ← pretrained, not updated")
    print(f"[MODEL]   Trainable (head):  {trainable:>12,}  ← only this trains!")


def build_mobilenet_v2(num_classes: int):
    """
    Transfer Learning with MobileNetV2:
    - Load pretrained ImageNet weights (feature extractor)
    - FREEZE entire backbone (no gradient computation = fast)
    - Replace only the classifier head (trains in minutes)
    """
    print("[MODEL] Loading MobileNetV2 (pretrained on ImageNet) ...")
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)

    # Freeze backbone
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace classifier head
    model.classifier = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(model.last_channel, num_classes),
    )
    _print_model_stats(model, "MobileNetV2")
    return model


def build_resnet18(num_classes: int):
    """
    Transfer Learning with ResNet18:
    - Load pretrained ImageNet weights
    - FREEZE entire backbone
    - Replace only the fc layer
    """
    print("[MODEL] Loading ResNet18 (pretrained on ImageNet) ...")
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)

    # Freeze backbone
    for name, param in model.named_parameters():
        if "fc" not in name:
            param.requires_grad = False

    num_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(num_features, num_classes),
    )
    _print_model_stats(model, "ResNet18")
    return model


def build_efficientnet_b0(num_classes: int):
    """
    Transfer Learning with EfficientNet-B0:
    - Best accuracy/speed tradeoff
    - Same family used in top Kaggle plant disease kernels
    """
    print("[MODEL] Loading EfficientNet-B0 (pretrained on ImageNet) ...")
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)

    # Freeze backbone
    for param in model.features.parameters():
        param.requires_grad = False

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, num_classes),
    )
    _print_model_stats(model, "EfficientNet-B0")
    return model


def train(model_type: str = "mobilenet", epochs: int = EPOCHS, full: bool = False):
    """
    Main training pipeline using Transfer Learning.

    Args:
        model_type : 'mobilenet' | 'resnet' | 'efficientnet'
        epochs     : number of training epochs
        full       : use full dataset instead of balanced subset
    """
    print("\n" + "=" * 65)
    print("🌱  Plant Disease Model — Transfer Learning Training")
    print(f"    Dataset: abdallahalidev/plantvillage-dataset")
    print("=" * 65)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[TRAIN] Device:   {device}")
    print(f"[TRAIN] Model:    {model_type.upper()}")
    print(f"[TRAIN] Epochs:   {epochs}")
    print(f"[TRAIN] Strategy: Frozen backbone + trainable head (Transfer Learning)")

    # ── Download dataset ──────────────────────────────────────────────────────
    # abdallahalidev/plantvillage-dataset has NO pre-made train/valid split.
    # We get a flat color/ folder of 38 class dirs and create our own split.
    color_dir = get_dataset_path()

    # ── Data transforms ───────────────────────────────────────────────────────
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.1),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # ── Load dataset & create train/val split ─────────────────────────────────
    print("\n[DATA] Loading dataset ...")
    full_dataset = datasets.ImageFolder(color_dir, transform=train_transform)
    num_classes  = len(full_dataset.classes)
    total_size   = len(full_dataset)

    # 80/20 stratified split
    val_size   = int(0.2 * total_size)
    train_size = total_size - val_size
    generator  = torch.Generator().manual_seed(42)
    train_dataset_raw, val_dataset_raw = torch.utils.data.random_split(
        full_dataset, [train_size, val_size], generator=generator
    )

    # Apply correct transforms to val set
    val_dataset_raw.dataset = datasets.ImageFolder(color_dir, transform=val_transform)

    use_sub = USE_SUBSET and not full
    if use_sub:
        # Create balanced subset from the full dataset before splitting
        print(f"[DATA] Subset mode: {SUBSET_PER_CLASS} images/class (stratified)")
        full_dataset_nosub = datasets.ImageFolder(color_dir, transform=train_transform)
        subset_full = create_subset(full_dataset_nosub, SUBSET_PER_CLASS)

        sub_size  = len(subset_full)
        sub_val   = int(0.2 * sub_size)
        sub_train = sub_size - sub_val
        train_dataset, val_dataset = torch.utils.data.random_split(
            subset_full, [sub_train, sub_val], generator=generator
        )
    else:
        train_dataset = train_dataset_raw
        val_dataset   = val_dataset_raw

    print(f"[DATA] Total images : {total_size:,}")
    print(f"[DATA] Training     : {len(train_dataset):,} images")
    print(f"[DATA] Validation   : {len(val_dataset):,} images")
    print(f"[DATA] Classes      : {num_classes}")

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=NUM_WORKERS, pin_memory=False,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE, shuffle=False,
        num_workers=NUM_WORKERS, pin_memory=False,
    )

    # ── Save class mapping ────────────────────────────────────────────────────
    class_to_idx = full_dataset.class_to_idx
    idx_to_class = {str(v): k for k, v in class_to_idx.items()}

    with open(CLASS_MAP_PATH, "w") as f:
        json.dump({
            "class_to_idx": class_to_idx,
            "idx_to_class": idx_to_class,
            "num_classes":  num_classes,
            "model_type":   model_type,
            "dataset":      "abdallahalidev/plantvillage-dataset",
            "dataset_url":  "https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset",
        }, f, indent=2)
    print(f"[DATA] ✓ Class mapping saved → {CLASS_MAP_PATH}")

    # ── Build model ───────────────────────────────────────────────────────────
    print()
    if model_type == "mobilenet":
        model = build_mobilenet_v2(num_classes)
    elif model_type == "resnet":
        model = build_resnet18(num_classes)
    elif model_type == "efficientnet":
        model = build_efficientnet_b0(num_classes)
    else:
        print(f"[ERROR] Unknown model_type '{model_type}'. Use: mobilenet | resnet | efficientnet")
        sys.exit(1)

    model = model.to(device)

    # ── Loss, Optimizer, Scheduler ────────────────────────────────────────────
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)   # label smoothing helps generalization
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # ── Training loop ─────────────────────────────────────────────────────────
    best_acc    = 0.0
    total_start = time.time()
    history     = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    print(f"\n[TRAIN] Starting — {epochs} epochs, {len(train_loader)} batches/epoch")
    print("-" * 65)

    for epoch in range(epochs):
        epoch_start = time.time()

        # ---- Train ----------------------------------------------------------
        model.train()
        running_loss, correct, total = 0.0, 0, 0

        for batch_idx, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss    = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted  = torch.max(outputs, 1)
            total         += labels.size(0)
            correct       += (predicted == labels).sum().item()

            if (batch_idx + 1) % 10 == 0 or batch_idx == len(train_loader) - 1:
                print(
                    f"  Epoch {epoch+1}/{epochs} | "
                    f"Batch {batch_idx+1:>3}/{len(train_loader)} | "
                    f"Loss: {running_loss/(batch_idx+1):.4f} | "
                    f"Acc: {100*correct/total:>5.1f}%",
                    end="\r",
                )

        train_loss = running_loss / len(train_loader)
        train_acc  = 100 * correct / total
        print()  # newline after \r

        # ---- Validate -------------------------------------------------------
        model.eval()
        val_correct, val_total, val_loss_sum = 0, 0, 0.0

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs        = model(inputs)
                loss           = criterion(outputs, labels)
                val_loss_sum  += loss.item()
                _, predicted   = torch.max(outputs, 1)
                val_total     += labels.size(0)
                val_correct   += (predicted == labels).sum().item()

        val_loss = val_loss_sum / len(val_loader)
        val_acc  = 100 * val_correct / val_total
        epoch_t  = time.time() - epoch_start

        history["train_loss"].append(round(train_loss, 4))
        history["train_acc"].append(round(train_acc, 2))
        history["val_loss"].append(round(val_loss, 4))
        history["val_acc"].append(round(val_acc, 2))

        lr_now = scheduler.get_last_lr()[0] if hasattr(scheduler, "get_last_lr") else LEARNING_RATE
        print(f"\n📊 Epoch [{epoch+1}/{epochs}] ({epoch_t:.0f}s | lr={lr_now:.2e})")
        print(f"   Train — Loss: {train_loss:.4f} | Acc: {train_acc:.1f}%")
        print(f"   Valid — Loss: {val_loss:.4f} | Acc: {val_acc:.1f}%")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"   ✅ Best model saved! (Val Acc: {val_acc:.1f}%)")

        print("-" * 65)
        scheduler.step()

    # ── Summary ───────────────────────────────────────────────────────────────
    total_time = time.time() - total_start
    print(f"\n{'=' * 65}")
    print(f"🎉  Training Complete in {total_time:.0f}s ({total_time/60:.1f} min)!")
    print(f"    Best Validation Accuracy : {best_acc:.1f}%")
    print(f"    Model saved to           : {MODEL_SAVE_PATH}")
    print(f"    Class mapping saved to   : {CLASS_MAP_PATH}")
    print(f"    History: {history}")
    print(f"{'=' * 65}")
    print(f"\n▶  Restart the backend to use the newly trained model:")
    print(f"   python main.py")
    return history


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Train plant disease model (PlantVillage — akashbhakat kernel dataset)"
    )
    p.add_argument(
        "--model", default="mobilenet",
        choices=["mobilenet", "resnet", "efficientnet"],
        help="Backbone architecture (default: mobilenet)",
    )
    p.add_argument(
        "--epochs", type=int, default=EPOCHS,
        help=f"Number of training epochs (default: {EPOCHS})",
    )
    p.add_argument(
        "--full", action="store_true",
        help="Use full dataset instead of balanced subset (slower but more accurate)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(model_type=args.model, epochs=args.epochs, full=args.full)
