"""
🌱 AI-Powered Smart Agriculture Robot - Backend API
FastAPI server that accepts plant images and returns disease predictions.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from model import PlantDiseaseModel

# ===== App Setup =====
app = FastAPI(
    title="🌱 Smart Agriculture API",
    description="AI-powered plant disease detection from images",
    version="1.0.0",
)

# CORS - allow frontend & ESP32
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Load AI Model
print("[MODEL] Loading plant disease detection model...")
model = PlantDiseaseModel()
print("[MODEL] ✓ Model loaded and ready!")

# History of predictions (in-memory for hackathon)
prediction_history = []


# ===== Routes =====

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "🌱 Smart Agriculture API",
        "model": "PlantDiseaseNet (ResNet18)",
        "version": "1.0.0",
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Accept a plant image and return disease prediction.
    
    Returns:
        JSON with disease name, confidence, and treatment solution.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image (JPEG/PNG)."
        )

    # Save image
    file_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file_id}.jpg"
    filepath = UPLOAD_DIR / filename

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    print(f"[UPLOAD] Saved: {filepath} ({len(contents)} bytes)")

    # Run AI prediction
    try:
        result = model.predict(str(filepath))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model prediction failed: {str(e)}"
        )

    # Build response
    response = {
        "disease": result["disease"],
        "confidence": result["confidence"],
        "solution": result["solution"],
        "image_file": filename,
        "timestamp": datetime.now().isoformat(),
    }

    # Store in history
    prediction_history.append(response)
    # Keep only last 50
    if len(prediction_history) > 50:
        prediction_history.pop(0)

    print(f"[PREDICT] {result['disease']} ({result['confidence']:.1%})")
    return response


@app.post("/predict_batch")
async def predict_batch(files: list[UploadFile] = File(...)):
    """
    Accept multiple plant images (e.g., 3 shots of the same plant)
    and return a consolidated disease prediction.
    """
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []
    saved_filenames = []

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        # Save image
        file_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_{timestamp}_{file_id}.jpg"
        filepath = UPLOAD_DIR / filename

        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)
        
        saved_filenames.append(filename)

        # Predict
        try:
            res = model.predict(str(filepath))
            results.append(res)
            print(f"[BATCH] Photo {file.filename} processed: {res['disease']}")
        except Exception as e:
            print(f"[BATCH] Error processing photo {file.filename}: {str(e)}")
            continue

    if not results:
        print("[BATCH] ❌ Critical: No results generated for the entire batch!")
        raise HTTPException(status_code=500, detail="Failed to process any images in the batch. Check backend logs for details.")

    # Collate: Simple majority vote with confidence tie-breaker
    disease_counts = {}
    disease_total_conf = {}
    disease_solutions = {}

    for res in results:
        d = res["disease"]
        disease_counts[d] = disease_counts.get(d, 0) + 1
        disease_total_conf[d] = disease_total_conf.get(d, 0) + res["confidence"]
        disease_solutions[d] = res["solution"]

    # Pick the winner
    # Sort by count (primary) and total confidence (secondary)
    winner = max(disease_counts.keys(), key=lambda d: (disease_counts[d], disease_total_conf[d]))

    response = {
        "disease": winner,
        "confidence": disease_total_conf[winner] / disease_counts[winner], # Average conf of the winner
        "solution": disease_solutions[winner],
        "image_file": saved_filenames[0], # Show the first image as representative
        "batch_images": saved_filenames,
        "is_batch": True,
        "num_photos": len(results),
        "timestamp": datetime.now().isoformat(),
    }

    prediction_history.append(response)
    if len(prediction_history) > 50:
        prediction_history.pop(0)

    print(f"[BATCH] Result: {winner} from {len(results)} photos")
    return response

@app.get("/history")
async def get_history():
    """Return prediction history (most recent first)."""
    return {"predictions": list(reversed(prediction_history))}


@app.get("/uploads/{filename}")
async def get_upload(filename: str):
    """Serve uploaded images."""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath)





# ===== Run =====
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🌱 Smart Agriculture API Starting...")
    print("=" * 50)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
