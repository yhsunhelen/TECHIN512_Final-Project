# easter2.py

import time
import displayio
import terminalio
from adafruit_display_text import label


def _play_beep(buzzer, freq=800, duration=0.1, volume=0.3):
    """Internal helper: play a simple beep."""
    if buzzer is None:
        time.sleep(duration)
        return
    buzzer.frequency = int(freq)
    buzzer.duty_cycle = int(65535 * volume)
    time.sleep(duration)
    buzzer.duty_cycle = 0


def _wait_for_button(btn):
    """Wait until button is pressed and then released."""
    while True:
        if not btn.value:           # active low
            while not btn.value:
                time.sleep(0.01)    # wait for release
            break
        time.sleep(0.01)


def show_boss_easter(display, btn, buzzer):
    """
    Boss shield + 5 taps in 1 second easter egg:
    1. Play an animation: you dash through a horde of zombies.
    2. Show several pages of story; press button to go to next page.
    3. Last page: press button to return to the main game
       (main.py is responsible for restoring root_group).
    """

    # ========== 1. Animation: running through the horde ==========

    group = displayio.Group()
    display.root_group = group

    # Player character (center-bottom-ish)
    player = label.Label(terminalio.FONT, text="@", x=60, y=40)
    group.append(player)

    title = label.Label(terminalio.FONT, text="...RUNNING...", x=18, y=10)
    group.append(title)

    # Pre-create zombie labels on left and right sides
    left_zombies = []
    right_zombies = []

    for i in range(5):
        z = label.Label(terminalio.FONT, text="Z",
                        x=-10,  # enter from left off-screen
                        y=18 + i * 8)
        left_zombies.append(z)
        group.append(z)

    for i in range(5):
        z = label.Label(terminalio.FONT, text="Z",
                        x=138,  # enter from right off-screen
                        y=18 + i * 8)
        right_zombies.append(z)
        group.append(z)

    start = time.monotonic()
    duration = 3.0  # seconds

    # Low background "hum"
    _play_beep(buzzer, freq=200, duration=0.15, volume=0.3)

    # Main animation loop
    while True:
        now = time.monotonic()
        if now - start > duration:
            break

        # Left zombies drifting from left to right
        for z in left_zombies:
            z.x += 3
            if z.x > 138:
                z.x = -10  # loop

        # Right zombies drifting from right to left
        for z in right_zombies:
            z.x -= 3
            if z.x < -10:
                z.x = 138  # loop

        # Slight player sway to look like running
        phase = int((now - start) * 10)
        player.x = 60 + (phase % 3 - 1)

        # Allow skipping animation by pressing the button
        if not btn.value:
            while not btn.value:
                time.sleep(0.01)
            break

        time.sleep(0.05)

    # Short triple beep to show you broke through the horde
    for f in (600, 800, 1000):
        _play_beep(buzzer, freq=f, duration=0.08, volume=0.4)
        time.sleep(0.03)

    # ========== 2. Story pages ==========

    pages = []

    # Page 1
    p1 = [
        "You broke through",
        "layers of zombies.",
        "",
        "The screams behind",
        "you slowly fade",
        "into the dark."
    ]
    pages.append(p1)

    # Page 2
    p2 = [
        "You suddenly realize",
        "it wasn't bullets",
        "that saved you,",
        "",
        "but the fact you",
        "still chose to press."
    ]
    pages.append(p2)

    # Page 3
    p3 = [
        "Maybe the real thing",
        "infected was never",
        "just the city,",
        "",
        "but hearts that say",
        "\"I don't care anymore.\""
    ]
    pages.append(p3)

    # Page 4 (last page, return hint)
    p4 = [
        "Your weapon is",
        "loaded again.",
        "",
        "Zombies still wait",
        "ahead of you,",
        "but now you know",
        "",
        "you are more than",
        "just a trigger.",
        "",
        "BTN: Back to game"
    ]
    pages.append(p4)

    for idx, lines in enumerate(pages):
        page_group = displayio.Group()
        display.root_group = page_group

        # Small header
        header = label.Label(terminalio.FONT,
                             text="BOSS EASTER",
                             x=8, y=8)
        page_group.append(header)

        # Body text
        y = 20
        for line in lines:
            lbl = label.Label(terminalio.FONT, text=line, x=0, y=y)
            page_group.append(lbl)
            y += 10

        # Footer hint
        if idx < len(pages) - 1:
            hint = label.Label(terminalio.FONT,
                               text="BTN: Next page",
                               x=0, y=60)
            page_group.append(hint)
        else:
            # Last page already has "BTN: Back to game"
            pass

        # Wait for button
        _wait_for_button(btn)

    # Ending beep
    _play_beep(buzzer, freq=900, duration=0.12, volume=0.4)
    time.sleep(0.1)

