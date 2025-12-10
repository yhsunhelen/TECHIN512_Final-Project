import time
import displayio
import terminalio
from adafruit_display_text import label

# 主菜单选项
MENU_OPTIONS = ["PLAY", "SCORES", "SETTINGS"]

# 难度菜单选项
DIFFICULTY_OPTIONS = ["EASY", "NORMAL", "DIFFICULT"]

# 旋钮累积阈值：累积到 ±2 才真正移动一格菜单
STEP_THRESHOLD = 2


# ========== 主菜单绘制 ==========

def draw_menu(display, selected, current_difficulty):
    """绘制主菜单界面，并在 SETTINGS 后显示当前难度"""
    group = displayio.Group()
    display.root_group = group

    # 标题
    title = label.Label(
        terminalio.FONT,
        text="ZOMBIE SHOOTER",
        x=5,
        y=10
    )
    group.append(title)

    # 菜单选项列表
    start_y = 28
    for i, txt in enumerate(MENU_OPTIONS):
        # SETTINGS 后面加上当前难度
        if txt == "SETTINGS":
            txt_to_show = "SETTINGS(" + current_difficulty + ")"
        else:
            txt_to_show = txt

        prefix = "> " if i == selected else "  "
        item = label.Label(
            terminalio.FONT,
            text=prefix + txt_to_show,
            x=5,
            y=start_y + i * 12
        )
        group.append(item)

    return group


def main_menu(display, encoder, btn, current_difficulty):
    """
    主菜单逻辑：
    - 旋钮：用 get_delta() + 累积，避免抖动来回跳
    - 按按钮：确认选择
    """
    selected = 0

    # 旋钮累积量
    accum = 0

    # 先画一次菜单
    draw_menu(display, selected, current_difficulty)

    while True:
        # 更新旋钮内部状态
        encoder.update()
        delta = encoder.get_delta()  # 这段时间的净变化（可能是 -3, -2, -1, 0, 1,...）

        if delta != 0:
            accum += delta

            # 顺时针：累积到正方向阈值
            if accum >= STEP_THRESHOLD:
                selected = (selected + 1) % len(MENU_OPTIONS)
                accum = 0
                draw_menu(display, selected, current_difficulty)

            # 逆时针：累积到负方向阈值
            elif accum <= -STEP_THRESHOLD:
                selected = (selected - 1) % len(MENU_OPTIONS)
                accum = 0
                draw_menu(display, selected, current_difficulty)

        # 按钮确认
        if not btn.value:
            time.sleep(0.15)  # 简单去抖
            if not btn.value:
                while not btn.value:
                    time.sleep(0.01)
                return MENU_OPTIONS[selected]

        time.sleep(0.01)


# ========== 难度菜单绘制 ==========

def draw_difficulty_menu(display, selected):
    """绘制难度选择菜单"""
    group = displayio.Group()
    display.root_group = group

    # 标题
    title = label.Label(
        terminalio.FONT,
        text="SELECT LEVEL",
        x=20,
        y=10
    )
    group.append(title)

    # 难度选项
    start_y = 28
    for i, txt in enumerate(DIFFICULTY_OPTIONS):
        prefix = "> " if i == selected else "  "
        item = label.Label(
            terminalio.FONT,
            text=prefix + txt,
            x=30,
            y=start_y + i * 12
        )
        group.append(item)

    return group


def difficulty_menu(display, encoder, btn):
    """
    难度菜单逻辑：
    - 一样用累积的方式来防抖
    - 返回 "EASY" / "NORMAL" / "DIFFICULT"
    """
    selected = 1  # 默认 NORMAL
    accum = 0

    draw_difficulty_menu(display, selected)

    while True:
        encoder.update()
        delta = encoder.get_delta()

        if delta != 0:
            accum += delta

            if accum >= STEP_THRESHOLD:
                selected = (selected + 1) % len(DIFFICULTY_OPTIONS)
                accum = 0
                draw_difficulty_menu(display, selected)
            elif accum <= -STEP_THRESHOLD:
                selected = (selected - 1) % len(DIFFICULTY_OPTIONS)
                accum = 0
                draw_difficulty_menu(display, selected)

        # 按钮确认
        if not btn.value:
            time.sleep(0.15)
            if not btn.value:
                while not btn.value:
                    time.sleep(0.01)
                return DIFFICULTY_OPTIONS[selected]

        time.sleep(0.01)


