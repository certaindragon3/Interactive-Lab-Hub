"""One expressive face plus a separate, neutral interaction-state label."""
import math
import time


def render(state, now=None):
    from PIL import Image, ImageDraw, ImageFont
    now = time.monotonic() if now is None else now
    image = Image.new("RGB", (240, 135), "#11131a")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    mood, phase = state.get("mood", "neutral"), state.get("phase", "idle")
    color = {"smile": "#64dc94", "wry": "#f3ca62", "glare": "#ef736c"}.get(mood, "#a0b4cc")
    offset = round(math.sin(now * 5) * 3) if mood == "smile" else 0
    cx, cy = 56, 58 + offset
    draw.ellipse((cx-39, cy-39, cx+39, cy+39), outline=color, width=3)
    for ex in (cx-14, cx+14):
        draw.ellipse((ex-3, cy-8, ex+3, cy-2), fill=color)
    if mood == "smile":
        draw.arc((cx-18, cy-7, cx+18, cy+22), 10, 170, fill=color, width=3)
    elif mood == "glare":
        draw.line((cx-23, cy-19, cx-6, cy-12), fill=color, width=3)
        draw.line((cx+6, cy-12, cx+23, cy-19), fill=color, width=3)
        draw.line((cx-13, cy+15, cx+13, cy+15), fill=color, width=3)
    else:
        draw.line((cx-15, cy+15, cx+15, cy+10), fill=color, width=3)
        if mood == "wry":
            draw.line((cx+7, cy-19, cx+24, cy-24), fill=color, width=3)
    labels = {"idle": "READY", "connecting": "CONNECTING", "listening": "LISTENING", "thinking": "SAVING",
              "speaking": "SPEAKING", "finalizing": "CHECKING", "synthesizing": "RECAP", "summary": "RECAP",
              "draining": "RECAP", "closing": "CLOSING", "done": "SAVED", "error": "CHECK LOG"}
    draw.text((106, 24), labels.get(phase, phase.upper()), font=font, fill="white")
    # This cue is an activity indicator, never a health/score color.
    for i in range(5):
        height = 5 + int(8 * abs(math.sin(now * 4 + i))) if phase in ("speaking", "summary", "draining") else 5
        draw.rectangle((109+i*13, 68-height, 114+i*13, 68+height), fill="#c2c9d3")
    if phase in ("summary", "draining", "closing", "done", "error"):
        score = state.get("score")
        draw.text((106, 85), "Game: " + (str(score) if score is not None else "--"), font=font, fill="white")
    draw.text((10, 115), "A: start" if phase in ("idle", "done", "error") else "A: recap & finish", font=font, fill="#a0a8b7")
    return image


class Display:
    def __init__(self):
        import board
        import digitalio
        from adafruit_rgb_display import st7789
        self.pins = [digitalio.DigitalInOut(board.D5), digitalio.DigitalInOut(board.D25), digitalio.DigitalInOut(board.D22)]
        self.pins[2].switch_to_output(value=True)
        self.spi = board.SPI()
        self.device = st7789.ST7789(self.spi, cs=self.pins[0], dc=self.pins[1], rst=None,
                                  baudrate=64000000, width=135, height=240, x_offset=53, y_offset=40)

    def show(self, state):
        self.device.image(render(state), rotation=90)

    def close(self):
        for pin in self.pins:
            pin.deinit()
        self.spi.deinit()
