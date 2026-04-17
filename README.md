# 🌱 Neural Crop
### Agentic AI for Plant Disease Detection

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-CNN-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![PyTorch](https://img.shields.io/badge/YOLOv8-PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![ESP32](https://img.shields.io/badge/ESP32-IoT-E7352C?style=for-the-badge&logo=espressif&logoColor=white)

> A smart IoT + AI system that watches over your tomato crops — combining a live camera feed with ground sensors to detect disease before it spreads.

Most plant disease apps just look at a photo. Neural Crop goes further: it cross-references what it *sees* (the leaf) with what it *feels* (temperature, humidity, soil moisture) to make smarter, more reliable predictions — just like an experienced agronomist would.

---

## How It Works (The Big Picture)

```
[ESP32-CAM] ──── photo ────┐
                            ├──► [Python AI Server] ──► [Web Dashboard]
[ESP32 + Sensors] ─ data ──┘         (your laptop)         (browser)
```

Two ESP32 boards send data to a Python server running on your laptop. The server runs the AI models and displays everything on a clean web dashboard you open in your browser. That's it.

---

## What You'll Need

### Hardware
| Component | Purpose |
|---|---|
| ESP32-CAM Module | Eyes — captures leaf photos |
| ESP32 DevKit Board | Hands — reads the environment |
| DHT11 Sensor | Measures temperature & humidity |
| Soil Moisture Sensor (Analog) | Measures soil water content |
| Jumper wires + Breadboard | Connects everything |

### Software
- Python 3.8+ (on your laptop/PC)
- Arduino IDE (to flash the ESP32 boards)
- A modern browser (Chrome or Edge)

---

## Part 1 — Wiring the Hardware

No soldering needed. Just jumper wires.

### DHT11 → ESP32 DevKit
```
DHT11 VCC  →  ESP32 3V3
DHT11 GND  →  ESP32 GND
DHT11 Data →  ESP32 GPIO 4
```

### Soil Moisture Sensor → ESP32 DevKit
```
Sensor VCC  →  ESP32 3V3
Sensor GND  →  ESP32 GND
Sensor A0   →  ESP32 GPIO 34
```

### ESP32-CAM
Just power it: connect **5V** and **GND**. It has no extra sensors.

---

## Part 2 — Setting Up the Python Server

This is the brain. Run it on your laptop and leave it on while using the system.

**1. Install Python** from [python.org](https://python.org).
> ⚠️ On Windows, check **"Add Python to PATH"** during install or nothing will work.

**2. Open a terminal** and go to the project folder:
```bash
cd path/to/neural-crop
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Start the server:**
```bash
python server/app.py
```

**5. Open the dashboard:**
Go to `http://localhost:5000` in your browser. If you see the dashboard, you're good to go.

> 💡 Note the IP address printed in your terminal (e.g., `192.168.1.5`). You'll need it for the ESP32 setup below.

---

## Part 3 — Flashing the ESP32 Boards

**1. Install Arduino IDE** from [arduino.cc](https://arduino.cc).

**2. Add ESP32 board support:**
- Open Arduino IDE → `File` → `Preferences`
- Paste this into "Additional Boards Manager URLs":
  ```
  https://dl.espressif.com/dl/package_esp32_index.json
  ```
- Go to `Tools` → `Board` → `Boards Manager`, search **esp32**, and click Install.

**3. Configure WiFi & server IP:**

Open both files below and update the top lines:
- `esp32/main/main.ino` ← for the Camera board
- `esp32/sensor_node/sensor_node.ino` ← for the Sensor board

```cpp
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverName = "192.168.1.5"; // ← your laptop's IP
```

**4. Upload to each board:**
- Plug in an ESP32 via USB
- In Arduino IDE: `Tools` → select the correct **Board** and **Port**
- Click the **Upload** button (→)
- Repeat for the second board

---

## Using the Dashboard

Once everything is running, open `http://localhost:5000` in your browser. You'll see 4 sections:

| Section | What It Shows |
|---|---|
| ① Live Telemetry | Real-time temperature, humidity, soil moisture |
| ② Disease Detection | AI result from the camera feed (updates every few seconds) |
| ③ Predictive Forecast | Warns if environmental conditions are becoming risky |
| ④ Intelligence Report | Cure/treatment advice if a disease is detected |

> **Quick test:** Breathe warm air on the DHT11 sensor. You should see Section ③ trigger a fungal risk warning within seconds.

---

## AI Models & Dataset

- **Vision model:** MobileNetV2 fine-tuned on the [PlantVillage Dataset](https://www.kaggle.com/datasets/emmarex/plantdisease), specifically trained on 10 tomato disease classes for field conditions.
- **Environmental model:** Gradient Boosting classifier trained on a custom `tomato.csv` dataset built from established agricultural thresholds for fungal and viral spore incubation.

---

## Troubleshooting

**Dashboard doesn't load?**
Make sure `python server/app.py` is still running. Check that you're visiting the right IP/port.

**ESP32 not connecting?**
Double-check the WiFi credentials and that `serverName` in the `.ino` file matches your laptop's IP (not `localhost`).

**Sensor readings look wrong?**
Verify wiring — especially that VCC is on **3V3**, not 5V. The DHT11 and soil sensor are 3.3V components.

**Upload fails in Arduino IDE?**
Make sure the correct **Board** and **Port** are selected under the `Tools` menu before uploading.

---

## Project Structure

```
neural-crop/
├── server/
│   └── app.py              # Flask server + AI inference
├── esp32/
│   ├── main/
│   │   └── main.ino        # ESP32-CAM firmware
│   └── sensor_node/
│       └── sensor_node.ino # Sensor node firmware
├── models/                 # Trained model files
├── data/
│   └── tomato.csv          # Environmental training data
└── requirements.txt
```

---

## License

MIT — free to use, modify, and build upon.
