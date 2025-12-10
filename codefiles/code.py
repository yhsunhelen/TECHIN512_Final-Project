import time
import random

import board
import busio
import displayio
import terminalio
import digitalio
from adafruit_display_text import label
import i2cdisplaybus
import adafruit_displayio_ssd1306
import adafruit_adxl34x

import neopixel
import pwmio
import ui

from rotary_encoder import RotaryEncoder
import score          # leaderboard
import NameInput      # name input
import menu           # main menu & difficulty menu
import easter         # easter egg 1: no-shot
import easter2        # easter egg 2: clear all 10 levels


# ========== 0. CONSTANTS ==========

GAME_DURATION = 10.0       # seconds per level
MAX_HP = 3                 # player HP
MAX_LEVEL = 10             # 10 levels per difficulty
FLASH_WARNING_TIME = 3.0   # last seconds flashing before zombie disappears

# fingerprint unlock on/off
FINGERPRINT_UNLOCK_ENABLED = True

# tutorial only once per power-on
tutorial_shown = False

# 每难度、每一关僵尸停留时间（秒）——你可以自己改
ZOMBIE_LIFETIME_TABLE = {
    "EASY":      [8, 8, 7.5, 7.5, 7, 6.5, 6, 5.5, 5, 4.5],
    "NORMAL":    [7, 6.5, 6, 5.5, 5, 4.5, 4, 3.7, 3.4, 3],
    "DIFFICULT": [5, 4.5, 4, 3.5, 3, 2.8, 2.6, 2.4, 2.2, 2],
}


# ========== LEVEL CONFIG HELPER ==========

def get_level_config(difficulty, level_index):
    """
    Return parameters for a given difficulty + level:
      - max_on_screen: max zombies on screen (only depends on difficulty)
      - spawn_interval: spawn interval (seconds, only depends on difficulty)
      - zombie_lifetime: how long each zombie stays (seconds, depends on level)
      - hp_bonus: extra HP (here always 0, all zombies = 1 HP)
      - boss: True if this is the boss level (level 10)
    """

    # 同屏数量 & 刷新速度：只随难度变化
    if difficulty == "EASY":
        max_on_screen  = 3      # fewer zombies on screen
        spawn_interval = 2.5    # slower spawn
    elif difficulty == "NORMAL":
        max_on_screen  = 4
        spawn_interval = 1.8
    else:  # DIFFICULT
        max_on_screen  = 5      # more zombies
        spawn_interval = 1.2    # much faster spawn

    # 僵尸停留时间：由上面的表 + 当前关卡决定
    lifetime_list = ZOMBIE_LIFETIME_TABLE[difficulty]
    zombie_lifetime = lifetime_list[level_index - 1]  # level_index is 1-based

    # 所有僵尸 1 血，不再有多血僵尸
    hp_bonus = 0

    boss = (level_index == MAX_LEVEL)

    return {
        "max_on_screen": max_on_screen,
        "spawn_interval": spawn_interval,
        "zombie_lifetime": zombie_lifetime,
        "hp_bonus": hp_bonus,
        "boss": boss,
    }


# ========== 1. DISPLAY & I2C INIT ==========

displayio.release_displays()

i2c = busio.I2C(board.SCL, board.SDA)  # OLED + ADXL345 share I2C

display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)


# ========== 2. SENSORS / IO ==========

# ADXL345 accelerometer
accelerometer = adafruit_adxl34x.ADXL345(i2c)

# trigger button: D9 (pull-up, pressed = False)
btn = digitalio.DigitalInOut(board.D9)
btn.switch_to_input(pull=digitalio.Pull.UP)

# rotary encoder on D0, D1
encoder = RotaryEncoder(board.D0, board.D1, debounce_ms=3, pulses_per_detent=1)

# NeoPixel at D10
pixel = neopixel.NeoPixel(board.D10, 1, brightness=0.3, auto_write=False)

# vibration motor on D8
motor = digitalio.DigitalInOut(board.D8)
motor.switch_to_output(value=False)

# buzzer on D7 (PWM)
buzzer = pwmio.PWMOut(board.D7, duty_cycle=0, frequency=440, variable_frequency=True)

# buzzer state: True while buzzing (used to ignore sound sensor self-noise)
buzzer_active = False

# capacitive touch sensor (shield) on D2
touch = digitalio.DigitalInOut(board.D2)
touch.switch_to_input(pull=digitalio.Pull.DOWN)

# sound sensor on D3
# quiet = 1, sound = 0
sound_sensor = digitalio.DigitalInOut(board.D3)
sound_sensor.switch_to_input(pull=digitalio.Pull.UP)


# ========== 3. BUTTON DEBOUNCE ==========

last_state = btn.value
stable_state = btn.value
last_time = 0
debounce_delay = 0.02  # 20 ms

def update_button():
    """Return True when a new press edge is detected."""
    global last_state, stable_state, last_time
    now = time.monotonic()
    current_state = btn.value

    if current_state != last_state:
        last_time = now
        last_state = current_state

    pressed_event = False

    if (now - last_time) > debounce_delay:
        if stable_state != current_state:
            stable_state = current_state
            if not stable_state:   # stable_state False = pressed
                pressed_event = True

    return pressed_event


# ========== 4. LEADERBOARD & GAME OVER ==========

def show_leaderboard(display_obj):
    from score import load_scores

    records = load_scores()

    # no records
    if not records:
        group = displayio.Group()
        display_obj.root_group = group

        title = label.Label(terminalio.FONT, text="HIGH SCORES", x=0, y=8)
        group.append(title)

        msg = label.Label(terminalio.FONT, text="No records yet", x=0, y=30)
        group.append(msg)

        hint = label.Label(terminalio.FONT, text="BTN: BACK", x=0, y=56)
        group.append(hint)

        while True:
            if not btn.value:
                while not btn.value:
                    time.sleep(0.01)
                return
            time.sleep(0.01)

    PAGE_LINES = 3
    start_index = 0

    def clamp_start(idx):
        if len(records) <= PAGE_LINES:
            return 0
        if idx < 0:
            return 0
        max_start = len(records) - PAGE_LINES
        if idx > max_start:
            idx = max_start
        return idx

    def draw_page(start):
        group = displayio.Group()
        display_obj.root_group = group

        title = label.Label(terminalio.FONT, text="HIGH SCORES", x=0, y=8)
        group.append(title)

        y = 20
        end = min(start + PAGE_LINES, len(records))
        for i in range(start, end):
            item = records[i]
            line = f"{i+1}. {item['name']} {item['score']}"
            lbl = label.Label(terminalio.FONT, text=line, x=0, y=y)
            group.append(lbl)
            y += 12

        hint = label.Label(terminalio.FONT, text="ENC:SCROLL  BTN:BACK", x=0, y=56)
        group.append(hint)

    start_index = clamp_start(0)
    draw_page(start_index)

    encoder.update()
    last_pos = encoder.position

    while True:
        encoder.update()
        pos = encoder.position
        if pos != last_pos:
            delta = pos - last_pos
            last_pos = pos

            if delta > 0:
                start_index = clamp_start(start_index + 1)
                draw_page(start_index)
            elif delta < 0:
                start_index = clamp_start(start_index - 1)
                draw_page(start_index)

        if not btn.value:
            time.sleep(0.05)
            if not btn.value:
                while not btn.value:
                    time.sleep(0.01)
                return

        time.sleep(0.01)


def show_game_over(display_obj, score_value, hp_reached_zero):
    group = displayio.Group()
    display_obj.root_group = group

    text = "YOU DIED" if hp_reached_zero else "TIME UP"

    go_label = label.Label(terminalio.FONT, text=text, x=20, y=20)
    group.append(go_label)

    score_lbl = label.Label(terminalio.FONT, text=f"Score: {score_value}", x=20, y=35)
    group.append(score_lbl)

    hint_label = label.Label(terminalio.FONT, text="BTN: CONTINUE", x=5, y=56)
    group.append(hint_label)

    while True:
        if not btn.value:
            while not btn.value:
                time.sleep(0.01)
            break
        time.sleep(0.01)


def show_easter_egg_no_shot(display_obj):
    group = displayio.Group()
    display_obj.root_group = group

    title = label.Label(terminalio.FONT, text="SECRET MODE!", x=5, y=15)
    group.append(title)

    line1 = label.Label(terminalio.FONT, text="No bullet fired.", x=5, y=30)
    group.append(line1)

    line2 = label.Label(terminalio.FONT, text="Peaceful player :)", x=5, y=42)
    group.append(line2)

    hint = label.Label(terminalio.FONT, text="BTN: BACK TO MENU", x=0, y=56)
    group.append(hint)

    while True:
        if not btn.value:
            while not btn.value:
                time.sleep(0.01)
            break
        time.sleep(0.01)


# ========== 5. FINGERPRINT UNLOCK (OPTIONAL) ==========

def fingerprint_unlock():
    """
    Simulated fingerprint unlock: ask player to touch the left capacitive pad.
    """
    group = displayio.Group()
    display.root_group = group

    line1 = label.Label(terminalio.FONT,
                        text="Know: put your finger",
                        x=0, y=15)
    line2 = label.Label(terminalio.FONT,
                        text="on the left touch pad",
                        x=0, y=27)
    line3 = label.Label(terminalio.FONT,
                        text="when it glows green,",
                        x=0, y=39)
    line4 = label.Label(terminalio.FONT,
                        text="to unlock your weapon.",
                        x=0, y=51)
    group.append(line1)
    group.append(line2)
    group.append(line3)
    group.append(line4)

    pixel[0] = (0, 80, 0)
    pixel.show()

    touched_start = None
    REQUIRED_HOLD = 0.5  # seconds

    while True:
        if touch.value:
            if touched_start is None:
                touched_start = time.monotonic()
            else:
                if time.monotonic() - touched_start >= REQUIRED_HOLD:
                    line1.text = "Weapon unlocked!"
                    line2.text = "Welcome back,"
                    line3.text = "Zombie Hunter."
                    line4.text = "Press BTN to start"
                    pixel[0] = (0, 255, 0)
                    pixel.show()
                    break
        else:
            touched_start = None

        time.sleep(0.02)

    while True:
        if not btn.value:
            while not btn.value:
                time.sleep(0.01)
            break

    pixel[0] = (0, 0, 0)
    pixel.show()


# ========== 6. BOOT ANIMATION ==========

ui.show_boot_animation(display, btn, buzzer)


# ========== 7. GAME UI GROUP (ONLY ONCE) ==========

main_group = displayio.Group()

score_label = label.Label(terminalio.FONT, text="S:0", x=0, y=8)
hp_label    = label.Label(terminalio.FONT, text=f"HP:{MAX_HP}", x=44, y=8)
timer_label = label.Label(terminalio.FONT, text="T:10", x=88, y=8)

crosshair = label.Label(terminalio.FONT, text="+", x=64, y=36)

zombies_group = displayio.Group()

state_label = label.Label(terminalio.FONT, text="N L1", x=0, y=54)
info        = label.Label(terminalio.FONT, text="",   x=0, y=56)

main_group.append(score_label)
main_group.append(hp_label)
main_group.append(timer_label)
main_group.append(crosshair)
main_group.append(zombies_group)
main_group.append(state_label)
main_group.append(info)

display.root_group = main_group


# ========== 8. MAPPING & ZOMBIE MANAGEMENT ==========

alpha = 0.2
x_f = 0.0
y_f = 0.0

MIN_X = -6.0
MAX_X =  6.0
MIN_Y = -6.0
MAX_Y =  6.0

SCREEN_X_MIN = 0
SCREEN_X_MAX = 127
SCREEN_Y_MIN = 18
SCREEN_Y_MAX = 48

def map_to_range(value, in_min, in_max, out_min, out_max):
    if value < in_min:
        value = in_min
    if value > in_max:
        value = in_max
    span_in = in_max - in_min
    ratio = (value - in_min) / span_in
    return int(out_min + ratio * (out_max - out_min))


zombies = []
last_spawn_time = 0.0


def spawn_zombie(level_cfg, level_index):
    global zombies_group

    # type: Z / S / T
    r = random.random()

    if level_cfg["boss"]:
        # boss level: 10% Z, 40% S, 50% T
        if r < 0.10:
            z_type = "Z"
        elif r < 0.50:
            z_type = "S"
        else:
            z_type = "T"
    else:
        if level_index == 1:
            z_type = "Z"  # level 1: only Z
        elif level_index <= 3:
            # level 2–3: 80% Z, 10% S, 10% T
            if r < 0.80:
                z_type = "Z"
            elif r < 0.90:
                z_type = "S"
            else:
                z_type = "T"
        else:
            # level 4–9: 60% Z, 20% S, 20% T
            if r < 0.60:
                z_type = "Z"
            elif r < 0.80:
                z_type = "S"
            else:
                z_type = "T"

    # 所有僵尸 1 血
    if z_type == "Z":
        glyph = "Z"
    elif z_type == "S":
        glyph = "S"
    else:  # "T"
        glyph = "T"

    hp = 1

    zx = random.randint(SCREEN_X_MIN + 5, SCREEN_X_MAX - 5)
    zy = random.randint(SCREEN_Y_MIN + 5, SCREEN_Y_MAX - 5)

    z_label = label.Label(terminalio.FONT, text=glyph, x=zx, y=zy)
    zombies_group.append(z_label)

    zombie = {
        "label": z_label,
        "x": zx,
        "y": zy,
        "spawn_time": time.monotonic(),
        "lifetime": level_cfg["zombie_lifetime"],
        "type": z_type,
        "hp": hp,
        "max_hp": hp,
        "dead": False,
    }
    zombies.append(zombie)


def find_hit_zombie(px, py):
    """Return the first zombie hit by crosshair (only Z is killable by shooting)."""
    for z in zombies:
        if z["dead"]:
            continue
        dx = abs(px - z["x"])
        dy = abs(py - z["y"])
        if dx <= 6 and dy <= 8:
            return z
    return None


def remove_zombie(z):
    if z not in zombies:
        return
    z["dead"] = True
    try:
        zombies_group.remove(z["label"])
    except ValueError:
        pass
    zombies.remove(z)


def update_zombies(now, shield_active, player_hp, level_cfg):
    """
    Update flashing / disappearing.
    When a zombie lifetime ends:
      - if shield is NOT active -> player takes damage
      - then zombie is removed
    """
    for z in zombies[:]:
        if z["dead"]:
            continue

        age = now - z["spawn_time"]
        lifetime = z["lifetime"]
        lbl = z["label"]

        if age >= lifetime:
            if not shield_active:
                player_hp -= 1
            remove_zombie(z)
            continue

        warn_time = min(FLASH_WARNING_TIME, lifetime)
        if age >= lifetime - warn_time:
            flash_phase = int((age - (lifetime - warn_time)) * 6)
            lbl.hidden = (flash_phase % 2 == 1)
        else:
            lbl.hidden = False

    return player_hp


# ========== 9. EFFECTS & UI HELPERS ==========

def muzzle_flash():
    pixel[0] = (255, 255, 255)
    pixel.show()
    time.sleep(0.03)
    pixel[0] = (0, 0, 0)
    pixel.show()


def play_beep(freq=800, duration=0.1, volume=0.3):
    global buzzer_active
    buzzer_active = True
    buzzer.frequency = int(freq)
    buzzer.duty_cycle = int(65535 * volume)
    time.sleep(duration)
    buzzer.duty_cycle = 0
    buzzer_active = False


def hit_effect():
    for _ in range(2):
        pixel[0] = (0, 255, 0)
        pixel.show()
        motor.value = True
        play_beep(freq=1200, duration=0.05, volume=0.4)
        motor.value = False
        pixel[0] = (0, 0, 0)
        pixel.show()
        time.sleep(0.05)


def miss_effect():
    pixel[0] = (255, 0, 0)
    pixel.show()
    play_beep(freq=300, duration=0.1, volume=0.3)
    pixel[0] = (0, 0, 0)
    pixel.show()


def damage_effect():
    pixel[0] = (255, 50, 0)
    pixel.show()
    motor.value = True
    play_beep(freq=200, duration=0.15, volume=0.4)
    motor.value = False
    pixel[0] = (0, 0, 0)
    pixel.show()


def game_start_sound():
    play_beep(freq=500, duration=0.08, volume=0.3)
    play_beep(freq=750, duration=0.08, volume=0.3)
    play_beep(freq=1000, duration=0.15, volume=0.35)


def update_hp_display(hp):
    hp_label.text = f"HP:{hp}"


def update_state_display(difficulty, level_index):
    diff_char = difficulty[0]   # E / N / D
    state_label.text = f"{diff_char} L{level_index}"


def show_level_banner(level_index):
    """Full-screen 'LEVEL X' banner in the center."""
    group = displayio.Group()
    display.root_group = group

    text = f"LEVEL {level_index}"
    # 简单水平居中估算：每个字符大约 6 像素宽
    x = max(0, (128 - len(text) * 6) // 2)
    y = 32

    lbl = label.Label(terminalio.FONT, text=text, x=x, y=y)
    group.append(lbl)

    time.sleep(1.2)  # 显示约 1.2 秒

    display.root_group = main_group


def wait_for_button_release_press():
    """Helper: wait for a full press cycle."""
    # 等待松手
    while not btn.value:
        time.sleep(0.01)
    # 等待按下
    while True:
        if not btn.value:
            while not btn.value:
                time.sleep(0.01)
            break
        time.sleep(0.01)


# ========== 10. TUTORIAL (ONLY FIRST PLAY) ==========

def show_tutorial(display_obj):
    """
    Intro tutorial shown once after power-on:
      Part 1: Text -> practice shoot Z
      Part 2: Text -> practice kill S by sound
      Part 3: Text -> practice T + touch/shield
    """

    # --- Part 1-A: text only ---
    g1_text = displayio.Group()
    display_obj.root_group = g1_text

    title = label.Label(terminalio.FONT, text="Tutorial 1/3", x=0, y=8)
    line1 = label.Label(terminalio.FONT, text="Tilt to move +", x=0, y=22)
    line2 = label.Label(terminalio.FONT, text="Aim + on Z", x=0, y=34)
    line3 = label.Label(terminalio.FONT, text="Press BTN to shoot", x=0, y=46)
    hint = label.Label(terminalio.FONT, text="BTN: NEXT", x=0, y=58)

    g1_text.append(title)
    g1_text.append(line1)
    g1_text.append(line2)
    g1_text.append(line3)
    g1_text.append(hint)

    wait_for_button_release_press()

    # --- Part 1-B: practice shooting Z on empty page ---
    g1 = displayio.Group()
    display_obj.root_group = g1

    tut_z = label.Label(terminalio.FONT, text="Z", x=64, y=36)
    g1.append(tut_z)

    tut_cross = label.Label(terminalio.FONT, text="+", x=64, y=20)
    g1.append(tut_cross)

    hit_ok = False
    local_xf = 0.0
    local_yf = 0.0
    local_alpha = 0.2

    while not hit_ok:
        try:
            x, y, z = accelerometer.acceleration
        except OSError:
            x = y = z = 0.0

        local_xf = local_alpha * x + (1 - local_alpha) * local_xf
        local_yf = local_alpha * y + (1 - local_alpha) * local_yf

        px = map_to_range(local_xf, MIN_X, MAX_X, SCREEN_X_MIN, SCREEN_X_MAX)
        py = map_to_range(-local_yf, MIN_Y, MAX_Y, SCREEN_Y_MIN, SCREEN_Y_MAX)

        tut_cross.x = px
        tut_cross.y = py

        if update_button():
            dx = abs(tut_cross.x - tut_z.x)
            dy = abs(tut_cross.y - tut_z.y)
            if dx <= 6 and dy <= 8:
                hit_ok = True
                hit_effect()
            else:
                miss_effect()

        time.sleep(0.02)

    time.sleep(0.6)

    # --- Part 2-A: text only for S ---
    g2_text = displayio.Group()
    display_obj.root_group = g2_text

    s_title = label.Label(terminalio.FONT, text="Tutorial 2/3", x=0, y=8)
    s1 = label.Label(terminalio.FONT, text="When S appears,", x=0, y=22)
    s2 = label.Label(terminalio.FONT, text="no need to aim.", x=0, y=34)
    s3 = label.Label(terminalio.FONT, text="Make a loud sound", x=0, y=46)
    s_hint = label.Label(terminalio.FONT, text="BTN: NEXT", x=0, y=58)

    g2_text.append(s_title)
    g2_text.append(s1)
    g2_text.append(s2)
    g2_text.append(s3)
    g2_text.append(s_hint)

    wait_for_button_release_press()

    # --- Part 2-B: practice S on clean page ---
    g2 = displayio.Group()
    display_obj.root_group = g2

    s_demo = label.Label(terminalio.FONT, text="S", x=64, y=36)
    g2.append(s_demo)

    last_state = sound_sensor.value  # quiet = 1
    triggered = False

    while not triggered:
        cur = sound_sensor.value
        if last_state and (not cur) and (not buzzer_active):
            triggered = True
            play_beep(freq=900, duration=0.08, volume=0.4)
            hit_effect()
        last_state = cur
        time.sleep(0.01)

    time.sleep(0.6)

    # --- Part 3-A: text only for T ---
    g3_text = displayio.Group()
    display_obj.root_group = g3_text

    t_title = label.Label(terminalio.FONT, text="Tutorial 3/3", x=0, y=8)
    t1 = label.Label(terminalio.FONT, text="When T appears,", x=0, y=22)
    t2 = label.Label(terminalio.FONT, text="touch left pad to", x=0, y=34)
    t3 = label.Label(terminalio.FONT, text="raise shield", x=0, y=46)
    t_hint = label.Label(terminalio.FONT, text="BTN: NEXT", x=0, y=58)

    g3_text.append(t_title)
    g3_text.append(t1)
    g3_text.append(t2)
    g3_text.append(t3)
    g3_text.append(t_hint)

    wait_for_button_release_press()

    # --- Part 3-B: practice T on clean page ---
    g3 = displayio.Group()
    display_obj.root_group = g3

    t_demo = label.Label(terminalio.FONT, text="T", x=64, y=36)
    g3.append(t_demo)

    hold_start = None
    HOLD_TIME = 0.5
    unlocked = False

    while not unlocked:
        if touch.value:
            if hold_start is None:
                hold_start = time.monotonic()
            else:
                if time.monotonic() - hold_start >= HOLD_TIME:
                    unlocked = True
                    pixel[0] = (0, 150, 0)
                    pixel.show()
                    hit_effect()
        else:
            hold_start = None
        time.sleep(0.02)

    time.sleep(0.6)

    pixel[0] = (0, 0, 0)
    pixel.show()
    display_obj.root_group = main_group


# ========== 11. MAIN GAME LOOP ==========

current_difficulty = "NORMAL"

while True:
    # --- 11.1 Menu loop ---
    while True:
        choice = menu.main_menu(display, encoder, btn, current_difficulty)
        print("Menu selected:", choice, "Current diff:", current_difficulty)

        if choice == "PLAY":
            break

        elif choice == "SCORES":
            show_leaderboard(display)

        elif choice == "SETTINGS":
            current_difficulty = menu.difficulty_menu(display, encoder, btn)
            print("Difficulty selected:", current_difficulty)

    # show tutorial only on first PLAY after power-on
    if not tutorial_shown:
        show_tutorial(display)
        tutorial_shown = True

    # optional fingerprint unlock
    if FINGERPRINT_UNLOCK_ENABLED:
        fingerprint_unlock()
        display.root_group = main_group

    # --- 11.2 Start a game ---
    game_score = 0
    score_label.text = "S:0"
    timer_label.text = f"T:{int(GAME_DURATION)}"
    info.text = ""

    player_hp = MAX_HP
    update_hp_display(player_hp)
    cleared_all_levels = False   # did player clear all 10 levels?

    current_level = 1
    update_state_display(current_difficulty, current_level)
    level_cfg = get_level_config(current_difficulty, current_level)

    # 显示 LEVEL 1 banner
    show_level_banner(current_level)

    zombies.clear()
    for _ in range(level_cfg["max_on_screen"]):
        spawn_zombie(level_cfg, current_level)
    last_spawn_time = time.monotonic()

    fired_any_shot = False

    game_start_sound()

    x_f = 0.0
    y_f = 0.0

    display.root_group = main_group

    print("Game started; difficulty:", current_difficulty)

    start_time = time.monotonic()
    running = True
    hp_reached_zero = False

    # sound sensor edge detection (quiet=1 -> sound=0)
    sound_last_state = sound_sensor.value

    while running:
        now = time.monotonic()
        elapsed = now - start_time
        remaining = GAME_DURATION - elapsed

        # 每关 10 秒：时间到了，如果没死就进下一关
        if remaining <= 0:
            if current_level < MAX_LEVEL:
                current_level += 1
                update_state_display(current_difficulty, current_level)
                level_cfg = get_level_config(current_difficulty, current_level)

                # 显示 LEVEL X banner
                show_level_banner(current_level)

                # 重置计时，从新的一关 10 秒开始
                start_time = time.monotonic()
                remaining = GAME_DURATION

                # 清空当前僵尸，按新配置刷新
                for z in zombies[:]:
                    remove_zombie(z)
                for _ in range(level_cfg["max_on_screen"]):
                    spawn_zombie(level_cfg, current_level)
                last_spawn_time = time.monotonic()
            else:
                # 第 10 关也坚持完 10 秒：通关
                cleared_all_levels = True
                running = False
                remaining = 0

        timer_label.text = "T:{:2d}".format(int(remaining))

        # shield via touch sensor
        shield_active = bool(touch.value)
        can_shoot = not shield_active

        # ADXL aiming
        try:
            x, y, z = accelerometer.acceleration
        except OSError:
            x = y = z = 0.0

        x_f = alpha * x + (1 - alpha) * x_f
        y_f = alpha * y + (1 - alpha) * y_f

        px = map_to_range(x_f, MIN_X, MAX_X, SCREEN_X_MIN, SCREEN_X_MAX)
        py = map_to_range(-y_f, MIN_Y, MAX_Y, SCREEN_Y_MIN, SCREEN_Y_MAX)

        crosshair.x = px
        crosshair.y = py

        # update zombies: lifetime / flashing / disappearing damage
        old_hp = player_hp
        player_hp = update_zombies(now, shield_active, player_hp, level_cfg)
        if player_hp < old_hp:
            update_hp_display(player_hp)
            damage_effect()
            if player_hp <= 0:
                hp_reached_zero = True
                running = False

        # keep zombie count
        if running:
            if len(zombies) < level_cfg["max_on_screen"]:
                if now - last_spawn_time >= level_cfg["spawn_interval"]:
                    spawn_zombie(level_cfg, current_level)
                    last_spawn_time = now

        # sound edge detection: 1 -> 0
        cur_sound = sound_sensor.value
        sound_edge = (sound_last_state and (not cur_sound))
        sound_last_state = cur_sound

        if sound_edge and (not buzzer_active):
            # player made a sound: kill all S zombies on screen
            killed_any_S = False
            for z in zombies[:]:
                if z["dead"]:
                    continue
                if z["type"] == "S":
                    remove_zombie(z)
                    game_score += 1
                    killed_any_S = True
                    break   

            if killed_any_S:
                score_label.text = f"S:{game_score}"
                hit_effect()

        # if shield is up: clear ONE T zombie only
        if shield_active:
            killed_any_T = False
            for z in zombies[:]:      # 遍历当前所有僵尸
                if z["dead"]:
                    continue
                if z["type"] == "T":
                    remove_zombie(z)  # 杀掉这个 T 僵尸
                    game_score += 1
                    killed_any_T = True
                    break             # ✅ 只杀第一个，马上停

            if killed_any_T:
                score_label.text = f"S:{game_score}"
                hit_effect()


        # shooting
        if running and update_button():
            if can_shoot:
                fired_any_shot = True
                muzzle_flash()
                target = find_hit_zombie(px, py)
                if target is not None and target["type"] == "Z":
                    # 所有僵尸 1HP，打中就死
                    remove_zombie(target)
                    game_score += 1
                    score_label.text = f"S:{game_score}"
                    hit_effect()
                else:
                    # shot S or T or empty → miss
                    miss_effect()
            else:
                info.text = "SHIELD UP!"
                time.sleep(0.1)
                info.text = ""

        time.sleep(0.02)

    # --- 11.4 End of game handling ---

    # cleared all 10 levels → boss easter egg
    if cleared_all_levels:
        easter2.show_boss_easter(display, btn, buzzer)
        display.root_group = main_group
        if score.can_enter_leaderboard(game_score):
            player_name = NameInput.enter_name(display, encoder, btn, max_len=3)
            score.add_score(player_name, game_score)
            print("Saved score:", player_name, game_score)
        else:
            print("Score not high enough for leaderboard:", game_score)
        show_leaderboard(display)
        display.root_group = main_group
        continue

    # no-shot easter egg
    if not fired_any_shot:
        print("Easter egg: no shot fired this round!")
        easter.show_no_shot(display, btn, buzzer)
        display.root_group = main_group
        continue

    # normal game over
    show_game_over(display, game_score, hp_reached_zero)

    if score.can_enter_leaderboard(game_score):
        player_name = NameInput.enter_name(display, encoder, btn, max_len=3)
        score.add_score(player_name, game_score)
        print("Saved score:", player_name, game_score)
    else:
        print("Score not high enough for leaderboard:", game_score)

    show_leaderboard(display)
    display.root_group = main_group

