# SPDX-FileCopyrightText: 2024
# SPDX-License-Identifier: MIT

"""Menorah for Adafruit Keybow 2040
Nine RGBW NeoPixel strips (8 LEDs each) with APDS-9960 gesture control.
Phases: 1) Select night, 2) Light candles, 3) Burn animation (~40 min).
Key constants at top of file. Trevor Hoffman December 2025
"""

# Libraries Used:
# - time (standard library) - timing and delays
# - board (CircuitPython) - hardware pin definitions
# - neopixel (CircuitPython) - NeoPixel LED control
# - random (standard library) - random values for candle durations and animations
# - math (standard library) - mathematical functions for animations
# - adafruit_apds9960.apds9960 (Adafruit) - APDS-9960 gesture sensor
# - busio (CircuitPython) - I2C communication for gesture sensor

import time
import board
import neopixel
import random
import math

# ============================================================================
# MOST IMPORTANT PROGRAM CONSTANTS
# ============================================================================
# Key settings - see line references for usage locations

# Candle Burn Duration (~line 365-366, 722, 887)
CANDLE_DURATION_MIN = 2  # Minutes (e.g., 45 for ~40 min runtime)
CANDLE_DURATION_VARIATION = 0.10  # Random variation: min + random(0, variation) * min

# Default Candle Color (~line 267, 287) - Format: (G, R, B, W) GRBW order
CANDLE_BASE_COLOR = (10, 10, 255, 10)  # Blue candle base
CANDLE_BASE_BRIGHTNESS = 0.80  # Relative brightness to the flame 0.0-1.0

# Default Brightness Settings (~line 84, 746, 950, 971, 989, 993)
MENORAH_BRIGHTNESS_LEVELS = [0.01, 0.06, 0.20, 0.50, 0.99]  # 1%, 6%, 20%, 50%, 99%
menorah_brightness_index = 2  # Current level index

# Flame Brightness (~line 221, 223, 692, 693, 726, 727, 850, 893, 894)
FLAME_START_BRIGHTNESS = 0.50  # Initial brightness 0.0-1.0
FLAME_MAX_BRIGHTNESS = 0.80  # Max brightness 0.0-1.0

# ============================================================================
# Hardware Configuration
# ============================================================================
LEDS_PER_STRIP = 8  # Number of LEDs per strip
NUM_CANDLES = 8  # Number of candles (8 nights of Hanukkah)
PIXEL_ORDER = neopixel.RGBW  # Pixel color order: GRBW (Green, Red, Blue, White)
# Idk why my LEDs are in GRBW order, but they are. it doesnt match.

# Menorah Night Configuration (~line 53, 619, 622, 625, 870)
MENORAH_NIGHTS = list(range(1, 9))  # Nights 1-8 (shamash + N candles)
menorah_night_index = 3  # Current night index

# Startup Configuration (~line 608)
STARTUP_BRIGHTNESS = MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]

# Candle Color Configuration (~line 552, 607) - Format: (G, R, B, W) GRBW order
WARM_COLOR = (50, 255, 5, 180)  # Warm white ~2700K-3000K

# Menorah Phases: 1) Night selection, 2) Lighting, 3) Burning, 4) Out

# Candle LED Configuration (~line 219, 689, 723, 890)
# Adjusts how many LEDs are part of the candle base and flame animation
# Typical range for bases: 2-6, flames: 2-6
CANDLE_BASE_LEDS = 5    # Number of LEDs for candle base (static color, bottom of strip)
FLAME_START_LEDS = 3    # Number of LEDs for flame when candle is first lit (top of strip)
FLAME_MAX_LEDS = 5      # Maximum number of LEDs flame can grow to
# ----------------------------------------------------------------

# Test Mode Configuration (~line 401-402, 863, 913)
TEST_MODE = True  # If True, skip to phase 3 with all 9 candles burning
ANIMATION_OPTION = 6  # Animation option to test (1-9, see ~line 440-544 for animation definitions)

# Phase 2 (Lighting) Configuration
LIGHTING_GESTURE_TIMEOUT = 1.0  # Seconds between gesture and next candle
LIGHTING_REVERSE_ORDER = True  # Light candles in reverse order

# Flame Color Palette (~line 310-313) - Format: (G, R, B, W) GRBW order
FLAME_COLOR_RED = (5, 255, 5, 50)
FLAME_COLOR_ORANGE = (30, 255, 5, 80)
FLAME_COLOR_YELLOW = (70, 255, 5, 120)
FLAME_COLOR_WHITE = (100, 150, 50, 255)  # White flicker layer
FLAME_COLORS = [FLAME_COLOR_RED, FLAME_COLOR_ORANGE, FLAME_COLOR_YELLOW]

# Animation Speed Configuration (~line 411-412)
ANIMATION_SPEED = 0.5  # Multiplier: 1.0=normal, 2.0=2x faster, 0.5=2x slower
ANIMATION_VARIATION = 0.2  # Per-candle speed variation: SPEED * (1.0 ± VARIATION)

# Phase 2 Proximity Configuration (unused - kept for reference)
PROXIMITY_THRESHOLD = 10  # Proximity "close" threshold (0-255)
PROXIMITY_HOLD_TIME = 3.0  # Seconds to hold proximity

# Physical Candle-to-Strip Mapping (offset by one position)
# Night 1: Strip 8 (D10), Night 2: Strip 0 (D2), Night 3: Strip 1 (D3), Night 4: Strip 2 (D4)
# Shamash: Strip 4 (D6), Night 5: Strip 3 (D5), Night 6: Strip 5 (D7), Night 7: Strip 6 (D8), Night 8: Strip 7 (D9)


# NeoPixel Strip Pin Configuration
SHAMASH_PIN = board.D6  # Shamash candle pin
# Candle pins array: [0]=Night 1, [1]=Night 2, ..., [7]=Night 8 (D2-D10 on Keybow 2040)
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
try:
    from adafruit_apds9960.apds9960 import APDS9960
    try:
        import busio
        i2c = busio.I2C(board.SCL, board.SDA)  # Try explicit I2C first
    except (AttributeError, ImportError):
        i2c = board.I2C()  # Fall back to board.I2C()
    apds = APDS9960(i2c)
    apds.enable_proximity = True
    apds.proximity_gain = 3  # Max sensitivity (0-3)
    apds.enable_gesture = True
    apds.gesture_gain = 3  # Max sensitivity (0-3)
    time.sleep(0.5)  # Sensor initialization delay
    GESTURE_ENABLED = True
    print("APDS-9960 gesture sensor initialized")
except Exception as e:
    print(f"APDS-9960 not found: {e}")
    GESTURE_ENABLED = False
    apds = None

# Initialize NeoPixel Strips (brightness=1.0, controlled via color scaling)
shamash_strip = neopixel.NeoPixel(SHAMASH_PIN, LEDS_PER_STRIP, brightness=1.0, pixel_order=PIXEL_ORDER, auto_write=False)
candle_strips = []  # [0]=Night 1, [1]=Night 2, ..., [7]=Night 8
for pin in CANDLE_PINS:
    candle_strips.append(neopixel.NeoPixel(pin, LEDS_PER_STRIP, brightness=1.0, pixel_order=PIXEL_ORDER, auto_write=False))

# Candle State Structure
class CandleState:
    def __init__(self):
        self.placed = False  # Placed in phase 2
        self.lit = False  # Lit in phase 2
        self.burn_start_time = None  # Phase 3 start time
        self.duration_minutes = None  # Random duration assigned at lighting
        self.candle_base_leds = CANDLE_BASE_LEDS  # Base LEDs (decreases over time)
        self.flame_leds = FLAME_START_LEDS  # Flame LEDs (increases over time)
        self.flame_brightness = FLAME_START_BRIGHTNESS  # Current brightness
        # Animation state
        self.base_flame_brightness = FLAME_START_BRIGHTNESS  # Base brightness from burn progress
        self.base_flame_leds = FLAME_START_LEDS  # Base flame size from burn progress
        self.flame_color_index = 0  # Current color in palette
        self.flame_color_mix = 0.0  # Color mix factor 0.0-1.0
        self.white_flicker = 0.0  # White flicker amount 0.0-1.0
        self.animation_speed = 1.0  # Per-candle speed multiplier
        self.animation_phase_offset = random.uniform(0, math.pi * 2)  # Random phase offset
        self.flame_led_brightness = [1.0] * FLAME_MAX_LEDS  # Per-LED brightness for upward traveling effects
        self.candle_base_led_brightness = [1.0] * CANDLE_BASE_LEDS  # Per-LED brightness for candle base (dimmer than flame)

# Initialize candle states (8 regular candles + 1 shamash = 9 total)
candle_states = [CandleState() for _ in range(NUM_CANDLES + 1)]  # +1 for shamash

def update_candle_display(candle_index, brightness_scale=1.0):
    """Update display for a single candle based on its state
    
    Args:
        candle_index: Index of candle (0-7 for regular candles, 8 for shamash)
        brightness_scale: Additional brightness scaling (0.0 to 1.0)
    """
    if candle_index >= len(candle_states):
        return
    
    # Handle shamash (index 8) - use shamash_strip
    if candle_index == 8:
        strip = shamash_strip
    elif candle_index < len(candle_strips):
        strip = candle_strips[candle_index]
    else:
        return
    
    state = candle_states[candle_index]
    
    # Clear the strip first
    strip.fill((0, 0, 0, 0))
    
    if not state.placed:
        # Candle not placed yet - do nothing
        return
    
    if not state.lit:
        # Candle placed but not lit, or burned out - show candle base
        # If burned out (candle_base_leds == 1), show single blue LED
        # If not lit yet, show dim candle base
        r, g, b, w = CANDLE_BASE_COLOR
        if state.candle_base_leds == 1:
            # Burned out - show single blue LED at full brightness
            scale = CANDLE_BASE_BRIGHTNESS * brightness_scale
        else:
            # Not lit yet - show dim candle base
            scale = CANDLE_BASE_BRIGHTNESS * 0.3 * brightness_scale
        color = (
            int(r * scale),
            int(g * scale),
            int(b * scale),
            int(w * scale)
        )
        # Show candle base (bottom LEDs)
        for i in range(min(state.candle_base_leds, LEDS_PER_STRIP)):
            strip[i] = color
        return
    
    # Candle is lit - show candle base and flame
    # Candle base (bottom LEDs, static color) - dimmer than flame
    r, g, b, w = CANDLE_BASE_COLOR
    base_brightness_mult = CANDLE_BASE_BRIGHTNESS * 0.4  # Candle base is 40% of flame brightness
    base_scale = base_brightness_mult * brightness_scale
    
    # Place candle base at bottom (LEDs 0 to candle_base_leds-1) with per-LED brightness
    for i in range(min(state.candle_base_leds, LEDS_PER_STRIP)):
        # Apply per-LED brightness multiplier (if available)
        led_brightness = state.candle_base_led_brightness[i] if i < len(state.candle_base_led_brightness) else 1.0
        led_scale = base_scale * led_brightness
        base_color = (
            int(r * led_scale),
            int(g * led_scale),
            int(b * led_scale),
            int(w * led_scale)
        )
        strip[i] = base_color
    
    # Flame (top LEDs, animated) - starts right above candle base (no gap)
    flame_start_led = state.candle_base_leds
    flame_end_led = min(state.candle_base_leds + state.flame_leds, LEDS_PER_STRIP)
    
    # Mix colors from palette (reds, oranges, yellows)
    color1_idx = int(state.flame_color_index) % len(FLAME_COLORS)
    color2_idx = (color1_idx + 1) % len(FLAME_COLORS)
    color1, color2 = FLAME_COLORS[color1_idx], FLAME_COLORS[color2_idx]
    mix = state.flame_color_mix
    r = int(color1[0] * (1 - mix) + color2[0] * mix)
    g = int(color1[1] * (1 - mix) + color2[1] * mix)
    b = int(color1[2] * (1 - mix) + color2[2] * mix)
    w = int(color1[3] * (1 - mix) + color2[3] * mix)
    
    # Add white flicker layer
    white_flicker = state.white_flicker
    wf = FLAME_COLOR_WHITE
    r = int(r * (1 - white_flicker) + wf[0] * white_flicker)
    g = int(g * (1 - white_flicker) + wf[1] * white_flicker)
    b = int(b * (1 - white_flicker) + wf[2] * white_flicker)
    w = int(w * (1 - white_flicker) + wf[3] * white_flicker)
    
    # Apply gradient brightness (brightest at bottom) + per-LED multipliers for upward traveling effects
    num_flame_leds = flame_end_led - flame_start_led
    for led_offset in range(num_flame_leds):
        led_index = flame_start_led + led_offset
        gradient_factor = 1.0 - (led_offset * 0.4 / max(1, num_flame_leds - 1))  # 1.0 to 0.6
        led_brightness_mult = state.flame_led_brightness[led_offset] if led_offset < len(state.flame_led_brightness) else 1.0
        led_scale = state.flame_brightness * gradient_factor * led_brightness_mult * brightness_scale
        
        flame_color = (
            int(r * led_scale),
            int(g * led_scale),
            int(b * led_scale),
            int(w * led_scale)
        )
        
        strip[led_index] = flame_color

def calculate_candle_duration():
    """Calculate random candle duration based on min + percentage variation
    
    Returns:
        Duration in minutes: min + random(0, variation) * min
    """
    variation_amount = random.uniform(0, CANDLE_DURATION_VARIATION) * CANDLE_DURATION_MIN
    return CANDLE_DURATION_MIN + variation_amount

def calculate_intensity_curve(burn_progress):
    """Calculate intensity curve: tame start, peak at 80%, then simmer down.
    
    Args:
        burn_progress: Burn progress 0.0 to 1.0
    
    Returns:
        Intensity multiplier 0.0 to 1.0
    """
    if burn_progress <= 0.0:
        return 0.3  # Start tame (30% intensity)
    elif burn_progress >= 1.0:
        return 0.0  # Completely burned out
    
    # Peak at 80% (0.8) of burn time
    peak_position = 0.8
    
    if burn_progress <= peak_position:
        # Ramp up from 0.3 to 1.0 over 0.0 to 0.8
        # Use smooth curve (ease-in)
        normalized = burn_progress / peak_position  # 0.0 to 1.0
        # Ease-in curve: x^2 for smooth acceleration
        intensity = 0.3 + (1.0 - 0.3) * (normalized ** 1.5)
    else:
        # Ramp down from 1.0 to 0.0 over 0.8 to 1.0
        # Use smooth curve (ease-out)
        normalized = (burn_progress - peak_position) / (1.0 - peak_position)  # 0.0 to 1.0
        # Ease-out curve: 1 - (1-x)^2 for smooth deceleration
        intensity = 1.0 - (normalized ** 1.5)
    
    return max(0.0, min(1.0, intensity))

def update_flame_animation(candle_index, frame):
    """Update flame animation with upward traveling effects.
    
    Nine animation options (1-9): slow wave, fast pulse, random bursts, ripple,
    double wave, chaotic flicker, steady flow, spiral, multi-layer.
    Base flame height: 3 LEDs, brightness tapers 50% (1.0 to 0.5).
    Animations can vary flame height above/below 3 LEDs.
    
    Args:
        candle_index: Candle index (0-7 regular, 8 shamash)
        frame: Animation frame counter
    """
    if candle_index >= len(candle_states):
        return
    
    state = candle_states[candle_index]
    if not state.lit:
        return
    
    # Select animation option
    # Test mode: Each candle displays a different animation (candle 0 = option 1, candle 1 = option 2, etc.)
    # Normal mode: All candles use ANIMATION_OPTION
    if TEST_MODE:
        option = (candle_index % 9) + 1  # Cycle through options 1-9 for each candle
    else:
        option = ANIMATION_OPTION
    
    # Initialize animation speed and phase offset if needed
    if not hasattr(state, 'animation_speed') or state.animation_speed == 1.0:
        speed_variation = random.uniform(-ANIMATION_VARIATION, ANIMATION_VARIATION)
        state.animation_speed = ANIMATION_SPEED * (1.0 + speed_variation)
    if not hasattr(state, 'animation_phase_offset'):
        state.animation_phase_offset = random.uniform(0, math.pi * 2)
    
    # Calculate intensity curve based on burn progress
    # For phase 2 (not burning yet), use low intensity (just lit)
    if state.burn_start_time is None:
        intensity_mult = 0.3  # Just lit, tame intensity
        burn_progress = 0.0
    else:
        current_time = time.monotonic()
        elapsed_minutes = (current_time - state.burn_start_time) / 60.0
        burn_progress = elapsed_minutes / state.duration_minutes if state.duration_minutes > 0 else 1.0
        intensity_mult = calculate_intensity_curve(burn_progress)
    
    animated_frame = frame * state.animation_speed
    
    # Color cycling (reds/oranges/yellows) - smooth, slow transitions
    color_speed = 0.03 * state.animation_speed  # Slower, smoother color transitions
    color_phase = (animated_frame * color_speed + candle_index * 0.3 + state.animation_phase_offset) % (len(FLAME_COLORS) * 2)
    state.flame_color_index = color_phase / 2.0
    state.flame_color_mix = (color_phase % 2.0) / 2.0
    
    # Smooth white flicker - multiple sine waves for realistic randomness
    # Use smoother, lower frequency waves for more natural flicker
    flicker_base = 0.15  # Base flicker amount
    flicker1 = 0.12 * math.sin(animated_frame * 0.08 + candle_index * 0.3 + state.animation_phase_offset)
    flicker2 = 0.08 * math.sin(animated_frame * 0.15 + candle_index * 0.5 + state.animation_phase_offset * 1.7)
    flicker3 = 0.05 * math.sin(animated_frame * 0.25 + candle_index * 0.7 + state.animation_phase_offset * 2.3)
    # Add very small random component for subtle variation (smoother than before)
    white_random = random.uniform(-0.02, 0.02)
    state.white_flicker = max(0.0, min(0.35, flicker_base + flicker1 + flicker2 + flicker3 + white_random))
    
    # Base flame height: 3 LEDs (can vary with animation)
    BASE_FLAME_HEIGHT = 3
    
    # Apply intensity curve to base brightness
    state.flame_brightness = FLAME_START_BRIGHTNESS * intensity_mult
    
    # Initialize per-LED brightness array if needed (use max possible height)
    max_flame_height = FLAME_MAX_LEDS + 1  # Allow going slightly above max
    if len(state.flame_led_brightness) < max_flame_height:
        state.flame_led_brightness.extend([1.0] * (max_flame_height - len(state.flame_led_brightness)))
    
    # Option 1: Smooth upward wave - gentle sine wave traveling upward
    if option == 1:
        wave_speed = 0.12 * state.animation_speed
        wave_position = (animated_frame * wave_speed + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 2.5)
        # Flame height varies: base 3, can dip to 2 or rise to 4
        height_variation = 1.0 * math.sin(animated_frame * 0.1 + state.animation_phase_offset)
        flame_height = int(BASE_FLAME_HEIGHT + height_variation + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(4, flame_height))  # Range: 2-4 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            wave_phase = (wave_position - i * 2.2) % (BASE_FLAME_HEIGHT * 2.5)
            wave_variation = 0.1 * math.sin(wave_phase * math.pi / (BASE_FLAME_HEIGHT * 1.25))
            state.flame_led_brightness[i] = max(0.4, min(1.1, base_brightness + wave_variation))
    
    # Option 2: Smooth upward pulse - gentle bright pulses traveling upward
    elif option == 2:
        pulse_speed = 0.25 * state.animation_speed
        pulse_position = (animated_frame * pulse_speed + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 4)
        # Flame height pulses: base 3, can dip to 2 or rise to 5
        height_pulse = 2.0 * math.sin(animated_frame * 0.15 + state.animation_phase_offset)
        flame_height = int(BASE_FLAME_HEIGHT + height_pulse + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(5, flame_height))  # Range: 2-5 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            pulse_phase = (pulse_position - i * 3.5) % (BASE_FLAME_HEIGHT * 4)
            pulse_variation = 0.15 * math.sin(pulse_phase * math.pi / (BASE_FLAME_HEIGHT * 2))
            state.flame_led_brightness[i] = max(0.4, min(1.15, base_brightness + max(0, pulse_variation)))
    
    # Option 3: Smooth random bursts - gentle bright spots moving upward
    elif option == 3:
        if not hasattr(state, '_burst_positions'):
            state._burst_positions = []
        if frame % 25 == 0:  # Spawn new burst less frequently
            if random.random() < 0.2:  # 20% chance
                state._burst_positions.append(0.0)  # Start at bottom
        # Update and remove old bursts
        new_bursts = []
        for burst_pos in state._burst_positions:
            burst_pos += 0.18 * state.animation_speed  # Slower movement
            if burst_pos < BASE_FLAME_HEIGHT + 3:
                new_bursts.append(burst_pos)
        state._burst_positions = new_bursts
        # Flame height varies with bursts: base 3, can dip to 2 or rise to 4
        height_boost = 0.0
        for burst_pos in state._burst_positions:
            if burst_pos < BASE_FLAME_HEIGHT:
                height_boost += 0.8
        # Also add base variation
        base_variation = 0.5 * math.sin(animated_frame * 0.08 + state.animation_phase_offset)
        flame_height = int(BASE_FLAME_HEIGHT + height_boost + base_variation + 0.5)
        flame_height = max(2, min(4, flame_height))  # Range: 2-4 LEDs
        state.flame_leds = flame_height
        
        # Apply bursts with smooth falloff
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            burst_boost = 0.0
            for burst_pos in state._burst_positions:
                distance = abs(i - burst_pos)
                if distance < 1.5:
                    burst_boost += 0.2 * (0.5 + 0.5 * math.cos(distance * math.pi / 1.5))
            state.flame_led_brightness[i] = max(0.4, min(1.2, base_brightness + burst_boost))
    
    # Option 4: Smooth upward ripple - gentle wave with multiple peaks
    elif option == 4:
        ripple_speed = 0.1 * state.animation_speed
        ripple_position = (animated_frame * ripple_speed + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 5)
        # Flame height ripples: base 3, can dip to 2 or rise to 4
        height_ripple = 1.0 * math.sin(animated_frame * 0.08 + state.animation_phase_offset)
        flame_height = int(BASE_FLAME_HEIGHT + height_ripple + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(4, flame_height))  # Range: 2-4 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            ripple_phase = (ripple_position - i * 4.5) % (BASE_FLAME_HEIGHT * 5)
            ripple_variation = 0.12 * math.sin(ripple_phase * math.pi / (BASE_FLAME_HEIGHT * 2.5))
            state.flame_led_brightness[i] = max(0.4, min(1.12, base_brightness + ripple_variation))
    
    # Option 5: Double wave traveling upward - two smooth waves offset
    elif option == 5:
        wave_speed = 0.14 * state.animation_speed
        wave1_pos = (animated_frame * wave_speed + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 2.5)
        wave2_pos = (animated_frame * wave_speed + state.animation_phase_offset + BASE_FLAME_HEIGHT * 1.2) % (BASE_FLAME_HEIGHT * 2.5)
        # Flame height varies with waves: base 3, can dip to 2 or rise to 4
        height_wave = 1.0 * (math.sin(animated_frame * 0.12 + state.animation_phase_offset) + 
                            math.sin(animated_frame * 0.12 + state.animation_phase_offset + math.pi / 2)) / 2.0
        flame_height = int(BASE_FLAME_HEIGHT + height_wave + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(4, flame_height))  # Range: 2-4 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            phase1 = (wave1_pos - i * 2.2) % (BASE_FLAME_HEIGHT * 2.5)
            phase2 = (wave2_pos - i * 2.2) % (BASE_FLAME_HEIGHT * 2.5)
            wave1 = 0.1 * math.sin(phase1 * math.pi / (BASE_FLAME_HEIGHT * 1.25))
            wave2 = 0.1 * math.sin(phase2 * math.pi / (BASE_FLAME_HEIGHT * 1.25))
            state.flame_led_brightness[i] = max(0.4, min(1.1, base_brightness + (wave1 + wave2) / 2.0))
    
    # Option 6: Smooth chaotic flicker - multiple sine waves for natural randomness
    elif option == 6:
        chaos_speed = 0.18 * state.animation_speed
        # Flame height flickers chaotically: base 3, can dip to 2 or rise to 4
        chaos_height_phase = (animated_frame * chaos_speed + state.animation_phase_offset) % 15
        height_wave1 = 0.8 * math.sin(chaos_height_phase)
        height_wave2 = 0.6 * math.sin(chaos_height_phase * 2.3)
        height_variation = (height_wave1 + height_wave2) / 2.0
        flame_height = int(BASE_FLAME_HEIGHT + height_variation + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(4, flame_height))  # Range: 2-4 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            chaos_phase = (animated_frame * chaos_speed - i * 2.5 + state.animation_phase_offset) % 12
            wave1 = 0.08 * math.sin(chaos_phase)
            wave2 = 0.06 * math.sin(chaos_phase * 2.1)
            wave3 = 0.04 * math.sin(chaos_phase * 3.3)
            flicker_variation = (wave1 + wave2 + wave3) / 3.0
            state.flame_led_brightness[i] = max(0.4, min(1.15, base_brightness + flicker_variation))
    
    # Option 7: Steady upward flow - smooth continuous flow moving upward
    elif option == 7:
        flow_speed = 0.16 * state.animation_speed
        flow_position = (animated_frame * flow_speed + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 2.5)
        # Flame height flows upward: base 3, can dip to 2 or rise to 5
        flow_height_phase = (animated_frame * flow_speed * 0.8 + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 3)
        height_flow = 2.0 * math.sin(flow_height_phase * math.pi / (BASE_FLAME_HEIGHT * 1.5))
        flame_height = int(BASE_FLAME_HEIGHT + height_flow + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(5, flame_height))  # Range: 2-5 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            flow_phase = (flow_position - i * 2.3) % (BASE_FLAME_HEIGHT * 2.5)
            if flow_phase < BASE_FLAME_HEIGHT:
                flow_boost = 0.15 * (0.5 + 0.5 * math.cos(flow_phase * math.pi / BASE_FLAME_HEIGHT))
            else:
                flow_boost = 0.0
            state.flame_led_brightness[i] = max(0.4, min(1.15, base_brightness + flow_boost))
    
    # Option 8: Upward spiral effect - smooth rotating brightness pattern
    elif option == 8:
        spiral_speed = 0.15 * state.animation_speed
        spiral_position = (animated_frame * spiral_speed + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 3.5)
        # Flame height spirals: base 3, can dip to 2 or rise to 4
        spiral_height_phase = (animated_frame * spiral_speed * 0.7 + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 4)
        height_spiral = 1.0 * math.sin(spiral_height_phase * 2 * math.pi / (BASE_FLAME_HEIGHT * 4))
        flame_height = int(BASE_FLAME_HEIGHT + height_spiral + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(4, flame_height))  # Range: 2-4 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            spiral_phase = (spiral_position - i * 2.8) % (BASE_FLAME_HEIGHT * 3.5)
            spiral_variation = 0.15 * math.sin(spiral_phase * 2 * math.pi / (BASE_FLAME_HEIGHT * 3.5))
            state.flame_led_brightness[i] = max(0.4, min(1.15, base_brightness + spiral_variation))
    
    # Option 9: Complex multi-layer - smooth combination of multiple effects
    elif option == 9:
        # Layer 1: Slow wave
        wave1_speed = 0.08 * state.animation_speed
        wave1_pos = (animated_frame * wave1_speed + state.animation_phase_offset) % (BASE_FLAME_HEIGHT * 2.5)
        # Layer 2: Medium pulse
        wave2_speed = 0.22 * state.animation_speed
        wave2_pos = (animated_frame * wave2_speed + state.animation_phase_offset * 1.5) % (BASE_FLAME_HEIGHT * 3.5)
        # Flame height varies with both layers: base 3, can dip to 2 or rise to 5
        height_layer1 = 1.2 * math.sin(animated_frame * wave1_speed * 0.5 + state.animation_phase_offset)
        height_layer2 = 1.6 * math.sin(animated_frame * wave2_speed * 0.7 + state.animation_phase_offset * 1.5)
        height_variation = (height_layer1 + height_layer2) / 2.0
        flame_height = int(BASE_FLAME_HEIGHT + height_variation + 0.5)  # +0.5 for proper rounding
        flame_height = max(2, min(5, flame_height))  # Range: 2-5 LEDs
        state.flame_leds = flame_height
        
        for i in range(flame_height):
            # Brightness tapers 50%: 1.0 at bottom to 0.5 at top
            base_brightness = 1.0 - (i * 0.5 / max(1, flame_height - 1))
            phase1 = (wave1_pos - i * 2.2) % (BASE_FLAME_HEIGHT * 2.5)
            phase2 = (wave2_pos - i * 3.2) % (BASE_FLAME_HEIGHT * 3.5)
            layer1 = 0.08 * math.sin(phase1 * math.pi / (BASE_FLAME_HEIGHT * 1.25))
            layer2 = 0.1 * math.sin(phase2 * math.pi / (BASE_FLAME_HEIGHT * 1.75))
            state.flame_led_brightness[i] = max(0.4, min(1.15, base_brightness + (layer1 + layer2) / 2.0))

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
    """Phase 1: Night selection function
    
    Shows number of LEDs on shamash candle to indicate selected night (1-8).
    Uses UP/DOWN gestures to change night.
    - UP (0x01): increase night (1->2->...->8->1)
    - DOWN (0x02): decrease night (8->7->...->1->8)
    - RIGHT (0x04): confirm selection and move to Phase 2
    
    Returns the selected night index (0-7 corresponding to nights 1-8).
    """
    print("Phase 1: Select Night")
    print("UP (0x01) to increase night")
    print("DOWN (0x02) to decrease night")
    print("RIGHT (0x04) to confirm and enter Phase 2")
    print("Number of LEDs on shamash indicates selected night")
    
    # Clear all strips
    shamash_strip.fill((0, 0, 0, 0))
    for strip in candle_strips:
        strip.fill((0, 0, 0, 0))
    
    # State for gesture detection
    last_gesture_time = time.monotonic()
    gesture_cooldown = 0.5  # Prevent gesture spam
    current_night_index = menorah_night_index  # Start with default night
    
    print(f"Current Night: {MENORAH_NIGHTS[current_night_index]}")
    
    # Night selection loop
    while True:
        current_time = time.monotonic()
        
        # Update shamash display - show number of LEDs equal to selected night
        selected_night = MENORAH_NIGHTS[current_night_index]
        shamash_strip.fill((0, 0, 0, 0))
        r, g, b, w = WARM_COLOR
        scale = STARTUP_BRIGHTNESS
        startup_color = (
            int(r * scale),
            int(g * scale),
            int(b * scale),
            int(w * scale)
        )
        # Light LEDs 0 to (selected_night - 1) to show the number
        for i in range(min(selected_night, LEDS_PER_STRIP)):
            shamash_strip[i] = startup_color
        shamash_strip.show()
        
        # Check for gestures
        if GESTURE_ENABLED and apds:
            cooldown_elapsed = current_time - last_gesture_time
            if cooldown_elapsed >= gesture_cooldown:
                try:
                    gesture = apds.gesture()
                    
                    if gesture != 0:  # 0 = no gesture detected
                        last_gesture_time = current_time
                        
                        # Adafruit gesture values: 0x01=UP, 0x02=DOWN, 0x03=LEFT, 0x04=RIGHT
                        if gesture == 0x01 or gesture == 1:  # UP (0x01) -> increase night
                            current_night_index = (current_night_index + 1) % len(MENORAH_NIGHTS)
                            print(f"Night: {MENORAH_NIGHTS[current_night_index]}")
                        elif gesture == 0x02 or gesture == 2:  # DOWN (0x02) -> decrease night
                            current_night_index = (current_night_index - 1) % len(MENORAH_NIGHTS)
                            print(f"Night: {MENORAH_NIGHTS[current_night_index]}")
                        elif gesture == 0x04 or gesture == 4:  # RIGHT (0x04) -> confirm and enter Phase 2
                            print(f"Night {MENORAH_NIGHTS[current_night_index]} confirmed. Entering Phase 2.")
                            return current_night_index
                        # LEFT (0x03) not used in phase 1
                except Exception:
                    pass  # Ignore gesture errors
        
        # Small delay to prevent busy loop
        time.sleep(0.05)

def phase2_lighting(nights):
    """Phase 2: Lighting - Place candles and light them one by one
    
    Step 1: Wait for proximity (3 seconds) to light shamash
    Step 2: Use gestures (left OR right) to light candles one at a time (max 1 per second)
    Animations are active during lighting.
    
    Args:
        nights: Number of candles to light (1-8), not including shamash
    
    Returns when all candles are lit, then transitions to phase 3.
    """
    print("Phase 2: Lighting Candles")
    print("Step 1: Hold hand over sensor for 3 seconds to light shamash")
    
    # Clear all candles and reset states
    for i in range(len(candle_states)):
        candle_states[i].placed = False
        candle_states[i].lit = False
        candle_states[i].burn_start_time = None
        candle_states[i].duration_minutes = None
        candle_states[i].candle_base_leds = CANDLE_BASE_LEDS
        candle_states[i].base_flame_leds = FLAME_START_LEDS
        candle_states[i].flame_leds = FLAME_START_LEDS
        candle_states[i].base_flame_brightness = FLAME_START_BRIGHTNESS
        candle_states[i].flame_brightness = FLAME_START_BRIGHTNESS
        candle_states[i].flame_color_index = 0.0
        candle_states[i].flame_color_mix = 0.0
        candle_states[i].white_flicker = 0.0
        # Initialize animation properties
        speed_variation = random.uniform(-ANIMATION_VARIATION, ANIMATION_VARIATION)
        candle_states[i].animation_speed = ANIMATION_SPEED * (1.0 + speed_variation)
        candle_states[i].animation_phase_offset = random.uniform(0, math.pi * 2)
    
    # Determine lighting order
    if LIGHTING_REVERSE_ORDER:
        candle_indices = list(range(nights - 1, -1, -1))
    else:
        candle_indices = list(range(nights))
    
    # Place all candles (but don't light them yet)
    for i in candle_indices:
        if i < len(candle_states):
            candle_states[i].placed = True
    
    # Step 1: Light shamash immediately when entering Phase 2
    print("Phase 2: Lighting shamash and candles")
    frame_counter = 0
    
    # Light shamash immediately
    shamash_state = candle_states[8]  # Shamash is index 8
    shamash_state.placed = True
    shamash_state.lit = True
    # burn_start_time will be set when entering phase 3
    shamash_state.duration_minutes = CANDLE_DURATION_MIN  # Shamash uses minimum duration
    shamash_state.candle_base_leds = CANDLE_BASE_LEDS
    shamash_state.base_flame_leds = FLAME_START_LEDS
    shamash_state.flame_leds = FLAME_START_LEDS
    shamash_state.base_flame_brightness = FLAME_START_BRIGHTNESS
    shamash_state.flame_brightness = FLAME_START_BRIGHTNESS
    speed_variation = random.uniform(-ANIMATION_VARIATION, ANIMATION_VARIATION)
    shamash_state.animation_speed = ANIMATION_SPEED * (1.0 + speed_variation)
    shamash_state.animation_phase_offset = random.uniform(0, math.pi * 2)
    print("Shamash lit!")
    
    # Step 2: Light candles one by one with gestures
    print(f"Step 2: Swipe UP (0x01) or DOWN (0x02) to light candles (max 1 per second)")
    candles_lit = 0
    last_gesture_time = time.monotonic()
    last_light_time = time.monotonic()  # Track last time a candle was lit
    gesture_cooldown = 0.3
    min_time_between_lights = 1.0  # Maximum 1 candle per second
    
    while candles_lit < nights:
        current_time = time.monotonic()
        frame_counter += 1
        
        # Update display with animations
        brightness_scale = MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]
        for i in range(nights):
            if candle_states[i].lit:
                # Update animation for lit candles
                update_flame_animation(i, frame_counter)
            update_candle_display(i, brightness_scale)
        # Update shamash with animation
        if candle_states[8].lit:
            update_flame_animation(8, frame_counter)
        update_candle_display(8, brightness_scale)
        
        # Show all strips
        shamash_strip.show()
        for strip in candle_strips:
            strip.show()
        
        # Check for gestures to light next candle (UP or DOWN)
        time_since_last_light = current_time - last_light_time
        if GESTURE_ENABLED and apds and time_since_last_light >= min_time_between_lights:
            cooldown_elapsed = current_time - last_gesture_time
            if cooldown_elapsed >= gesture_cooldown:
                try:
                    gesture = apds.gesture()
                    # UP (0x01) or DOWN (0x02) gesture lights next candle
                    if gesture == 0x01 or gesture == 1 or gesture == 0x02 or gesture == 2:
                        last_gesture_time = current_time
                        
                        if candles_lit < len(candle_indices):
                            candle_idx = candle_indices[candles_lit]
                            if candle_idx < len(candle_states):
                                candle_states[candle_idx].lit = True
                                candle_states[candle_idx].duration_minutes = calculate_candle_duration()
                                # burn_start_time will be set when entering phase 3
                                candles_lit += 1
                                last_light_time = current_time
                                print(f"Candle {candles_lit}/{nights} lit (duration: {candle_states[candle_idx].duration_minutes:.2f} min)")
                except Exception:
                    pass
        
        time.sleep(0.02)  # 50Hz update rate
    
    # All candles are lit - set burn_start_time for all lit candles (timer starts now)
    phase3_start_time = time.monotonic()
    for i in range(nights):
        if i < len(candle_states) and candle_states[i].lit:
            candle_states[i].burn_start_time = phase3_start_time
    # Also set shamash burn start time
    if 8 < len(candle_states) and candle_states[8].lit:
        candle_states[8].burn_start_time = phase3_start_time
    
    print(f"All {nights} candles + shamash lit! Entering Phase 3: Burning (timer started)")

def phase3_burning_update(nights):
    """Phase 3: Burning - Update candle burn-down and flame growth
    
    Args:
        nights: Number of candles that are lit (1-8)
    
    Returns True if all candles have burned out, False otherwise.
    """
    current_time = time.monotonic()
    all_burned_out = True
    
    for i in range(num_candles):
        if i >= len(candle_states):
            continue
        
        state = candle_states[i]
        
        if not state.lit or state.burn_start_time is None:
            continue
        
        # Calculate burn progress (0.0 to 1.0)
        elapsed_minutes = (current_time - state.burn_start_time) / 60.0
        burn_progress = elapsed_minutes / state.duration_minutes if state.duration_minutes > 0 else 1.0
        
        if burn_progress >= 1.0:
            # Candle has burned out - keep 1 blue LED
            state.lit = False
            state.flame_leds = 0
            state.flame_brightness = 0.0
            state.candle_base_leds = 1  # Stay as single blue LED after burn out
        else:
            # Candle is still burning
            all_burned_out = False
            
            # Candle base decreases in steps: 5->4->3->2->1 based on burn progress
            # 0-20%: 5 LEDs, 20-40%: 4 LEDs, 40-60%: 3 LEDs, 60-80%: 2 LEDs, 80-100%: 1 LED
            if burn_progress < 0.20:
                state.candle_base_leds = 5
            elif burn_progress < 0.40:
                state.candle_base_leds = 4
            elif burn_progress < 0.60:
                state.candle_base_leds = 3
            elif burn_progress < 0.80:
                state.candle_base_leds = 2
            else:
                state.candle_base_leds = 1
            
            # Store base values for animation (animation will modify these)
            flame_growth = burn_progress  # 0.0 to 1.0
            state.base_flame_leds = FLAME_START_LEDS + (FLAME_MAX_LEDS - FLAME_START_LEDS) * flame_growth
            state.base_flame_leds = min(state.base_flame_leds, FLAME_MAX_LEDS)
            
            state.base_flame_brightness = FLAME_START_BRIGHTNESS + (FLAME_MAX_BRIGHTNESS - FLAME_START_BRIGHTNESS) * flame_growth
            state.base_flame_brightness = min(state.base_flame_brightness, FLAME_MAX_BRIGHTNESS)
            
            # Animation will be updated in main loop
    
    return all_burned_out

def test_mode_init_all_candles():
    """Test mode: Initialize all 9 candles (8 regular + shamash) and go straight to phase 3
    
    This function sets up all candles as lit and burning for testing animation options.
    """
    print("TEST MODE: Initializing all 9 candles (8 regular + shamash)")
    print(f"Test Mode: Each candle displays a different animation (1-9)")
    print(f"Normal Mode: All candles use Animation Option: {ANIMATION_OPTION}")
    print("=" * 50)
    print("Animation Options (base height: 3 LEDs, brightness tapers 50%, height varies 2-5 LEDs):")
    print("1: Smooth upward wave - gentle sine wave traveling upward (height: 2-4 LEDs)")
    print("2: Smooth upward pulse - gentle bright pulses traveling upward (height: 2-5 LEDs)")
    print("3: Smooth random bursts - gentle bright spots moving upward (height: 2-4 LEDs)")
    print("4: Smooth upward ripple - gentle wave with multiple peaks (height: 2-4 LEDs)")
    print("5: Double wave traveling upward - two smooth waves offset (height: 2-4 LEDs)")
    print("6: Smooth chaotic flicker - multiple sine waves for natural randomness (height: 2-4 LEDs)")
    print("7: Steady upward flow - smooth continuous flow moving upward (height: 2-5 LEDs)")
    print("8: Upward spiral effect - smooth rotating brightness pattern (height: 2-4 LEDs)")
    print("9: Complex multi-layer - smooth combination of multiple effects (height: 2-5 LEDs)")
    print("=" * 50)
    
    current_time = time.monotonic()
    
    # Initialize all 9 candles (8 regular + 1 shamash)
    for i in range(9):  # 0-7 are regular candles, 8 is shamash
        if i < len(candle_states):
            candle_states[i].placed = True
            candle_states[i].lit = True
            candle_states[i].burn_start_time = current_time
            # Shamash (index 8) always uses minimum duration
            if i == 8:  # Shamash
                candle_states[i].duration_minutes = CANDLE_DURATION_MIN
            else:
                candle_states[i].duration_minutes = calculate_candle_duration()
            candle_states[i].candle_base_leds = CANDLE_BASE_LEDS
            candle_states[i].base_flame_leds = FLAME_START_LEDS
            candle_states[i].flame_leds = FLAME_START_LEDS
            candle_states[i].base_flame_brightness = FLAME_START_BRIGHTNESS
            candle_states[i].flame_brightness = FLAME_START_BRIGHTNESS
            candle_states[i].flame_color_index = 0.0
            candle_states[i].flame_color_mix = 0.0
            candle_states[i].white_flicker = 0.0
            candle_name = "Shamash" if i == 8 else f"Candle {i+1}"
            print(f"{candle_name}: Duration {candle_states[i].duration_minutes:.2f} min")
    
    print("All 9 candles initialized and burning!")
    return 9  # Return number of candles (8 regular + 1 shamash)

# Startup: Clear all LEDs to ensure clean state
# Clear all NeoPixel strips to start from a known state (especially important after bugs/crashes)
shamash_strip.fill((0, 0, 0, 0))
shamash_strip.show()
for strip in candle_strips:
    strip.fill((0, 0, 0, 0))
    strip.show()

# Startup: Night Selection (Phase 1) or Test Mode
if TEST_MODE:
    # Test Mode: Skip to phase 3 with all candles burning
    selected_nights = test_mode_init_all_candles()
    current_phase = 3  # Start in phase 3
else:
    # Normal Mode: Night selection and lighting
    menorah_night_index = select_startup_night()
    selected_nights = MENORAH_NIGHTS[menorah_night_index]
    
    # Phase 2: Lighting
    phase2_lighting(selected_nights)
    
    # Phase state tracking
    current_phase = 3  # Start in phase 3 after lighting

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
    
    if current_phase == 3:
        # Phase 3: Burning - timer started when all candles were lit in phase 2
        # Update candle burn-down and flame growth
        # Update all 9 candles (8 regular + shamash)
        num_candles = 9  # Always include shamash in phase 3
        all_burned_out = phase3_burning_update(num_candles)
        
        # Update display for all candles with animations
        brightness_scale = MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]
        for i in range(num_candles):
            if i < len(candle_states) and candle_states[i].lit:
                # Update animation for lit candles
                update_flame_animation(i, menorah_frame)
            update_candle_display(i, brightness_scale)
        
        # Update all NeoPixel strips
        shamash_strip.show()
        for strip in candle_strips:
            strip.show()
        
        # Check if all candles burned out (transition to phase 4 if needed)
        if all_burned_out:
            print("All candles have burned out")
            # TODO: Phase 4 implementation
            current_phase = 4
    
    elif current_phase == 4:
        # Phase 4: (Future implementation)
        # For now, just keep display as-is
        brightness_scale = MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]
        for i in range(selected_nights):
            update_candle_display(i, brightness_scale)
        shamash_strip.show()
        for strip in candle_strips:
            strip.show()
    
    # Gesture Detection (phase-specific behavior)
    if GESTURE_ENABLED and apds and (current_time - last_gesture_time) >= gesture_cooldown:
        try:
            gesture = apds.gesture()
            if gesture != 0:  # 0 = no gesture detected
                last_gesture_time = current_time
                
                # Adafruit gesture values: 0x01=UP, 0x02=DOWN, 0x03=LEFT, 0x04=RIGHT
                if current_phase == 3:
                    # Phase 3: UP/DOWN gestures change brightness
                    if gesture == 0x01 or gesture == 1:  # UP (0x01) -> increase brightness
                        menorah_brightness_index = (menorah_brightness_index + 1) % len(MENORAH_BRIGHTNESS_LEVELS)
                        print(f"Brightness: {MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]*100:.0f}%")
                    elif gesture == 0x02 or gesture == 2:  # DOWN (0x02) -> decrease brightness
                        menorah_brightness_index = (menorah_brightness_index - 1) % len(MENORAH_BRIGHTNESS_LEVELS)
                        print(f"Brightness: {MENORAH_BRIGHTNESS_LEVELS[menorah_brightness_index]*100:.0f}%")
                    # LEFT (0x03) and RIGHT (0x04) not used in phase 3
                else:
                    # Other phases: gestures not used (or handled elsewhere)
                    pass
        except Exception:
            pass  # Ignore gesture errors (sensor may be temporarily unavailable)
    
    # Maintain consistent loop timing (20ms update interval)
    # Calculate how long the loop took and sleep for the remainder
    elapsed_in_loop = time.monotonic() - loop_start
    sleep_time = max(0, update_interval - elapsed_in_loop)
    if sleep_time > 0:
        time.sleep(sleep_time)
