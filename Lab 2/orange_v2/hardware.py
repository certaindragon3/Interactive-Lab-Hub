"""Lazy hardware adapter; importing the core/simulator never imports GPIO."""

import time

from .render import render


class Display:
    def __init__(self, swap_buttons=False):
        import board
        import digitalio
        from adafruit_rgb_display import st7789

        self.resources = []
        self.backlight = None
        self.display = None
        try:
            def pin(name):
                value = digitalio.DigitalInOut(getattr(board, name))
                self.resources.append(value)
                return value

            # Matches the locally verified screen_clock.py, including GPIO5 CS
            # rewire. Do not silently substitute the factory CE0 connection.
            cs, dc = pin("D5"), pin("D25")
            spi = board.SPI()
            self.resources.append(spi)
            self.display = st7789.ST7789(
                spi, cs=cs, dc=dc, rst=None, baudrate=64000000,
                width=135, height=240, x_offset=53, y_offset=40,
            )
            self.backlight = pin("D22")
            self.backlight.switch_to_output(value=True)
            a, b = pin("D23"), pin("D24")
            a.switch_to_input(pull=digitalio.Pull.UP)
            b.switch_to_input(pull=digitalio.Pull.UP)
            self.buttons = {"A": b if swap_buttons else a,
                            "B": a if swap_buttons else b}
        except BaseException:
            self.close()
            raise

    def pressed(self):
        return {name for name, pin in self.buttons.items() if not pin.value}

    def show(self, view):
        self.display.image(render(view), 90)

    def close(self):
        # Best-effort cleanup even if initialization or a display write failed.
        if self.backlight is not None:
            try:
                self.backlight.value = False
            except Exception:
                pass
        for resource in reversed(self.resources):
            try:
                resource.deinit()
            except Exception:
                pass
        self.resources.clear()


def run(timer, swap_buttons=False):
    display = Display(swap_buttons)
    try:
        next_frame = 0
        while True:
            now = time.monotonic()
            view = timer.step(now, display.pressed())
            if now >= next_frame:
                display.show(view)
                next_frame = now + 1 / 30
            time.sleep(0.005)
    finally:
        display.close()
