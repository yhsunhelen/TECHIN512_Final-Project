# ui.py
import time
import displayio
import terminalio
from adafruit_display_text import label


def _play_note(buzzer, freq, duration, volume=0.3):
    """播放一个音符。buzzer 为 None 时只延时，不发声。"""
    if buzzer is None:
        time.sleep(duration)
        return

    buzzer.frequency = int(freq)
    buzzer.duty_cycle = int(65535 * volume)
    time.sleep(duration)
    buzzer.duty_cycle = 0
    time.sleep(0.03)  # 音符之间留一点空隙


def _play_boot_melody(buzzer):
    """
    开机旋律：
    la, #la, do, re, re, do, 低音la
    -> A4, A#4, C5, D5, D5, C5, A3
    """
    A3  = 220
    A4  = 440
    AS4 = 466
    C5  = 523
    D5  = 587

    melody = [
        (A4,  0.18),
        (AS4, 0.18),
        (C5,  0.18),
        (D5,  0.22),
        (D5,  0.22),
        (C5,  0.18),
        (A3,  0.30),
    ]

    for freq, dur in melody:
        _play_note(buzzer, freq, dur)


def show_boot_animation(display, btn, buzzer=None):
    """
    Boot animation:
    1. Play short boot melody on buzzer (if provided)
    2. Title "Zombie Shooter" slides in
    3. Story pages with blinking 'N'
    """

    # ===== 0) 开机音乐 =====
    _play_boot_melody(buzzer)

    # ===== 1) 标题飘入 =====
    splash = displayio.Group()
    display.root_group = splash

    title = label.Label(terminalio.FONT, text="Zombie Shooter", x=-80, y=30)
    splash.append(title)

    # 从左往右移动
    for x in range(-80, 20):
        title.x = x
        time.sleep(0.02)

    time.sleep(0.5)

    # ===== 2) 切到剧情画面 =====
    story = displayio.Group()
    display.root_group = story

    # 剧情文字（多行）
    text_label = label.Label(terminalio.FONT, text="", x=0, y=8)
    story.append(text_label)

    # 右下角闪烁的 N
    n_label = label.Label(terminalio.FONT, text="N", x=118, y=60)
    story.append(n_label)

    # 英文剧情（我顺了一下语法）
    pages = [
        "\"Who are you?\"",
        "......",
        "",
        "You wake up\nwith no memories.",
        "You only know\nit's 2080.",
        "A new virus\nappeared in the world.",
        "Those infected\nbecame zombies.",
        "So many zombies...\n......",
        "ZZZZZZZZZZZZZZZ\nZZZZZZZZZZZZZZZ\nZZZZZZZZZZZZZZZ\nZZZZZZZZZZZZZZZ",
        "Being eaten or\nkilling them...",
        "For you it is\nnot a question.",
        "Only one sentence\nkeeps echoing:",
        "To stay alive,\n\"SHOOT THEM!\"",
    ]

    def wait_with_blink():
        """右下角 N 闪烁 + 等待按钮按下"""
        visible = True
        n_label.hidden = False
        last_toggle = time.monotonic()

        while True:
            now = time.monotonic()
            # 每 0.3 秒闪一次
            if now - last_toggle > 0.3:
                visible = not visible
                n_label.hidden = not visible
                last_toggle = now

            # 检测按钮按下（低电平）
            if not btn.value:
                time.sleep(0.05)  # 去抖
                if not btn.value:
                    while not btn.value:
                        time.sleep(0.01)
                    break

            time.sleep(0.01)

    # 依次播放每一页剧情
    for txt in pages:
        text_label.text = txt
        wait_with_blink()

