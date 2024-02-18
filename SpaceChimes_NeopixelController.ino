#include <FastLED.h>

#define LED_PIN     6 // Neopixels connected to D6
#define NUM_LEDS    8 // THIS NEEDS TO CHANGE FOR JEWELS
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB
#define DIST_POT_PIN     A0 // Potentiometer connected to A0
#define VOL_POT_PIN     A1
#define NEO_POT_PIN     A2 

// This is pretty much done - just needs to have updates for groups of 7 pixels when jewels get here


CRGB leds[NUM_LEDS];
bool highlight[NUM_LEDS] = {false}; // Tracks whether an LED is highlighted

void setup() {
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  Serial.begin(9600);
}

void loop() {
  // Read pots to adjust settings - too complicated reading on pi so just read all pots on arduino and send relevant values to Pi 

  //int potBrightnessValue = analogRead(NEO_POT_PIN);
  //int potVolumeValue = analogRead(VOL_POT_PIN);
  //int potDistanceValue = analogRead(DIST_POT_PIN);

  int potVolumeValue = 500;
  int potDistanceValue = 500;

  // Send the values over serial in a comma-separated format
  Serial.print(potVolumeValue);
  Serial.print(",");
  Serial.println(potDistanceValue);

  //delay(100);

  //int brightness = map(potValue, 0, 1023, 0, 255);
  FastLED.setBrightness(80);

  static uint8_t hue = 0;
  // Update the rainbow cycle for non-highlighted LEDs
  for (int i = 0; i < NUM_LEDS; i++) {
    if (!highlight[i]) { // Only update if not highlighted
      leds[i] = CHSV((hue + i * 10) % 255, 255, 255); // Adjust '10' to change the rainbow spread
    }
  }
  FastLED.show();
  hue++;

  // Check for serial input
  if (Serial.available()) {
    String inputString = Serial.readStringUntil('\n'); // Read the input until newline
    inputString.trim(); // Remove any whitespace
    if (inputString.length() > 0) { // Check if the string is not empty
      if (inputString == "999") { // Reset command
        fadeOutHighlighted();
        for (int i = 0; i < NUM_LEDS; i++) {
          highlight[i] = false; // After fading, reset all LEDs to rainbow
        }
      } else {
        int input = inputString.toInt(); // Convert string to integer for LED index
        if (input >= 0 && input < NUM_LEDS) {
          highlight[input] = true; // Highlight the specified LED
          leds[input] = CRGB::White;
          FastLED.show();
        }
      }
    }
  }

  delay(10); // Adjust for speed of the rainbow cycle
}

void fadeOutHighlighted() {
  for (int fadeValue = 255; fadeValue >= 0; fadeValue -= 5) { // Fade out value
    for (int i = 0; i < NUM_LEDS; i++) {
      if (highlight[i]) {
        leds[i] = CRGB(fadeValue, fadeValue, fadeValue); // Apply fade
      }
    }
    FastLED.show();
    delay(30); // Delay for fade effect, adjust for faster/slower fade
  }
}
