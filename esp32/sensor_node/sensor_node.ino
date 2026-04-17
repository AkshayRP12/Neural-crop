// =============================================================
// Crop Disease IoT — Sensor Node Firmware
// Device: ESP32 DevKit (separate from ESP32-CAM)
// Sensors: DHT11 (GPIO 4) + Soil Moisture (GPIO 34) + Relay (GPIO 26)
// Sends: HTTP POST to Flask /api/update_sensors every 5 seconds
// =============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ===========================
// WiFi credentials
// ===========================
const char* ssid     = "abcd";          // <-- Your WiFi name
const char* password = "12345678";      // <-- Your WiFi password

// ===========================
// Flask Server IP
// ===========================
String serverName = "http://10.100.45.164:5000/api/update_sensors";

// ===========================
// Pin Definitions
// ===========================
#define DHTPIN     4      // GPIO 4 — DHT11 data pin
#define DHTTYPE    DHT11
#define SOIL_PIN   34     // GPIO 34 — Soil moisture analog
#define RELAY_PIN  26     // GPIO 26 — Relay control

// ===========================
// Thresholds
// ===========================
#define SOIL_DRY_THRESHOLD  2500   // ADC above this = dry soil → pump ON
#define SEND_INTERVAL_MS    2000   // Send every 2s — fast enough for real-time demo

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  Serial.println("\n[SensorNode] Starting...");

  // Initialize pins
  dht.begin();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // Relay OFF initially (active LOW)

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("[WiFi] Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected. IP: " + WiFi.localIP().toString());
}

void loop() {
  // ─── Read DHT11 ────────────────────────────────────────────
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    Serial.println("[DHT] Read failed — skipping this cycle.");
    delay(SEND_INTERVAL_MS);
    return; // Do not send bad data to Flask
  }

  // ─── Read Soil Moisture ────────────────────────────────────
  int rawSoil = analogRead(SOIL_PIN);
  // Map ADC (0-4095) to percentage: high ADC = dry = low %, low ADC = wet = high %
  float soilPct = map(rawSoil, 4095, 0, 0, 100);

  // ─── Relay Control ────────────────────────────────────────
  if (rawSoil > SOIL_DRY_THRESHOLD) {
    Serial.println("[Relay] Soil DRY → Pump ON");
    digitalWrite(RELAY_PIN, LOW);   // Relay ON
  } else {
    Serial.println("[Relay] Soil WET → Pump OFF");
    digitalWrite(RELAY_PIN, HIGH);  // Relay OFF
  }

  Serial.printf("[Sensors] Temp: %.1fC | Hum: %.1f%% | Soil: %.1f%% (raw: %d)\n",
                temp, hum, soilPct, rawSoil);

  // ─── Send to Flask ─────────────────────────────────────────
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.setTimeout(5000);
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String body = "temperature=" + String(temp, 1)
                + "&humidity="    + String(hum, 1)
                + "&soil_moisture=" + String(soilPct, 1);

    int code = http.POST(body);
    if (code > 0) {
      Serial.printf("[POST] Sent to Flask — Response: %d\n", code);
    } else {
      Serial.printf("[POST] Failed: %s\n", http.errorToString(code).c_str());
    }
    http.end();
  } else {
    Serial.println("[WiFi] Disconnected — skipping send.");
    WiFi.reconnect();
  }

  delay(SEND_INTERVAL_MS);
}
