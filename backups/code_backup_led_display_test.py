# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""LED and Display Test for Pimoroni Pico LiPo
Four RGBW NeoPixel strips (8 LEDs each) and SSD1327 OLED display test.
BACKUP - Original LED test code
"""

import time
import board
import neopixel
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_ssd1327 import SSD1327

# Configuration
NUM_STRIPS = 4
LEDS_PER_STRIP = 8
MAX_BRIGHTNESS = 0.10  # 10% brightness
CHANGE_RATE_HZ = 4  # 4Hz = 0.25 seconds per LED
PIXEL_ORDER = neopixel.RGBW

# NeoPixel strip pins (in order)
STRIP_PINS = [board.GP19, board.GP20, board.GP21, board.GP22]

# Initialize NeoPixel strips
strips = []
for i, pin in enumerate(STRIP_PINS):
    strip = neopixel.NeoPixel(
        pin,
        LEDS_PER_STRIP,
        brightness=MAX_BRIGHTNESS,
        pixel_order=PIXEL_ORDER,
        auto_write=False
    )
    strips.append(strip)

# Release any existing displays (required for SSD1327)
displayio.release_displays()

# Initialize I2C bus
# Try default I2C first, but also allow explicit pin specification if needed
try:
    i2c = board.I2C()
except Exception:
    # If default I2C fails, try explicit pins (GP4=SDA, GP5=SCL for Pimoroni Pico LiPo)
    import busio
    i2c = busio.I2C(board.GP5, board.GP4)  # SCL, SDA

# Scan I2C bus to find display address
i2c_addresses = []
try:
    while not i2c.try_lock():
        pass
    i2c_addresses = i2c.scan()
    i2c.unlock()
except Exception:
    pass

# Initialize SSD1327 OLED display
# Try found addresses first, then common defaults
display = None
display_bus = None
addresses_to_try = []
# Add any found I2C addresses first (prioritize detected devices)
for addr in i2c_addresses:
    if 0x3C <= addr <= 0x3F:
        addresses_to_try.append(addr)
# Add common defaults if not already in list
if 0x3C not in addresses_to_try:
    addresses_to_try.append(0x3C)
if 0x3D not in addresses_to_try:
    addresses_to_try.append(0x3D)

for addr in addresses_to_try:
    try:
        display_bus = displayio.I2CDisplay(i2c, device_address=addr)
        display = SSD1327(display_bus, width=128, height=128)
        time.sleep(0.5)  # Longer delay for display initialization
        break  # Success, exit the loop
    except Exception:
        continue  # Try next address

# Create display group and labels
if display:
    splash = displayio.Group()
    display.show(splash)
    
    # Create "Hello" label on top line
    hello_label = label.Label(
        terminalio.FONT,
        text="Hello",
        color=0xFFFFFF,  # White for grayscale display
        x=10,
        y=10
    )
    splash.append(hello_label)
    
    # Create LED status label below
    led_label = label.Label(
        terminalio.FONT,
        text="Starting...",
        color=0xFFFFFF,  # White for grayscale display
        x=10,
        y=30
    )
    splash.append(led_label)
    
    # Force initial display update
    display.refresh()
    time.sleep(0.2)

# Calculate delay for 4Hz rate
delay_time = 1.0 / CHANGE_RATE_HZ  # 0.25 seconds

# Main loop - wipe through all LEDs
while True:
    for strip_index, strip in enumerate(strips):
        # Wipe through each LED in this strip
        for led_index in range(LEDS_PER_STRIP):
            # Turn off all LEDs in this strip
            strip.fill((0, 0, 0, 0))
            
            # Light up current LED (white)
            strip[led_index] = (255, 255, 255, 255)
            strip.show()
            
            # Update display
            if display:
                led_label.text = f"Strip {strip_index + 1}, LED {led_index + 1}"
                # displayio should auto-refresh, but explicit refresh can help
                try:
                    display.refresh()
                except AttributeError:
                    # Some displays don't have refresh method, that's OK
                    pass
            
            # Wait for 4Hz rate
            time.sleep(delay_time)
        
        # Brief pause between strips
        time.sleep(0.1)

