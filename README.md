# Zombie Shooter – 90s-Style Handheld Reaction Game

A 90s-style handheld electronic game built with the Seeed Studio **XIAO ESP32C3** and **CircuitPython**.  
The game mixes fast reactions, motion aiming, sound input, a touch-shield, and zombies.

> Platform: XIAO ESP32C3 + CircuitPython  
> Display: SSD1306 128×64 OLED  
> Inputs: ADXL345 accelerometer, rotary encoder, trigger button, capacitive touch pad, sound sensor  
> Outputs: NeoPixel RGB LED, piezo buzzer, vibration motor  
> Power: LiPo battery + on/off switch

---

## How to Play

### 1. Power-On & Splash Screen

When the device is turned on:

- An animated story / splash screen is shown by `ui.show_boot_animation(display, btn)`.
- This splash animation plays **only on power-up**, not when restarting after Game Over.

After the splash, the game enters the **main menu**.

---

## Menus & Difficulty

The **rotary encoder** is used only outside of gameplay:

- Rotate to move between menu items.
- Press the encoder button to confirm.

Main menu (`menu.main_menu`):

- `PLAY` – start a new game.
- `SCORES` – view the high-score leaderboard.
- `SETTINGS` – change difficulty.

### Difficulty Settings

From `menu.difficulty_menu` the player can choose:

- `EASY`
- `NORMAL`
- `DIFFICULT`

The selected difficulty affects:

- How many zombies can be on screen at once.
- How quickly zombies spawn.
- How long each zombie stays alive before it disappears and may damage the player.

For each difficulty, `ZOMBIE_LIFETIME_TABLE` defines the lifetime for levels 1–10  
(shorter lifetimes at higher levels ⇒ harder).

---

## One-Time Tutorial (3 Parts)

The tutorial runs **once** after power-on, the first time the player chooses `PLAY`:

```python
tutorial_shown = False
...
if not tutorial_shown:
    show_tutorial(display)
    tutorial_shown = True
```

`show_tutorial(display)` contains 3 parts:

### Tutorial 1/3 – Shooting Z

- **Part 1-A (text)**: Explains that you tilt to move the `+` crosshair and press the button to shoot `Z`.
- **Part 1-B (practice)**:
  - A `+` crosshair and one `Z` appear on a clean screen.
  - The accelerometer (ADXL345) is read and filtered with an exponential moving average:

    ```python
    local_xf = local_alpha * x + (1 - local_alpha) * local_xf
    local_yf = local_alpha * y + (1 - local_alpha) * local_yf
    ```

  - Filtered X/Y are mapped to screen coordinates; the crosshair follows your tilt.
  - Pressing the trigger button checks if the crosshair is near the `Z`:
    - Close enough → `hit_effect()` (NeoPixel green, beep, vibration).
    - Miss → `miss_effect()` (NeoPixel red, different beep).

### Tutorial 2/3 – S & Sound Sensor

- **Part 2-A (text)**: Explains that when `S` appears you use **sound**, not aiming.
- **Part 2-B (practice)**:
  - A big `S` is shown on screen.
  - The digital sound sensor on D3 is read:
    - Quiet = 1, loud spike = 0
  - A transition `1 → 0` while the buzzer is not active triggers:
    - A beep and `hit_effect()` — simulating the destruction of `S` by a clap or shout.

### Tutorial 3/3 – T & Shield Touch

- **Part 3-A (text)**: Explains that when `T` appears, you touch the left pad to raise the shield.
- **Part 3-B (practice)**:
  - A simple scene with a `T` and text.
  - Touching the **left capacitive pad** (D2) long enough:
    - Calls `hit_effect()` and removes the T in the tutorial.
    - Demonstrates the “shield vs T” mechanic.

---

## Fingerprint Unlock (Touch Pad)

After the tutorial (if enabled by `FINGERPRINT_UNLOCK_ENABLED = True`),  
a “fingerprint unlock” screen appears before entering the real game:

```python
if FINGERPRINT_UNLOCK_ENABLED:
    fingerprint_unlock()
    display.root_group = main_group
```

`fingerprint_unlock()`:

- Shows text:

  > Know: put your finger  
  > on the left touch pad  
  > when it glows green,  
  > to unlock your weapon.

- Sets the NeoPixel to a **dim green** `(0, 80, 0)` while waiting.
- When the player touches the pad and holds it for `REQUIRED_HOLD = 0.5s`:
  - The text changes to:

    > Weapon unlocked!  
    > Welcome back,  
    > Zombie Hunter.  
    > Press BTN to start

  - NeoPixel changes to **bright green** `(0, 255, 0)`.
- The player presses the button to continue to the main game.

---

## Game Structure

### Levels & Timing

- Each run contains **10 levels** per difficulty:

  ```python
  MAX_LEVEL = 10
  GAME_DURATION = 10.0  # seconds per level
  ```

- Each level lasts exactly **10 seconds**.
- If the player is still alive when the level timer reaches 0:
  - If current level < 10 → advance to the next level.
  - If current level == 10 → the player has cleared all levels.

During gameplay the top of the OLED shows:

- `S:<score>` – current score
- `HP:<value>` – player health (max 3)
- `T:<seconds>` – remaining time in the current level

The bottom shows difficulty and level:

- `E L1`, `N L4`, `D L7`, etc.

### HP and Damage

- `MAX_HP = 3`
- When a zombie’s personal lifetime expires, `update_zombies()` checks the shield:
  - If shield **not** active → HP decreases by 1.
  - The zombie is removed.
- When HP decreases:
  - The HP label is updated.
  - `damage_effect()` plays: NeoPixel orange flash + vibration + low-pitch beep.
- If HP reaches 0:
  - `hp_reached_zero = True`
  - `running = False` → end of the game.

---

## Zombies & Player Moves

There are three zombie types:

- **Z** – standard zombie (shoot with crosshair + button)
- **S** – sound zombie (destroy with sound)
- **T** – shield zombie (destroy with touch shield)

Spawn logic (`spawn_zombie`) selects Z/S/T probabilities based on:

- Difficulty (`EASY`, `NORMAL`, `DIFFICULT`)
- Current level index

### In-Game Controls

1. **Aim with Tilt (ADXL345)**  
   - Crosshair `+` is always controlled by the accelerometer:

     ```python
     x_f = alpha * x + (1 - alpha) * x_f
     y_f = alpha * y + (1 - alpha) * y_f
     px = map_to_range(x_f, MIN_X, MAX_X, SCREEN_X_MIN, SCREEN_X_MAX)
     py = map_to_range(-y_f, MIN_Y, MAX_Y, SCREEN_Y_MIN, SCREEN_Y_MAX)
     ```

   - `alpha = 0.2` for smooth movement (low-pass filter).
   - Filtered values are mapped/clamped into the screen area and set as `crosshair.x` / `crosshair.y`.

2. **Shoot (Trigger Button on D9)**  
   - The trigger button is debounced by `update_button()`.
   - When pressed and **shield is not active** (`can_shoot = True`):
     - `fired_any_shot = True`
     - `muzzle_flash()` is called (NeoPixel white flash).
     - `find_hit_zombie(px, py)` tests if the crosshair overlaps a `Z`.
       - If a `Z` is found:
         - It is removed.
         - Score increments, label updated.
         - `hit_effect()` plays (green flashes, beep, vibration).
       - If nothing / `S` / `T` is hit:
         - `miss_effect()` plays (red flash, miss sound).

   - If the button is pressed while the shield is up (`can_shoot = False`):
     - The text area briefly shows `SHIELD UP!` and no shot is fired.

3. **Sound Move (Sound Sensor on D3, for S)**  
   - Each loop reads the digital sound sensor:
     - Quiet: `sound_sensor.value == 1`
     - Loud spike: `sound_sensor.value == 0`
   - A `1 → 0` edge is detected:

     ```python
     sound_edge = (sound_last_state and (not cur_sound))
     ```

   - If `sound_edge` and the buzzer is not playing:
     - One **S zombie** on screen is removed (loop breaks after the first).
     - Score increases and `hit_effect()` is called.

4. **Shield Move (Touch Pad on D2, for T)**  
   - `shield_active = bool(touch.value)`; when true:
     - `can_shoot = False` (cannot fire).
     - A loop walks through `zombies[:]`:
       - On the first alive `T` zombie:
         - It is removed.
         - Score increases.
         - `hit_effect()` plays.
         - Loop breaks → **one T per shield activation**.
   - When shield is active and a zombie lifetime ends:
     - The player does **not** lose HP (see `update_zombies`).

These four moves — **tilt to aim**, **shoot button**, **sound**, and **shield touch** — are the player’s actual actions.

---

## Scoring & Leaderboard

### Score

- Each destroyed zombie (Z/S/T) adds 1 point.
- Score label: `S:<value>` is updated whenever `game_score` changes.
- Final score is shown on the Game Over or victory/clear screen.

### Game Over & Clear

At the end of the `while running` loop:

- If the player survived all 10 levels → `cleared_all_levels = True`.
- If HP reached 0 → `hp_reached_zero = True`.

Then:

1. **Boss Easter Egg (Clear All Levels)**  
   If `cleared_all_levels` is `True`:

   ```python
   easter2.show_boss_easter(display, btn, buzzer)
   ```

   - Special animation of running through zombies and story text.
   - Buzzer sound effects during this sequence.

2. **No-Shot Easter Egg**  
   After the game:

   ```python
   if not fired_any_shot:
       easter.show_no_shot(display, btn, buzzer)
       display.root_group = main_group
       continue
   ```

   - If the player never fired a bullet in the whole run,  
     a “peaceful player / no bullet fired” easter egg screen is shown instead of the normal Game Over.

3. **Normal Game Over Screen**

   If the run was not a no-shot easter egg:

   ```python
   show_game_over(display, game_score, hp_reached_zero)
   ```

   - Displays:
     - `"YOU DIED"` if HP reached zero, or `"TIME UP"` otherwise.
     - `Score: <value>`
     - `BTN: CONTINUE`

4. **High Score Entry & Leaderboard**

   - Uses `score.py`:

     ```python
     if score.can_enter_leaderboard(game_score):
         player_name = NameInput.enter_name(display, encoder, btn, max_len=3)
         score.add_score(player_name, game_score)
     ```

   - `NameInput.enter_name` lets the player use the rotary encoder to select 3-character initials.
   - Scores are stored in `scores.json` on the internal flash (no SD card).
   - `show_leaderboard(display)` then shows the high score list:
     - Up to several entries with rank, initials, and score.
     - Encoder rotates to scroll if more entries exist.
     - Press button to go back to main menu.

The player can start a new game from the menu **without power-cycling**.

---

## NeoPixel Behavior

A single NeoPixel on **D10** is used for clear color-coded feedback:

- **Unlock Tutorial / Fingerprint Screen**
  - Dim green `(0, 80, 0)` while waiting for touch.
  - Bright green `(0, 255, 0)` when the weapon is successfully unlocked.

- **Shield Tutorial (Part 3 practice)**  
  - When the player successfully clears the T in the tutorial, a green flash + `hit_effect()` is used.

- **Muzzle Flash (Shooting) – `muzzle_flash()`**
  - Brief **white** `(255, 255, 255)` flash when the trigger is pressed.

- **Hit Effect – `hit_effect()`**
  - Two short **green** `(0, 255, 0)` flashes.
  - Vibration motor on D8 pulses.
  - A high-pitch beep plays.

- **Miss Effect – `miss_effect()`**
  - Single **red** `(255, 0, 0)` flash.
  - Medium-pitch miss beep.

- **Damage Effect – `damage_effect()`**
  - **Orange** `(255, 50, 0)` flash.
  - Vibration pulse and deeper tone.

After each effect, the pixel is set back to `(0, 0, 0)` (off).

> The NeoPixel uses multiple distinct colors (dim & bright green, white, red, orange),  
> which clearly satisfies the requirement to use more than one color.

---

## Audio & Vibration

### Buzzer (D7, PWM)

The buzzer is driven by `pwmio.PWMOut` on D7:

- `play_beep(freq, duration, volume)`:
  - Sets `buzzer_active = True` during playback to prevent the sound sensor from falsely triggering.
- **Game start sound**:

  ```python
  def game_start_sound():
      play_beep(500, 0.08)
      play_beep(750, 0.08)
      play_beep(1000, 0.12)
  ```

  Called at the beginning of each game.

- Different tones for:
  - Hit (`hit_effect`)
  - Miss (`miss_effect`)
  - Damage (`damage_effect`)
  - Tutorial confirmations and easter egg scenes.

### Vibration Motor (D8)

- Controlled by a digital output on D8:
  - Pulses during `hit_effect()` and `damage_effect()` to give haptic feedback.

---

## Sensors & Filtering

### ADXL345 Accelerometer

- Connected via I2C with the OLED.
- Used only for **aiming** the crosshair.
- The code uses an exponential moving average:

  ```python
  alpha = 0.2
  x_f = alpha * x + (1 - alpha) * x_f
  y_f = alpha * y + (1 - alpha) * y_f
  ```

- Then maps the smoothed values into a limited range `[MIN_X, MAX_X]` / `[MIN_Y, MAX_Y]` and finally into OLED pixel coordinates `[SCREEN_X_MIN, SCREEN_X_MAX]` / `[SCREEN_Y_MIN, SCREEN_Y_MAX]`.

This provides proper filtering for the accelerometer as required.

### Sound Sensor (D3)

- Digital input with pull-up:
  - Quiet: `1`
  - Loud spike: `0`
- A `1 → 0` transition triggers:
  - Tutorial Part 2 success.
  - In-game S-zombie kill (one `S` per edge).

### Touch Pad (D2)

- Digital input with pull-down.
- Used for:
  - Fingerprint unlock.
  - T-zombie shield move during gameplay.

### Trigger Button (D9) & Encoder

- Trigger button:
  - Debounced by `update_button()` for reliable edge detection.
- Rotary encoder:
  - Implemented by `RotaryEncoder` class in `rotary_encoder.py`.
  - Used for menus and name/initial selection.

---


## Files & Project Structure

Suggested repository structure:

```text
.
├── codfiles/
│   ├── code.py             # Main game loop, state machine, input handling
│   ├── ui.py               # Splash screen, story pages, UI screens
│   ├── menu.py             # Main menu and difficulty selection
│   ├── easter1.py          # First easter egg (optional/mini event)
│   ├── easter2.py          # Boss / major easter egg animation and story
│   ├── scores.py           # Scoring and high score storage (scores.json)
│   ├── name_input.py       # Rotary encoder-based name/initial input
│   ├── rotary_encoder.py   # Rotary encoder helper class / driver
│
├── lib/                    # CircuitPython libraries used by the game
│   ├── adafruit_display_text/
│   ├── adafruit_displayio_ssd1306.mpy
│   ├── adafruit_adxl34x.mpy
│   ├── i2cdisplaybus.mpy
│   ├── neopixel.mpy
│
├── Documentation/
│   ├── System Block Diagram.png  # system block diagram
│   └── Final Circuit Diagrams.pdf # wiring diagram / schematic
│
├── enclosure/
│   ├── 20251207_1.stl
│   ├── 20251207_2.stl
│
└── README.md

To run on the actual device, copy the contents of `code/` and `lib/` to the CIRCUITPY drive (with `code.py` at the root).

---

## Hardware & Enclosure Summary

- Seeed Studio **XIAO ESP32C3** microcontroller  
- **SSD1306 128×64 OLED** on I2C (shared with ADXL345)  
- **ADXL345 accelerometer** (I2C)  
- **Rotary encoder + push button** for menus & name input  
- **Trigger button** (D9) for shooting  
- **Capacitive touch pad** (D2) for shield/unlock  
- **Digital sound sensor** (D3) for S-zombie move  
- **NeoPixel RGB LED** (D10)  
- **Piezo buzzer** on D7 (PWM)  
- **Vibration motor** on D8  
- **LiPo battery** and **on/off switch**  
- All mounted on perfboard or a PCB using **female headers** so modules are removable.

The enclosure:

- Securely holds all electronics.
- Exposes:
  - USB-C port for the XIAO.
  - On/off switch.
  - OLED window.
  - Openings for trigger, encoder, and touch pad.
- Has a removable lid/side so the electronics can be accessed easily.
- Any 3D-printed parts are **not yellow**, following the project constraints.

