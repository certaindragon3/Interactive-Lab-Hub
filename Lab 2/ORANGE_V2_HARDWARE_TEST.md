# Orange v2 hardware verification — September 16, 2026

Orange v2 ran on Orange's Raspberry Pi 5 and ST7789 display for five minutes at
60× laundry speed. Physical button input and state transitions were observed in
the program log. After the session, Jiesen confirmed that the orange/teal regions,
breathing animation, and brown spots displayed normally. These are separate
sources of evidence; no photo or video was supplied for this record.

## Setup and scope

| Item | Verified setup |
| --- | --- |
| Application source | `623c103d217d31976a62f0cb1a148741a3b6f0d3` on the personal `Fall2026` branch |
| Device | Raspberry Pi 5, identified by Blinka as `RASPBERRY_PI_5` |
| Runtime | Existing lab environment, Python 3.11.2 and Pillow 11.3.0 |
| Display | ST7789, 240 × 135 landscape frame, rotation 90°, offsets 53/40 |
| Pins | CS GPIO5, DC GPIO25, backlight GPIO22; A/B GPIO23/24, active-low |
| Time settings | Laundry speed 60×; holds remain two real seconds |
| Isolation | New `/home/pi/orange-v2-test.DQPWhV` directory; no overwrite of the existing Pi checkout |

The application files were transferred from the committed source, and the
SHA-256 hashes of the entry point and all five modules matched the Mac copies.
`pip check` found no broken requirements. All **38 automated tests passed on the
Pi**, and compilation succeeded. This includes pure state/render tests, an HTTP
simulator integration test, and fake-pin adapter tests; those test results alone
do not establish physical GPIO behavior.

The physical session then executed the same `orange_timer.py --hardware --speed
60` entry point through a temporary observer. The observer wrapped `Timer.step`
to print raw button changes, actions, and state changes. It did not synthesize
button input or change the timer, gesture, or rendering logic. The real GPIO
adapter supplied the button samples and drove the display.

## Observed physical interactions

The [event log](test-evidence/orange-v2-2026-09-16.log) records real monotonic
seconds relative to observer startup. Values below are rounded from that log;
they are observations from this session, not timing precision guarantees.

| Interaction | Recorded evidence | Result |
| --- | --- | --- |
| A short press from idle | `start_wash` at 39.15 s | Wash started |
| Hold A while washing | Press at 49.80 s; `cancel` at 51.85 s | Cancelled after about 2.05 real seconds |
| B short press from idle | `start_dry` at 52.84 s | Dry started |
| Hold B while drying | Press at 57.44 s; `cancel` at 59.49 s | Cancelled after about 2.05 real seconds |
| Complete a wash | Start 78.71 s; waiting 116.73 s | Completion after about 38.02 real seconds |
| Confirm washed clothes collected | A short press; `collect` at 125.84 s; idle at 126.49 s | Collection fade then idle |
| Short A during another wash | Press/release at 148.62–148.75 s | No restart or cancellation |
| Wrong-button B during that wash | Press/release at 149.58–149.71 s | No switch or cancellation |
| Overlapping A+B during that wash | A, A+B, B, released at 151.49–151.75 s | No action; original wash continued |
| Original wash finishes after those inputs | Start 147.54 s; waiting 185.58 s | Original schedule preserved, about 38.04 seconds |
| Collect that wash and start drying separately | Collection at 199.29 s, idle 199.93 s; B starts dry 201.99 s | Two explicit rounds |
| Complete the dry | Start 201.99 s; waiting 262.05 s | Completion after about 60.06 real seconds |

Jiesen's subsequent confirmation covers the observed two-color ripening,
breathing, and spot appearance. It is not a measured contrast, frame-rate, or
viewing-distance study. The log does not record pixel colors or the user's gaze.

## Exit and recovery

Before the session, `piscreen.service` was active. The test wrapper temporarily
stopped it to avoid concurrent display access and installed an exit cleanup step.
The planned 300-second timeout sent SIGTERM; the application printed its normal
stop message. Timeout returned **124**, which was the expected timeout status,
not an application crash. Cleanup restarted `piscreen.service`.

A separate, fresh SSH connection then verified:

```text
active
SubState=running
TEST_PROCESS_STOPPED
```

No boot-service definition, automatic-start behavior, or course Python environment
was modified. Existing Pi checkout changes to `.gitignore` and `screen_clock.py`
were preserved. The test did not start, stop, or sense a laundry machine.

## What remains unverified

- Full-duration 38-minute washing and 60-minute drying operation at normal speed.
- Visibility and legibility at the intended laundry placement distance.
- Physical reproduction of exact completion-boundary gestures, early-release
  thresholds, long simultaneous holds, and collection by a long hold. These have
  automated coverage; the recorded manual session did not exercise all of them.
- A long real-time wait beyond the visual spot cap. The cap and continuing elapsed
  time are covered by automated checks, not a 30-minute physical waiting session.
- The course demonstration video.

For subsequent runs, follow [ORANGE_V2_RUN.md](ORANGE_V2_RUN.md). Fresh key-based
SSH access was separately verified during setup; authentication material and
machine-specific connection configuration are intentionally outside this commit.
