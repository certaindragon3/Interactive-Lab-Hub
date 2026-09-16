# Running Orange v2

Orange v2 is a separate application; `screen_clock.py`, the course examples,
the boot display, and the first storyboard remain intact. The confirmed
interaction is documented in `orange-v2-design.md` (maintained separately).

Orange records elapsed time. It cannot control a laundry machine, detect its
completion, or detect collection. Brown spots represent time since the preset
duration, not damage or hygiene. One round is held in memory: exiting, a crash,
or a reboot discards it and the next launch starts idle. There is no persistence
or automatic machine synchronization.

## Files and environment

- `orange_timer.py`: command-line entry point; requires an explicit mode.
- `orange_v2/core.py`: pure state, debounce, gestures, and fruit progress.
- `orange_v2/render.py`: the same 240 × 135 Pillow renderer for all modes.
- `orange_v2/hardware.py`: GPIO and ST7789 adapter, imported only in hardware mode.
- `orange_v2/simulator.py`: local browser controls and rendered screen.
- `orange_v2/gallery.py`: reproducible visual fixtures, including a breathing GIF.
- `tests/test_orange_v2.py`, `tests/test_orange_entrypoints.py`: behavior and adapter checks.

Use Python 3.11 or newer. Desktop rendering/simulation needs only Pillow; the
core is standard-library Python. The Pi dependencies are already pinned in
`requirements.txt`, including Pillow 11.3.0 and the Adafruit drivers.

For a new desktop environment, from `Lab 2`:

```bash
python3 -m venv .venv-orange-v2
source .venv-orange-v2/bin/activate
python -m pip install pillow==11.3.0
```

Use a fresh environment name if that path already exists. Do not install the
Pi GPIO stack on the Mac just to run the simulator. The scripts need no font
download or artwork files: Pillow supplies the font and Python draws the fruit.

## Local demo

From `Lab 2`:

```bash
python orange_timer.py --simulate --speed 60
```

Open the loopback URL printed in the terminal, normally
`http://127.0.0.1:8765/`. If the port is occupied, add `--port 8876` or `--port 0`
to choose an available port automatically. It serves only on `127.0.0.1` and
does not access the GPIO, SD card, or Pi network. Use a single browser tab.

Hold the onscreen A/B controls with mouse or touch, or use the A/B keyboard
keys. Very fast desktop taps are extended to 80 ms to pass the hardware's
30 ms debounce; long holds retain their real duration. Keyboard A+B can test simultaneous presses. A focused control activated
with Enter/Space generates a short tap; use A/B keys for timed holds. Switching
away from the page cancels the pending gesture without starting or collecting
a round. An abandoned connection also releases simulator input after one second.

At `--speed 60`, one real second equals one laundry minute: wash takes 38 real
seconds, dry takes 60, and the waiting milestones occur 10/20/30 real seconds
after completion. The two-second hold, 30 ms debounce, five-second breath, and
0.6-second collection fade always use **real time**. Omit `--speed` for normal time.
Use Ctrl+C in the terminal to exit.

To experiment with waiting milestones without changing the design defaults:

```bash
python orange_timer.py --simulate --speed 60 --spot-minutes 5 15 25
```

Provide exactly three positive increasing values. The milestones produce few,
more visible, and dense spots; spots accumulate gradually between them. The
last milestone caps appearance while internal waiting elapsed time continues.

## Interaction contract

| State at press start | Initiating button | Other button / both buttons |
| --- | --- | --- |
| Idle | Short A starts wash; short B starts dry. A hold of at least two seconds does nothing. | A+B has no command. |
| Running | Short press does nothing. Two-second hold cancels, with a filling bottom line; early release clears the line. | No switching, cancellation, or restart. |
| Waiting | Short press or two-second hold confirms collection, briefly fades, then returns idle. | Cannot implicitly collect or replace the round. |

Wash uses two blocks (20 + 18 minutes); dry uses three (20 + 20 + 20).
Only the current fruit breathes. Completed fruit freeze at their prescribed
orange/teal area ratios: orange fills from left to right within each fruit,
while its remaining area stays teal. Unstarted ones are outlines, and idle has
no fruit. At completion all breathing stops and
only the final fruit develops brown spots. There is no numerical countdown,
inverted flashing, extra menu, or automatic transition from washing to drying.
Collect washed clothes and confirm with A, then separately start the dryer and B.

One physical press produces at most one action. Every button must be stably
released before another gesture. A button held during launch must be released
first. Any overlap observed before an action invalidates the gesture until all
buttons are released, including staggered A+B presses. A second button pressed
after an already executed action cannot undo that action. Debounce requires a
stable set for 30 ms; shorter pulses are rejected. Sampling cannot observe an
overlap shorter than the polling interval.

The first observed press edge captures its starting state. A press that begins
while running and ends after the due time cannot confirm collection: an early
release leaves it waiting, while a two-second hold still cancels that round.
A press begun during the fade is ignored even if released after idle returns.

## Reproducible local checks

From `Lab 2`:

```bash
python -m unittest discover -s tests -v
python -m compileall -q orange_timer.py orange_v2 tests
python orange_timer.py --render /tmp/orange-v2-frames
```

Choose a **new** output directory each time. Rendering refuses to overwrite an
existing directory. Output includes 13 native-size PNGs, `contact-sheet.png`,
and `breathing.gif`; names on the contact sheet are test annotations outside the
device screen. Gallery timing is fixed to the confirmed defaults. Use the
simulator to inspect custom speed or spot milestones.

Tests cover wash/dry boundaries, immutable completed fruit, five-second breathing,
spot milestones and visual cap, early release, exact hold threshold, double-button
suppression, wrong-button immunity, collection/fade, all-up rearming, and gestures
across completion. An HTTP test exercises start → waiting → collection → idle
using the actual server. GPIO-adapter tests use fake pins and verify mapping,
rotation, active-low reads, and cleanup; they are **not hardware tests**.

## Run on Orange

The first Pi hardware session was completed on September 16, 2026, after the
device became reachable again. It used an isolated test copy so the existing
Pi checkout's uncommitted work stayed intact. See the
[hardware verification record](ORANGE_V2_HARDWARE_TEST.md) for the tested source,
observed interactions, user-confirmed visuals, and limits of the evidence.
Check connectivity and the current files before starting a later session.

The existing lab environment is `/home/pi/Interactive-Lab-Hub/.venv` (Python 3.11).
The course image's `/home/pi/venv` runs the boot display; preserve it. If the lab
dependencies need installation, use the lab environment and existing pinned
`Lab 2/requirements.txt`, never `/home/pi/venv`.

The adapter matches `screen_clock.py` and the button definitions in
`screen_test.py`:

| Function | BCM GPIO | Header pin / setting |
| --- | --- | --- |
| Display CS | 5 | Pin 29; existing custom CS wire, **not factory CE0** |
| Display DC | 25 | Pin 22 |
| Backlight | 22 | Pin 15 |
| A | 23 | Pin 16, internal pull-up, active-low |
| B | 24 | Pin 18, internal pull-up, active-low |
| SPI | `board.SPI()` | Existing SPI0 wiring, 64 MHz as in the clock example |
| ST7789 | 135 × 240 | offsets 53/40; frame 240 × 135, rotation 90° |

These display settings were checked against the device's clock and boot-display
scripts and exercised by Orange v2 during the recorded hardware session.
Verify the physical wiring again if the hardware setup changes.
Confirm that logical A is physically upper and B lower in the installed landscape
orientation. If they are reversed, use `--swap-buttons`; do not guess or rewire.

On the Pi, after the reviewed files are present in the lab checkout:

```bash
cd /home/pi/Interactive-Lab-Hub
source .venv/bin/activate
python -m pip check
cd "Lab 2"
sudo systemctl stop piscreen.service
python orange_timer.py --hardware --speed 60
# Ctrl+C exits the application.
sudo systemctl start piscreen.service
sudo systemctl is-active piscreen.service
deactivate
```

For real laundry timing, use `python orange_timer.py --hardware` without
`--speed`. SIGINT/Ctrl+C and SIGTERM release GPIO/SPI resources and turn off the
application backlight. They **do not** start, stop, enable, disable, or modify any
service. Restore `piscreen.service` manually after a normal exit **or an error**.
If the shell disconnected, reconnect and run:

```bash
sudo systemctl start piscreen.service
sudo systemctl is-active piscreen.service
```

Make sure the timer process has exited before restoring the service; two
processes must not drive the display at once. If the boot screen fails to return,
inspect `sudo journalctl -u piscreen.service -n 30 --no-pager`. No boot-service
installation or automatic launch is included.

## Validation status and remaining checks

Local verification on September 16, 2026: all **38 tests passed** in an isolated
Mac environment using **Python 3.11.11 + Pillow 11.3.0** (matching the Pi's Python
minor version and pinned Pillow). Compilation passed. All 13 rendered fixtures
were inspected on their contact sheet, and the browser simulator's rendered
screen and keyboard activation were checked. Render tests explicitly distinguish
orange/teal areas from a uniformly blended color. These are Mac results, not
Raspberry Pi hardware results.

Subsequently, the Pi's Python 3.11.2 / Pillow 11.3.0 environment passed the same
38 tests and compilation. A five-minute run of the actual application at 60×
verified physical button input, cancellation, wash/dry completion, collection,
and the tested accidental-input cases. Jiesen confirmed that the orange/teal
regions, breathing, and brown spots displayed normally. The timer stopped and
the boot-display service was independently verified active/running afterward.
The [hardware record](ORANGE_V2_HARDWARE_TEST.md) separates logged observations
from that user confirmation.

Remaining checks are full-duration 38/60-minute operation, visibility at the
intended laundry placement distance, and physical reproduction of edge cases
currently covered only by automated tests (including presses crossing the exact
completion boundary). No course demonstration video is included in this record.

The implementation and tests were authored with Codex assistance from Jiesen's
confirmed interaction design. Report desktop, automated Pi, physical interaction,
and user visual observations separately; none substitutes for a demonstration video.
