# 🌱 AgriSense — AI-Powered Smart Agriculture Robot

> Real-time plant disease detection using ESP32-CAM, FastAPI, and PyTorch.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red?logo=pytorch)
![ESP32](https://img.shields.io/badge/ESP32--CAM-Arduino-orange?logo=arduino)

---

## 📁 Project Structure

```
smart-agriculture/
├── esp32_cam/
│   └── esp32_cam.ino          # ESP32-CAM Arduino firmware
├── backend/
│   ├── main.py                # FastAPI server
│   ├── model.py               # PyTorch inference + training
│   ├── requirements.txt       # Python dependencies
│   └── uploads/               # Saved plant images (auto-created)
├── frontend/
│   ├── index.html             # Dashboard UI
│   ├── style.css              # Premium dark-mode styles
│   └── app.js                 # Frontend logic
└── README.md                  # This file
```

---

## ⚙️ System Architecture

```
ESP32-CAM ──WiFi──► FastAPI Backend ──► PyTorch Model
                         │                    │
                         ▼                    ▼
                    Save Image         Predict Disease
                         │                    │
                         ▼                    ▼
                   Web Dashboard ◄──── JSON Response
                   (shows results)    {disease, confidence, solution}
```

---

## 🚀 Quick Start (Step-by-Step)

### Step 1: Set Up the Backend

```bash
# Navigate to backend
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

The API will be running at: **http://localhost:8000**

Test it: Open http://localhost:8000 in your browser — you should see the health check JSON.

### Step 2: Open the Frontend Dashboard

Open `frontend/index.html` in your browser, or serve it:

```bash
# From project root
cd frontend
python3 -m http.server 3000
```

Then open: **http://localhost:3000**

The dashboard will auto-connect to the backend at port 8000.

### Step 3: Test with an Image (No ESP32 Required)

1. Open the dashboard in your browser
2. Drag & drop any plant leaf image into the upload zone
3. Click **"Analyze Plant"**
4. See the disease prediction, confidence, and treatment

### Step 4: Flash the ESP32-CAM (Hardware)

1. Open `esp32_cam/esp32_cam.ino` in **Arduino IDE**
2. Install the **ESP32** board package:
   - Go to `File → Preferences`
   - Add to Board Manager URLs: `https://dl.espressif.com/dl/package_esp32_index.json`
   - Go to `Tools → Board → Board Manager` → Search "ESP32" → Install
3. Select board: **AI Thinker ESP32-CAM**
4. **Edit the code** — update these lines:
   ```cpp
   const char* ssid     = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   const char* serverUrl = "http://YOUR_PC_IP:8000/predict";
   ```
   Replace `YOUR_PC_IP` with your computer's local IP (e.g., `192.168.1.100`).
   
   Find your IP:
   ```bash
   # macOS
   ipconfig getifaddr en0
   
   # Linux
   hostname -I
   
   # Windows
   ipconfig
   ```
5. Connect ESP32-CAM via FTDI programmer
6. Upload the sketch
7. Open Serial Monitor (115200 baud) to see logs

---

## 🧠 Training Your Own Model (Optional)

### Download the Dataset

1. Go to [PlantVillage Dataset on Kaggle](https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset)
2. Download and extract into a `dataset/` folder:
   ```
   dataset/
   ├── train/
   │   ├── Apple___Apple_scab/
   │   ├── Apple___Black_rot/
   │   └── ...
   └── val/
       ├── Apple___Apple_scab/
       └── ...
   ```
3. Split the data into `train/` and `val/` folders (80/20 split).

### Train the Model

```python
# In backend/
python -c "from model import train_model; train_model('path/to/dataset', epochs=10)"
```

This will save `plant_disease_model.pth` in the backend folder. The server will automatically load it on next startup.

---

## 🔌 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check |
| `/predict` | POST | Upload image, get disease prediction |
| `/history` | GET | Get all prediction history |
| `/uploads/{filename}` | GET | Serve uploaded images |

### POST /predict

**Request:** `multipart/form-data` with field `file` (image)

**Response:**
```json
{
    "disease": "Tomato - Late blight",
    "confidence": 0.9432,
    "solution": "Apply fungicide immediately. Remove and destroy infected plants.",
    "image_file": "20260417_120000_abc123.jpg",
    "timestamp": "2026-04-17T12:00:00.000000"
}
```

---

## 🌿 Supported Diseases (38 Classes)

| Plant | Diseases |
|---|---|
| 🍎 Apple | Scab, Black Rot, Cedar Rust, Healthy |
| 🫐 Blueberry | Healthy |
| 🍒 Cherry | Powdery Mildew, Healthy |
| 🌽 Corn | Cercospora, Common Rust, Northern Blight, Healthy |
| 🍇 Grape | Black Rot, Esca, Leaf Blight, Healthy |
| 🍊 Orange | Citrus Greening |
| 🍑 Peach | Bacterial Spot, Healthy |
| 🌶️ Pepper | Bacterial Spot, Healthy |
| 🥔 Potato | Early Blight, Late Blight, Healthy |
| 🫐 Raspberry | Healthy |
| 🫘 Soybean | Healthy |
| 🎃 Squash | Powdery Mildew |
| 🍓 Strawberry | Leaf Scorch, Healthy |
| 🍅 Tomato | Bacterial Spot, Early/Late Blight, Leaf Mold, Septoria, Spider Mites, Target Spot, YLCV, Mosaic Virus, Healthy |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Microcontroller | ESP32-CAM (AI-Thinker) |
| Firmware | Arduino (C++) |
| Backend | Python, FastAPI, Uvicorn |
| AI Model | PyTorch, ResNet18, torchvision |
| Frontend | HTML, CSS, JavaScript |
| Communication | HTTP REST, WiFi |

---

## ⚠️ Troubleshooting

| Issue | Solution |
|---|---|
| ESP32 can't connect to WiFi | Double-check SSID & password. Ensure 2.4GHz network. |
| Camera init failed | Check pin definitions match your board (AI-Thinker). |
| HTTP POST fails | Verify server IP. Ensure both devices on same network. Firewall? |
| Model predictions seem random | Expected without trained weights. Train on PlantVillage dataset. |
| Upload too slow | Reduce camera resolution to QVGA in firmware. |

---

## 📄 License

MIT — Built for Hackathon 2026 🚀
