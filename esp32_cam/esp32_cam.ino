/*
 * 🌱 AI-Powered Smart Agriculture Robot - ESP32-CAM Firmware
 *
 * Captures plant images and sends them to the backend API
 * for plant disease detection via HTTP POST.
 *
 * Board: AI-Thinker ESP32-CAM
 * Framework: Arduino
 */

#include "esp_camera.h"
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

// ===== WiFi Configuration =====
const char *ssid = "YOUR_WIFI_SSID";
const char *password = "YOUR_WIFI_PASSWORD";

// ===== Backend API Configuration =====
// Base URL of the machine running the FastAPI backend (no trailing slash).
// Find your PC's LAN IP:  macOS: ipconfig getifaddr en0 | Linux: hostname -I |
// Windows: ipconfig The ESP32 must be on the same network, and the network must
// be 2.4GHz.
const char *baseUrl = "http://192.168.1.100:8000";
// If the ESP32 cannot reach your LAN (e.g. backend is tunneled), use an https
// URL instead: const char* baseUrl  = "https://your-tunnel-host.lhr.life";

// ===== Capture Interval (milliseconds) =====
#define CAPTURE_INTERVAL 10000 // 10 seconds

// ===== AI-Thinker ESP32-CAM Pin Definitions =====
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// Built-in LED (flash)
#define FLASH_LED_PIN 4

// ===== Camera Initialization =====
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Use lower resolution for faster transfer
  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 12;
    config.fb_count = 2;
    Serial.println("[CAM] PSRAM found - using VGA resolution");
  } else {
    config.frame_size = FRAMESIZE_QVGA; // 320x240
    config.jpeg_quality = 15;
    config.fb_count = 1;
    Serial.println("[CAM] No PSRAM - using QVGA resolution");
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init FAILED: 0x%x\n", err);
    return false;
  }

  // Adjust camera settings for plant photography
  sensor_t *s = esp_camera_sensor_get();
  s->set_brightness(s, 1);    // Slightly brighter
  s->set_contrast(s, 1);      // Better contrast
  s->set_saturation(s, 1);    // Vivid colors for leaf detection
  s->set_whitebal(s, 1);      // Auto white balance
  s->set_awb_gain(s, 1);      // AWB gain
  s->set_exposure_ctrl(s, 1); // Auto exposure

  Serial.println("[CAM] Camera initialized successfully");
  return true;
}

// ===== WiFi Connection =====
void connectWiFi() {
  Serial.printf("[WiFi] Connecting to %s", ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected!");
    Serial.printf("[WiFi] IP Address: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] Connection FAILED! Restarting...");
    ESP.restart();
  }
}

// ===== Capture 3 Photos & Send Batch =====
void captureAndSendBatch() {
  const int NUM_PHOTOS = 3;
  uint8_t *photo_buffers[NUM_PHOTOS];
  size_t photo_lens[NUM_PHOTOS];
  bool success = true;

  Serial.println("\n========================================");
  Serial.println("[BATCH] Starting 3-shot capture sequence...");

  // 1. Capture 3 photos with short delays, releasing FB immediately
  for (int i = 0; i < NUM_PHOTOS; i++) {
    Serial.printf("[BATCH] Capturing photo %d/%d...\n", i + 1, NUM_PHOTOS);

    digitalWrite(FLASH_LED_PIN, HIGH);
    delay(200); // Wait for flash to stabilize
    camera_fb_t *fb = esp_camera_fb_get();
    digitalWrite(FLASH_LED_PIN, LOW);

    if (!fb) {
      Serial.printf("[BATCH] Failed to capture photo %d!\n", i + 1);
      for (int j = 0; j < i; j++)
        free(photo_buffers[j]);
      return;
    }

    // Copy to heap and return FB to driver immediately
    photo_lens[i] = fb->len;
    photo_buffers[i] = (uint8_t *)malloc(fb->len);
    if (photo_buffers[i]) {
      memcpy(photo_buffers[i], fb->buf, fb->len);
      Serial.printf("[BATCH] Photo %d captured (%d bytes)\n", i + 1, fb->len);
    } else {
      Serial.println("[BATCH] Memory allocation failed for photo copy!");
      success = false;
    }

    esp_camera_fb_return(fb); // IMPORTANT: Release buffer for next shot

    if (!success) {
      for (int j = 0; j <= i; j++)
        if (photo_buffers[j])
          free(photo_buffers[j]);
      return;
    }

    if (i < NUM_PHOTOS - 1) {
      delay(2000); // 2s interval for movement/angle change
    }
  }

  // 2. Build Multipart Body
  Serial.println("[HTTP] Assembling multipart batch request...");
  String boundary = "----ESP32BatchBoundary";

  size_t totalLen = 0;
  String parts_head[NUM_PHOTOS];
  // Each part already ends with "\r\n" (added below), so the closing
  // boundary only needs the delimiter itself.
  String tail = "--" + boundary + "--\r\n";

  for (int i = 0; i < NUM_PHOTOS; i++) {
    parts_head[i] =
        "--" + boundary +
        "\r\n"
        "Content-Disposition: form-data; name=\"files\"; filename=\"shot_" +
        String(i) +
        ".jpg\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n";
    totalLen += parts_head[i].length() + photo_lens[i] + 2;
  }
  totalLen += tail.length();

  uint8_t *body = (uint8_t *)malloc(totalLen);
  if (!body) {
    Serial.println("[HTTP] Memory allocation failed for total body!");
    for (int i = 0; i < NUM_PHOTOS; i++)
      free(photo_buffers[i]);
    return;
  }

  // Assemble the payload
  size_t offset = 0;
  for (int i = 0; i < NUM_PHOTOS; i++) {
    memcpy(body + offset, parts_head[i].c_str(), parts_head[i].length());
    offset += parts_head[i].length();

    memcpy(body + offset, photo_buffers[i], photo_lens[i]);
    offset += photo_lens[i];

    memcpy(body + offset, "\r\n", 2);
    offset += 2;

    free(photo_buffers[i]); // Done with this individual buffer
  }
  memcpy(body + offset, tail.c_str(), tail.length());

  // 3. POST to Backend
  String batchUrl = String(baseUrl) + "/predict_batch";
  HTTPClient http;

  if (batchUrl.startsWith("https")) {
    static WiFiClientSecure tlsClient;
    tlsClient.setInsecure(); // Self-signed / tunnel certs: skip verification
    http.begin(tlsClient, batchUrl);
  } else {
    static WiFiClient wifiClient;
    http.begin(wifiClient, batchUrl);
  }
  http.setTimeout(30000);
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  Serial.printf("[HTTP] Sending batch (%d bytes)...\n", totalLen);
  int httpCode = http.POST(body, totalLen);

  if (httpCode > 0) {
    Serial.printf("[HTTP] Batch Response: %d\n", httpCode);
    if (httpCode == HTTP_CODE_OK) {
      Serial.println("[SUCCESS] ✓ Multi-shot analysis complete!");
    }
  } else {
    Serial.printf("[HTTP] Batch FAILED: %s\n",
                  http.errorToString(httpCode).c_str());
  }

  free(body);
  http.end();
  Serial.println("========================================\n");
}

// ===== Setup =====
void setup() {
  Serial.begin(115200);
  Serial.println("\n\n");
  Serial.println("╔════════════════════════════════════════╗");
  Serial.println("║  🌱 Smart Agriculture Robot v1.0      ║");
  Serial.println("║  AI Plant Disease Detection            ║");
  Serial.println("╚════════════════════════════════════════╝");

  // Initialize flash LED
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  // Initialize camera
  if (!initCamera()) {
    Serial.println("[FATAL] Camera init failed. Halting.");
    while (true) {
      delay(1000);
    }
  }

  // Connect to WiFi
  connectWiFi();

  Serial.println("[READY] System ready! Starting capture loop...");
  Serial.printf("[CONFIG] Capture interval: %d ms\n", CAPTURE_INTERVAL);
  Serial.printf("[CONFIG] Server: %s\n", baseUrl);
}

// ===== Main Loop =====
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Connection lost - reconnecting...");
    connectWiFi();
  }
  captureAndSendBatch();
  // Wait longer between batches (30 seconds)
  delay(30000);
}
