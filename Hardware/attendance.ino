#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <TimeLib.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <LiquidCrystal.h>
#include <WiFiClientSecure.h>

const char* ssid = "localhost:0000";
const char* password = "cceh2712";

const char* ap_ssid = "ESP32-AP";
const char* ap_password = "12345678";

const char* serverName = "https://attendancesystem-pz0c.onrender.com/api/attendance";
// const char* serverName = "http://localhost:5000/api/attendance";

#define SS_PIN 5
#define RST_PIN 22
MFRC522 rfid(SS_PIN, RST_PIN);

// =================== LCD Setup ===================
// Pins: RS, EN, D4, D5, D6, D7
LiquidCrystal lcd(16, 17, 25, 26, 27, 32);

// =================== NTP Setup ===================
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org");

// =================== LED Indicators ===================
#define RED_LED 12
#define GREEN_LED 14

// =================== State Variables ===================
String cardID = "";
unsigned long lastScanTime = 0;
const unsigned long scanCooldown = 3000;
unsigned long lastLCDUpdate = 0;
const unsigned long lcdUpdateInterval = 1000;

bool wifiConnected = false;

// =================== Setup ===================
void setup() {
  Serial.begin(115200);

  // LCD setup
  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("Attendance Sys");
  lcd.setCursor(0, 1);
  lcd.print("Starting...");

  // RFID setup
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID Ready");

  // LED setup
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  digitalWrite(RED_LED, LOW);
  digitalWrite(GREEN_LED, LOW);

  // Try Wi-Fi connection
  connectToWiFi();

  // Start NTP (time)
  timeClient.begin();
  timeClient.setTimeOffset(0);  // Adjust timezone offset if needed
  timeClient.update();

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("System Ready");
  lcd.setCursor(0, 1);
  lcd.print("Scan your card");
}

// =================== Main Loop ===================
void loop() {
  if (millis() - lastLCDUpdate > lcdUpdateInterval) {
    updateLCDTime();
    lastLCDUpdate = millis();
  }

  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial() && (millis() - lastScanTime > scanCooldown)) {
    lastScanTime = millis();
    cardID = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      cardID.concat(String(rfid.uid.uidByte[i] < 0x10 ? "0" : ""));
      cardID.concat(String(rfid.uid.uidByte[i], HEX));
    }
    cardID.toUpperCase();

    Serial.println("Card: " + cardID);
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Card Detected");
    lcd.setCursor(0, 1);
    lcd.print("Processing...");

    timeClient.update();

    if (wifiConnected && WiFi.status() == WL_CONNECTED) {
      recordAttendance(cardID);
    } else {
      Serial.println("WiFi Disconnected");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("WiFi Error");
      lcd.setCursor(0, 1);
      lcd.print("Reconnecting...");
      connectToWiFi();
      blinkLED(RED_LED);
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }
}

// =================== Helper Functions ===================
void updateLCDTime() {
  if (millis() - lastScanTime > 5000) {
    timeClient.begin();
    timeClient.setTimeOffset(3600);
    timeClient.update();
    lcd.setCursor(0, 0);
    lcd.print("Ready ");
    lcd.print(timeClient.getFormattedTime());
    lcd.setCursor(0, 1);
    lcd.print("Scan your card  ");
  }
}

void connectToWiFi() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");
  WiFi.begin(ssid, password);

  unsigned long startAttemptTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 10000) {
    delay(500);
    Serial.print(".");
    digitalWrite(RED_LED, !digitalRead(RED_LED));
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    digitalWrite(RED_LED, LOW);
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP());
    Serial.print("\nConnected! IP: ");
    Serial.println(WiFi.localIP());
    delay(2000);
  } else {
    // Fallback: Create Access Point
    wifiConnected = false;
    Serial.println("\nFailed to connect. Starting AP...");
    WiFi.softAP(ap_ssid, ap_password);

    IPAddress IP = WiFi.softAPIP();
    Serial.print("AP IP address: ");
    Serial.println(IP);

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("AP Mode Active");
    lcd.setCursor(0, 1);
    lcd.print(IP);
  }
}

void recordAttendance(String cardUID) {
  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.begin(client, serverName);  
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  http.setTimeout(10000);
  http.setReuse(true);

  http.addHeader("Content-Type", "application/json");

  String formattedTime = timeClient.getFormattedTime();
  unsigned long epochTime = timeClient.getEpochTime();

  StaticJsonDocument<200> doc;
  doc["card_id"] = cardUID;
  doc["timestamp"] = epochTime;
  doc["formatted_time"] = formattedTime;

  String jsonData;
  serializeJson(doc, jsonData);

  int httpResponseCode = http.POST(jsonData);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);

    StaticJsonDocument<512> resDoc;
    DeserializationError error = deserializeJson(resDoc, response);

    if (error) {
      Serial.println("JSON parse error");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Server Error");
      lcd.setCursor(0, 1);
      lcd.print("Try again");
      blinkLED(RED_LED);
    } else if (httpResponseCode >= 200 && httpResponseCode < 300 && resDoc["status"] == "success") {
      const char* name = resDoc["user_name"] | resDoc["student_name"] | resDoc["staff_name"] | "Unknown";
      const char* userType = resDoc["user_type"] | "user";
      String displayType = String(userType);
      displayType.toLowerCase();
      if (displayType == "student") {
        displayType = "Student";
      } else if (displayType == "staff") {
        displayType = "Staff";
      } else {
        displayType = "User";
      }

      Serial.println("Success: " + String(name) + " [" + String(userType) + "]");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Welcome ");
      lcd.print(displayType);
      lcd.setCursor(0, 1);
      lcd.print(String(name).substring(0, 16));
      blinkLED(GREEN_LED);
    } else if (resDoc["status"] == "error" && String(resDoc["message"] | "") == "Card not registered") {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Unregistered Card");
      lcd.setCursor(0, 1);
      lcd.print(cardUID.substring(0, 16));
      blinkLED(RED_LED);
    } else {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Server Error");
      lcd.setCursor(0, 1);
      lcd.print("Try again");
      blinkLED(RED_LED);
    }
  } else {
    Serial.println("HTTP Error: " + String(httpResponseCode));
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Server Error");
    blinkLED(RED_LED);
  }

  http.end();
}

void blinkLED(int pin) {
  for (int i = 0; i < 2; i++) {
    digitalWrite(pin, HIGH);
    delay(200);
    digitalWrite(pin, LOW);
    delay(200);
  }
}
