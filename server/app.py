from flask import Flask, render_template,request,redirect,send_from_directory,url_for
import numpy as np
import json
import uuid
import joblib
import pandas as pd
import tensorflow as tf
from datetime import datetime
import os
import sys

# Set absolute path for root directory to resolve paths properly from the /server folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import extracted logic
import server.sensor_fusion as sensor_fusion
import server.notifier as notifier

# Global state for IoT dashboard
latest_iot_data = {
    "has_data": False,
    "imagepath": "",
    "temperature": "--",
    "humidity": "--",
    "soil_moisture": "--",
    "prediction": {},
    "fused_alert_message": "",
    "fused_alert_type": "info",
    "timestamp": ""
}

# Latest sensor readings from the ESP32 DevKit sensor node
# Updated independently by /api/update_sensors
# None = DevKit not yet connected (no fake data shown)
latest_sensor_readings = {
    "temperature": None,
    "humidity": None,
    "soil_moisture": None,
    "timestamp": None
}

# The disease currently identified by the CNN (from the last camera capture)
# Used to lock thresholds — when you show a new leaf, this changes instantly
active_disease = None

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'dashboard'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# Ensure upload directory exists so camera uploads don't crash the server
os.makedirs(os.path.join(BASE_DIR, 'uploadimages'), exist_ok=True)

model_path = os.path.join(BASE_DIR, "model", "plant_disease_recog_model_pwp.keras")
model = tf.keras.models.load_model(model_path)

# Load sensor-based disease prediction model (GradientBoosting)
sensor_model_path = os.path.join(BASE_DIR, "model", "sensor_disease_model.joblib")
sensor_model = joblib.load(sensor_model_path)
treatment_map_path = os.path.join(BASE_DIR, "model", "treatment_map.json")
with open(treatment_map_path, 'r') as f:
    treatment_map = json.load(f)
danger_path = os.path.join(BASE_DIR, "model", "danger_thresholds.json")
with open(danger_path, 'r') as f:
    danger_thresholds = json.load(f)
disease_kb_path = os.path.join(BASE_DIR, "model", "disease_knowledge.json")
with open(disease_kb_path, 'r', encoding='utf-8') as f:
    disease_knowledge = json.load(f)
print("[+] Sensor disease model + knowledge base loaded")

def predict_from_sensors(temp, hum, soil):
    """Predict disease from sensor readings + generate warnings for ALL sensors."""
    if temp is None or hum is None or soil is None:
        return None
    try:
        temp = float(temp)
        hum = float(hum)
        soil = float(soil)
        input_df = pd.DataFrame([[temp, hum, soil]], columns=["Temp", "Humidity", "Soil"])
        pred = str(sensor_model.predict(input_df)[0])
        proba = sensor_model.predict_proba(input_df)[0]
        confidence = float(round(max(proba) * 100, 1))
        treatment = treatment_map.get(pred, "Consult agronomist")
        
        # Get danger thresholds for this disease
        thresholds = danger_thresholds.get(pred, {"temp": 99, "hum": 99, "soil": 99})
        d_temp = thresholds["temp"]
        d_hum  = thresholds["hum"]
        d_soil = thresholds["soil"]
        
        # Build warnings for each sensor that crosses threshold
        warnings = []
        if pred != "Healthy":
            # Temperature check
            if temp >= d_temp:
                warnings.append(f"Temperature ({temp:.1f}C) CROSSED danger threshold ({d_temp}C)")
            elif temp >= d_temp - 5:
                warnings.append(f"Temperature ({temp:.1f}C) approaching danger zone ({d_temp}C)")
            
            # Humidity check
            if pred == "Spider_Mites":
                # Spider mites thrive in LOW humidity
                if hum <= d_hum:
                    warnings.append(f"Humidity ({hum:.1f}%) DANGEROUSLY LOW (threshold: {d_hum}%)")
            else:
                if hum >= d_hum:
                    warnings.append(f"Humidity ({hum:.1f}%) CROSSED danger threshold ({d_hum}%)")
                elif hum >= d_hum - 10:
                    warnings.append(f"Humidity ({hum:.1f}%) approaching danger zone ({d_hum}%)")
            
            # Soil moisture check
            if pred == "Spider_Mites":
                # Spider mites thrive in DRY soil
                if soil <= d_soil:
                    warnings.append(f"Soil moisture ({soil:.1f}%) CRITICALLY LOW (threshold: {d_soil}%)")
            else:
                if soil >= d_soil:
                    warnings.append(f"Soil moisture ({soil:.1f}%) CROSSED danger threshold ({d_soil}%)")
        
        # Combine warnings
        warning = None
        warning_level = "ok"
        if warnings:
            is_critical = any("CROSSED" in w or "CRITICALLY" in w or "DANGEROUSLY" in w for w in warnings)
            warning_level = "critical" if is_critical else "warning"
            prefix = "CRITICAL" if is_critical else "WARNING"
            warning = f"{prefix} for {pred.replace('_', ' ')}: " + " | ".join(warnings) + f". Treatment: {treatment}"
        
        # Get disease knowledge
        info = disease_knowledge.get(pred, {})
        
        return {
            "disease": pred,
            "confidence": confidence,
            "treatment": treatment,
            "warning": warning,
            "warning_level": warning_level,
            "danger_temp": d_temp,
            "danger_hum": d_hum,
            "danger_soil": d_soil,
            "severity": info.get("severity", "Unknown"),
            "risks": info.get("risks", []),
            "remedies": info.get("remedies", []),
            "ideal_conditions": info.get("ideal_conditions", ""),
            "trigger_conditions": info.get("trigger_conditions", "")
        }
    except:
        return None

# -------- Load Disease Labels & Map --------
json_path = os.path.join(BASE_DIR, "model", "class_labels.json")
with open(json_path, 'r') as file:
    # 38 classes array
    plant_disease_map = json.load(file)
    plant_disease = {i: item["name"] for i, item in enumerate(plant_disease_map)}

# Define explicit map to safely convert original Tomato 38-class strings 
# into our new highly-accurate IoT edge boundaries
TOMATO_CLASS_MAPPING = {
    "Tomato___Bacterial_spot": "Bacterial_Spot",
    "Tomato___Early_blight": "Early_Blight",
    "Tomato___Late_blight": "Late_Blight",
    "Tomato___Leaf_Mold": "Leaf_Mold",
    "Tomato___Septoria_leaf_spot": "Septoria_Leaf_Spot",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Spider_Mites",
    "Tomato___Target_Spot": "Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus": "Mosaic_Virus",
    "Tomato___healthy": "Healthy",
    "Background_without_leaves": "No_Plant_Detected"
}

# Separate indices: Tomato-only (for leaf classification) and Background (for no-plant detection)
tomato_only_indices = [idx for idx, label in plant_disease.items() if "Tomato" in label]
background_idx = [idx for idx, label in plant_disease.items() if "Background" in label]

# print(plant_disease[4])

@app.route('/uploadimages/<path:filename>')
def uploaded_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'uploadimages'), filename)

@app.route('/',methods = ['GET'])
def home():
    global latest_iot_data
    return render_template('index.html', iot_data=latest_iot_data)

def extract_features(image):
    """Load image, center-crop to remove bezels/background, then resize for CNN."""
    from PIL import Image
    pil_img = Image.open(image)
    w, h = pil_img.size
    
    # Center-crop: remove outer 25% on each side so the leaf fills the frame
    crop_pct = 0.25
    left   = int(w * crop_pct)
    top    = int(h * crop_pct)
    right  = int(w * (1 - crop_pct))
    bottom = int(h * (1 - crop_pct))
    pil_img = pil_img.crop((left, top, right, bottom))
    
    # Resize to model input size
    pil_img = pil_img.resize((160, 160))
    feature = tf.keras.utils.img_to_array(pil_img)
    feature = np.array([feature])
    return feature

def model_predict(image):
    img = extract_features(image)
    prediction_probs = model.predict(img)[0]
    
    # Step 1: Check if overall top prediction is Background
    overall_top = int(prediction_probs.argmax())
    if overall_top in background_idx and prediction_probs[overall_top] > 0.5:
        return {"name": "No_Plant_Detected", "confidence": float(round(prediction_probs[overall_top] * 100, 1))}
    
    # Step 2: Among Tomato-only classes, pick the highest — pure CNN, no sensor tricks
    max_tomato_prob = -1.0
    best_tomato_idx = tomato_only_indices[0]
    
    for idx in tomato_only_indices:
        if prediction_probs[idx] > max_tomato_prob:
            max_tomato_prob = prediction_probs[idx]
            best_tomato_idx = idx

    predicted_label_raw = plant_disease[best_tomato_idx]
    predicted_label = TOMATO_CLASS_MAPPING.get(predicted_label_raw, "Healthy")
    confidence = float(round(max_tomato_prob * 100, 1))
    
    return {"name": predicted_label, "confidence": confidence}

@app.route('/upload/',methods = ['POST','GET'])
def uploadimage():
    if request.method == "POST":
        image = request.files['img']
        temp_name = f"uploadimages/temp_{uuid.uuid4().hex}"
        save_path = os.path.join(BASE_DIR, f"{temp_name}_{image.filename}")
        image.save(save_path)
        print(save_path)
        prediction = model_predict(save_path)
        image_route = f"/{temp_name}_{image.filename}"
        
        # Use LIVE sensor readings from DevKit for sensor fusion
        # If DevKit is connected: real values. If not: neutral defaults.
        temp = latest_sensor_readings["temperature"] if latest_sensor_readings["temperature"] is not None else 25
        hum  = latest_sensor_readings["humidity"]    if latest_sensor_readings["humidity"] is not None else 60
        soil = latest_sensor_readings["soil_moisture"] if latest_sensor_readings["soil_moisture"] is not None else 50
        
        plant_profile = sensor_fusion.get_plant_profile(prediction['name'], temp, hum, soil)
        alert_msg, alert_type = sensor_fusion.generate_fused_alert(prediction['name'], temp, hum, soil)
        
        # Sensor-based disease prediction
        sensor_prediction = predict_from_sensors(temp, hum, soil)
        
        # Since the new CNN model shares the exact labels from tomato.csv/sensor model
        # We can directly pass the name without complex mapping
        mapped_disease = prediction['name']
        
        # Get disease knowledge + check thresholds
        disease_info = None
        cnn_warnings = []
        if mapped_disease and mapped_disease in disease_knowledge:
            info = disease_knowledge[mapped_disease]
            thresholds = danger_thresholds.get(mapped_disease, {"temp": 99, "hum": 99, "soil": 99})
            
            if mapped_disease != "Healthy":
                if mapped_disease == "Spider_Mites":
                    if temp >= thresholds["temp"]: cnn_warnings.append(f"Temp ({temp}C) exceeds {thresholds['temp']}C")
                    if hum <= thresholds["hum"]: cnn_warnings.append(f"Humidity ({hum}%) dangerously low")
                    if soil <= thresholds["soil"]: cnn_warnings.append(f"Soil ({soil}%) critically dry")
                else:
                    if temp >= thresholds["temp"]: cnn_warnings.append(f"Temp ({temp}C) exceeds {thresholds['temp']}C")
                    if hum >= thresholds["hum"]: cnn_warnings.append(f"Humidity ({hum}%) exceeds {thresholds['hum']}%")
                    if soil >= thresholds["soil"]: cnn_warnings.append(f"Soil ({soil}%) exceeds {thresholds['soil']}%")
            
            disease_info = {
                "severity": info.get("severity"), "risks": info.get("risks", []),
                "remedies": info.get("remedies", []), "treatment": treatment_map.get(mapped_disease, ""),
                "ideal_conditions": info.get("ideal_conditions", ""),
                "trigger_conditions": info.get("trigger_conditions", ""),
                "thresholds": thresholds, "warnings": cnn_warnings,
                "is_critical": len(cnn_warnings) > 0
            }
        
        return render_template('index.html', result=True, imagepath=image_route,
                               prediction=prediction, plant_profile=plant_profile,
                               alert_message=alert_msg, alert_type=alert_type,
                               live_temp=temp, live_hum=hum, live_soil=soil,
                               sensor_prediction=sensor_prediction,
                               disease_info=disease_info,
                               iot_data=latest_iot_data)
    
    else:
        return redirect('/')

# generate_fused_alert extracted to sensor_fusion.py

@app.route('/api/upload_sensor', methods=['POST'])
def api_upload_sensor():
    global latest_iot_data
    if 'img' not in request.files:
        return {"error": "No image uploaded from IoT device."}, 400
        
    image = request.files['img']
    
    # Use REAL sensor readings from the DevKit if available (posted separately)
    # Falls back to values sent by the CAM (dummy values) if DevKit not connected
    temp = latest_sensor_readings["temperature"]
    hum  = latest_sensor_readings["humidity"]
    soil = latest_sensor_readings["soil_moisture"]
    
    temp_name = f"uploadimages/iot_{uuid.uuid4().hex}"
    save_path = os.path.join(BASE_DIR, f"{temp_name}_{image.filename}")
    image.save(save_path)
    
    prediction = model_predict(save_path)
    
    alert_msg, alert_type = sensor_fusion.generate_fused_alert(prediction['name'], temp, hum, soil)
    plant_profile = sensor_fusion.get_plant_profile(prediction['name'], temp, hum, soil)
    
    # Trigger notification if danger
    if alert_type == "danger" or alert_type == "warning":
        context = f"Temp: {temp}C | Hum: {hum}% | Soil: {soil}%"
        notifier.send_alert(prediction['name'], alert_msg, context)
    
    # Sensor-based disease prediction
    sensor_pred = predict_from_sensors(temp, hum, soil)
    
    # Lock thresholds to the newly identified CNN disease
    global active_disease
    active_disease = prediction['name']
    print(f"[CNN] Detected: {prediction['name']} -> Active disease: {active_disease}")
    
    latest_iot_data = {
        "has_data": True,
        "imagepath": f"/{temp_name}_{image.filename}",
        "temperature": temp,
        "humidity": hum,
        "soil_moisture": soil,
        "prediction": prediction,
        "sensor_prediction": sensor_pred,
        "plant_profile": plant_profile,
        "disease_info": disease_knowledge.get(prediction['name'], {}),
        "fused_alert_message": alert_msg,
        "fused_alert_type": alert_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return {"status": "success", "message": "Data received and analyzed.", "alert": alert_msg}

@app.route('/api/latest_sensor_data', methods=['GET'])
def get_latest_sensor_data():
    global latest_iot_data
    return latest_iot_data

@app.route('/api/update_sensors', methods=['POST'])
def update_sensors():
    """Receives live sensor data from the ESP32 DevKit sensor node."""
    global latest_sensor_readings
    try:
        temp = float(request.form.get('temperature', 25.0))
        hum  = float(request.form.get('humidity', 60.0))
        soil = float(request.form.get('soil_moisture', 50.0))
        latest_sensor_readings = {
            "temperature": temp,
            "humidity": hum,
            "soil_moisture": soil,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        print(f"[SensorNode] Temp: {temp}C | Hum: {hum}% | Soil: {soil}%")
        return {"status": "ok", "received": latest_sensor_readings}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400

@app.route('/api/live_sensors', methods=['GET'])
def live_sensors():
    """Fast-polling: sensor readings + sensor model prediction + CNN-locked thresholds."""
    result = dict(latest_sensor_readings)
    
    # Sensor model prediction (independent)
    result["sensor_prediction"] = predict_from_sensors(
        latest_sensor_readings["temperature"],
        latest_sensor_readings["humidity"],
        latest_sensor_readings["soil_moisture"]
    )
    
    # CNN-locked disease thresholds (set when camera captures a leaf)
    result["active_disease"] = active_disease
    if active_disease and active_disease in danger_thresholds:
        thresholds = danger_thresholds[active_disease]
        info = disease_knowledge.get(active_disease, {})
        temp = latest_sensor_readings["temperature"]
        hum = latest_sensor_readings["humidity"]
        soil = latest_sensor_readings["soil_moisture"]
        
        # Check current sensors against the CNN-identified disease
        cnn_warnings = []
        if temp is not None:
            if active_disease != "Healthy":
                if active_disease == "Spider_Mites":
                    if temp >= thresholds["temp"]:
                        cnn_warnings.append(f"Temp ({temp:.1f}C) exceeds {thresholds['temp']}C")
                    if hum is not None and hum <= thresholds["hum"]:
                        cnn_warnings.append(f"Humidity ({hum:.1f}%) dangerously low (<{thresholds['hum']}%)")
                    if soil is not None and soil <= thresholds["soil"]:
                        cnn_warnings.append(f"Soil ({soil:.1f}%) critically dry (<{thresholds['soil']}%)")
                else:
                    if temp >= thresholds["temp"]:
                        cnn_warnings.append(f"Temp ({temp:.1f}C) exceeds {thresholds['temp']}C")
                    if hum is not None and hum >= thresholds["hum"]:
                        cnn_warnings.append(f"Humidity ({hum:.1f}%) exceeds {thresholds['hum']}%")
                    if soil is not None and soil >= thresholds["soil"]:
                        cnn_warnings.append(f"Soil ({soil:.1f}%) exceeds {thresholds['soil']}%")
            
            elif active_disease == "Healthy":
                # Predictive Risk Scanning against all known diseases
                for potential_disease, limits in danger_thresholds.items():
                    if potential_disease == "Healthy": continue
                    
                    risk_factors = []
                    if potential_disease == "Spider_Mites":
                        if temp >= limits["temp"]: risk_factors.append("High Temp")
                        if hum is not None and hum <= limits["hum"]: risk_factors.append("Low Humidity")
                        if soil is not None and soil <= limits["soil"]: risk_factors.append("Dry Soil")
                    else:
                        if temp >= limits["temp"]: risk_factors.append("High Temp")
                        if hum is not None and hum >= limits["hum"]: risk_factors.append("High Humidity")
                        if soil is not None and soil >= limits["soil"]: risk_factors.append("Saturated Soil")
                    
                    # If the environment ticks multiple danger boxes for a disease, flag it
                    if len(risk_factors) >= 2:
                        cnn_warnings.append(f"High risk of {potential_disease.replace('_', ' ')} due to {', '.join(risk_factors)}")
        
        result["cnn_disease"] = {
            "name": active_disease.replace("_", " "),
            "thresholds": thresholds,
            "severity": info.get("severity", "Unknown"),
            "risks": info.get("risks", []),
            "remedies": info.get("remedies", []),
            "treatment": treatment_map.get(active_disease, ""),
            "ideal_conditions": info.get("ideal_conditions", ""),
            "trigger_conditions": info.get("trigger_conditions", ""),
            "warnings": cnn_warnings,
            "is_critical": len(cnn_warnings) > 0
        }
    
    return result

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)