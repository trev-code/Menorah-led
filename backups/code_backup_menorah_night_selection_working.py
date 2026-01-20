# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""Menorah for Adafruit Keybow 2040
Nine RGBW NeoPixel strips (8 LEDs each) - Hanukkah menorah with gesture control.
Gesture control via APDS-9960: LEFT/RIGHT to change nights, UP/DOWN to change brightness.
"""

import time
import board
import neopixel

# Hardware Configuration
LEDS_PER_STRIP = 8  # Number of LEDs per strip
NUM_CANDLES = 8  # Number of candles (8 nights of Hanukkah)
PIXEL_ORDER = neopixel.RGBW  # Pixel color order: RGBW (Green, Red, Blue, White)

# Candle Color Configuration
# Warm white color for regular candles (~2700K-3000K color temperature - incandescent-like)
# Format: (Green, Red, Blue, White) - RGBW order
WARM_COLOR = (50, 255, 5, 180)  # Warm white with slight green tint

# Menorah Brightness Configuration
# Brightness levels available for menorah candles (0.0 to 1.0)
MENORAH_BRIGHTNESS_LEVELS = [0.10, 0.20, 0.30, 0.40, 0.50]  # 10%, 20%, 30%, 40%, 50%
menorah_brightness_index = 2  # Current brightness level index (starts at 30%)

# Menorah Night Configuration
# Number of candles to light for each night (1-8, not including shamash)
# Night 1: shamash + 1 candle, Night 2: shamash + 2 candles, ..., Night 8: shamash + 8 candles
MENORAH_NIGHTS = list(range(1, 9))  # 1-8 nights (8 nights of Hanukkah)
menorah_night_index = 0  # Current night index (starts at night 1)

# Startup Configuration
STARTUP_BRIGHTNESS = 0.30  # Brightness for startup LED (0.0 to 1.0)

# Physical Candle-to-Strip Mapping (offset by one position)
# This mapping defines which strip controls which night's candle
# Night 1: Strip 8 (pin 10/D10), 1 LED (LED 0)
# Night 2: Strip 0 (pin 2/D2), 2 LEDs (LEDs 0-1)
# Night 3: Strip 1 (pin 3/D3), 3 LEDs (LEDs 0-2)
# Night 4: Strip 2 (pin 4/D4), 4 LEDs (LEDs 0-3)
# Shamash: Strip 4 (pin 6/D6), 8 LEDs (LEDs 0-7), blue color
# Night 5: Strip 3 (pin 5/D5), 5 LEDs (LEDs 0-4)
# Night 6: Strip 5 (pin 7/D7), 6 LEDs (LEDs 0-5)
# Night 7: Strip 6 (pin 8/D8), 7 LEDs (LEDs 0-6)
# Night 8: Strip 7 (pin 9/D9), 8 LEDs (LEDs 0-7)


# NeoPixel Strip Pin Configuration
# Shamash candle pin (the helper candle in the middle)
SHAMASH_PIN = board.D6  # Pin 6 for shamash

# Candle pins array - order determines night order
# First element = Night 1, second = Night 2, ..., eighth = Night 8
# Pins 2 to 10 on Adafruit Keybow 2040 (D2-D10)
# If your board uses GP naming instead of D naming, use: board.GP2, board.GP3, etc.
CANDLE_PINS = [
    board.D10,  # Night 1 (first candle)
    board.D2,   # Night 2
    board.D3,   # Night 3
    board.D4,   # Night 4
    board.D5,   # Night 5
    board.D7,   # Night 6
    board.D8,   # Night 7
    board.D9,   # Night 8 (last candle)
]

# Initialize APDS-9960 Gesture Sensor
# Used for gesture control: LEFT/RIGHT to change nights, UP/DOWN to change brightness
try:
    from adafruit_apds9960.apds9960 import APDS9960
    # Try explicit I2C first, fall back to board.I2C()
    try:
        import busio
        # Use explicit I2C pins (Adafruit example style) if available
        i2c = busio.I2C(board.SCL, board.SDA)
    except (AttributeError, ImportError):
        # Fall back to board.I2C() if SCL/SDA not available
        i2c = board.I2C()
    apds = APDS9960(i2c)
    apds.enable_proximity = True  # Enable proximity (sometimes needed for gestures)
    apds.enable_gesture = True
    # Try different gain values: 0=lowest, 1=low, 2=medium, 3=highest sensitivity
    # Start with maximum sensitivity 
    apds.gesture_gain = 3  # Gesture sensitivity (0-3, higher = more sensitive) - trying maximum
    print(f"DEBUG: Gesture gain set to: {apds.gesture_gain}")
    time.sleep(0.5)  # Longer delay for sensor initialization
    GESTURE_ENABLED = True
    print("APDS-9960 gesture sensor is initialized")
except Exception as e:
    print(f"APDS-9960 not found: {e}")
    GESTURE_ENABLED = False
    apds = None

# Initialize NeoPixel Strips
# Create NeoPixel objects for shamash and candles separately
# Brightness set to max (1.0) - we control brightness via color scaling

# Shamash strip (helper candle in the middle)
shamash_strip = neopixel.NeoPixel(
    SHAMASH_PIN,
    LEDS_PER_STRIP,
    brightness=1.0,  # Maximum hardware brightness
    pixel_order=PIXEL_ORDER,
    auto_write=False  # Manual control - call strip.show() to update
)

# Candle strips (8 candles for 8 nights)
# Array order determines night order: [0] = Night 1, [1] = Night 2, ..., [7] = Night 8
candle_strips = []
for pin in CANDLE_PINS:
    strip = neopixel.NeoPixel(
        pin,
        LEDS_PER_STRIP,
        brightness=1.0,  # Maximum hardware brightness
        pixel_order=PIXEL_ORDER,
        auto_write=False  # Manual control - call strip.show() to update
    )
    candle_strips.append(strip)


def update_menorah_strips(nights, brightness):
    """Light up the specified number of candles for the current night
    
    Args:
        nights: Number of candles to light (1-8), not including the shamash
        brightness: Brightness level (0.0 to 1.0) to apply to all candles
    
    Note: The order of CANDLE_PINS array determines night order.
    Night 1: lights candle_strips[0] (first candle)
    Night 2: lights candle_strips[0-1] (first two candles)
    ...
    Night 8: lights candle_strips[0-7] (all 8 candles)
    """
    # Calculate warm white color with brightness scaling
    r, g, b, w = WARM_COLOR
    scale = brightness
    color = (
        int(r * scale),
        int(g * scale),
        int(b * scale),
        int(w * scale)
    )
    
    # Light up candles based on night number
    # Array order determines night order: [0] = Night 1, [1] = Night 2, etc.
    for i in range(nights):
        if i < len(candle_strips):
            candle_strips[i].fill(color)
    
    # Turn off any candles that should not be lit
    for i in range(nights, len(candle_strips)):
        candle_strips[i].fill((0, 0, 0, 0))

def select_startup_night():
    """Startup night selection function
    
    Lights the first LED on the shamash candle (LED 0) and waits for
    LEFT/RIGHT gestures to select the night (1-8).
    - LEFT swipe: increase night (1->2->...->8->1)
    - RIGHT swipe: decrease night (8->7->...->1->8)
    - UP swipe: confirm selection and exit
    
    Returns the selected night index (0-7 corresponding to nights 1-8).
    """
    print("Startup: Select Night")
    print("DOWN=increase night, UP=decrease night, LEFT=confirm and exit")
    
    # Clear all strips
    shamash_strip.fill((0, 0, 0, 0))
    for strip in candle_strips:
        strip.fill((0, 0, 0, 0))
    
    # Light first LED on shamash (LED 0) with startup brightness
    r, g, b, w = WARM_COLOR
    scale = STARTUP_BRIGHTNESS
    startup_color = (
        int(r * scale),
        int(g * scale),
        int(b * scale),
        int(w * scale)
    )
    shamash_strip[0] = startup_color
    shamash_strip.show()
    
    # State for gesture detection
    last_gesture_time = time.monotonic()
    gesture_cooldown = 0.5  # Prevent gesture spam
    current_night_index = menorah_night_index  # Start with default night
    
    print(f"Current Night: {MENORAH_NIGHTS[current_night_index]}")
    
    # Night selection loop
    while True:
        current_time = time.monotonic()
        
        # Check for gestures
        if GESTURE_ENABLED and apds:
            cooldown_elapsed = current_time - last_gesture_time
            if cooldown_elapsed >= gesture_cooldown:
                try:
                    # Read gesture - Adafruit example uses 0x01-0x04 values
                    gesture = apds.gesture()
                    
                    if gesture != 0:  # 0 = no gesture detected
                        last_gesture_time = current_time
                        
                        # Adafruit gesture values: 0x01=UP, 0x02=DOWN, 0x03=LEFT, 0x04=RIGHT
                        # Sensor is mounted sideways, so remap directions:
                        # LEFT (0x03) -> UP (confirm), UP (0x01) -> RIGHT (decrease), 
                        # RIGHT (0x04) -> DOWN (ignore), DOWN (0x02) -> LEFT (increase)
                        # Note: Gestures 3 and 4 are swapped
                        if gesture == 0x04 or gesture == 4:  # RIGHT gesture -> confirm selection and exit
                            print(f"Night {MENORAH_NIGHTS[current_night_index]} selected")
                            return current_night_index
                        elif gesture == 0x02 or gesture == 2:  # DOWN gesture -> increase night (1->2->...->8->1)
                            current_night_index = (current_night_index + 1) % len(MENORAH_NIGHTS)
                            print(f"Night: {MENORAH_NIGHTS[current_night_index]}")
                        elif gesture == 0x01 or gesture == 1:  # UP gesture -> decrease night (8->7->...->1->8)
                            current_night_index = (current_night_index - 1) % len(MENORAH_NIGHTS)
                            print(f"Night: {MENORAH_NIGHTS[current_night_index]}")
                        elif gesture == 0x03 or gesture == 3:  # LEFT gesture -> not used in selection
                            pass  # Ignore left gesture
                except Exception:
                    pass  # Ignore gesture errors
        
        # Small delay to prevent busy loop
        time.sleep(0.05)

# Startup: Night Selection
# Light first LED on shamash and allow user to select night via gestures
menorah_night_index = select_startup_night()

# Runtime State Variables
last_gesture_time = time.monotonic()  # Timestamp of last gesture detection
gesture_cooldown = 0.5  # Minimum time between gesture detections (prevents spam)
menorah_frame = 0  # Frame counter for animation timing
update_interval = 0.02  # Main loop update interval (20ms = 50Hz for smooth animation)

# Main Menorah Control Loop
while True:
    current_time = time.monotonic()
    loop_start = current_time
    
    # Increment frame counter for animation timing
    menorah_frame += 1
    
    # Gesture Detection and Control
    # Check for gestures if sensor is enabled and cooldown period has elapsed
    if GESTURE_ENABLED and apds and (current_time - last_gesture_time) >= gesture_cooldown:
        try:
            gesture = apds.gesture()
            if gesture != 0:  # 0 = no gesture detected
                last_gesture_time = current_time
                
                # Adafruit gesture values: 0x01=UP, 0x02=DOWN, 0x03=LEFT, 0x04=RIGHT
                # Sensor is mounted sideways, so remap directions:
                # LEFT (0x03) -> UP (increase brightness), UP (0x01) -> RIGHT (increase night),
                # RIGHT (0x04) -> DOWN (decrease brightness), DOWN (0x02) -> LEFT (decrease night)
                # Note: Gestures 3 and 4 are swapped
                if gesture == 0x04 or gesture == 4:  # RIGHT gesture -> increase brightness
                    menorah_brightness_index = (menorah_brightness_index + 1) % len(MENORAH_BRIGHTNESS_LEVELS)
                    print(f"Menorah Brightness: {MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]*100:.0f}%")
                elif gesture == 0x02 or gesture == 2:  # DOWN gesture -> decrease night (go to previous night)
                    menorah_night_index = (menorah_night_index - 1) % len(MENORAH_NIGHTS)
                    print(f"Menorah Night: {MENORAH_NIGHTS[menorah_night_index]}")
                elif gesture == 0x01 or gesture == 1:  # UP gesture -> increase night (go to next night)
                    menorah_night_index = (menorah_night_index + 1) % len(MENORAH_NIGHTS)
                    print(f"Menorah Night: {MENORAH_NIGHTS[menorah_night_index]}")
                elif gesture == 0x03 or gesture == 3:  # LEFT gesture -> decrease brightness
                    menorah_brightness_index = (menorah_brightness_index - 1) % len(MENORAH_BRIGHTNESS_LEVELS)
                    print(f"Menorah Brightness: {MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]*100:.0f}%")
        except Exception:
            pass  # Ignore gesture errors (sensor may be temporarily unavailable)
    
    # Get current menorah settings
    menorah_brightness = MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]
    nights = MENORAH_NIGHTS[menorah_night_index]
    
    # Update menorah display - light up candles for the current night
    update_menorah_strips(nights, menorah_brightness)
    
    # Update all NeoPixel strips to display the current state
    shamash_strip.show()
    for strip in candle_strips:
        strip.show()
    
    # Maintain consistent loop timing (20ms update interval)
    # Calculate how long the loop took and sleep for the remainder
    elapsed_in_loop = time.monotonic() - loop_start
    sleep_time = max(0, update_interval - elapsed_in_loop)
    if sleep_time > 0:
        time.sleep(sleep_time)
