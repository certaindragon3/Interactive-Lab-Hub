"""Deterministic 240 x 135 pixel art; also used by the desktop simulator."""

from PIL import Image, ImageDraw, ImageFont

from .core import Phase


SIZE = (240, 135)
BACKGROUND = (9, 15, 18)
TEAL = (41, 173, 157)
ORANGE = (249, 150, 38)
TEXT = (185, 198, 193)
OUTLINE = (43, 64, 65)
FONT = ImageFont.load_default(size=10)

# Pixel coordinates on a 24 x 26 fruit, drawn at 2x without smoothing.
BODY = [(8, 5), (16, 5), (16, 6), (20, 6), (20, 8), (22, 8),
        (22, 12), (23, 12), (23, 19), (21, 19), (21, 22), (18, 22),
        (18, 24), (6, 24), (6, 22), (3, 22), (3, 19), (1, 19),
        (1, 12), (2, 12), (2, 8), (5, 8), (5, 6), (8, 6)]
# Fixed positions keep spots stable between frames; only coverage grows.
SPOTS = [(16, 17, 2), (6, 11, 1), (12, 9, 1), (8, 20, 2),
         (19, 12, 1), (12, 15, 1), (5, 16, 1), (15, 21, 1),
         (16, 8, 1), (10, 12, 1), (19, 19, 1), (11, 22, 1),
         (8, 8, 1), (9, 16, 1), (15, 12, 1), (4, 13, 1),
         (13, 18, 1), (18, 15, 1), (6, 19, 1), (12, 7, 1)]


def _mix(a, b, amount):
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def _fruit(fruit):
    tile = Image.new("RGB", (25, 27), BACKGROUND)
    draw = ImageDraw.Draw(tile)
    if fruit.outline:
        draw.polygon(BODY, outline=OUTLINE)
        draw.line([(12, 5), (12, 2)], fill=OUTLINE)
    else:
        # Ripeness is orange AREA, growing from left to right inside the fruit.
        # Keep both hues intact: a completed half block is half orange / teal,
        # never a uniformly mixed olive-colored fruit.
        teal = _mix(BACKGROUND, TEAL, fruit.brightness)
        orange = _mix(BACKGROUND, ORANGE, fruit.brightness)
        body = Image.new("RGB", tile.size, teal)
        split = 1 + round(23 * fruit.ripeness)  # body spans columns 1..23
        ImageDraw.Draw(body).rectangle((0, 0, split - 1, 26), fill=orange)
        mask = Image.new("L", tile.size)
        ImageDraw.Draw(mask).polygon(BODY, fill=255)
        tile.paste(body, (0, 0), mask)
        # Highlights and shadows use the hue under each pixel, preserving the
        # boundary instead of painting a single hue across both regions.
        shadow = Image.new("L", tile.size)
        ImageDraw.Draw(shadow).line([(4, 18), (4, 20), (7, 20), (7, 22), (17, 22)], fill=255)
        for y in range(tile.height):
            for x in range(tile.width):
                if shadow.getpixel((x, y)):
                    draw.point((x, y), fill=_mix(BACKGROUND, body.getpixel((x, y)), .73))
        for y in range(9, 13):
            for x in range(5, 8):
                draw.point((x, y), fill=_mix(body.getpixel((x, y)), (244, 226, 164), .30))
        draw.line([(12, 5), (12, 2)], fill=(129, 103, 61))
        draw.polygon([(13, 3), (16, 1), (20, 1), (17, 4), (13, 4)],
                     fill=_mix(BACKGROUND, (87, 143, 73), fruit.brightness))
        coverage = fruit.spots * len(SPOTS)
        for index, (x, y, radius) in enumerate(SPOTS):
            amount = max(0.0, min(1.0, coverage - index))
            if amount:
                draw.rectangle((x, y, x + radius, y + radius),
                               fill=_mix(body.getpixel((x, y)), (100, 62, 36), amount))
    return tile.resize((50, 54), Image.Resampling.NEAREST)


def render(view):
    image = Image.new("RGB", SIZE, BACKGROUND)
    draw = ImageDraw.Draw(image)
    if view.phase == Phase.IDLE:
        draw.text((26, 113), "A  WASH", font=FONT, fill=TEXT)
        draw.text((158, 113), "B  DRY", font=FONT, fill=TEXT)
        return image

    draw.text((12, 9), "ORANGE", font=FONT, fill=ORANGE)
    label = view.routine.name.upper()
    draw.text((228 - draw.textlength(label, font=FONT), 9), label, font=FONT, fill=TEXT)
    layer = Image.new("RGB", SIZE, BACKGROUND)
    count = len(view.fruits)
    gap = 22
    left = (SIZE[0] - (50 * count + gap * (count - 1))) // 2
    for index, fruit in enumerate(view.fruits):
        layer.paste(_fruit(fruit), (left + index * (50 + gap), 42))
    if view.opacity < 1:
        layer = Image.blend(Image.new("RGB", SIZE, BACKGROUND), layer, view.opacity)
    image.paste(layer.crop((0, 35, 240, 103)), (0, 35))
    if view.phase == Phase.WAITING:
        caption = f"COLLECT, THEN TAP {view.routine.button}"
    elif view.phase == Phase.FADING:
        caption = "COLLECTED"
    else:
        caption = f"HOLD {view.routine.button} TO CANCEL"
    draw.text(((240 - draw.textlength(caption, font=FONT)) // 2, 113), caption,
              font=FONT, fill=TEXT)
    if view.hold > 0:
        draw.rectangle((12, 130, 227, 132), fill=OUTLINE)
        draw.rectangle((12, 130, 12 + round(215 * view.hold), 132), fill=ORANGE)
    return image
