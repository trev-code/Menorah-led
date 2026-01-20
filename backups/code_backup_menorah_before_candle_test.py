# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""Light Box for Adafruit Keybow 2040
Nine RGBW NeoPixel strips (8 LEDs each) - Morning light with warm sequential fade-in.
Gesture control via APDS-9960 to switch brightness modes.
Party mode activated by proximity (hold close for 3 seconds).
"""

import time
import board
import neopixel
import math
import random

# Configuration
NUM_STRIPS = 9
LEDS_PER_STRIP = 8
FADE_DURATION = 5.0  # seconds for each LED to fade in
LED_DELAY = 0.05  # Delay between each LED starting (seconds)
STRIP_DELAY_LEDS = 4  # Next strip starts when previous has this many LEDs started
PIXEL_ORDER = neopixel.RGBW  # Confirmed: RGBW order (not GRBW)

# Default brightness - start dim for menorah use
DEFAULT_BRIGHTNESS = 0.05  # 5% - dim default for menorah

# Brightness modes (0.0 to 1.0)
BRIGHTNESS_MODES = [0.25, 0.50, 0.75, 0.99]  # 25%, 50%, 75%, 99%
current_mode_index = 0  # Start at first brightness mode
TARGET_BRIGHTNESS = DEFAULT_BRIGHTNESS  # Start at dim default

# Warm color (warmer white - more red/orange, less green and blue)
# Warm white ~2700K-3000K color temperature - incandescent-like
WARM_COLOR = (50, 255, 5, 180)  # Green Red Blue White

# Shimmer effect configuration (for light box mode)
SHIMMER_BRIGHTNESS_AMOUNT = 0.15  # Brightness variation amount (15% of base brightness)
SHIMMER_SPEED = 0.3  # Speed of shimmer wave (higher = faster)

# Menorah mode configuration
MENORAH_DEBUG_MODE = True  # Set to True to boot directly into menorah mode
MENORAH_LOCK_MODE = False  # Set to True to lock into menorah mode (can't exit)
MENORAH_FLICKER_AMOUNT = 0.25  # Brightness variation for flame flicker (25%)
MENORAH_FLICKER_SPEED = 0.2  # Speed of flame flicker (higher = faster)
# Flame colors - oscillates between these two colors
MENORAH_FLAME_COLOR_1 = WARM_COLOR  # Start with warm color from light box
MENORAH_FLAME_COLOR_2 = (60, 255, 10, 200)  # Slightly brighter/warmer variant (G, R, B, W)
# Menorah brightness levels
MENORAH_BRIGHTNESS_LEVELS = [0.10, 0.20, 0.30, 0.40, 0.50]  # 10%, 20%, 30%, 40%, 50%
menorah_brightness_index = 2  # Start at 30%
# Menorah nights (number of candles to light, not including shamash)
# Night 1: shamash + 1 candle, Night 2: shamash + 2 candles, ..., Night 8: shamash + 8 candles
MENORAH_NIGHTS = list(range(1, 9))  # 1-8 nights (8 nights of Hanukkah)
menorah_night_index = 0  # Start at night 1 (shamash + 1 candle)

# Party mode brightness levels
PARTY_BRIGHTNESS_LEVELS = [0.25, 0.50, 0.75, 1.0]  # 25%, 50%, 75%, 100%
party_brightness_index = 2  # Start at 75%

# Party mode animation modes
PARTY_MODES = ["Rainbow", "Chase", "Pulse", "Twinkle", "Wave", "Strip Chase", "Alternating", "Spiral", "Fireworks", "Matrix"]
party_mode_index = 0

# Proximity settings
PROXIMITY_THRESHOLD = 10  # Proximity value to consider "close" (0-255) - start low for testing
PROXIMITY_HOLD_TIME = 3.0  # Seconds to hold proximity to activate/deactivate

# NeoPixel strip pins (in order) - pins 2 to 10 on Adafruit Keybow 2040
# If your board uses GP naming instead of D naming, use: [board.GP2, board.GP3, ..., board.GP10]
STRIP_PINS = [board.D2, board.D3, board.D4, board.D5, board.D6, board.D7, board.D8, board.D9, board.D10]

# Initialize APDS-9960 gesture sensor
try:
    from adafruit_apds9960.apds9960 import APDS9960
    i2c = board.I2C()
    apds = APDS9960(i2c)
    apds.enable_proximity = True
    apds.enable_gesture = True
    apds.gesture_gain = 0  # Set gain (0-3, higher = more sensitive)
    apds.proximity_gain = 3  # Set proximity gain (0-3, higher = more sensitive) - max sensitivity
    # Wait a bit for proximity to initialize
    time.sleep(0.1)
    GESTURE_ENABLED = True
    print("APDS-9960 gesture sensor initialized")
    # Test proximity reading
    test_prox = apds.proximity
    print(f"Initial proximity reading: {test_prox}")
except Exception as e:
    print(f"APDS-9960 not found: {e}")
    GESTURE_ENABLED = False
    apds = None

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

# Party mode animation functions
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

def update_party_rainbow(frame, brightness):
    """Rainbow animation for party mode"""
    for strip_index, strip in enumerate(strips):
        for led_index in range(LEDS_PER_STRIP):
            # Create rainbow effect
            hue = ((frame * 2 + strip_index * 32 + led_index * 4) % 256)
            r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness))
            strip[led_index] = (r, g, b, w)

def update_party_chase(frame, brightness):
    """Chase animation for party mode"""
    for strip_index, strip in enumerate(strips):
        strip.fill((0, 0, 0, 0))
        chase_pos = (frame + strip_index * 2) % LEDS_PER_STRIP
        r, g, b, w = hsv_to_rgbw((frame * 5) % 256, 255, int(255 * brightness))
        strip[chase_pos] = (r, g, b, w)
        if chase_pos > 0:
            fade = int(255 * brightness * 0.5)
            strip[chase_pos - 1] = (r // 2, g // 2, b // 2, w // 2)

def update_party_pulse(frame, brightness):
    """Pulse animation for party mode"""
    pulse = (math.sin(frame * 0.1) + 1) / 2  # 0 to 1
    pulse_brightness = brightness * (0.3 + pulse * 0.7)
    r, g, b, w = hsv_to_rgbw((frame * 3) % 256, 255, int(255 * pulse_brightness))
    color = (r, g, b, w)
    for strip in strips:
        strip.fill(color)

def update_party_twinkle(frame, brightness):
    """Twinkle animation for party mode"""
    if frame % 3 == 0:  # Update every 3 frames
        for strip in strips:
            for led_index in range(LEDS_PER_STRIP):
                if random.randint(0, 100) < 15:  # 15% chance to twinkle
                    hue = random.randint(0, 255)
                    r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness))
                    strip[led_index] = (r, g, b, w)
                else:
                    # Fade out
                    r, g, b, w = strip[led_index]
                    strip[led_index] = (r * 9 // 10, g * 9 // 10, b * 9 // 10, w * 9 // 10)

def update_party_wave(frame, brightness):
    """Wave animation moving across strips"""
    wave_speed = 0.3
    wave_length = LEDS_PER_STRIP * 2
    for strip_index, strip in enumerate(strips):
        for led_index in range(LEDS_PER_STRIP):
            # Create wave effect across strips
            wave_pos = (frame * wave_speed + strip_index * 2 + led_index * 0.5) % wave_length
            wave_intensity = (math.sin(wave_pos * math.pi / wave_length) + 1) / 2
            hue = ((frame * 2 + strip_index * 51) % 256)
            r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness * wave_intensity))
            strip[led_index] = (r, g, b, w)

def update_party_strip_chase(frame, brightness):
    """Chase effect that moves between strips"""
    # Clear all strips
    for strip in strips:
        strip.fill((0, 0, 0, 0))
    
    # Calculate which strip and LED position
    total_positions = NUM_STRIPS * LEDS_PER_STRIP
    chase_pos = frame % total_positions
    strip_index = chase_pos // LEDS_PER_STRIP
    led_index = chase_pos % LEDS_PER_STRIP
    
    # Set the chase LED
    hue = (frame * 10) % 256
    r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness))
    strips[strip_index][led_index] = (r, g, b, w)
    
    # Add trailing effect
    for i in range(1, 4):
        prev_pos = (chase_pos - i) % total_positions
        prev_strip = prev_pos // LEDS_PER_STRIP
        prev_led = prev_pos % LEDS_PER_STRIP
        fade = int(255 * brightness * (1.0 - i * 0.25))
        if fade > 0:
            strips[prev_strip][prev_led] = (r * fade // 255, g * fade // 255, b * fade // 255, w * fade // 255)

def update_party_alternating(frame, brightness):
    """Alternating colors between strips"""
    for strip_index, strip in enumerate(strips):
        # Alternate between two colors
        color_index = (strip_index + (frame // 10)) % 2
        if color_index == 0:
            hue = (frame * 3) % 256
        else:
            hue = ((frame * 3) + 128) % 256
        r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness))
        strip.fill((r, g, b, w))

def update_party_spiral(frame, brightness):
    """Spiral effect rotating across strips"""
    spiral_speed = 0.2
    for strip_index, strip in enumerate(strips):
        for led_index in range(LEDS_PER_STRIP):
            # Create spiral effect
            angle = (frame * spiral_speed + strip_index * 0.4 + led_index * 0.3) % (math.pi * 2)
            spiral_intensity = (math.sin(angle) + 1) / 2
            hue = ((frame * 2 + strip_index * 51 + led_index * 8) % 256)
            r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness * (0.3 + spiral_intensity * 0.7)))
            strip[led_index] = (r, g, b, w)

def update_party_fireworks(frame, brightness):
    """Random fireworks bursts on different strips"""
    if frame % 5 == 0:  # Update every 5 frames
        # Random chance to create new firework
        if random.randint(0, 100) < 20:  # 20% chance
            strip_index = random.randint(0, NUM_STRIPS - 1)
            led_index = random.randint(0, LEDS_PER_STRIP - 1)
            hue = random.randint(0, 255)
            r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness))
            strips[strip_index][led_index] = (r, g, b, w)
    
    # Fade all LEDs
    for strip in strips:
        for led_index in range(LEDS_PER_STRIP):
            r, g, b, w = strip[led_index]
            strip[led_index] = (r * 92 // 100, g * 92 // 100, b * 92 // 100, w * 92 // 100)

def update_party_matrix(frame, brightness):
    """Matrix rain effect across strips"""
    if frame % 2 == 0:  # Update every 2 frames
        for strip_index, strip in enumerate(strips):
            # Shift all LEDs down
            for led_index in range(LEDS_PER_STRIP - 1, 0, -1):
                strip[led_index] = strip[led_index - 1]
                # Fade as it falls
                r, g, b, w = strip[led_index]
                strip[led_index] = (r * 85 // 100, g * 85 // 100, b * 85 // 100, w * 85 // 100)
            
            # Random chance to start new drop at top
            if random.randint(0, 100) < 30:  # 30% chance
                hue = random.randint(85, 170)  # Green-ish range
                r, g, b, w = hsv_to_rgbw(hue, 255, int(255 * brightness))
                strip[0] = (r, g, b, w)
            else:
                strip[0] = (0, 0, 0, 0)

def update_shimmer(frame, base_brightness):
    """Shimmer effect - flowing brightness modulation across LEDs"""
    r, g, b, w = WARM_COLOR
    for strip_index, strip in enumerate(strips):
        for led_index in range(LEDS_PER_STRIP):
            # Create flowing wave effect
            wave_pos = (frame * SHIMMER_SPEED + strip_index * 0.5 + led_index * 0.3)
            shimmer_variation = (math.sin(wave_pos) + 1) / 2  # 0 to 1
            # Apply shimmer: base brightness ± variation amount
            shimmer_brightness = base_brightness * (1.0 - SHIMMER_BRIGHTNESS_AMOUNT + 
                                                   shimmer_variation * SHIMMER_BRIGHTNESS_AMOUNT * 2)
            scale = shimmer_brightness / BRIGHTNESS_MODES[-1] if BRIGHTNESS_MODES[-1] > 0 else 0.0
            strip[led_index] = (
                int(r * scale),
                int(g * scale),
                int(b * scale),
                int(w * scale)
            )

def update_menorah_flame(frame, brightness):
    """Flame flicker effect for menorah candle (first strip)"""
    # Oscillate between two colors with flicker
    flicker = (math.sin(frame * MENORAH_FLICKER_SPEED) + 1) / 2  # 0 to 1
    # Add random flicker variation
    random_flicker = random.uniform(-MENORAH_FLICKER_AMOUNT, MENORAH_FLICKER_AMOUNT)
    flicker_brightness = brightness * (1.0 + random_flicker)
    flicker_brightness = max(0.0, min(1.0, flicker_brightness))  # Clamp to 0-1
    
    # Interpolate between two flame colors
    r1, g1, b1, w1 = MENORAH_FLAME_COLOR_1
    r2, g2, b2, w2 = MENORAH_FLAME_COLOR_2
    # Use flicker to blend between colors
    blend = (math.sin(frame * MENORAH_FLICKER_SPEED * 0.7) + 1) / 2  # Slower color oscillation
    r = int(r1 + (r2 - r1) * blend)
    g = int(g1 + (g2 - g1) * blend)
    b = int(b1 + (b2 - b1) * blend)
    w = int(w1 + (w2 - w1) * blend)
    
    # Apply brightness with flicker
    scale = flicker_brightness / BRIGHTNESS_MODES[-1] if BRIGHTNESS_MODES[-1] > 0 else 0.0
    color = (
        int(r * scale),
        int(g * scale),
        int(b * scale),
        int(w * scale)
    )
    
    # Apply to first strip (shamash candle)
    strips[0].fill(color)

def update_menorah_strips(nights, brightness):
    """Light up the specified number of candles for menorah (reversed direction)
    nights: number of candles to light (1-8), not including the shamash
    Strip 0 = shamash (always lit with flame flicker)
    Strips 1-8 = the 8 candles for the 8 nights (reversed: last strip lights first)
    Night 1: shamash + 1 candle (strip 8 - the last one)
    Night 2: shamash + 2 candles (strips 7-8)
    ...
    Night 8: shamash + 8 candles (strips 1-8 - all of them)
    """
    r, g, b, w = WARM_COLOR
    scale = brightness / BRIGHTNESS_MODES[-1] if BRIGHTNESS_MODES[-1] > 0 else 0.0
    color = (
        int(r * scale),
        int(g * scale),
        int(b * scale),
        int(w * scale)
    )
    
    # Light up strips from the end backwards (strip 0 is the shamash with flame, always lit separately)
    # Night 1: light strip 8 (1 candle - the last one)
    # Night 2: light strips 7-8 (2 candles)
    # Night 8: light strips 1-8 (8 candles - all of them)
    # Start from strip 8 and work backwards
    start_strip = 8  # Last candle strip (strip 8)
    end_strip = start_strip - nights + 1  # Go backwards for 'nights' number of strips
    
    for strip_index in range(end_strip, start_strip + 1):
        if strip_index >= 1 and strip_index < NUM_STRIPS:
            strips[strip_index].fill(color)
    
    # Turn off remaining strips (strips before the lit ones)
    for strip_index in range(1, end_strip):
        strips[strip_index].fill((0, 0, 0, 0))

# Skip fade-in sequence - start directly with dim light
print("Starting in Light Box Mode (dim default)")
print("Light Box Mode: UP=cycle brightness, DOWN=toggle on/off")
print("Hold hand close for 3 seconds while LEDs are OFF to enter Menorah Mode")
if MENORAH_DEBUG_MODE:
    print("*** MENORAH DEBUG MODE: Booting directly into Menorah Mode ***")

# State tracking
current_brightness = DEFAULT_BRIGHTNESS  # Start at dim default
leds_on = True  # Track if LEDs are on or off
party_mode = False  # Track if in party mode
menorah_mode = MENORAH_DEBUG_MODE  # Start in menorah mode if debug flag is set
last_gesture_time = time.monotonic()
gesture_cooldown = 0.5  # Prevent gesture spam (0.5 seconds)
transition_speed = 0.02  # How fast to change brightness per update
menorah_frame = 0  # Frame counter for menorah mode

# Proximity tracking - simplified state machine
proximity_state = "idle"  # idle, detecting, holding
proximity_state_start = 0
party_frame = 0
update_interval = 0.02  # Update every 20ms for smooth animation
last_mode_switch_time = 0  # Cooldown after mode switch
mode_switch_cooldown = 2.0  # Wait 2 seconds after switch before allowing another
last_proximity_check = 0
proximity_check_interval = 0.05  # Check proximity every 50ms

while True:
    current_time = time.monotonic()
    loop_start = current_time
    
    # Check proximity more frequently with dedicated timing
    if (current_time - last_proximity_check) >= proximity_check_interval:
        last_proximity_check = current_time
        cooldown_elapsed = current_time - last_mode_switch_time
        can_switch = cooldown_elapsed >= mode_switch_cooldown
        
        if GESTURE_ENABLED and apds:
            try:
                proximity = apds.proximity
                
                if proximity >= PROXIMITY_THRESHOLD:
                    # Proximity detected
                    if proximity_state == "idle":
                        proximity_state = "detecting"
                        proximity_state_start = current_time
                        print(f"Proximity detected! Hold for {PROXIMITY_HOLD_TIME}s...")
                    elif proximity_state == "detecting":
                        # Still detecting, check if we've held long enough
                        elapsed = current_time - proximity_state_start
                        # Print progress every 0.5 seconds
                        if not hasattr(apds, '_last_prox_print'):
                            apds._last_prox_print = 0
                        if (current_time - apds._last_prox_print) >= 0.5:
                            print(f"  Holding... {elapsed:.1f}s / {PROXIMITY_HOLD_TIME}s (proximity: {proximity})")
                            apds._last_prox_print = current_time
                        
                        # Check if held long enough
                        if elapsed >= PROXIMITY_HOLD_TIME:
                            if can_switch:
                                print(f"*** SWITCHING MODE! *** Elapsed: {elapsed:.2f}s")
                                
                                # Check if LEDs are off - activate menorah mode
                                if not leds_on and not menorah_mode and not party_mode:
                                    # Activate menorah mode
                                    menorah_mode = True
                                    leds_on = True
                                    print("MENORAH MODE ACTIVATED!")
                                    print(f"Night: {MENORAH_NIGHTS[menorah_night_index]}, Brightness: {MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]*100:.0f}%")
                                    print("LEFT/RIGHT=change nights, UP/DOWN=change brightness")
                                    if MENORAH_LOCK_MODE:
                                        print("(Locked in Menorah Mode)")
                                elif menorah_mode and not MENORAH_LOCK_MODE:
                                    # Exit menorah mode (if not locked)
                                    menorah_mode = False
                                    leds_on = False
                                    print("Exiting Menorah Mode - LEDs OFF")
                                elif not menorah_mode:
                                    # Toggle party mode (existing behavior)
                                    party_mode = not party_mode
                                    if party_mode:
                                        print("PARTY MODE ACTIVATED!")
                                        print(f"Mode: {PARTY_MODES[party_mode_index]}, Brightness: {PARTY_BRIGHTNESS_LEVELS[party_brightness_index]*100:.0f}%")
                                        print("UP=change mode, DOWN=change brightness, hold close 3s to exit")
                                    else:
                                        print("Returning to Light Box Mode")
                                        # Immediately refresh LEDs to warm white
                                        leds_on = True
                                        current_brightness = TARGET_BRIGHTNESS
                                        scale = current_brightness / BRIGHTNESS_MODES[-1] if BRIGHTNESS_MODES[-1] > 0 else 0.0
                                        r, g, b, w = WARM_COLOR
                                        color = (
                                            int(r * scale),
                                            int(g * scale),
                                            int(b * scale),
                                            int(w * scale)
                                        )
                                        for strip in strips:
                                            strip.fill(color)
                                            strip.show()
                                
                                proximity_state = "idle"
                                last_mode_switch_time = current_time
                                if hasattr(apds, '_last_prox_print'):
                                    delattr(apds, '_last_prox_print')
                            else:
                                # Can't switch yet, but keep holding
                                if not hasattr(apds, '_cooldown_warned') or (current_time - apds._cooldown_warned) >= 1.0:
                                    print(f"  Held long enough but in cooldown ({cooldown_elapsed:.1f}s / {mode_switch_cooldown}s)")
                                    apds._cooldown_warned = current_time
                    # If state is "holding", we just switched, so ignore
                else:
                    # Proximity lost
                    if proximity_state == "detecting":
                        # Reset to idle
                        proximity_state = "idle"
                        print("Proximity lost, resetting timer")
                        if hasattr(apds, '_last_prox_print'):
                            delattr(apds, '_last_prox_print')
            except Exception as e:
                print(f"Error reading proximity: {e}")
    
    # Handle mode-specific logic
    if menorah_mode:
        # MENORAH MODE
        menorah_frame += 1
        
        # Check for gestures in menorah mode (only if not detecting proximity)
        if GESTURE_ENABLED and apds and proximity_state != "detecting" and (current_time - last_gesture_time) >= gesture_cooldown:
            try:
                gesture = apds.gesture()
                if gesture != 0:
                    last_gesture_time = current_time
                    
                    if gesture == 3:  # LEFT - decrease nights
                        menorah_night_index = (menorah_night_index - 1) % len(MENORAH_NIGHTS)
                        print(f"Menorah Night: {MENORAH_NIGHTS[menorah_night_index]}")
                    elif gesture == 4:  # RIGHT - increase nights
                        menorah_night_index = (menorah_night_index + 1) % len(MENORAH_NIGHTS)
                        print(f"Menorah Night: {MENORAH_NIGHTS[menorah_night_index]}")
                    elif gesture == 1:  # UP - increase brightness
                        menorah_brightness_index = (menorah_brightness_index + 1) % len(MENORAH_BRIGHTNESS_LEVELS)
                        print(f"Menorah Brightness: {MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]*100:.0f}%")
                    elif gesture == 2:  # DOWN - decrease brightness
                        menorah_brightness_index = (menorah_brightness_index - 1) % len(MENORAH_BRIGHTNESS_LEVELS)
                        print(f"Menorah Brightness: {MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]*100:.0f}%")
            except Exception:
                pass  # Ignore gesture errors
        
        # Update menorah animation
        menorah_brightness = MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]
        nights = MENORAH_NIGHTS[menorah_night_index]
        
        # First strip: shamash candle with flame flicker (always lit)
        update_menorah_flame(menorah_frame, menorah_brightness)
        
        # Strips 1-8: light up candles for the current night
        update_menorah_strips(nights, menorah_brightness)
        
        # Show all strips
        for strip in strips:
            strip.show()
        
    elif party_mode:
        # PARTY MODE
        party_frame += 1
        
        # Check for gestures in party mode (only if not detecting proximity)
        if GESTURE_ENABLED and apds and proximity_state != "detecting" and (current_time - last_gesture_time) >= gesture_cooldown:
            try:
                gesture = apds.gesture()
                if gesture != 0:
                    last_gesture_time = current_time
                    
                    if gesture == 1:  # UP - change party mode
                        party_mode_index = (party_mode_index + 1) % len(PARTY_MODES)
                        print(f"Party Mode: {PARTY_MODES[party_mode_index]}")
                    elif gesture == 2:  # DOWN - change brightness
                        party_brightness_index = (party_brightness_index + 1) % len(PARTY_BRIGHTNESS_LEVELS)
                        print(f"Party Brightness: {PARTY_BRIGHTNESS_LEVELS[party_brightness_index]*100:.0f}%")
            except Exception:
                pass  # Ignore gesture errors
        
        # Update party animation
        party_brightness = PARTY_BRIGHTNESS_LEVELS[party_brightness_index]
        
        if PARTY_MODES[party_mode_index] == "Rainbow":
            update_party_rainbow(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Chase":
            update_party_chase(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Pulse":
            update_party_pulse(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Twinkle":
            update_party_twinkle(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Wave":
            update_party_wave(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Strip Chase":
            update_party_strip_chase(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Alternating":
            update_party_alternating(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Spiral":
            update_party_spiral(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Fireworks":
            update_party_fireworks(party_frame, party_brightness)
        elif PARTY_MODES[party_mode_index] == "Matrix":
            update_party_matrix(party_frame, party_brightness)
        
        # Show all strips
        for strip in strips:
            strip.show()
        
    else:
        # LIGHT BOX MODE
        # Check for gestures (only if not detecting proximity)
        if GESTURE_ENABLED and apds and proximity_state != "detecting" and (current_time - last_gesture_time) >= gesture_cooldown:
            try:
                gesture = apds.gesture()
                if gesture != 0:  # 0 = NONE
                    last_gesture_time = current_time
                    
                    # Gesture values: 1=UP, 2=DOWN, 3=LEFT, 4=RIGHT
                    if gesture == 1:  # UP - cycle through brightness modes
                        if leds_on:
                            current_mode_index = (current_mode_index + 1) % len(BRIGHTNESS_MODES)
                            new_target = BRIGHTNESS_MODES[current_mode_index]
                            TARGET_BRIGHTNESS = new_target
                            print(f"Gesture UP: Switching to {new_target*100:.0f}% brightness")
                        else:
                            print("Gesture UP: LEDs are off, swipe DOWN to turn on")
                    elif gesture == 2:  # DOWN - toggle on/off
                        leds_on = not leds_on
                        if leds_on:
                            print(f"Gesture DOWN: Turning ON at {TARGET_BRIGHTNESS*100:.0f}% brightness")
                        else:
                            print("Gesture DOWN: Turning OFF")
            except Exception:
                pass  # Ignore gesture errors
        
        # Determine target brightness based on on/off state
        if leds_on:
            target_brightness = TARGET_BRIGHTNESS
        else:
            target_brightness = 0.0
        
        # Smoothly transition to target brightness
        if abs(current_brightness - target_brightness) > 0.001:
            # Smooth transition
            if current_brightness < target_brightness:
                current_brightness = min(current_brightness + transition_speed, target_brightness)
            else:
                current_brightness = max(current_brightness - transition_speed, target_brightness)
        
        # Apply brightness to all LEDs (no shimmer in light box mode)
        if leds_on and current_brightness > 0:
            scale = current_brightness / BRIGHTNESS_MODES[-1] if BRIGHTNESS_MODES[-1] > 0 else 0.0
            r, g, b, w = WARM_COLOR
            color = (
                int(r * scale),
                int(g * scale),
                int(b * scale),
                int(w * scale)
            )
            for strip in strips:
                strip.fill(color)
        else:
            # LEDs off - clear all
            for strip in strips:
                strip.fill((0, 0, 0, 0))
        
        # Show all strips
        for strip in strips:
            strip.show()
    
    # Sleep to maintain consistent loop timing (proximity checked every iteration)
    elapsed_in_loop = time.monotonic() - loop_start
    sleep_time = max(0, update_interval - elapsed_in_loop)
    if sleep_time > 0:
        time.sleep(sleep_time)
