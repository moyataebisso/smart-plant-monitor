#include <Arduino_HTS221.h>

#define MOISTURE_PIN A6
#define BUZZER_PIN 12
#define LED_PIN LED_BUILTIN

int MOISTURE_DRY = 800;
int MOISTURE_WET = 300;

unsigned long lastRead = 0;
bool hts221_ok = false;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000);
  
  pinMode(MOISTURE_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  
  if (HTS.begin()) hts221_ok = true;
  
  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);
  
  Serial.println("READY");
}

void loop() {
  if (millis() - lastRead >= 5000) {
    lastRead = millis();
    
    float temp = hts221_ok ? HTS.readTemperature() : 22.0;
    float hum = hts221_ok ? HTS.readHumidity() : 50.0;
    
    int moistRaw = analogRead(MOISTURE_PIN);
    int moisture = map(moistRaw, MOISTURE_DRY, MOISTURE_WET, 0, 100);
    moisture = constrain(moisture, 0, 100);
    
    String status = (moisture < 30) ? "NEEDS_WATER" : "HEALTHY";
    
    Serial.print("{\"temp\":");
    Serial.print(temp, 1);
    Serial.print(",\"humidity\":");
    Serial.print(hum, 1);
    Serial.print(",\"moisture\":");
    Serial.print(moisture);
    Serial.print(",\"status\":\"");
    Serial.print(status);
    Serial.println("\"}");
    
    if (moisture < 30) {
      for (int i = 0; i < 3; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(150);
        digitalWrite(BUZZER_PIN, LOW);
        delay(100);
      }
    }
    
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
  }
}

