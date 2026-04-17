# Neural Crop: Agentic AI for Plant Disease Detection 🌱🤖

Welcome to **Neural Crop**! This project is an advanced IoT and AI system designed to help farmers detect and prevent crop diseases. Instead of just using a camera (which can be easily tricked by poor lighting), this system acts like a "smart agricultural agent" by combining **Visual AI** (Camera) with **Ground Sensors** (Temperature, Humidity, Soil Moisture).

This guide is written so that **anyone**, even without a deep technical background, can set it up successfully.

---

## 🛠️ What You Need (Requirements)

### 1. Hardware Components
*   **ESP32-CAM Module** (Acts as the "Eyes" - captures photos of the plant leaves).
*   **ESP32 DevKit Board** (Acts as the "Hands" - collects data from the environment).
*   **DHT11 Sensor** (Measures temperature and humidity).
*   **Analog Soil Moisture Sensor** (Measures the water content in the soil).
*   **Jumper wires and Breadboards** (To connect everything together).

### 2. Software Requirements
*   A Laptop or PC running Windows, Mac, or Linux.
*   **Python 3.8+** (For the AI and Web Server).
*   **Arduino IDE** (To program the ESP32 microcontrollers).

---

## 🔌 Hardware Setup (The Wiring Guide)

Even a beginner can wire this up. Grab your jumper cables and follow these connections:

**1. Connecting the DHT11 Sensor (Temperature & Humidity)**
*   **VCC** (or +) pins ➜ Connect to **3v3** pin on the ESP32.
*   **GND** (or -) pins ➜ Connect to a **GND** pin on the ESP32.
*   **Data** (or Out) pin ➜ Connect to **GPIO 4** on the ESP32.

**2. Connecting the Soil Moisture Sensor**
*   **VCC** ➜ Connect to **3v3** pin on the ESP32.
*   **GND** ➜ Connect to a **GND** pin on the ESP32.
*   **Analog Out (A0)** ➜ Connect to **GPIO 34** on the ESP32.

**3. The ESP32-CAM**
*   This module doesn't need external sensors! Just supply it with 5V power and GND via the respective pins to turn it on.

---

## 🚀 Step-by-Step Installation Guide

### Step 1: Set up the Python Server (The "Brain")
This server runs the AI models and hosts the beautiful web dashboard.

1.  **Install Python:** Download and install Python from `python.org`. *Make sure to check the box "Add Python to PATH" during installation!*
2.  **Open a Terminal / Command Prompt** and navigate to this project folder.
3.  **Install the required libraries:** Run the following command exactly as shown:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Start the Server:** Turn on the AI brain by running:
    ```bash
    python server/app.py
    ```
5.  **View the Dashboard:** Open your web browser (Chrome/Edge) and go to: `http://localhost:5000` (or the IP address printed in your terminal).

---

### Step 2: Set up the ESP32 Hardware (The "Senses")
You need to put the code onto the microcontrollers so they can talk to the server.

1.  **Install Arduino IDE:** Download from `arduino.cc`.
2.  **Add ESP32 Board Support:**
    *   Go to `File` > `Preferences` in Arduino IDE.
    *   Paste this URL into the "Additional Boards Manager URLs" box: `https://dl.espressif.com/dl/package_esp32_index.json`
    *   Go to `Tools` > `Board` > `Boards Manager`, search for "esp32", and click Install.
3.  **Update WiFi & Server Settings:**
    *   Open `esp32/main/main.ino` (For the Camera) and `esp32/sensor_node/sensor_node.ino` (For the Sensors) in the Arduino IDE.
    *   At the top of both files, change **`ssid`** and **`password`** to match your WiFi network.
    *   Change the **`serverName`** (or server IP) to the IP address of the laptop running the Python server (e.g., `192.168.1.5`).
4.  **Upload the Code:**
    *   Plug in your ESP32 boards via USB.
    *   Select the correct Board and Port in the `Tools` menu.
    *   Click the **Upload** button (the right-pointing arrow).

---

## 📊 Dataset & AI Model Info

If you want to train your own models or understand where the data came from:
*   **The Vision Dataset:** The core CNN model was trained using the famous [PlantVillage Dataset](https://www.kaggle.com/datasets/emmarex/plantdisease). We specifically isolated 10 tomato-related classes and used Transfer Learning (MobileNetV2) to heavily fine-tune it for field-captured edge AI imagery.
*   **The Environmental Dataset:** The `tomato.csv` matrix used by our GradientBoosting Predictive Forecast model was custom-built using standard agricultural biology thresholds for fungal/viral spore incubation.

---

## 🎮 How to Use the System

Once the Python server is running and both ESP32 boards are powered on:

1.  **Watch the Dashboard:** Open the dashboard in your browser. You will see 4 distinct numbered sections.
2.  **Live Telemetry:** Section ① will immediately start showing real-time temperature, humidity, and soil moisture from your physical sensors.
3.  **Predictive Forecast:** Section ③ will tell you if the current environment is becoming a breeding ground for fungal diseases. (Try blowing warm, humid breath on the DHT11 sensor to see it trigger an alarm!)
4.  **Disease Detection:** Point the ESP32-CAM at a tomato leaf. It will automatically take a photo every few seconds, send it to the AI, and display the result in Section ②. 
5.  **Intelligence Report:** Section ④ will give you a detailed report on how to cure the disease if one is found.

---

## 🧠 How the AI Works (For Dummies)
Most agricultural IoT systems fail because standard cameras get confused by bright sunlight or blurry lenses, falsely identifying diseases where none exist.

Our system uses an **Agentic Sensor Override Mechanism**:
*   The Camera looks at the leaf and makes a "guess" using a Deep Learning Convolutional Neural Network (CNN).
*   At the exact same time, the Ground Sensors check the physical environment using a Machine Learning algorithm (Gradient Boosting).
*   **The Magic:** If the camera thinks it sees a disease, but the ground sensors prove that the temperature and humidity make that disease *impossible* to exist, the system overrides the camera and declares the plant "Healthy". It acts like a human detective cross-referencing clues!
