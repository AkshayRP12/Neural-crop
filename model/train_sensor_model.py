"""
Tomato Disease Prediction Model — Sensor-Based (New Dataset)
Trained directly from the ranges provided in tomato.csv
"""
import pandas as pd
import numpy as np
import random
import joblib
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, accuracy_score

random.seed(42)
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Load the new tomato.csv
tomato_csv_path = os.path.join(BASE_DIR, "model", "tomato.csv")
df_tomato = pd.read_csv(tomato_csv_path)

data = []
danger_map = {}
disease_knowledge = {}

# Define logic for danger thresholds and generate synthetic data for the model
# For most diseases, upper bounds are the trigger.
# For Spider Mites, lower humidity/soil are triggers.
for _, row in df_tomato.iterrows():
    disease = row['Disease'].replace(" ", "_")
    
    t_min = float(row['Temperature_Min(°C)'])
    t_max = float(row['Temperature_Max(°C)'])
    h_min = float(row['Humidity_Min(%)'])
    h_max = float(row['Humidity_Max(%)'])
    s_min = float(row['Soil_Moisture_Min(%)'])
    s_max = float(row['Soil_Moisture_Max(%)'])
    
    # Calculate danger thresholds based on bounds
    if disease == "Spider_Mites":
        d_temp = t_max - 2  # Danger if it gets this hot
        d_hum = h_max - 10   # Danger if it gets this dry
        d_soil = s_max - 5  # Danger if it gets this dry
    elif disease == "Healthy":
        d_temp = 99
        d_hum = 99
        d_soil = 99
    else:
        d_temp = t_min + (t_max - t_min) * 0.7  # getting close to high
        d_hum = h_min + (h_max - h_min) * 0.7   # getting close to high
        d_soil = s_min + (s_max - s_min) * 0.7  # getting close to high
        
    danger_map[disease] = {
        "temp": round(d_temp, 1),
        "hum": round(d_hum, 1),
        "soil": round(d_soil, 1)
    }

    # Generate synthetic samples within these boundaries
    for _ in range(500):
        # We use a uniform distribution inside the min/max so model learns the exact boundaries
        temp = round(random.uniform(t_min, t_max), 2)
        hum  = round(random.uniform(h_min, h_max), 2)
        soil = round(random.uniform(s_min, s_max), 2)
        data.append([temp, hum, soil, disease])

# Create DataFrame
df = pd.DataFrame(data, columns=["Temp", "Humidity", "Soil", "Disease"])

# Save generated dataset
csv_path = os.path.join(BASE_DIR, "model", "plant_disease_dataset_new.csv")
df.to_csv(csv_path, index=False)
print(f"[+] Dataset generated: {len(df)} samples across {df['Disease'].nunique()} classes")

# Features & Labels
X = df[["Temp", "Humidity", "Soil"]]
y = df["Disease"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Train GradientBoosting
model = GradientBoostingClassifier(
    n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"\n[+] MODEL ACCURACY: {accuracy * 100:.1f}%")
# print(f"\n{classification_report(y_test, y_pred)}")

# Save the model
model_path = os.path.join(BASE_DIR, "model", "sensor_disease_model.joblib")
joblib.dump(model, model_path)
print(f"[+] Model saved: {model_path}")

danger_path = os.path.join(BASE_DIR, "model", "danger_thresholds.json")
with open(danger_path, "w") as f:
    json.dump(danger_map, f, indent=2)
print(f"[+] Danger thresholds saved: {danger_path}")

