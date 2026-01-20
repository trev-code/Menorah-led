# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""Three rotary encoders controlling 24 LED RGBW Neopixel ring with animation modes."""

import time
import board
import neopixel
import random
from adafruit_seesaw import digitalio, rotaryio, seesaw

# ============================================================================
# CONFIGURATION VARIABLES - Adjust these to customize behavior
# ============================================================================

# Neopixel Configuration
NEOPIXEL_PIN = board.GP22
NUM_PIXELS = 24
MAX_BRIGHTNESS = 0.25  # Maximum brightness (0.0 to 1.0, 0.25 = 25%)
PIXEL_ORDER = neopixel.GRBW  # RGBW pixel order (GRBW or RGBW)

# Encoder I2C Addresses
ENCODER_BRIGHTNESS_ADDR = 0x36  # Encoder 1: Hue/Color (no jumpers)
ENCODER_COLOR_ADDR = 0x37       # Encoder 2: Brightness (A0 jumper)
ENCODER_SPEED_ADDR = 0x38       # Encoder 3: Speed (A1 jumper)

# Animation Configuration
ANIMATION_MODE = 0  # Starting animation mode (0-14)
ANIMATION_SPEED_MIN = 1   # Minimum speed value (fastest)
ANIMATION_SPEED_MAX = 100 # Maximum speed value (slowest)
ANIMATION_SPEED_DEFAULT = 50  # Default speed (1=fastest, 100=slowest)
ANIMATION_SPEED_DIVISOR = 5   # Speed calculation divisor

# Color Configuration
HUE_DEFAULT = 0        # Default color hue (0-255)
HUE_CHANGE_RATE = 2    # How much hue changes per encoder step

# Brightness Configuration
BRIGHTNESS_MIN = 0.01      # Minimum brightness (1% - prevents LEDs from turning off)
BRIGHTNESS_DEFAULT = 0.25  # Default brightness (MIN_BRIGHTNESS to MAX_BRIGHTNESS)
BRIGHTNESS_CHANGE_RATE = 0.01  # Brightness change per encoder step

# Animation Direction
REVERSE_DIRECTION_DEFAULT = False  # Default animation direction (False = forward)

# Animation Modes List
ANIMATION_MODES = [
    "Solid Color",
    "Rainbow Rotate",
    "Chase/Spinner",
    "Pulse/Breathe",
    "Fire/Lava",
    "Twinkle",
    "Color Wave",
    "Scanner",
    "Knight Rider",
    "Matrix Rain",
    "Plasma",
    "Spiral",
    "Bounce",
    "Strobe",
    "Comet"
]

# ============================================================================
# END CONFIGURATION - Hardware initialization below
# ============================================================================

# Initialize I2C bus
i2c = board.I2C()

# Initialize three Seesaw encoders at different addresses
seesaw_brightness = seesaw.Seesaw(i2c, addr=ENCODER_BRIGHTNESS_ADDR)  # Encoder 1: Hue/Color
seesaw_color = seesaw.Seesaw(i2c, addr=ENCODER_COLOR_ADDR)            # Encoder 2: Brightness (A0)
seesaw_index = seesaw.Seesaw(i2c, addr=ENCODER_SPEED_ADDR)            # Encoder 3: Speed (A1)

# Verify all encoders
for name, seesaw_dev, addr in [("Hue/Color", seesaw_brightness, ENCODER_BRIGHTNESS_ADDR),
                                ("Brightness", seesaw_color, ENCODER_COLOR_ADDR),
                                ("Speed", seesaw_index, ENCODER_SPEED_ADDR)]:
    try:
        product = (seesaw_dev.get_version() >> 16) & 0xFFFF
        print(f"{name} encoder (0x{addr:02X}): Found product {product}")
        if product != 4991:
            print(f"  Warning: Expected product 4991")
    except Exception as e:
        print(f"{name} encoder (0x{addr:02X}): Error - {e}")

# Configure buttons for all encoders (pin 24 on Seesaw)
for seesaw_dev in [seesaw_brightness, seesaw_color, seesaw_index]:
    seesaw_dev.pin_mode(24, seesaw_dev.INPUT_PULLUP)

button_brightness = digitalio.DigitalIO(seesaw_brightness, 24)
button_color = digitalio.DigitalIO(seesaw_color, 24)
button_index = digitalio.DigitalIO(seesaw_index, 24)

# Initialize encoders
encoder_brightness = rotaryio.IncrementalEncoder(seesaw_brightness)
encoder_color = rotaryio.IncrementalEncoder(seesaw_color)
encoder_index = rotaryio.IncrementalEncoder(seesaw_index)

# Store last positions
last_pos_brightness = -encoder_brightness.position
last_pos_color = -encoder_color.position
last_pos_index = -encoder_index.position

# Button state tracking
button_brightness_held = False
button_color_held = False
button_index_held = False

# Neopixel setup
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS_DEFAULT,
                          pixel_order=PIXEL_ORDER, auto_write=False)

# Runtime control parameters (initialized from config)
BRIGHTNESS = BRIGHTNESS_DEFAULT
hue_value = HUE_DEFAULT
animation_speed = ANIMATION_SPEED_DEFAULT
animation_frame = 0
reverse_direction = REVERSE_DIRECTION_DEFAULT

print("=" * 50)
print("Three Encoder Neopixel Controller")
print("=" * 50)
print("Encoder 1 (0x36): Hue/Color")
print("Encoder 2 (0x37): Brightness")
print("Encoder 3 (0x38): Animation Speed")
print("-" * 50)
print("Button 1: Next animation mode")
print("Button 2: Randomize all settings")
print("Button 3: Reverse animation direction")
print("=" * 50)

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

def update_animation():
    """Update pixels based on current animation mode."""
    global animation_frame
    
    # Calculate speed divisor (1=fastest, 100=slowest)
    # Lower speed_div = faster animation
    # When animation_speed = 1, multiply frame by 1000 for 1000x speed
    if animation_speed == ANIMATION_SPEED_MIN:
        effective_frame = animation_frame * 1000
        speed_div = 1
    else:
        effective_frame = animation_frame
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
    
    if ANIMATION_MODE == 0:  # Solid Color
        color = hsv_to_rgbw(hue_value, 255, 255)
        pixels.fill(color)
    
    elif ANIMATION_MODE == 1:  # Rainbow Rotate
        direction = -1 if reverse_direction else 1
        for i in range(NUM_PIXELS):
            pixel_hue = ((i * 256 // NUM_PIXELS) + hue_value + (effective_frame * direction)) % 256
            pixels[i] = wheel(pixel_hue)
    
    elif ANIMATION_MODE == 2:  # Chase/Spinner
        pixels.fill((0, 0, 0, 0))
        direction = -1 if reverse_direction else 1
        chase_pos = ((effective_frame * direction) // speed_div) % NUM_PIXELS
        if chase_pos < 0:
            chase_pos = NUM_PIXELS + chase_pos
        color = hsv_to_rgbw(hue_value, 255, 255)
        for offset in range(3):
            idx = (chase_pos + offset) % NUM_PIXELS
            fade = 255 - (offset * 85)
            r, g, b, w = color
            pixels[idx] = (r * fade // 255, g * fade // 255, b * fade // 255, w * fade // 255)
    
    elif ANIMATION_MODE == 3:  # Pulse/Breathe
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        pulse_phase = (effective_frame * 2 // speed_div) % 512
        if pulse_phase < 256:
            brightness_factor = pulse_phase
        else:
            brightness_factor = 512 - pulse_phase
        brightness_factor = 50 + (brightness_factor * 205 // 255)
        color = hsv_to_rgbw(hue_value, 255, brightness_factor)
        pixels.fill(color)
    
    elif ANIMATION_MODE == 4:  # Fire/Lava
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        for i in range(NUM_PIXELS):
            base_intensity = (i * 37 + (effective_frame * 3 // speed_div)) % 256
            intensity = (base_intensity + (i % 3) * 20) % 256
            if intensity < 85:
                pixels[i] = (intensity * 3, intensity // 3, 0, 0)
            elif intensity < 170:
                pixels[i] = (255, (intensity - 85) * 3, 0, 0)
            else:
                pixels[i] = (255, 255, (intensity - 170) * 3, 0)
    
    elif ANIMATION_MODE == 5:  # Twinkle
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        if effective_frame % (speed_div * 2) == 0:
            for i in range(NUM_PIXELS):
                if random.randint(0, 100) < 10:
                    pixels[i] = hsv_to_rgbw(hue_value + random.randint(-30, 30), 255, 255)
                else:
                    r, g, b, w = pixels[i]
                    pixels[i] = (r * 9 // 10, g * 9 // 10, b * 9 // 10, w * 9 // 10)
    
    elif ANIMATION_MODE == 6:  # Color Wave
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        direction = -1 if reverse_direction else 1
        for i in range(NUM_PIXELS):
            wave_pos = (i * 256 // NUM_PIXELS + (effective_frame * direction // speed_div)) % 256
            wave_hue = (hue_value + int(128 * (1 + (wave_pos / 128 - 1) ** 2))) % 256
            pixels[i] = hsv_to_rgbw(wave_hue, 255, 255)
    
    elif ANIMATION_MODE == 7:  # Scanner
        pixels.fill((0, 0, 0, 0))
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        direction = -1 if reverse_direction else 1
        scan_pos = ((effective_frame * direction) // speed_div) % (NUM_PIXELS * 2)
        if scan_pos < 0:
            scan_pos = NUM_PIXELS * 2 + scan_pos
        if scan_pos < NUM_PIXELS:
            color = hsv_to_rgbw(hue_value, 255, 255)
            pixels[scan_pos] = color
            if scan_pos > 0:
                fade_color = hsv_to_rgbw(hue_value, 255, 128)
                pixels[scan_pos - 1] = fade_color
        else:
            reverse_pos = NUM_PIXELS * 2 - scan_pos - 1
            color = hsv_to_rgbw(hue_value, 255, 255)
            pixels[reverse_pos] = color
            if reverse_pos < NUM_PIXELS - 1:
                fade_color = hsv_to_rgbw(hue_value, 255, 128)
                pixels[reverse_pos + 1] = fade_color
    
    elif ANIMATION_MODE == 8:  # Knight Rider
        pixels.fill((0, 0, 0, 0))
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        direction = -1 if reverse_direction else 1
        pos = ((effective_frame * direction) // speed_div) % (NUM_PIXELS * 2)
        if pos < 0:
            pos = NUM_PIXELS * 2 + pos
        if pos < NUM_PIXELS:
            pixels[pos] = hsv_to_rgbw(hue_value, 255, 255)
            if pos > 0:
                pixels[pos - 1] = hsv_to_rgbw(hue_value, 255, 128)
            if pos > 1:
                pixels[pos - 2] = hsv_to_rgbw(hue_value, 255, 64)
        else:
            rpos = NUM_PIXELS * 2 - pos - 1
            pixels[rpos] = hsv_to_rgbw(hue_value, 255, 255)
            if rpos < NUM_PIXELS - 1:
                pixels[rpos + 1] = hsv_to_rgbw(hue_value, 255, 128)
            if rpos < NUM_PIXELS - 2:
                pixels[rpos + 2] = hsv_to_rgbw(hue_value, 255, 64)
    
    elif ANIMATION_MODE == 9:  # Matrix Rain
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        for i in range(NUM_PIXELS):
            drop_pos = (i * 3 + (effective_frame // speed_div)) % (NUM_PIXELS * 2)
            if drop_pos < NUM_PIXELS:
                intensity = 255 - (drop_pos * 255 // NUM_PIXELS)
                pixels[i] = hsv_to_rgbw((hue_value + i * 10) % 256, 255, intensity)
            else:
                pixels[i] = (0, 0, 0, 0)
    
    elif ANIMATION_MODE == 10:  # Plasma
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        for i in range(NUM_PIXELS):
            angle1 = (i * 2 + effective_frame // speed_div) % 256
            angle2 = (i * 3 + effective_frame // speed_div * 2) % 256
            plasma = ((angle1 + angle2) // 2) % 256
            pixels[i] = hsv_to_rgbw((hue_value + plasma) % 256, 255, 255)
    
    elif ANIMATION_MODE == 11:  # Spiral
        pixels.fill((0, 0, 0, 0))
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        direction = -1 if reverse_direction else 1
        spiral_pos = ((effective_frame * direction) // speed_div) % NUM_PIXELS
        for i in range(3):
            idx = (spiral_pos + i) % NUM_PIXELS
            fade = 255 - (i * 85)
            pixels[idx] = hsv_to_rgbw((hue_value + idx * 10) % 256, 255, fade)
    
    elif ANIMATION_MODE == 12:  # Bounce
        pixels.fill((0, 0, 0, 0))
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        direction = -1 if reverse_direction else 1
        bounce_pos = abs(((effective_frame * direction) // speed_div) % (NUM_PIXELS * 2 - 2) - (NUM_PIXELS - 1))
        pixels[bounce_pos] = hsv_to_rgbw(hue_value, 255, 255)
        if bounce_pos > 0:
            pixels[bounce_pos - 1] = hsv_to_rgbw(hue_value, 255, 128)
        if bounce_pos < NUM_PIXELS - 1:
            pixels[bounce_pos + 1] = hsv_to_rgbw(hue_value, 255, 128)
    
    elif ANIMATION_MODE == 13:  # Strobe
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        if (effective_frame // speed_div) % 2 == 0:
            pixels.fill(hsv_to_rgbw(hue_value, 255, 255))
        else:
            pixels.fill((0, 0, 0, 0))
    
    elif ANIMATION_MODE == 14:  # Comet
        pixels.fill((0, 0, 0, 0))
        speed_div = max(1, animation_speed // ANIMATION_SPEED_DIVISOR)
        direction = -1 if reverse_direction else 1
        comet_pos = ((effective_frame * direction) // speed_div) % NUM_PIXELS
        if comet_pos < 0:
            comet_pos = NUM_PIXELS + comet_pos
        for i in range(5):
            idx = (comet_pos - i) % NUM_PIXELS
            fade = 255 - (i * 51)
            pixels[idx] = hsv_to_rgbw((hue_value + i * 20) % 256, 255, fade)
    
    pixels.show()
    animation_frame += 1

# Main loop
last_update = time.monotonic()

while True:
    current_time = time.monotonic()
    
    # Read encoder positions with error handling
    try:
        pos_brightness = -encoder_brightness.position
    except OSError:
        pos_brightness = last_pos_brightness  # Use last known position if error
    
    try:
        pos_color = -encoder_color.position
    except OSError:
        pos_color = last_pos_color  # Use last known position if error
    
    try:
        pos_index = -encoder_index.position
    except OSError:
        pos_index = last_pos_index  # Use last known position if error
    
    # Handle encoder 1: Hue/Color
    if pos_brightness != last_pos_brightness:
        change = pos_brightness - last_pos_brightness
        hue_value = (hue_value + change * HUE_CHANGE_RATE) % 256
        print(f"Color Hue: {hue_value}")
        last_pos_brightness = pos_brightness
    
    # Handle encoder 2: Brightness
    if pos_color != last_pos_color:
        change = pos_color - last_pos_color
        BRIGHTNESS = max(BRIGHTNESS_MIN, min(MAX_BRIGHTNESS, BRIGHTNESS + (change * BRIGHTNESS_CHANGE_RATE)))
        pixels.brightness = BRIGHTNESS
        print(f"Brightness: {int(BRIGHTNESS * 100)}%")
        last_pos_color = pos_color
    
    # Handle index/speed encoder (1=fastest, 100=slowest)
    if pos_index != last_pos_index:
        change = pos_index - last_pos_index
        animation_speed = max(ANIMATION_SPEED_MIN, min(ANIMATION_SPEED_MAX, animation_speed + change))
        print(f"Animation Speed: {animation_speed} (1=fastest, 100=slowest)")
        last_pos_index = pos_index
    
    # Handle button 1: Next animation mode
    try:
        if not button_brightness.value and not button_brightness_held:
            button_brightness_held = True
            ANIMATION_MODE = (ANIMATION_MODE + 1) % len(ANIMATION_MODES)
            animation_frame = 0  # Reset animation frame when changing modes
            print(f"Animation Mode: {ANIMATION_MODES[ANIMATION_MODE]}")
        
        if button_brightness.value and button_brightness_held:
            button_brightness_held = False
    except (OSError, AttributeError):
        pass  # Encoder not available, skip button handling
    
    # Handle button 2: Randomize all settings
    try:
        if not button_color.value and not button_color_held:
            button_color_held = True
            # Random brightness (MIN_BRIGHTNESS to MAX_BRIGHTNESS)
            BRIGHTNESS = random.uniform(BRIGHTNESS_MIN, MAX_BRIGHTNESS)
            # Random hue
            hue_value = random.randint(0, 255)
            # Random animation speed
            animation_speed = random.randint(ANIMATION_SPEED_MIN, ANIMATION_SPEED_MAX)
            # Random direction
            reverse_direction = random.choice([True, False])
            pixels.brightness = BRIGHTNESS
            print(f"Randomized: Brightness={int(BRIGHTNESS*100)}%, Hue={hue_value}, Speed={animation_speed}, Direction={'Reversed' if reverse_direction else 'Normal'}")
        
        if button_color.value and button_color_held:
            button_color_held = False
    except (OSError, AttributeError):
        pass  # Encoder not available, skip button handling
    
    # Handle button 3: Reverse animation direction
    try:
        if not button_index.value and not button_index_held:
            button_index_held = True
            reverse_direction = not reverse_direction
            direction_text = "Reversed" if reverse_direction else "Normal"
            print(f"Animation Direction: {direction_text}")
        
        if button_index.value and button_index_held:
            button_index_held = False
    except (OSError, AttributeError):
        pass  # Encoder not available, skip button handling
    
    # Update animation as fast as possible (no throttling for smooth animations)
    update_animation()
    
    time.sleep(0.0001)  # Ultra-minimal delay (0.1ms) for maximum refresh rate
