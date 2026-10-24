"""Single source of truth for GPIO assignments (ESP32-S3-Zero)."""
HEATER = 4      # MOSFET gate via 220R, 10k pulldown
ONEWIRE = 5     # DS18B20 data, 4.7k pull-up to 3V3
LED_RING = 6    # WS2812B x16 data
LED_ONBOARD = 21  # Onboard WS2812 RGB LED
