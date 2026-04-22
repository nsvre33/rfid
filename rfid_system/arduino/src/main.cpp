#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9
#define BUZZER_PIN 5

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
    Serial.begin(9600);
    while (!Serial) {
        ;
    }
    
    SPI.begin();
    mfrc522.PCD_Init();
    
    pinMode(BUZZER_PIN, OUTPUT);
    analogWrite(BUZZER_PIN, 0);
}

void loop() {
    if (!mfrc522.PICC_IsNewCardPresent()) {
        return;
    }
    
    if (!mfrc522.PICC_ReadCardSerial()) {
        return;
    }
    
    String uid_string = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        if (mfrc522.uid.uidByte[i] < 0x10) {
            uid_string += "0";
        }
        uid_string += String(mfrc522.uid.uidByte[i], HEX);
    }
    uid_string.toUpperCase();
    
    Serial.print("RFID:");
    Serial.println(uid_string);
    
    analogWrite(BUZZER_PIN, 25);
    delay(50);
    analogWrite(BUZZER_PIN, 0);
    delay(50);
    
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    
    delay(600);
}
