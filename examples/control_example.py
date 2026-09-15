#!/usr/bin/env python3
"""
Command-line tool for exercising device control (write) endpoints:
tracking mode, search mode, LED, and buzzer.

These calls change your collar's real behavior - a mode change affects
battery life and update frequency, the buzzer makes noise, and search mode
is meant to be temporary. Use this to validate the implementation in
pettracer/client.py against your own account before relying on it.

Usage:
    export PETTRACER_USERNAME="your_username"
    export PETTRACER_PASSWORD="your_password"

    # List devices and their current mode/state
    python examples/control_example.py list

    # Change tracking mode (fast, normal, slow, super_slow)
    python examples/control_example.py mode <device_id> fast

    # Activate search mode (~21s updates, self-expiring)
    python examples/control_example.py search <device_id>

    # Toggle the LED / buzzer
    python examples/control_example.py led <device_id> on
    python examples/control_example.py buzzer <device_id> off
"""
import argparse
import asyncio
import os

from pettracer import PetTracerClient, TrackingMode

MODE_NAMES = {
    "fast": TrackingMode.FAST,
    "normal": TrackingMode.NORMAL,
    "slow": TrackingMode.SLOW,
    "super_slow": TrackingMode.SUPER_SLOW,
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List devices and their current mode/state")

    mode_p = sub.add_parser("mode", help="Change tracking mode")
    mode_p.add_argument("device_id", type=int)
    mode_p.add_argument("mode", choices=sorted(MODE_NAMES))

    search_p = sub.add_parser("search", help="Activate search mode (~21s updates)")
    search_p.add_argument("device_id", type=int)

    led_p = sub.add_parser("led", help="Turn the LED on or off")
    led_p.add_argument("device_id", type=int)
    led_p.add_argument("state", choices=["on", "off"])

    buz_p = sub.add_parser("buzzer", help="Turn the buzzer on or off")
    buz_p.add_argument("device_id", type=int)
    buz_p.add_argument("state", choices=["on", "off"])

    return parser.parse_args()


def print_device(device):
    name = device.details.name if device.details else "?"
    print(
        f"[{device.id}] {name}: mode={device.mode} modeSet={device.modeSet} "
        f"search={device.search} searchModeDuration={device.searchModeDuration} "
        f"led={device.led} buz={device.buz} battery={device.bat}mV"
    )


async def main():
    args = parse_args()

    username = os.getenv("PETTRACER_USERNAME")
    password = os.getenv("PETTRACER_PASSWORD")
    if not username or not password:
        print("Please set PETTRACER_USERNAME and PETTRACER_PASSWORD environment variables")
        return

    async with PetTracerClient() as client:
        await client.login(username, password)

        if args.command == "list":
            for device in await client.get_all_devices():
                print_device(device)
            return

        device = client.get_device(args.device_id)

        if args.command == "mode":
            mode = MODE_NAMES[args.mode]
            print(f"Setting device {args.device_id} to {mode.name} (cmdNr={int(mode)})...")
            await device.set_tracking_mode(mode)
        elif args.command == "search":
            print(f"Activating search mode on device {args.device_id}...")
            await device.start_search_mode()
        elif args.command == "led":
            print(f"Turning LED {args.state} on device {args.device_id}...")
            await device.set_led(args.state == "on")
        elif args.command == "buzzer":
            print(f"Turning buzzer {args.state} on device {args.device_id}...")
            await device.set_buzzer(args.state == "on")

        print("Request sent. Current cached state (mode/search may take a moment to be acknowledged by the collar):")
        info = await device.get_info()
        if isinstance(info, list):
            info = info[0]
        print_device(info)


if __name__ == "__main__":
    asyncio.run(main())
