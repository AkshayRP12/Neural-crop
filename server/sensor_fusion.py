import json
import os

# Load plant knowledge base once at import time
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KNOWLEDGE_PATH = os.path.join(_BASE_DIR, "model", "plant_knowledge.json")
try:
    with open(_KNOWLEDGE_PATH, "r") as f:
        PLANT_KNOWLEDGE = json.load(f)
except Exception as e:
    print(f"[SensorFusion] Warning: Could not load plant_knowledge.json: {e}")
    PLANT_KNOWLEDGE = {}


def get_plant_name(prediction_name):
    """Extract the plant genus from a prediction label like 'Tomato___Early_blight'."""
    if "___" in prediction_name:
        return prediction_name.split("___")[0].replace(",_bell", "").replace("_", " ").strip()
    return prediction_name


def get_plant_profile(prediction_name, temp, hum, soil):
    """
    Looks up the plant in the knowledge base and returns a rich profile dict
    comparing current sensor readings against ideal growing conditions.
    """
    plant_name = get_plant_name(prediction_name)

    # Normalize: "Pepper" covers "Pepper,_bell"
    lookup_key = None
    for key in PLANT_KNOWLEDGE:
        if key.lower() in plant_name.lower() or plant_name.lower() in key.lower():
            lookup_key = key
            break

    if not lookup_key:
        return None

    kb = PLANT_KNOWLEDGE[lookup_key]

    # Convert sensor values safely
    try:
        t = float(temp)
        h = float(hum)
        s = float(soil)
    except Exception:
        return None

    def check_range(value, low, high):
        if value < low:
            return "low", f"{value:.1f} (ideal: {low}–{high})"
        elif value > high:
            return "high", f"{value:.1f} (ideal: {low}–{high})"
        else:
            return "ok", f"{value:.1f} (ideal: {low}–{high})"

    temp_status, temp_detail = check_range(t, kb["ideal_temp_min"], kb["ideal_temp_max"])
    hum_status,  hum_detail  = check_range(h, kb["ideal_humidity_min"], kb["ideal_humidity_max"])
    soil_status, soil_detail = check_range(s, kb["ideal_soil_min"], kb["ideal_soil_max"])

    STATUS_ICON = {"ok": "✅", "low": "⚠️ Too Low", "high": "🚨 Too High"}

    return {
        "plant_name": lookup_key,
        "scientific_name": kb["scientific_name"],
        "ideal_temp": f"{kb['ideal_temp_min']}°C – {kb['ideal_temp_max']}°C",
        "ideal_humidity": f"{kb['ideal_humidity_min']}% – {kb['ideal_humidity_max']}%",
        "ideal_soil": f"{kb['ideal_soil_min']}% – {kb['ideal_soil_max']}%",
        "temp_status": STATUS_ICON[temp_status],
        "temp_detail": temp_detail,
        "hum_status": STATUS_ICON[hum_status],
        "hum_detail": hum_detail,
        "soil_status": STATUS_ICON[soil_status],
        "soil_detail": soil_detail,
        "growing_tips": kb["growing_tips"],
        "susceptible_diseases": kb["susceptible_diseases"],
    }


def generate_fused_alert(prediction_name, temp, hum, soil):
    """
    Fuses environmental sensor readings with the ML prediction to generate a dynamic alert.
    Returns: (alert_message, alert_bootstrap_type)
    """
    alert_msg = "Prediction is consistent with normal environmental conditions."
    alert_type = "success"

    try:
        t = float(temp)
        h = float(hum)
        s = float(soil)
    except Exception:
        return "Warning: Missing or invalid sensor data. Cannot fuse logic.", "warning"

    name_lower = prediction_name.lower()

    fungal_keywords = ["blight", "scab", "rot", "rust", "mildew", "spot", "mold"]
    is_fungal = any(k in name_lower for k in fungal_keywords)

    if is_fungal and h < 50:
        alert_msg = f"Low Confidence: Model predicts a fungal issue ({prediction_name}), but current humidity ({h}%) is too low for fungal growth. Might be misidentified leaf damage."
        alert_type = "warning"
    elif is_fungal and h >= 70:
        alert_msg = f"High Confidence: Fungal footprint detected. Supported by the highly humid environment ({h}%)."
        alert_type = "danger"

    if "healthy" in name_lower:
        if s < 30:
            alert_msg = f"Warning: Plant appears healthy, but soil moisture is critical ({s}%). Drought stress is imminent. Please irrigate."
            alert_type = "warning"
        elif t > 35:
            alert_msg = f"Warning: Plant is healthy, but extreme heat detected ({t}°C). Monitor for heat stress."
            alert_type = "warning"

    return alert_msg, alert_type

