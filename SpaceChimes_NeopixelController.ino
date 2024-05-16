#include <Adafruit_NeoPixel.h>

#define LED_PIN         6 // Neopixels connected to D6
#define NUM_LEDS        56
#define LEDS_PER_CLUSTER 7
#define NUM_CLUSTERS    (NUM_LEDS / LEDS_PER_CLUSTER)
#define COLOR_ORDER     NEO_GRBW // Change as necessary

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, COLOR_ORDER + NEO_KHZ800);

bool clusterHighlighted[NUM_CLUSTERS] = {false}; // Track which clusters are highlighted
int fadeValue[NUM_CLUSTERS] = {0}; // Track the fade value for each cluster
bool fading[NUM_CLUSTERS] = {false}; // Track whether a cluster is currently fading
unsigned long previousMillis[NUM_CLUSTERS] = {0}; // Track the last update time for each cluster
const long fadeInterval = 30; // Interval between fade steps in milliseconds

void setup() {
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
  Serial.begin(9600);
}

void loop() {
  int brightness = analogRead(A2); // Assuming potentiometer is connected to A2
  brightness = map(brightness, 0, 1023, 0, 255);
  strip.setBrightness(brightness);

  // Apply a rotating rainbow effect to non-highlighted clusters
  static uint8_t hue = 0;
  for (int cluster = 0; cluster < NUM_CLUSTERS; cluster++) {
    if (!clusterHighlighted[cluster] && !fading[cluster]) {
      int clusterHue = (hue + cluster * 36) % 256; // Increment hue by cluster
      uint32_t color = strip.ColorHSV(clusterHue * 65536 / 256, 255, 255); // RGB only, no white component
      for (int i = cluster * LEDS_PER_CLUSTER; i < (cluster + 1) * LEDS_PER_CLUSTER; i++) {
        strip.setPixelColor(i, color);
      }
    }
  }
  strip.show();
  hue++;

  // Check for incoming serial data
  int incomingByte = Serial.read();
  if (incomingByte != -1) {
    if (incomingByte == 'r') { // Reset command
      startFadeOut();
    } else if (incomingByte >= '0' && incomingByte < ('0' + NUM_CLUSTERS)) {
      int clusterIndex = incomingByte - '0';
      highlightCluster(clusterIndex);
    }
  }

  // Update fading clusters
  updateFadeOut();
}

void highlightCluster(int clusterIndex) {
  clusterHighlighted[clusterIndex] = true;
  fading[clusterIndex] = false;
  fadeValue[clusterIndex] = 255;
  int startIndex = clusterIndex * LEDS_PER_CLUSTER;
  for (int i = startIndex; i < startIndex + LEDS_PER_CLUSTER; i++) {
    strip.setPixelColor(i, strip.Color(255, 255, 255, 0)); // RGB with no White
  }
  strip.show();
}

void startFadeOut() {
  for (int cluster = 0; cluster < NUM_CLUSTERS; cluster++) {
    if (clusterHighlighted[cluster]) {
      fading[cluster] = true;
      previousMillis[cluster] = millis();
    }
  }
}

void updateFadeOut() {
  unsigned long currentMillis = millis();
  for (int cluster = 0; cluster < NUM_CLUSTERS; cluster++) {
    if (fading[cluster]) {
      if (currentMillis - previousMillis[cluster] >= fadeInterval) {
        previousMillis[cluster] = currentMillis;
        fadeValue[cluster] -= 5;
        if (fadeValue[cluster] <= 0) {
          fadeValue[cluster] = 0;
          fading[cluster] = false;
          clusterHighlighted[cluster] = false;
        }
        int startIndex = cluster * LEDS_PER_CLUSTER;
        for (int i = startIndex; i < startIndex + LEDS_PER_CLUSTER; i++) {
          strip.setPixelColor(i, strip.Color(fadeValue[cluster], fadeValue[cluster], fadeValue[cluster], 0));
        }
        strip.show();
      }
    }
  }
}
