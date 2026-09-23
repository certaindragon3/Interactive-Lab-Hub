#!/usr/bin/env python3
"""Use Orange's upper Mini PiTFT button (GPIO23) to start/stop GPT-Live.

Run through run_roast_button.sh, which manages the competing boot display.
This controller uses the existing Lab 2 GPIO environment. The voice client
runs in Lab 3's independent environment.
"""

import argparse
import math
import signal
import subprocess
import sys
import time
from pathlib import Path

import board
import digitalio


LAB_DIR = Path(__file__).resolve().parent.parent
CLIENT = LAB_DIR / "speech-scripts" / "roast_master_live.py"
PYTHON = LAB_DIR / ".venv" / "bin" / "python"


def beep(frequency: int, count: int = 1) -> None:
    """A short audible acknowledgment before audio starts or after it stops."""
    rate = 24000
    tone = bytearray()
    for i in range(int(rate * 0.12)):
        value = int(6000 * math.sin(2 * math.pi * frequency * i / rate))
        tone.extend(value.to_bytes(2, "little", signed=True))
    try:
        for _ in range(count):
            subprocess.run(
                ["aplay", "-q", "-D", "default", "-t", "raw", "-f", "S16_LE",
                 "-r", "24000", "-c", "1"],
                input=tone, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=2, check=False,
            )
            if count > 1:
                time.sleep(0.08)
    except (OSError, subprocess.TimeoutExpired):
        pass


class VoiceSession:
    def __init__(self) -> None:
        self.recorder: subprocess.Popen | None = None
        self.agent: subprocess.Popen | None = None
        self.player: subprocess.Popen | None = None

    @property
    def running(self) -> bool:
        return self.agent is not None and self.agent.poll() is None

    def start(self, max_seconds: int) -> None:
        if not PYTHON.is_file():
            raise RuntimeError(f"Missing Lab 3 environment: {PYTHON}")
        beep(880)
        self.recorder = subprocess.Popen(
            ["arecord", "-q", "-D", "default", "-t", "raw", "-f", "S16_LE",
             "-r", "24000", "-c", "1"],
            stdout=subprocess.PIPE, start_new_session=True,
        )
        assert self.recorder.stdout is not None
        try:
            self.agent = subprocess.Popen(
                [str(PYTHON), "-u", str(CLIENT)],
                stdin=self.recorder.stdout, stdout=subprocess.PIPE,
                start_new_session=True,
            )
            self.recorder.stdout.close()
            assert self.agent.stdout is not None
            self.player = subprocess.Popen(
                ["aplay", "-q", "-D", "default", "-t", "raw", "-f", "S16_LE",
                 "-r", "24000", "-c", "1"],
                stdin=self.agent.stdout, start_new_session=True,
            )
            self.agent.stdout.close()
        except BaseException:
            self.stop()
            raise
        print(f"已按 A 开始；再按 A 停止。最长运行 {max_seconds} 秒。", flush=True)

    def stop(self) -> None:
        recorder, agent, player = self.recorder, self.agent, self.player
        self.recorder = self.agent = self.player = None
        if recorder is not None and recorder.poll() is None:
            recorder.terminate()  # EOF lets the API client close its session.
        if recorder is not None:
            try:
                recorder.wait(timeout=3)
            except subprocess.TimeoutExpired:
                recorder.kill()
                recorder.wait()
        if agent is not None:
            try:
                agent.wait(timeout=20)
            except subprocess.TimeoutExpired:
                agent.terminate()
                try:
                    agent.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    agent.kill()
                    agent.wait()
        if player is not None:
            try:
                player.wait(timeout=4)
            except subprocess.TimeoutExpired:
                player.terminate()
                player.wait()
        if agent is not None:
            print(f"语音会话已停止（客户端退出码 {agent.returncode}）。", flush=True)
            beep(440, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=int, default=180)
    args = parser.parse_args()
    if not 10 <= args.max_seconds <= 180:
        parser.error("--max-seconds must be between 10 and 180")

    button = digitalio.DigitalInOut(board.D23)
    button.switch_to_input(pull=digitalio.Pull.UP)
    session = VoiceSession()
    started_at: float | None = None
    raw = button.value
    stable = raw
    changed_at = time.monotonic()
    print("按 Orange 上方 A 键开始；再次按 A 键停止。Ctrl+C 退出。", flush=True)
    try:
        while True:
            now = time.monotonic()
            current = button.value
            if current != raw:
                raw = current
                changed_at = now
            if current != stable and now - changed_at >= 0.06:
                stable = current
                if not stable:  # active-low press; one action per press
                    if session.running:
                        session.stop()
                        started_at = None
                    else:
                        session.stop()  # clear any failed prior process
                        session.start(args.max_seconds)
                        started_at = now
            if session.agent is not None and not session.running:
                print("客户端自行退出；请查看上面的错误。", flush=True)
                session.stop()
                started_at = None
            if session.running and started_at is not None and now - started_at >= args.max_seconds:
                print("达到会话时间上限，自动停止。", flush=True)
                session.stop()
                started_at = None
            time.sleep(0.02)
    finally:
        session.stop()
        button.deinit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已退出。", file=sys.stderr)
