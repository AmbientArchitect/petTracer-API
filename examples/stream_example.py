#!/usr/bin/env python3
"""
Command-line tool for exercising the realtime PetTracer stream.

Logs in, prints the current device list, then opens the push-update
stream and prints every update as it arrives until you press Ctrl+C.
Useful for manually verifying the streaming implementation in
pettracer/stream.py against a real account.

Usage:
    export PETTRACER_USERNAME="your_username"
    export PETTRACER_PASSWORD="your_password"
    python examples/stream_example.py

    # Or limit to specific device ids:
    python examples/stream_example.py 14758 14759

    # Verbose logging (raw STOMP/SockJS frames, reconnect attempts, etc.):
    python examples/stream_example.py --debug
"""
import argparse
import asyncio
import logging
import os
import signal

from pettracer import PetTracerClient


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "device_ids", nargs="*", type=int, help="Device ids to subscribe to (default: all devices on the account)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable verbose stream logging")
    return parser.parse_args()


async def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    username = os.getenv("PETTRACER_USERNAME")
    password = os.getenv("PETTRACER_PASSWORD")
    if not username or not password:
        print("Please set PETTRACER_USERNAME and PETTRACER_PASSWORD environment variables")
        return

    async with PetTracerClient() as client:
        print("=== Logging in ===")
        await client.login(username, password)
        print(f"Authenticated as {client.user_name} ({client.email})")

        devices = await client.get_all_devices()
        if not devices:
            print("No devices on this account - nothing to stream.")
            return

        print(f"\n=== {len(devices)} device(s) on account ===")
        for d in devices:
            name = d.details.name if d.details else "?"
            print(f"  [{d.id}] {name} - battery {d.bat}mV, last contact {d.lastContact}")

        device_ids = args.device_ids or None
        stream = client.get_stream()

        @stream.on_connect
        def _on_connect():
            print("\n>>> stream connected" + (f" (devices: {device_ids})" if device_ids else " (all devices)"))

        @stream.on_disconnect
        def _on_disconnect(exc):
            print(f">>> stream disconnected: {exc!r} - reconnecting...")

        @stream.on_update
        def _on_update(device):
            name = device.details.name if device.details else device.id
            pos = device.lastPos
            # print(vars(device))
            if pos:
                print(
                    f"[update] {name} (id={device.id}): "
                    f"lat={pos.posLat}, long={pos.posLong}, sat={pos.sat}, "
                    f"time={pos.timeMeasure}, battery={device.bat}mV"
                )
            else:
                print(f"[update] {name} (id={device.id}): lastContact={device.lastContact}, battery={device.bat}mV")

        @stream.on_portal_message
        def _on_portal(data):
            print(f"[portal] {data}")

        print("\n=== Starting stream (Ctrl+C to stop) ===")
        await stream.start(device_ids=device_ids)

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, stop.set)
        except NotImplementedError:
            # add_signal_handler isn't available on some platforms (e.g. Windows)
            pass

        try:
            await stop.wait()
        except KeyboardInterrupt:
            pass
        finally:
            print("\n=== Stopping stream ===")
            await stream.stop()


if __name__ == "__main__":
    asyncio.run(main())
