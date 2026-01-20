# LED Strip Menorah (CircuitPython + Gesture Control)

A menorah made from **nine NeoPixel RGBW LED strips** (8 LEDs each): **8 candles + 1 shamash**.  
Built around an **Adafruit KB2040 / Keybow 2040-class board** (or any microcontroller with ≥9 GPIO and I2C), with an **APDS-9960 gesture sensor** for night selection, lighting, and brightness control.

> **Safety note:** This is an *LED* menorah, not an open-flame device. Don’t leave it unattended if you mount it near flammable decorations, and ensure your USB power source and wiring are appropriate for the current draw.

---

## Background (Hanukkah rules the build follows)

A menorah has **8 candles + 1 shamash = 9 total**.

- **Night 1:** shamash + 1 candle  
- **Night 2:** shamash + 2 candles  
- ...
- **Night 8:** shamash + 8 candles  

This project models a “burn down” animation so the candles appear to melt down over time (default target runtime is ~40+ minutes per night).

---

## Demo Behavior (What it does)

### Phase 1 — Select night (1–8)
- The **shamash strip** displays the currently selected night by lighting **N LEDs**.
- Gestures:
  - **UP:** increase night (wraps 8 → 1)
  - **DOWN:** decrease night (wraps 1 → 8)
  - **RIGHT:** confirm selection and move to Phase 2

### Phase 2 — Light candles
- Shamash lights immediately on entering Phase 2.
- Swipe **UP or DOWN** to light the next candle (rate-limited to ~1 per second).
- Optional: light order can be reversed in code.

### Phase 3 — Burning
- Candles flicker with a layered flame animation.
- Each candle has a randomized burn duration (defaults to ~40 minutes + up to 10% variation).
- **UP / DOWN gestures change global brightness** while burning.
- Burn-down effect reduces the “wax” LED stack over time and eventually leaves a single blue “ember” LED.

### Phase 4 — (Placeholder)
- Currently keeps the display as-is after burn out.

---

## Materials

### Electronics
- **Adafruit KB2040 / Keybow 2040** (or microcontroller with **≥9 GPIO** + **I2C**)
- **9 × NeoPixel RGBW strips** (8 pixels per strip)
- **APDS-9960 gesture/proximity sensor** breakout
- Qwiic / STEMMA QT cable (or equivalent I2C wiring)
- Protoboard (or small perfboard)
- Solid-core wire (20–24 AWG recommended)
- USB-C cable + stable USB power

### Mechanical
- 3D printer (top + bottom enclosure parts)
- Glue (hot glue or CA)
- Zip tie (for bundling the strip leads)

---

## Wiring Overview

You will be building **9 independent NeoPixel outputs**:
- **8 candle strips** (one per night)
- **1 shamash strip**

### Strip wiring (repeat for each strip)
1. Solder wire leads to **5V**, **GND**, and **DATA IN** on each strip.
2. Keep wires **uniform length** to simplify routing and strain relief.
3. Label the back of strips (Night 1..8, Shamash) before assembly.

### Board + strip mapping (as coded)
The code expects the shamash on `D6`, and candles on these pins in *night order*:

- **Shamash:** `D6`
- **Night 1:** `D10`
- **Night 2:** `D2`
- **Night 3:** `D3`
- **Night 4:** `D4`
- **Night 5:** `D5`
- **Night 6:** `D7`
- **Night 7:** `D8`
- **Night 8:** `D9`

> This mapping is intentionally “physical-layout friendly” in the build, even if it looks non-sequential.

### Power & ground
- Tie all strip **5V** together and all **GND** together on the protoboard.
- Add power/ground jumpers as needed.
- Trim and inspect underside wires so nothing shorts against the case.

### Bundle + strain relief
- Bend strip leads toward a central trunk and secure with a **zip tie** before final closing.

---

## Firmware / Code Setup (CircuitPython)

### 1) Install CircuitPython
1. Put the KB2040 into bootloader mode.
2. Drag-and-drop the CircuitPython `.uf2` to the board.
3. After it mounts as `CIRCUITPY`, continue below.

### 2) Add libraries to `lib/`
Copy these into `CIRCUITPY/lib`:
- `neopixel.mpy`
- `adafruit_apds9960/` (folder)  
- `adafruit_bus_device/` (dependency folder)

(These come from the official CircuitPython library bundle.)

### 3) Copy code
- Save your main script as `code.py` on the `CIRCUITPY` drive.

### 4) Serial monitor
Use a serial monitor to see debug prints (gesture init, phase transitions, brightness changes, etc.).

---

## The “Governing Values” (tweak these first)

All the main knobs are at the top of the file:

- **Runtime**
  - `CANDLE_DURATION_MIN`
  - `CANDLE_DURATION_VARIATION`

- **Brightness**
  - `MENORAH_BRIGHTNESS_LEVELS`
  - `FLAME_START_BRIGHTNESS`, `FLAME_MAX_BRIGHTNESS`

- **Candle geometry (per strip)**
  - `LEDS_PER_STRIP` (should be 8)
  - `CANDLE_BASE_LEDS`
  - `FLAME_START_LEDS`
  - `FLAME_MAX_LEDS`

- **Color**
  - `CANDLE_BASE_COLOR` (your “wax” color, GRBW order)
  - `WARM_COLOR` (the warm white used in some phases)
  - `FLAME_COLORS` / `FLAME_COLOR_WHITE` (flicker palette)

- **Behavior toggles**
  - `LIGHTING_REVERSE_ORDER` (true = light from far side back toward shamash)
  - `ANIMATION_OPTION` (1–9)
  - `TEST_MODE` (true = skip phases and burn all candles for animation testing)

---

## 3D Printing

Print:
- **Top enclosure**
- **Bottom enclosure**

Recommended workflow:
1. Dry-fit everything first (board, sensor, strip exits).
2. Confirm the **orientation** of the sensor window and the board cutouts before gluing.

---

## Assembly Steps

1. **Bench test electronics**
   - Flash `code.py`
   - Confirm strips light
   - Confirm gesture sensor initializes (serial print)

2. **Mount protoboard into bottom case**
   - Dry fit first
   - Glue in place **with correct orientation**

3. **Mount gesture sensor into top case**
   - Ensure gesture window is facing outward
   - Glue carefully

4. **Route strips + wiring**
   - Thread strips and wires through the top case
   - Bundle leads, zip-tie for strain relief

5. **Close the case**
   - Glue halves together
   - Carefully bend strips into their final candle positions

---

## Usage Instructions

1. Plug in via USB-C.
2. **Select night** (1–8) using gestures (UP/DOWN), then confirm with RIGHT.
3. Shamash lights on entry to lighting.
4. Swipe UP/DOWN to light each candle sequentially.
5. Candles animate and “burn down” over the runtime.
6. During burning, swipe UP/DOWN to change brightness.

---

## Troubleshooting

### Gesture sensor not detected
- If you see `APDS-9960 not found`, check:
  - I2C wiring (SDA/SCL + 3V/5V + GND as required by your breakout)
  - Correct library folders in `lib/`
  - Cable orientation (Qwiic/STEMMA QT)

### Colors look “wrong”
- Your strips appear to be **GRBW** order (not the most common RGBW ordering).
- If colors don’t match expectations, verify `PIXEL_ORDER` and your color tuple ordering.

### Flicker too dim / too bright
- Adjust:
  - `MENORAH_BRIGHTNESS_LEVELS`
  - `FLAME_START_BRIGHTNESS`, `FLAME_MAX_BRIGHTNESS`
  - `CANDLE_BASE_BRIGHTNESS`

### Power resets / instability
- 9 strips × 8 pixels = 72 RGBW pixels total.
- Reduce brightness and confirm your USB power supply can handle the load.

---

## Project Structure (suggested)

