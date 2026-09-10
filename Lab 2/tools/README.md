# Export the Orange storyboard

The illustrations are individual Imagegen outputs. HTML/CSS handles the page,
short captions, and breathing curve. The full explanation lives in the lab
README. The exported PNG is **2560 × 3574 pixels**.

The exporter uses [Microsoft Playwright](https://github.com/microsoft/playwright)
with a separate headless Google Chrome process. It waits for all 12 images to
decode and for fonts to load, captures the entire storyboard element, and checks
the PNG dimensions and horizontal overflow before writing the result.

On a Mac with Google Chrome and the Python `playwright` package installed, run
from the repository root:

```bash
python3 "Lab 2/tools/render_storyboard.py"
```

To regenerate an existing export after editing the HTML:

```bash
python3 "Lab 2/tools/render_storyboard.py" --replace
```

The layout is 1280 CSS pixels wide with a device scale factor of 2. This renders
text and lines at the target resolution instead of enlarging a previous image.
Export was verified with Python Playwright 1.51.0 and Chrome 152 on macOS.
No web server, logged-in browser profile, or external upload is used.

Playwright was selected after comparing
[capture-website](https://github.com/sindresorhus/capture-website) and
[wkhtmltopdf/wkhtmltoimage](https://github.com/wkhtmltopdf/wkhtmltopdf).
The former is a reasonable alternative; the latter is archived and uses an old
WebKit engine. See the [Playwright screenshot documentation](https://playwright.dev/python/docs/screenshots)
and [Chrome channel support](https://playwright.dev/python/docs/browsers#google-chrome--microsoft-edge).
