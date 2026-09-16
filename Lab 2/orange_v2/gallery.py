"""Reproducible visual fixtures generated through real input transitions."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .core import Config, Timer
from .render import render


def started(button, speed=1):
    timer = Timer(Config(speed=speed))
    for now, pressed in ((0, ()), (.05, ()), (.10, (button,)),
                         (.15, (button,)), (.25, ()), (.30, ())):
        timer.step(now, pressed)
    return timer


def samples():
    result = [("idle", Timer().step(0))]
    for name, button, elapsed in (
        ("wash-10m", "A", 600), ("wash-29m", "A", 1740),
        ("dry-10m", "B", 600), ("dry-30m", "B", 1800),
        ("dry-50m", "B", 3000), ("wash-ready", "A", 2280),
        ("wash-wait-10m", "A", 2880), ("wash-wait-20m", "A", 3480),
        ("wash-wait-30m", "A", 4080), ("dry-wait-30m", "B", 5400),
    ):
        timer = started(button)
        result.append((name, timer.step(timer.started + elapsed)))
    timer = started("A")
    hold_start = timer.started + 1800
    timer.step(hold_start, ("A",))
    timer.step(hold_start + .05, ("A",))
    result.append(("wash-hold-1s", timer.step(hold_start + 1, ("A",))))
    timer = started("A")
    ready = timer.started + 2280
    timer.step(ready)
    timer.step(ready + .1, ("A",))
    timer.step(ready + .15, ("A",))
    timer.step(ready + .3)
    timer.step(ready + .35)
    result.append(("collection-fade", timer.step(ready + .65)))
    return result


def write_gallery(directory):
    directory = Path(directory)
    # Keep previous evidence intact; pick a fresh output directory each run.
    directory.mkdir(parents=True, exist_ok=False)
    fixtures = samples()
    sheet = Image.new("RGB", (3 * 520, ((len(fixtures) + 2) // 3) * 325), "#eeeae1")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    for index, (name, view) in enumerate(fixtures):
        frame = render(view)
        frame.save(directory / f"{name}.png")
        x, y = (index % 3) * 520 + 20, (index // 3) * 325
        draw.text((x, y + 8), name, font=font, fill="#25312f")
        sheet.paste(frame.resize((480, 270), Image.Resampling.NEAREST), (x, y + 38))
    sheet.save(directory / "contact-sheet.png")
    timer = started("A", speed=60)
    frames = [render(timer.step(timer.started + 8 + i / 10)) for i in range(50)]
    frames[0].save(directory / "breathing.gif", save_all=True,
                   append_images=frames[1:], duration=100, loop=0)
    print(f"Wrote {len(fixtures)} frames, contact-sheet.png and breathing.gif to {directory}")
