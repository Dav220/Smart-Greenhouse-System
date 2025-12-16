#include "DHT.h"
#include <Arduino.h>
#include <U8x8lib.h>
//#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define DHTPIN 3     // what pin we're connected to
#define DHTTYPE DHT22   // DHT 22 
DHT dht(DHTPIN, DHTTYPE);
int moisturePin = A0;
unsigned long previousMillis = 0;
#define INTERVAL 5000
int watering_state = 0;
int pumpPin = 5; // digital pin to activate the pump 


//U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(/* reset=*/ U8X8_PIN_NONE);

void setup(void) {
  Serial.begin(9600); 
  //Serial.println("DHTxx test!");
  dht.begin();
  // u8x8.begin();
  // u8x8.setPowerSave(0);  
  // u8x8.setFlipMode(1);
  pinMode(moisturePin,INPUT);
  pinMode(pumpPin,OUTPUT);
}

void loop(void) {
  unsigned long currentMillis = millis();
  float temp, humi;
  int moist;

    if (Serial.available() > 0) {
      String data = Serial.readStringUntil('\n');
      watering_state = data.toInt();
      bool state = (watering_state == 1);

      if (state) {
        digitalWrite(pumpPin,HIGH);
      }

      else {
        digitalWrite(pumpPin,LOW);
      }
    }
  
  
  if (currentMillis - previousMillis >= INTERVAL) {
    previousMillis = currentMillis;
    temp = dht.readTemperature();
    //delay(100);
    humi = dht.readHumidity();
    //delay(100);
    moist = analogRead(moisturePin);
    //delay(100);

    while (isnan(temp) || isnan(humi) || isnan(moist)) {
      temp = dht.readTemperature();
      //delay(100);
      humi = dht.readHumidity();
      //delay(100);
      moist = analogRead(moisturePin);
      //delay(100);
    }
    moist = map(moist,0,1023,255,0);

    

    // u8x8.setFont(u8x8_font_chroma48medium8_r);
    // u8x8.setCursor(0, 33);

    //Serial.print("Temp: ");
    Serial.println(temp);
    //Serial.println(" C");
    // u8x8.print("Temp:");
    // u8x8.print(temp);
    // u8x8.print("C");

    //u8x8.setCursor(0,50);

  
    //Serial.print("Humidity: ");
    Serial.println(humi);
    //Serial.println(" %");
    // u8x8.print("Humidity:");
    // u8x8.print(humi);
    // u8x8.print("%");

    // u8x8.setCursor(0,80);

    //Serial.print("Moisture: ");
    Serial.println(moist);
    // u8x8.print("Moisture:");
    // u8x8.print(moist);
    //u8x8.print("C");

    
    //u8x8.refreshDisplay();
  }
}
