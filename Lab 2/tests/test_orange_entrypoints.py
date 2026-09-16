"""Boundary checks for the HTTP simulator and hardware resource adapter."""

from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image

from orange_v2.core import Timer
from orange_v2.render import render


LAB = Path(__file__).resolve().parents[1]


class SimulatorTests(unittest.TestCase):
    def test_live_http_start_wait_collect_and_shutdown(self):
        process = subprocess.Popen(
            [sys.executable, str(LAB / "orange_timer.py"), "--simulate", "--speed", "36000", "--port", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            line = process.stdout.readline()
            self.assertTrue(line.startswith("Open http://127.0.0.1:"), line)
            base = line.split()[1].rstrip("/")

            def request(path, keys=None):
                data = None if keys is None else json.dumps(keys).encode()
                req = Request(base + path, data=data,
                              headers={"Content-Type": "application/json"})
                with urlopen(req, timeout=3) as response:
                    return response.read()

            def frame():
                return Image.open(BytesIO(request("/frame"))).tobytes()

            self.assertIn(b"local simulator", request("/"))
            time.sleep(.06)  # initial all-buttons-up debounce
            idle = frame()
            self.assertEqual(idle, render(Timer().step(0)).tobytes())
            request("/buttons", ["A"])
            time.sleep(.08)
            request("/buttons", [])
            time.sleep(.2)  # 38 min + 30 min at 36,000x, after release debounce
            self.assertNotEqual(frame(), idle)
            # Completion is stable even as waiting time continues to increase.
            capped = frame()
            time.sleep(.1)
            self.assertEqual(frame(), capped)
            request("/buttons", ["A"])
            time.sleep(.08)
            request("/buttons", [])
            time.sleep(.15)
            fading = frame()
            self.assertNotEqual(fading, capped)
            time.sleep(.6)
            self.assertEqual(frame(), idle)
            # Losing focus releases a candidate without triggering an idle start.
            request("/buttons", ["B"])
            time.sleep(.08)
            request("/reset", [])
            time.sleep(.06)
            self.assertEqual(frame(), idle)
            with self.assertRaises(HTTPError) as caught:
                request("/buttons", ["C"])
            self.assertEqual(caught.exception.code, 400)
        finally:
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, stderr)
        self.assertIn("stopped", stdout)
        self.assertEqual(stderr, "")


class HardwareAdapterTests(unittest.TestCase):
    def test_pin_mapping_active_low_rotation_and_cleanup_without_gpio(self):
        pins = {}

        class Pin:
            def __init__(self, name):
                self.name = name
                self.value = True
                self.closed = False
                pins[name] = self

            def switch_to_input(self, pull):
                self.pull = pull

            def switch_to_output(self, value):
                self.value = value

            def deinit(self):
                self.closed = True

        class SPI:
            closed = False

            def deinit(self):
                self.closed = True

        class TFT:
            def __init__(self, spi, **kwargs):
                self.config = kwargs

            def image(self, image, rotation):
                self.last_size, self.rotation = image.size, rotation

        spi = SPI()
        modules = {
            "board": SimpleNamespace(**{p: p for p in ("D5", "D25", "D22", "D23", "D24")}, SPI=lambda: spi),
            "digitalio": SimpleNamespace(DigitalInOut=Pin, Pull=SimpleNamespace(UP="up")),
            "adafruit_rgb_display": SimpleNamespace(st7789=SimpleNamespace(ST7789=TFT)),
        }
        from orange_v2.hardware import Display
        with patch.dict(sys.modules, modules):
            for swap in (False, True):
                display = Display(swap_buttons=swap)
                self.assertEqual(display.display.config["cs"].name, "D5")
                self.assertEqual(display.display.config["dc"].name, "D25")
                self.assertEqual(pins["D23"].pull, "up")
                pins["D23"].value = False
                self.assertEqual(display.pressed(), {"B" if swap else "A"})
                display.show(Timer().step(0))
                self.assertEqual(display.display.last_size, (240, 135))
                self.assertEqual(display.display.rotation, 90)
                display.close()
                self.assertFalse(pins["D22"].value)
                self.assertTrue(all(pin.closed for pin in pins.values()))
                self.assertTrue(spi.closed)


if __name__ == "__main__":
    unittest.main()
