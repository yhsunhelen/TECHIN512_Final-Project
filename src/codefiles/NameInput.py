# name_input.py
import time
import displayio
import terminalio
from adafruit_display_text import label

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def enter_name(display, encoder, btn, max_len=3):
    """
    用旋钮选择 A-Z，按钮录入名字：
      - 旋钮：旋转切换字母（用 get_delta + 累积，防止不灵敏 / 抖动）
      - 短按（< LONG_PRESS_TIME）：确认当前字母，最多 max_len 个
      - 长按（>= LONG_PRESS_TIME）：结束输入，可以只输入 1 或 2 个字母
    """
    group = displayio.Group()
    display.root_group = group

    title = label.Label(terminalio.FONT, text="ENTER NAME", x=0, y=10)
    name_label = label.Label(terminalio.FONT, text="_" * max_len, x=0, y=30)
    char_label = label.Label(terminalio.FONT, text="A", x=0, y=50)

    group.append(title)
    group.append(name_label)
    group.append(char_label)

    name = ""
    index = 0  # 当前字母在 LETTERS 中的索引

    # 旋钮累积参数
    STEP_THRESHOLD = 2     # 可以调手感：1更灵，3更稳
    accum = 0

    LONG_PRESS_TIME = 0.6  # 长按判定时间（秒）

    while True:
        # ===== 1. 处理旋钮 =====
        encoder.update()
        delta = encoder.get_delta()  # 这段时间净移动多少步

        if delta != 0:
            # ⭐ 关键：如果这次的方向和之前累积的方向相反，先把 accum 清零
            if accum != 0 and (accum > 0 and delta < 0 or accum < 0 and delta > 0):
                accum = 0

            accum += delta

            # 顺时针：切到下一个字母
            if accum >= STEP_THRESHOLD:
                index = (index + 1) % len(LETTERS)
                accum = 0
                char_label.text = LETTERS[index]

            # 逆时针：切到上一个字母
            elif accum <= -STEP_THRESHOLD:
                index = (index - 1) % len(LETTERS)
                accum = 0
                char_label.text = LETTERS[index]

        # ===== 2. 检测按钮按下：短按 / 长按 =====
        if not btn.value:  # 按钮被按下（低电平）
            press_start = time.monotonic()
            long_press = False

            # 等待松手，同时判断是不是长按
            while not btn.value:
                if time.monotonic() - press_start >= LONG_PRESS_TIME:
                    long_press = True
                    break
                time.sleep(0.01)

            if long_press:
                # 长按：结束输入
                if len(name) == 0:
                    # 没输入过，就直接用当前这个字母
                    name = LETTERS[index]
                return name
            else:
                # 短按：确认一个字母
                if len(name) < max_len:
                    name += LETTERS[index]
                    name_label.text = name + "_" * (max_len - len(name))
                else:
                    # 已经满了，再短按直接结束
                    return name

        time.sleep(0.01)
