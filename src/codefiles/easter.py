# easter.py
import time
import random
import displayio
import terminalio
from adafruit_display_text import label


def _play_glitch_beep(buzzer):
    """短促的失真蜂鸣噪音"""
    if buzzer is None:
        return
    # 随机频率 + 很短的时间，营造“干扰”感
    freq = random.randint(300, 2000)
    buzzer.frequency = freq
    buzzer.duty_cycle = int(65535 * 0.3)
    time.sleep(0.03)
    buzzer.duty_cycle = 0


def _show_paged_text(display, btn, pages, buzzer=None, glitch=False):
    """
    公共函数：一页一页显示 pages 文本
    - 右下角闪烁 'N'
    - glitch=True 时：屏幕轻微抖动 + 偶尔文本闪烁 + 蜂鸣器噪音 + 小僵尸图标
    """
    group = displayio.Group()
    display.root_group = group

    # 主剧情文字
    text_label = label.Label(terminalio.FONT, text="", x=0, y=8)
    group.append(text_label)

    # 右下角闪烁的 N
    n_label = label.Label(terminalio.FONT, text="N", x=118, y=60)
    group.append(n_label)

    # 如果需要干扰效果：加一个小僵尸 ASCII
    if glitch:
        z1 = label.Label(terminalio.FONT, text="  __",  x=80, y=18)
        z2 = label.Label(terminalio.FONT, text="(xx)",  x=80, y=28)
        z3 = label.Label(terminalio.FONT, text="/||\\", x=80, y=38)  # 注意反斜杠要转义
        group.append(z1)
        group.append(z2)
        group.append(z3)

    def wait_with_blink():
        """
        右下角 N 闪烁 + （可选）屏幕抖动 / 文本闪烁 / 噪音
        等待按钮按下进入下一页
        """
        visible = True
        n_label.hidden = False
        last_toggle = time.monotonic()
        last_shake = time.monotonic()

        base_x = 0
        base_y = 0
        group.x = base_x
        group.y = base_y

        while True:
            now = time.monotonic()

            # 0.3 秒闪一次 N
            if now - last_toggle > 0.3:
                visible = not visible
                n_label.hidden = not visible
                last_toggle = now

                if glitch:
                    # 每次闪烁 N 时，顺便来一下噪音
                    _play_glitch_beep(buzzer)

            if glitch:
                # 每 0.1 秒随机轻微抖动一次
                if now - last_shake > 0.1:
                    dx = random.choice([-1, 0, 1])
                    dy = random.choice([-1, 0, 1])
                    group.x = base_x + dx
                    group.y = base_y + dy
                    last_shake = now

                # 偶尔让文字闪一下（模拟干扰）
                if random.random() < 0.03:
                    text_label.hidden = True
                else:
                    text_label.hidden = False

            # 检测按钮按下
            if not btn.value:  # 被按下（低电平）
                time.sleep(0.05)  # 简单去抖
                if not btn.value:
                    # 等待松手再返回
                    while not btn.value:
                        time.sleep(0.01)
                    break

            time.sleep(0.01)

        # 恢复位置 / 显示，避免影响下一页
        group.x = base_x
        group.y = base_y
        text_label.hidden = False
        n_label.hidden = False

    # 一页一页播放
    for txt in pages:
        text_label.text = txt
        wait_with_blink()


def show_no_shot(display, btn, buzzer=None):
    """
    整局不射击 → 隐藏彩蛋
    1. 电台杂音剧情（带噪音 + 抖动 + 小僵尸）
    2. 僵尸王彩蛋结尾
    """

    # 第一段：电台杂音 / 神秘声音（带干扰）
    pages_radio = [
        "'@HAJs…Hell@j\nCAnYo36\nhear…me'",
        "......",
        "Someone is speaking.\nYou heard\nthat.",
        "Or, it's not someone\nIt's zombie?!",
        "......",
    ]
    _show_paged_text(display, btn, pages_radio, buzzer=buzzer, glitch=True)

    # 第二段：最终彩蛋（你是僵尸王），不干扰，好好给你看字
    group = displayio.Group()
    display.root_group = group

    # 标题
    title = label.Label(terminalio.FONT, text="EASTER EGG!!!", x=8, y=8)
    group.append(title)

    # 小表情
    face = label.Label(terminalio.FONT, text="^_^", x=50, y=24)
    group.append(face)

    # 文案
    line1 = label.Label(terminalio.FONT, text="SO YOU'RE THE", x=8, y=40)
    group.append(line1)
    line2 = label.Label(terminalio.FONT, text="ZOMBIE KING!", x=12, y=52)
    group.append(line2)

    # 返回提示
    hint = label.Label(terminalio.FONT, text="BTN: BACK TO MENU", x=0, y=60)
    group.append(hint)

    # 等待按钮按下退出
    while True:
        if not btn.value:
            while not btn.value:
                time.sleep(0.01)
            break
        time.sleep(0.01)

