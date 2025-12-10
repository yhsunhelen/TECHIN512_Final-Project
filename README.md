# Zombie Shooter: 90s-Style Handheld Reaction Game

A 90s-era inspired handheld electronic game built with the Seeed Studio XIAO ESP32C3 and CircuitPython.  
The game combines quick reactions, motion controls, and classic "Bop It"-style commands with a zombie survival theme.

> Platform: XIAO ESP32C3 + CircuitPython  
> Display: SSD1306 128x64 OLED  
> Sensors: ADXL345 Accelerometer, Rotary Encoder  
> Feedback: NeoPixel RGB LED(s), Piezo Buzzer  
> Power: LiPo Battery + On/Off Switch

---

## How to Play

### Boot & Splash Screen

- When you turn on the device, an **animated splash screen** appears:
  - Title **"Zombie Shooter"** slides in.
  - A short **boot melody** plays on the buzzer.
  - A short story is displayed in multiple pages with a blinking `N` in the bottom-right.
  - Press the button to advance through the story pages.
- The splash screen **only plays on power-on**, not when restarting the game from Game Over.

### Main Menu & Difficulty Selection

- After the splash/story screens, the **main menu** appears.
- Use the **Rotary Encoder** to move between difficulty options:
  - `Easy`
  - `Medium`
  - `Hard`
- Press the encoder button to **confirm** your difficulty.
- Difficulty affects:
  - Available time per move / per level.
  - Speed and frequency of zombie actions.
  - Number and complexity of required moves.

### Game Loop & Levels

- The game consists of **at least 10 levels** of increasing difficulty.
- On each level, the player must perform **commands correctly within a time limit**.
- The OLED displays:
  - `Level: X`
  - The **current move** or command (e.g. `RAISE SHIELD`, `TILT LEFT`, `SHOOT`, etc.)
  - Current **score** (if scoring is enabled).
- Failing to perform the correct move in time, or making the wrong move, triggers **Game Over**.

Example ways difficulty increases across levels:

- Shorter time limits.
- More complex sequences of moves.
- Faster / more frequent zombie threats.
- More "T" (shield-only) zombies mixed into normal ones.

---

## Player Moves & Inputs

The game uses multiple kinds of player input to satisfy the "minimum four possible moves" requirement:

1. **Rotate Encoder (Clockwise / Counterclockwise)**
   - Used for:
     - Menu navigation
     - Difficulty selection
     - Initial/Name input for high scores
   - Can also be used as an in-game move (e.g. "SPIN DIAL").

2. **Encoder Button / Fire Button / Touch Pad**
   - Used to:
     - Confirm selections in menus
     - **Shoot normal zombies** (fire action)
   - When the game displays `SHOOT` or similar, the correct move is pressing this button.

3. **Accelerometer – Tilt Left / Tilt Right**
   - Tilting the device left/right is detected using the **ADXL345 accelerometer**.
   - Used as additional moves, such as:
     - `TILT LEFT`
     - `TILT RIGHT`

4. **Accelerometer – Shield Up Gesture**
   - Raising the device (or tilting it upward past a threshold) is interpreted as **"Shield Up"**.
   - When a special "T" zombie is on screen, raising the shield can destroy **one** T-type zombie per activation.

These give you **more than four distinct move types**, satisfying the project requirements.

---

## Game States

### In-Game

- OLED shows:
  - Current **Level**
  - Required **Move**
  - **Timer** or feedback that time is running out
  - Optional: Zombie icons / characters to visualize threats.
- NeoPixel and Buzzer give feedback for correct/incorrect actions.

### Game Over

- Triggered when:
  - Player fails to input the correct move in time, or
  - Inputs the wrong move.
- OLED displays a **Game Over screen** with:
  - Final **Level** reached
  - Final **Score** (if scoring is enabled)
- From Game Over screen, the player can:
  - Press the button or encoder to **restart the game**  
    (without power cycling the device).

### Game Win

- If the player successfully completes **all levels**, a **Game Win screen** appears:
  - Congratulatory message.
  - Final score.
- NeoPixels may show a **celebration effect** (e.g. color cycle).
- Buzzer plays a **win melody**.

---

## Scoring & High Scores (Extra Credit)

> This section applies if you implement the extra credit features.

### Scoring

- Each successfully completed level awards **points**.
- Harder difficulties can award **more points per level**.
- The score is:
  - Displayed during the game (e.g. at the corner of the OLED).
  - Displayed again on **Game Over** or **Game Win** screens.

### High Score Board

- High scores are stored in a `scores.json` file on the XIAO’s internal flash.
- After Game Over or Game Win:
  - The game checks if the score is in the **top N** (e.g. top 5 or 10).
  - If so, a **high score name entry screen** appears.
- Player initials are entered using the **Rotary Encoder**:
  - Rotate to select letters (A–Z, maybe symbols or space).
  - Press to move to the next character.
  - Typically 3-character initials (e.g. `AAA`, `BOB`).
- The high score table can be viewed after each game and is preserved across power cycles.

---

## Sensors & Filtering

### ADXL345 Accelerometer

- Connected via **I2C** on the same bus as the OLED (SCL/SDA).
- Used for:
  - Tilt left/right detection.
  - "Shield Up" gesture (tilt up / raise).
  - Optional shake-based moves.

### Calibration / Filtering

To satisfy the "proper calibration/filtering" requirement:

- At boot, the accelerometer can be sampled multiple times to estimate a **baseline**.
- A **moving average filter** is applied to the raw X/Y/Z values:
  - E.g. using the last N samples to smooth out noise.
- Thresholds for tilt and shield gestures are based on:
  - Filtered signals.
  - Clear, documented numeric thresholds (e.g. `x > THRESHOLD_TILT_RIGHT`).

---

## NeoPixel Behavior

NeoPixel LED(s) are used to enhance gameplay and give quick visual feedback:

- **Game Start / Ready**  
  - NeoPixel glows a calm color (e.g. blue or green).
- **Waiting for Move**  
  - NeoPixel shows a neutral or level-based color.
- **Correct Move**  
  - Brief flash of **green** or another positive color.
- **Incorrect Move**  
  - Flash red.
- **Game Over**  
  - Pulsing or blinking **red**.
- **Game Win**  
  - A short **rainbow sequence** or cycling multiple colors.

> The NeoPixel uses **more than one color**, satisfying the requirement.

---

## Audio (Buzzer)

A piezo buzzer is driven by a PWM-capable GPIO pin to play simple tones and melodies:

- **Boot Melody**  
  - A short tune at power-on, matching the splash/story screen.
- **Correct Move Tone**  
  - A short positive beep or ascending tone.
- **Incorrect Move / Game Over Tone**  
  - A lower or dissonant tone.
- **Game Win Melody**  
  - A slightly longer celebratory tune.
- **Easter Egg / Boss Sequence** (if implemented)  
  - Custom tones during special animations (e.g. running through zombie horde).

This covers the **“at least three events have tones”** extra credit requirement.

---

## Files & Project Structure

Suggested repository structure:

```text
.
├── code/
│   ├── code.py             # Main game loop, state machine, input handling
│   ├── ui.py               # Splash screen, story pages, UI screens
│   ├── menu.py             # Main menu and difficulty selection
│   ├── easter1.py          # First easter egg (optional/mini event)
│   ├── easter2.py          # Boss / major easter egg animation and story
│   ├── scores.py           # Scoring and high score storage (scores.json)
│   ├── name_input.py       # Rotary encoder-based name/initial input
│   ├── rotary_encoder.py   # Rotary encoder helper class / driver
│   └── demo.py             # Small test/demo scripts used during development
│
├── lib/                    # CircuitPython libraries used by the game
│   ├── adafruit_display_text/
│   ├── adafruit_displayio_ssd1306.mpy
│   ├── adafruit_adxl34x.mpy
│   ├── i2cdisplaybus.mpy
│   ├── neopixel.mpy
│
├── diagrams/
│   ├── system_diagram.png  # system block diagram
│   └── circuit_diagram.png # wiring diagram / schematic
│
├── enclosure/
│   ├── enclosure_photo_1.jpg
│   ├── enclosure_photo_2.jpg
│   └── stl_or_cad_files/   # optional: 3D models or drawings
│
└── README.md
