# LED Strip Menorah (CircuitPython + Gesture Control)

A menorah made from **nine NeoPixel RGBW LED strips** (8 LEDs each): **8 candles + 1 shamash**.  
Built around an **Adafruit KB2040 / Keybow 2040-class board** (or any microcontroller with ≥9 GPIO and I2C), with an **APDS-9960 gesture sensor** for night selection, lighting, and brightness control.
---
<img width="2151" height="1619" alt="image" src="https://github.com/user-attachments/assets/b83d24cb-45f4-48f9-acff-d5a76ee948ea" />


some video: https://photos.app.goo.gl/8cVjn73NWGYfXF416
---

## Background

A menorah has **8 candles + 1 shamash = 9 total**.

- **Night 1:** shamash + 1 candle  
- **Night 2:** shamash + 2 candles  
- ...
- **Night 8:** shamash + 8 candles  

This project models a “burn down” animation so the candles appear to melt down over time (default target runtime is ~40+ minutes per night).

---

## Behavior (What it does)

### Phase 1 — Select night (1–8)
- The **shamash strip** displays the currently selected night by lighting **N LEDs**.
- Gestures:
  - **RIGHT:** increase night (wraps 8 → 1)
  - **LEFT:** decrease night (wraps 1 → 8)
  - **DOWN:** confirm selection and move to Phase 2

### Phase 2 — Light candles
- Shamash lights immediately on entering Phase 2.
- Swipe **LEFT or RIGHT** to light the next candle (rate-limited to ~1 per second).
- Optional: light direction can be reversed in code.

### Phase 3 — Burning
- Candles flicker with a layered flame animation.
- Each candle has a randomized burn duration (defaults to ~40 minutes + up to 10% variation).
- **LEFT / RIGHT gestures change global brightness** while burning.
- Burn-down effect reduces the “wax” LED stack over time and eventually leaves a single blue “ember” LED.

### Phase 4 — (Placeholder)
- Currently keeps the display as-is after burn out.
- Re-plug or press reset to start again.

---
<img width="922" height="1444" alt="image" src="https://github.com/user-attachments/assets/dda85477-0583-4842-8c90-171026e9e0b2" />
---
## Materials

### Electronics
- **Adafruit KB2040 / Keybow 2040** (or microcontroller with **≥9 GPIO** + **I2C**) https://www.adafruit.com/product/5302
- **9 × NeoPixel RGBW strips** (8 pixels per strip) https://www.adafruit.com/product/2867
- **APDS-9960 gesture/proximity sensor** breakout https://www.adafruit.com/product/3595
- Qwiic / STEMMA QT cable (or equivalent I2C wiring)
- Protoboard (or small perfboard) https://www.adafruit.com/product/1608
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
<img width="2151" height="1619" alt="image" src="https://github.com/user-attachments/assets/2f8194c6-27e6-4559-a514-8585cb6fcca1" />


### Board + strip mapping (as coded)
Before you solder the microcontroller to the protoboard, solder the USB+RAW bridge on the underside of the KB2040.
This will ensure the strips are safely pulling power directly from the USB port.
<img width="1003" height="506" alt="image" src="https://github.com/user-attachments/assets/35d4a3bd-8384-4f44-819a-7759d51bc58c" />

Next solder the microcontroller to the protoboard, ensuring the USB connector is towards the edge.
Then wire RAW pin to the 5V rail of the protoboard and install a jumper to provide power to the other power rail.
Tie Gnd pins to gnd rails of the protoboard.
<img width="792" height="911" alt="image" src="https://github.com/user-attachments/assets/111e3f50-ef52-47af-ab24-7c2d03b21919" />

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

<img width="1081" height="951" alt="image" src="https://github.com/user-attachments/assets/ff17f5de-0c20-46ce-b3d6-7112784d9697" />


> This mapping is intentionally “physical-layout friendly” in the build, even if it looks non-sequential.

### Power & ground
- Tie all strip **5V** together and all **GND** together on the protoboard.
- Add power/ground jumpers as needed.
- Trim and inspect underside wires so nothing shorts.

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
  - `FLAME_START_LEDS` changing these may cause weird behavior
  - `FLAME_MAX_LEDS`

- **Color**
  - `CANDLE_BASE_COLOR` (your “wax” color, GRBW order)
  - `WARM_COLOR` (the warm white used in some phases)
  - `FLAME_COLORS` / `FLAME_COLOR_WHITE` (flicker palette)

- **Behavior toggles**
  - `LIGHTING_REVERSE_ORDER` (true = light from other side first)
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
2. **Select night** (1–8) using gestures (LEFT/RIGHT), then confirm with DOWN.
3. Shamash lights on entry to lighting phase.
4. Swipe either direction to light each candle sequentially.
5. Candles animate and “burn down” over the runtime, once all candles are lit.
6. During burning, swipe LEFT/RIGHT to change brightness.

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
- In testing power draw was maximum ~2W

---


---

## License
MIT (see SPDX header in source).

---

## Credits
Built by Trevor Hoffman (Dec 2025).  
NeoPixel control via CircuitPython `neopixel`, and gesture input via `adafruit_apds9960`.


