#!/usr/bin/env python3
"""Orange v2 entry point. Hardware is used only with explicit --hardware."""

import argparse
import signal

from orange_v2.core import Config, Timer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--simulate", action="store_true", help="local browser simulator")
    mode.add_argument("--render", metavar="NEW_DIRECTORY", help="write visual fixtures")
    mode.add_argument("--hardware", action="store_true", help="run the Orange TFT/GPIO adapter")
    parser.add_argument("--speed", type=float, default=1.0, help="laundry seconds per real second")
    parser.add_argument("--spot-minutes", type=float, nargs=3, default=(10, 20, 30),
                        metavar=("FEW", "MORE", "DENSE"), help="three waiting milestones")
    parser.add_argument("--port", type=int, default=8765, help="simulator loopback port")
    parser.add_argument("--swap-buttons", action="store_true", help="swap GPIO23/24 logical A/B")
    args = parser.parse_args()
    try:
        config = Config(speed=args.speed, spot_milestones=tuple(v * 60 for v in args.spot_minutes))
    except ValueError as error:
        parser.error(str(error))
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535")
    if args.render and (args.speed != 1 or tuple(args.spot_minutes) != (10, 20, 30)):
        parser.error("Gallery uses the confirmed default timing; use --simulate for custom timing")
    if args.swap_buttons and not args.hardware:
        parser.error("--swap-buttons applies only to --hardware")

    def stop(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        if args.render:
            from orange_v2.gallery import write_gallery
            write_gallery(args.render)
        elif args.simulate:
            from orange_v2.simulator import run
            run(Timer(config), args.port)
        else:
            from orange_v2.hardware import run
            print(f"Orange v2: speed {config.speed:g}x. Ctrl+C to exit.", flush=True)
            run(Timer(config), args.swap_buttons)
    except KeyboardInterrupt:
        print("\nOrange v2 stopped. Hardware users: restore piscreen.service.")


if __name__ == "__main__":
    main()
