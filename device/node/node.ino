
// **********************************************************************************
// 
// RFM69 Radio sensor node.
//                                                       
// **********************************************************************************

#include <RFM69.h>              // https://www.github.com/lowpowerlab/rfm69
#include <RFM69_ATC.h>          // https://www.github.com/lowpowerlab/rfm69
#include <SPI.h>                // Included with Arduino IDE
#include <ArduinoJson.h>        // https://arduinojson.org/d
//#include <Adafruit_SleepyDog.h> // https://github.com/adafruit/Adafruit_SleepyDog
#include <I2S.h>

// Debug mode
bool DEBUG = true;

// Node and network config
#define NODEID        3    // The ID of this node (must be different for every node on network)
#define NETWORKID     100  // The network ID
#define GATEWAYID     1    // Where to send sensor data
#define CONFIGID      101  // Where to send config data
int TRANSMITPERIOD  = 5000; // Transmission interval in ms e.g. 5000 = every 5 seconds 
int CONFIGPERIOD    = 15000; // Time can be in config mode without ack
int dest = GATEWAYID;

#define NUM_RETRYS    3    // How many times to retry sending a message
#define RETRY_WAIT    500  // How long to wait for Acknoledgement

// Are you using the RFM69 Wing? Uncomment if you are.
//#define USING_RFM69_WING 

// The transmision frequency of the baord. Change as needed.
#define FREQUENCY      RF69_433MHZ //RF69_868MHZ // RF69_915MHZ

// An encryption key. Must be the same 16 characters on all nodes. Comment out to disable
#define ENCRYPTKEY    "sampleEncryptKey"

// Uncomment if this board is the RFM69HW/HCW not the RFM69W/CW
#define IS_RFM69HW_HCW

// Uncomment to enable auto transmission control - adjusts power to save battery
#define ENABLE_ATC

// Serial board rate - just used to print debug messages
#define SERIAL_BAUD   115200

// Which LED
#define LED LED_BUILTIN

// Board and radio specific config - You should not need to edit
#if defined (__AVR_ATmega32U4__) && defined (USING_RFM69_WING)
    #define RF69_SPI_CS  10   
    #define RF69_RESET   11   
    #define RF69_IRQ_PIN 2 
    #define RF69_IRQ_NUM digitalPinToInterrupt(RF69_IRQ_PIN) 
#elif defined (__AVR_ATmega32U4__)
    #define RF69_RESET    4
    #define RF69_SPI_CS   8
    #define RF69_IRQ_PIN  7
    #define RF69_IRQ_NUM  4
#elif defined(ARDUINO_SAMD_FEATHER_M0) && defined (USING_RFM69_WING)
    #define RF69_RESET    11
    #define RF69_SPI_CS   10
    #define RF69_IRQ_PIN  6
    #define RF69_IRQ_NUM  digitalPinToInterrupt(RF69_IRQ_PIN)
#elif defined(ARDUINO_SAMD_FEATHER_M0)
    #define RF69_RESET    4
    #define RF69_SPI_CS   8
    #define RF69_IRQ_PIN  3
    #define RF69_IRQ_NUM  3
#endif

// Battery pin
#if defined (__AVR_ATmega32U4__) 
  #define VBATPIN A9
#elif defined(ARDUINO_SAMD_FEATHER_M0)
  #define VBATPIN A7
#endif

// Create Radio
#ifdef ENABLE_ATC
    RFM69_ATC radio(RF69_SPI_CS, RF69_IRQ_PIN, false, RF69_IRQ_NUM);
#else
    RFM69 radio(RF69_SPI_CS, RF69_IRQ_PIN, false, RF69_IRQ_NUM);
#endif

// Operation modes
#define MODE_NORMAL 1
#define MODE_CONFIG  2
int mode = MODE_NORMAL;
int modeButtonPin = 5;
int modeLedPin = LED_BUILTIN;
unsigned long modeTimer = 0;

// Mic
#define SAMPLES 128

//===================================================
// Setup
//===================================================

void setup() {
  Serial.begin(SERIAL_BAUD);

  // Reset the radio
  resetRadio();

  // Initialize the radio
  radio.initialize(FREQUENCY,NODEID,NETWORKID);
  #ifdef IS_RFM69HW_HCW
    radio.setHighPower(); //must include this only for RFM69HW/HCW!
  #endif
  #ifdef ENCRYPTKEY
    radio.encrypt(ENCRYPTKEY);
  #endif

  // Microphone - start I2S at 16 kHz with 32-bits per sample
  if (!I2S.begin(I2S_PHILIPS_MODE, 16000, 32)) {
    Serial.println("Failed to initialize I2S!");
    while (1); // do nothing
  }
  
  // Debug
  if (DEBUG) printDebugInfo();
}

//===================================================
// Main loop
//===================================================

void loop() {

  // Revert to normal if no acks from alternative
  autoRevertModeManager();
  
  // Check for mode button press
  checkModeButton();
  indicateModeStatus();
  
  // Send a reading
  sendReading();

  // Listen for messages from gateway
  listenForMessages();
  
  // Sleep
  sleepTime();
}

//===================================================
// Sleep mode (If not in config mode)
//===================================================

void sleepTime() {
  if (mode == MODE_NORMAL) {
    //  delay(1000);
    if (DEBUG) Serial.println("Going to sleep");
    //radio.sleep();
    //Watchdog.sleep(TRANSMITPERIOD);
    delay(TRANSMITPERIOD);
  } else {
    delay(200);
  }
}

//===================================================
// Display the mode of operation i.e. Normal or Debug
//===================================================

void indicateModeStatus() {
  if (mode == MODE_NORMAL) {
      digitalWrite(modeLedPin, LOW);
  } else {
      digitalWrite(modeLedPin, HIGH);
  }
}

// Check if mode button has been pressed
void checkModeButton() {
  bool buttonState = digitalRead(modeButtonPin);
   if (buttonState == HIGH) {
      mode = MODE_CONFIG;
      dest = CONFIGID;
      modeTimer = millis(); 
  } 
}

void autoRevertModeManager() {
  if (modeTimer < millis() - CONFIGPERIOD) {
    mode = MODE_NORMAL;
    dest = GATEWAYID;
  }
}

//===================================================
// Listen form server messages after sending a msg
//===================================================

// Define struct for update payload
typedef struct {
  char key[20]; // command
  int value; // Battery voltage
} Update;
Update upd;

// 
void listenForMessages() { 
  unsigned long waitfor = 500;
  if (mode == MODE_NORMAL) {
    waitfor = 2000;
  }
  unsigned long started = millis();  
  while (millis() < started + waitfor) {
    if (radio.receiveDone()) {

      if (DEBUG) {
        Serial.print('[sender: '); Serial.print(radio.SENDERID, DEC); Serial.println("] ");
        Serial.print("Data length: "); Serial.println(radio.DATALEN);
        Serial.print("[RX_RSSI:"); Serial.print(radio.RSSI); Serial.println("]");
      }

      if (radio.DATALEN != sizeof(Update)) {
        if (DEBUG) Serial.print("# Invalid update received, not matching Payload struct. -- ");
      } else {    
        upd = *(Update*)radio.DATA; //assume radio.DATA actually contains our struct and not something else
        if (radio.ACKRequested()) { radio.sendACK(); }
      
        if (upd.key == "normal") {
            mode = MODE_NORMAL;
            
        } else if (upd.key == "config") {
             mode = MODE_CONFIG;
             
        } else if (upd.key == "interval") {
            TRANSMITPERIOD = upd.value;
            
        } else if (upd.key == "show") {
            Blink(500, 2);
            Blink(100, 10);
            Blink(500, 2);
            Blink(100, 10);
            Blink(500, 2);
        }
      }
    }
  }  
}



//===================================================
// Sending
//===================================================

// Define payload
typedef struct {
  int battery; // Battery voltage
  int volume;  // Volume
} Payload;
Payload payload;

// sendReading
void sendReading() {

  // Battery Level - multiplied by 100 to get precision as int, must be divided by 100 on the other end (hacky but works)
  payload.battery = (int) 100 * getBatteryLevel();

  // Volume 
  payload.volume  = (int) 100 * getSoundPressure(); 
  
  // Print payload
  Serial.print("Sending payload ("); Serial.print(sizeof(payload)); Serial.print(" bytes)");
  Serial.print(" battery="); Serial.print(payload.battery);
  Serial.print(" volume="); Serial.print(payload.volume);
  Serial.println(")");
  
  // Send payload
  if (radio.sendWithRetry(dest, (const void*) &payload, sizeof(payload), NUM_RETRYS, RETRY_WAIT)) {
    Serial.println(" Acknoledgment received!");
    modeTimer = millis();
    Blink(100, 1);
  } else {
    Serial.println(" No Acknoledgment after retries");
    Blink(500, 1);
  }
  Serial.println(" Done");
  //Watchdog.sleep(500);
  delay(500);
}

//===================================================
// Blink
//===================================================

void Blink(int delayms, int numberTimes) {
  pinMode(LED, OUTPUT);
  for (int x=0; x < numberTimes; x++) {
    digitalWrite(LED, HIGH);
    delay(delayms);
    digitalWrite(LED, LOW);
    delay(delayms);
  }
}

//===================================================
// Reset Radio
//===================================================

// Reset the Radio
void resetRadio() {
  Serial.print("Resetting radio...");
  pinMode(RF69_RESET, OUTPUT);
  digitalWrite(RF69_RESET, HIGH);
  delay(20);
  digitalWrite(RF69_RESET, LOW);
  delay(500);
  Serial.println(" complete");
}

//===================================================
// Debug Message
//===================================================

// Print Info
void printDebugInfo() {
  Serial.print("I am node: "); Serial.println(NODEID);
  Serial.print("on network: "); Serial.println(NETWORKID);
  Serial.print("talking to gateway "); Serial.print(GATEWAYID);
  Serial.print(" every "); Serial.print(TRANSMITPERIOD); Serial.println("ms");
  
  #if defined (__AVR_ATmega32U4__)
    Serial.println("AVR ATmega 32U4");
  #else
    Serial.println("SAMD FEATHER M0");
  #endif
  #ifdef USING_RFM69_WING
    Serial.println("Using RFM69 Wing: YES");
  #else
    Serial.println("Using RFM69 Wing: NO");
  #endif
  Serial.print("RF69_SPI_CS: "); Serial.println(RF69_SPI_CS);
  Serial.print("RF69_IRQ_PIN: "); Serial.println(RF69_IRQ_PIN);
  Serial.print("RF69_IRQ_NUM: "); Serial.println(RF69_IRQ_NUM);
  #ifdef ENABLE_ATC
    Serial.println("RFM69 Auto Transmission Control: Enabled");
  #else
    Serial.println("RFM69 Auto Transmission Control: Disabled");
  #endif
  #ifdef ENCRYPTKEY
    Serial.println("Encryption: Enabled");
  #else
    Serial.println("Encryption: Disabled");
  #endif
  char buff[50];
  sprintf(buff, "\nListening at %d Mhz...", FREQUENCY==RF69_433MHZ ? 433 : FREQUENCY==RF69_868MHZ ? 868 : 915);
  Serial.println(buff);
}

//===================================================
// Split String
//===================================================

String getValue(String data, char separator, int index) {
  int found = 0;
  int strIndex[] = {0, -1};
  int maxIndex = data.length()-1;
  for(int i=0; i<=maxIndex && found<=index; i++){
    if(data.charAt(i)==separator || i==maxIndex){
        found++;
        strIndex[0] = strIndex[1]+1;
        strIndex[1] = (i == maxIndex) ? i+1 : i;
    }
  }
  return found>index ? data.substring(strIndex[0], strIndex[1]) : "";
}

//===================================================
// Sensor Sound Level
//===================================================

float getSoundPressure() {
  // read a bunch of samples:
  int samples[SAMPLES];
 
  for (int i=0; i<SAMPLES; i++) {
    int sample = 0; 
    while ((sample == 0) || (sample == -1) ) {
      sample = I2S.read();
    }
    // convert to 18 bit signed
    sample >>= 14; 
    samples[i] = sample;
  }
 
  // ok we hvae the samples, get the mean (avg)
  float meanval = 0;
  for (int i=0; i<SAMPLES; i++) {
    meanval += samples[i];
  }
  meanval /= SAMPLES;
  //Serial.print("# average: " ); Serial.println(meanval);
 
  // subtract it from all sapmles to get a 'normalized' output
  for (int i=0; i<SAMPLES; i++) {
    samples[i] -= meanval;
    //Serial.println(samples[i]);
  }
 
  // find the 'peak to peak' max
  float maxsample, minsample;
  minsample = 100000;
  maxsample = -100000;
  for (int i=0; i<SAMPLES; i++) {
    minsample = min(minsample, samples[i]);
    maxsample = max(maxsample, samples[i]);
  }
  
  return maxsample - minsample;
}

//===================================================
// Sensor Battery Level
//===================================================

float getBatteryLevel() {
  float measuredvbat = analogRead(VBATPIN);
  measuredvbat *= 2;    // we divided by 2, so multiply back
  measuredvbat *= 3.3;  // Multiply by 3.3V, our reference voltage
  measuredvbat /= 1024; // convert to voltage
  return 100 * measuredvbat;
}
