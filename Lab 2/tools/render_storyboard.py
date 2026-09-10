"""Render the local Orange HTML with Playwright and a separate headless Chrome.

Run on the Mac: python3 "Lab 2/tools/render_storyboard.py"
Requires the Python playwright package and Google Chrome. No server is needed.
Existing outputs are preserved unless --replace is passed.
"""

import argparse
import math
from pathlib import Path
import struct

from playwright.sync_api import sync_playwright


def main():
    lab = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=lab / "storyboard-orange-render.png")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and not args.replace:
        parser.error(f"Output exists: {output}. Use --replace to regenerate it.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        try:
            page = browser.new_page(
                viewport={"width": 1280, "height": 900},
                device_scale_factor=2,
                reduced_motion="reduce",
            )
            page.goto((lab / "storyboard-orange.html").as_uri(), wait_until="load")
            page.add_style_tag(content=".tools { display:none !important; }")
            page.evaluate("""async () => {
                await document.fonts.ready;
                const images = [...document.querySelectorAll('#storyboard img')];
                if (images.length !== 12) throw new Error('Expected 12 storyboard frames');
                await Promise.all(images.map(async image => {
                    await image.decode();
                    if (!image.naturalWidth) throw new Error('Missing image: ' + image.src);
                }));
            }""")
            bounds = page.locator("#storyboard").bounding_box()
            if not bounds or bounds["width"] != 1280:
                raise RuntimeError(f"Unexpected storyboard bounds: {bounds}")
            overflow = page.evaluate("""() => [...document.querySelectorAll('#storyboard *')]
                .filter(el => el.scrollWidth > el.clientWidth + 1)
                .map(el => el.tagName + '.' + el.className)""")
            if overflow:
                raise RuntimeError(f"Content overflows its layout: {overflow}")
            # Screenshot the complete HTML element, including its final row.
            png = page.locator("#storyboard").screenshot(
                scale="device", animations="disabled", timeout=30000,
            )
        finally:
            browser.close()

    width, height = struct.unpack(">II", png[16:24])
    expected_height = math.ceil(bounds["height"] * 2)
    if width != 2560 or abs(height - expected_height) > 2:
        raise RuntimeError(f"Unexpected export size: {width} × {height}; bounds: {bounds}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(png)
    print(f"Exported {output}: {width} × {height} px; 12 images loaded; no overflow.")


if __name__ == "__main__":
    main()
