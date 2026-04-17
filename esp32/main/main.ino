#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include <DHT.h>

// ===========================
// Enter your WiFi credentials
// ===========================
const char* ssid     = "abcd";     // <-- Replace with your WiFi name
const char* password = "12345678"; // <-- Replace with your WiFi password

// ===========================
// Enter your Flask Server IP
// ===========================
String serverName = "http://10.100.45.164:5000/api/upload_sensor";

// ===========================
// Capture Interval (ms)
// ===========================
#define CAPTURE_INTERVAL_MS  5000   // 20 seconds between uploads

// ===========================
// Pin Definitions
// ===========================
#define DHTPIN 13
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);
#define SOIL_PIN 12

// CAMERA_MODEL_AI_THINKER Pins (do not change)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

bool ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  Serial.println("[WiFi] Reconnecting...");
  WiFi.disconnect();
  WiFi.begin(ssid, password);
  for (int i = 0; i < 20; i++) {
    if (WiFi.status() == WL_CONNECTED) { Serial.println("[WiFi] Reconnected."); return true; }
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Reconnect failed.");
  return false;
}

void setup() {
  Serial.begin(115200);

  // ── Sensors (commented for demo — uncomment to enable) ──────────────────
  // dht.begin();
  // pinMode(SOIL_PIN, INPUT);
  // ────────────────────────────────────────────────────────────────────────

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.println("[WiFi] Connecting...");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\n[WiFi] Connected. IP: " + WiFi.localIP().toString());

  // Initialize Camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  Serial.println("[Camera] Checking PSRAM...");
  if (psramFound()) {
    Serial.println("[Camera] PSRAM found. Using VGA.");
    config.frame_size   = FRAMESIZE_VGA;
    config.jpeg_quality = 10;
    config.fb_count     = 2;
  } else {
    Serial.println("[Camera] No PSRAM. Using CIF.");
    config.frame_size   = FRAMESIZE_CIF;
    config.jpeg_quality = 12;
    config.fb_count     = 1;
  }

  Serial.println("[Camera] Calling esp_camera_init...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[Camera] Init failed: 0x%x\n", err);
    Serial.println("[Camera] Check ribbon cable! Restarting in 5s...");
    delay(5000);
    ESP.restart();
  }
  Serial.println("[Camera] Initialized successfully!");
}

void loop() {
  if (!ensureWiFi()) {
    Serial.println("[Loop] Skipping cycle — no WiFi.");
    delay(CAPTURE_INTERVAL_MS);
    return;
  }

  // Sensors are read by the ESP32 DevKit (sensor_node.ino)
  // and sent separately to Flask via /api/update_sensors
  // The CAM only handles camera capture and image upload

  // Capture fresh frame — flush stale buffer first
  for (int i = 0; i < 4; i++) {
    camera_fb_t *stale = esp_camera_fb_get();
    if (stale) esp_camera_fb_return(stale);
    delay(100);
  }
  delay(500);

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[Camera] Capture failed — retrying next cycle.");
    delay(CAPTURE_INTERVAL_MS);
    return;
  }
  Serial.printf("[Camera] Captured %u bytes.\n", fb->len);

  // Build multipart POST body (image only — sensors come from DevKit)
  String boundary = "----ESP32Boundary7349";
  String partHeader = "";
  partHeader += "--" + boundary + "\r\n";
  partHeader += "Content-Disposition: form-data; name=\"img\"; filename=\"field_capture.jpg\"\r\n";
  partHeader += "Content-Type: image/jpeg\r\n\r\n";
  String partFooter = "\r\n--" + boundary + "--\r\n";

  size_t totalLen = partHeader.length() + fb->len + partFooter.length();
  uint8_t *bodyBuf = (uint8_t *)malloc(totalLen);
  if (!bodyBuf) {
    Serial.println("[POST] malloc failed — not enough heap.");
    esp_camera_fb_return(fb);
    delay(CAPTURE_INTERVAL_MS);
    return;
  }

  memcpy(bodyBuf,                                  partHeader.c_str(), partHeader.length());
  memcpy(bodyBuf + partHeader.length(),            fb->buf,            fb->len);
  memcpy(bodyBuf + partHeader.length() + fb->len,  partFooter.c_str(), partFooter.length());

  // POST to Flask
  HTTPClient http;
  http.begin(serverName);
  http.setTimeout(10000);
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  int httpCode = http.POST(bodyBuf, totalLen);
  if (httpCode > 0) {
    Serial.printf("[POST] Response code: %d\n", httpCode);
    Serial.println("[POST] Server: " + http.getString());
  } else {
    Serial.printf("[POST] Failed. HTTPClient error: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
  free(bodyBuf);
  esp_camera_fb_return(fb);

  Serial.printf("[Loop] Sleeping %d seconds...\n\n", CAPTURE_INTERVAL_MS / 1000);
  delay(CAPTURE_INTERVAL_MS);
}