# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""Light Box for Pimoroni Pico LiPo
Five RGBW NeoPixel strips (8 LEDs each) - Morning light with warm sequential fade-in.

MILESTONE BACKUP: Light box working with:
- Sequential LED fade-in animation (4x faster)
- Warm color (green-tinted white) with correct RGBW pixel order
- Brightness monitoring to serial (dimmest pixel)
- 5 strips on GP19, GP20, GP21, GP22, GP15
"""

import time
import board
import neopixel
import math

# Configuration
NUM_STRIPS = 5
LEDS_PER_STRIP = 8
TARGET_BRIGHTNESS = 0.99  # 50% brightness
FADE_DURATION = 5.0  # seconds for each LED to fade in
LED_DELAY = 0.05  # Delay between each LED starting (seconds)
STRIP_DELAY_LEDS = 4  # Next strip starts when previous has this many LEDs started
PIXEL_ORDER = neopixel.RGBW  # Confirmed: RGBW order (not GRBW)

# Warm color (warmer white - more red/orange, less green and blue)
# RGBW format: (Red, Green, Blue, White)
# Warm white ~2700K-3000K color temperature - incandescent-like
WARM_COLOR = (5, 255, 5, 180)  # Green Red Blue White

# NeoPixel strip pins (in order)
STRIP_PINS = [board.GP19, board.GP20, board.GP21, board.GP22, board.GP15]

# Initialize NeoPixel strips
strips = []
for i, pin in enumerate(STRIP_PINS):
    strip = neopixel.NeoPixel(
        pin,
        LEDS_PER_STRIP,
        brightness=1.0,  # Set to max, we'll control per-LED via color scaling
        pixel_order=PIXEL_ORDER,
        auto_write=False
    )
    strips.append(strip)

# Set all LEDs to warm color
for strip in strips:
    strip.fill(WARM_COLOR)

# Calculate start time for each LED
led_start_times = []
for strip_index in range(NUM_STRIPS):
    strip_times = []
    for led_index in range(LEDS_PER_STRIP):
        # Calculate when this strip should start
        if strip_index == 0:
            # First strip starts immediately
            strip_start = 0.0
        else:
            # Each subsequent strip starts when previous has STRIP_DELAY_LEDS LEDs started
            strip_start = (strip_index - 1) * STRIP_DELAY_LEDS * LED_DELAY
        
        # Each LED in the strip starts slightly after the previous
        led_start = strip_start + (led_index * LED_DELAY)
        strip_times.append(led_start)
    led_start_times.append(strip_times)

# Smooth easing function (ease-in-out)
def ease_in_out(t):
    """Smooth easing function for natural fade"""
    return t * t * (3.0 - 2.0 * t)

# Main fade loop
start_time = time.monotonic()
last_update = start_time
update_interval = 0.02  # Update every 20ms for smooth animation
print_interval = 0.1  # Print brightness every 100ms
last_print = start_time

while True:
    current_time = time.monotonic()
    elapsed = current_time - start_time
    
    # Track all brightness values to find the dimmest
    brightness_values = []
    
    # Update all LEDs
    all_at_max = True
    for strip_index, strip in enumerate(strips):
        for led_index in range(LEDS_PER_STRIP):
            led_start = led_start_times[strip_index][led_index]
            
            if elapsed < led_start:
                # LED hasn't started yet - fully off
                brightness = 0.0
                all_at_max = False
            else:
                # LED has started - calculate fade progress
                fade_elapsed = elapsed - led_start
                if fade_elapsed >= FADE_DURATION:
                    # Fully faded in
                    brightness = TARGET_BRIGHTNESS
                else:
                    # Still fading - use smooth easing
                    progress = fade_elapsed / FADE_DURATION
                    eased_progress = ease_in_out(progress)
                    brightness = eased_progress * TARGET_BRIGHTNESS
                    all_at_max = False
            
            # Store brightness value
            brightness_values.append(brightness)
            
            # Apply brightness to this LED by scaling the color values
            # brightness is 0.0 to TARGET_BRIGHTNESS, scale to 0.0 to 1.0
            scale = brightness / TARGET_BRIGHTNESS if TARGET_BRIGHTNESS > 0 else 0.0
            r, g, b, w = WARM_COLOR  # RGBW order: Red, Green, Blue, White
            strip[led_index] = (
                int(r * scale),
                int(g * scale),
                int(b * scale),
                int(w * scale)
            )
    
    # Find and print dimmest pixel brightness
    if current_time - last_print >= print_interval:
        if brightness_values:
            dimmest_brightness = min(brightness_values)
            print(f"Brightness (dimmest pixel): {dimmest_brightness:.4f} ({dimmest_brightness/TARGET_BRIGHTNESS*100:.2f}%)")
        last_print = current_time
    
    # Show all strips
    for strip in strips:
        strip.show()
    
    # If all LEDs are at max, we're done fading
    if all_at_max:
        break
    
    # Sleep until next update
    next_update = last_update + update_interval
    sleep_time = max(0, next_update - current_time)
    if sleep_time > 0:
        time.sleep(sleep_time)
    last_update = current_time

# Hold at target brightness
print(f"Fade complete. All LEDs at {TARGET_BRIGHTNESS:.4f} brightness ({TARGET_BRIGHTNESS*100:.2f}%)")
while True:
    time.sleep(1.0)

