#include <boarddefs.h>
#include <IRremote.h>
#include <IRremoteInt.h>

#define RECV_PIN 7
#define RECV_TIMEOUT 5000
#define SEND_TIMEOUT 5000
#define SEND_MAX_LEN 128
#define SEND_MAX_DIGITS 11
#define IS_LINE_BREAK(c) (c=='\n'||c=='\r')

bool irrecv() {
  IRrecv recv(RECV_PIN);
  decode_results results;
  unsigned long start = millis();

  Serial.println("RECV");
  recv.enableIRIn();

  while (start + RECV_TIMEOUT > millis()) {
    if (recv.decode(&results)) {
      Serial.print("DATA, ");
      for (int i = 1; i < results.rawlen; ++i) {
        Serial.print(results.rawbuf[i] * USECPERTICK + MARK_EXCESS * ((i % 2)?-1:1));
        Serial.print(", ");
      }
      Serial.println("");
      return true;
    }
  }
  
  Serial.println("TIMEOUT");
  return false;
}

bool irsend() {
  unsigned int data[SEND_MAX_LEN];
  char buf[SEND_MAX_DIGITS];
  int i = 0, j = 0;
  IRsend sender;
  unsigned long start = millis();

  Serial.println("SEND");
  while (true) {
    char c = Serial.read();
    if (c == 'C') {
      Serial.println("THEN");
      Serial.flush();
      continue;
    }
    if (start + SEND_TIMEOUT <= millis()) {
      Serial.println("TIMEOUT");
      return false;
    }
    if (i >= SEND_MAX_LEN || j >= SEND_MAX_DIGITS) {
      Serial.println("DATA TOO LONG");
      return false;
    }
    if ((IS_LINE_BREAK(c) || c == ',') && j > 0) {
      buf[j] = '\0';
      data[i++] = atoi(buf);
      j = 0;
    }
    if (isdigit(c)) {
      buf[j++] = c;
    }
    if (IS_LINE_BREAK(c) && i > 0) {
      sender.sendRaw(data, i, 38);
      Serial.print("DATA, ");
      for (int k = 0; k < i; k++) {
        Serial.print(data[k]);
        Serial.print(", ");
      }
      Serial.println("");
      return true;
    }
  }
  return false;
}

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.println("IDLE");
}

void loop() {
  char c = Serial.read();
  switch (c) {
    case 'R':
      Serial.println(irrecv()?"DONE OK":"DONE ERR");
      break;
    case 'S':
      Serial.println(irsend()?"DONE OK":"DONE ERR");
      break;
    case 'I':
      Serial.println("IDLE");
      break;
  }
}
