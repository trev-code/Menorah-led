# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""LIS2MDL Magnetometer controlling 24 RGBW LED ring."""

import time
import math
import board
import neopixel
from adafruit_lis2mdl import LIS2MDL

# Initialize I2C bus
i2c = board.I2C()

# Initialize LIS2MDL magnetometer
magnetometer = LIS2MDL(i2c)

# Neopixel setup - 24 RGBW LEDs on GP22
NEOPIXEL_PIN = board.GP22
NUM_PIXELS = 24
BRIGHTNESS = 0.25  # Max brightness 25%
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS,
                          pixel_order=neopixel.GRBW, auto_write=False)

print("LIS2MDL Magnetometer LED Ring Controller")
print("=" * 50)
print("LEDs will respond to magnetic field direction and strength")
print("=" * 50)

# Calibration values (will be set after initial readings)
min_x = max_x = 0
min_y = max_y = 0
min_z = max_z = 0
calibration_samples = 100
calibrated = False

def wheel(pos):
    """Generate rainbow colors across 0-255 positions (RGBW)."""
    pos = pos % 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3, 0)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3, 0)

def hsv_to_rgbw(h, s=255, v=255):
    """Convert HSV to RGBW. h=0-255, s=0-255, v=0-255."""
    h = h % 256
    s = max(0, min(255, s))
    v = max(0, min(255, v))
    
    if s == 0:
        return (0, 0, 0, v)  # Grayscale uses white channel
    
    region = h // 43
    remainder = (h - (region * 43)) * 6
    
    p = (v * (255 - s)) >> 8
    q = (v * (255 - ((s * remainder) >> 8))) >> 8
    t = (v * (255 - ((s * (255 - remainder)) >> 8))) >> 8
    
    if region == 0:
        r, g, b = v, t, p
    elif region == 1:
        r, g, b = q, v, p
    elif region == 2:
        r, g, b = p, v, t
    elif region == 3:
        r, g, b = p, q, v
    elif region == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    
    return (r, g, b, 0)

def calibrate_magnetometer():
    """Calibrate magnetometer by sampling magnetic field range."""
    global min_x, max_x, min_y, max_y, min_z, max_z, calibrated
    
    print("Calibrating magnetometer... Rotate the sensor slowly.")
    pixels.fill((0, 0, 0, 50))  # Dim white during calibration
    pixels.show()
    
    for i in range(calibration_samples):
        mag = magnetometer.magnetic
        x, y, z = mag
        
        if i == 0:
            min_x = max_x = x
            min_y = max_y = y
            min_z = max_z = z
        else:
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            min_z = min(min_z, z)
            max_z = max(max_z, z)
        
        if i % 10 == 0:
            print(f"Calibration: {i}/{calibration_samples}")
        time.sleep(0.05)
    
    calibrated = True
    print("Calibration complete!")
    print(f"X range: {min_x:.2f} to {max_x:.2f}")
    print(f"Y range: {min_y:.2f} to {max_y:.2f}")
    print(f"Z range: {min_z:.2f} to {max_z:.2f}")
    pixels.fill((0, 0, 0, 0))
    pixels.show()

def normalize(value, min_val, max_val):
    """Normalize value to 0-1 range."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)

def update_leds_from_magnetometer():
    """Update LED ring based on magnetometer readings."""
    mag = magnetometer.magnetic
    x, y, z = mag
    
    # Calculate magnitude (strength) of magnetic field
    magnitude = math.sqrt(x*x + y*y + z*z)
    
    # Normalize X, Y to -1 to 1 range (for direction)
    if calibrated:
        norm_x = normalize(x, min_x, max_x) * 2 - 1  # -1 to 1
        norm_y = normalize(y, min_y, max_y) * 2 - 1  # -1 to 1
    else:
        # Use raw values if not calibrated (will be less accurate)
        norm_x = x / 100.0  # Rough normalization
        norm_y = y / 100.0
        norm_x = max(-1, min(1, norm_x))
        norm_y = max(-1, min(1, norm_y))
    
    # Calculate angle from X, Y (compass direction)
    angle = math.atan2(norm_y, norm_x)
    # Convert to 0-2π range, then to 0-255 for color wheel
    angle_normalized = (angle + math.pi) / (2 * math.pi)  # 0 to 1
    hue = int(angle_normalized * 255)
    
    # Calculate brightness based on magnitude (normalize magnitude)
    # Typical range: 20-100 microtesla, scale to 0-255
    mag_normalized = min(1.0, magnitude / 100.0)  # Cap at 100 uT
    brightness = int(mag_normalized * 255)
    brightness = max(50, min(255, brightness))  # Keep visible (50-255)
    
    # Update LEDs - create a pattern based on magnetic field
    # Option 1: All LEDs show direction color with magnitude brightness
    color = hsv_to_rgbw(hue, 255, brightness)
    pixels.fill(color)
    
    # Option 2: Create a compass-like effect - one LED points in field direction (dimmed to 1%)
    # Calculate which LED should be dimmest (pointing in field direction)
    led_index = int((angle_normalized * NUM_PIXELS) % NUM_PIXELS)
    
    # Fade LEDs around the direction
    for i in range(NUM_PIXELS):
        # Calculate distance from this LED to the direction LED
        led_angle = (i * 360 / NUM_PIXELS) * math.pi / 180
        angle_diff = abs(angle - led_angle)
        # Normalize angle difference to 0-1
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff
        angle_diff_norm = angle_diff / math.pi
        
        # Inverted brightness: dimmest (1%) at direction, brighter as distance increases
        # At direction (angle_diff_norm = 0): fade = 0.01 (1%)
        # At opposite (angle_diff_norm = 1): fade = 1.0 (100%)
        fade = 0.01 + (angle_diff_norm * 0.99)  # 1% to 100% brightness
        fade = max(0.01, min(1.0, fade))
        
        # Apply magnitude-based brightness
        led_brightness = int(brightness * fade)
        led_brightness = max(3, min(255, led_brightness))  # Minimum 1% of 255 ≈ 3
        
        pixels[i] = hsv_to_rgbw(hue, 255, led_brightness)
    
    pixels.show()
    
    # Print debug info
    print(f"Mag: X={x:6.2f}, Y={y:6.2f}, Z={z:6.2f} | "
          f"Angle={math.degrees(angle):5.1f}° | "
          f"Magnitude={magnitude:5.2f}uT")

# Calibrate on startup
calibrate_magnetometer()

# Main loop
while True:
    update_leds_from_magnetometer()
    time.sleep(0.01)  # Update 100 times per second (10x faster)

