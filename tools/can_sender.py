"""Sends the frames of the CAN map through an SLCAN adapter.

The values come from the simulator of the dashboard (app/simulation), so
the bus carries a "working" storage: states, voltages, currents, cells.
Every frame with cycle_ms is sent with its period; the multiplexed frames
of КК go round their arrays, two values per frame.

Command frames (БУНЭ -> device) are never sent: on a bus with real devices
they could switch contactors or the converter.

    python tools/can_sender.py --port COM7 [--bitrate 500000] [--verbose]

Useful to test the dashboard end to end: adapter -> CAN bus -> another
adapter (or BUNEcan) -> dashboard.
"""

import argparse
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

import can

from canbus import protocol
from canmap import CELL_ARRAYS, FRAMES, temperature_sensor
from parameters import PARAMETERS
from settings import CAN_BITRATE, CAN_SERIAL_BAUDRATE
from simulation.simulator import TICK, Simulator


def array_values(frame_name, cc, position):
    """
    Values of a multiplexed frame number `position` of its array.
    """

    key, fields = CELL_ARRAYS[frame_name]
    cells = cc[key]
    free = cc["free_temperatures"]

    start = position * len(fields) % len(cells)
    values = {}

    for offset, field in enumerate(fields):

        place = start + offset

        if len(field) == 3 and place in free:

            # Unknown ROM code: sensor number 31, bus 7 when it is unknown too
            bus, value = free[place]

            values[field[0]] = bus or 7
            values[field[1]] = 31
            values[field[2]] = value

            continue

        if len(field) == 3:
            values[field[0]], values[field[1]] = temperature_sensor(place)
        else:
            values[field[0]] = place

        values[field[-1]] = cells[place]

    return values


def main():

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", required=True, help="serial port of the adapter, e.g. COM7")
    parser.add_argument("--bitrate", type=int, default=CAN_BITRATE, help="CAN bitrate, bit/s")
    parser.add_argument("--verbose", action="store_true", help="print every frame")
    arguments = parser.parse_args()

    simulator = Simulator(PARAMETERS)

    # Periodic frames that a device sends about itself
    periodic = [
        frame
        for frame in FRAMES.values()
        if "cycle_ms" in frame and frame["signals"] and not frame["is_command"]
    ]

    now = time.monotonic()
    next_send = {frame["id"]: now for frame in periodic}
    positions = {name: 0 for name in CELL_ARRAYS}
    counters = {frame["id"]: 0 for frame in periodic}
    next_tick = now

    sent = errors = 0
    report_at = now + 1

    with can.Bus(
        interface="slcan",
        channel=arguments.port,
        bitrate=arguments.bitrate,
        tty_baudrate=CAN_SERIAL_BAUDRATE,
    ) as bus:

        print(f"sending to {arguments.port} at {arguments.bitrate // 1000} kbit/s, Ctrl+C to stop")

        def send(frame_id, values):

            nonlocal sent, errors

            # CNT goes 0..15 separately for every CAN ID
            data = protocol.encode(frame_id, values, counters[frame_id])
            counters[frame_id] = (counters[frame_id] + 1) & 0x0F

            message = can.Message(arbitration_id=frame_id, data=data, is_extended_id=False)

            try:
                bus.send(message)
                sent += 1
            except can.CanError as error:
                errors += 1
                print("send error:", error)

            if arguments.verbose:
                print(f"TX 0x{frame_id:03X}: {data.hex(' ')}")

        try:

            while True:

                now = time.monotonic()

                if now >= next_tick:
                    simulator.tick()
                    next_tick += TICK

                for frame in periodic:

                    frame_id = frame["id"]

                    if now < next_send[frame_id]:
                        continue

                    name = frame["name"]

                    if name in CELL_ARRAYS:
                        values = array_values(name, PARAMETERS["cc"], positions[name])
                        positions[name] += 1
                    else:
                        values = PARAMETERS[frame["device"]]

                    send(frame_id, values)
                    next_send[frame_id] += frame["cycle_ms"] / 1000

                if now >= report_at:
                    bup = PARAMETERS["bup"]
                    print(f'{sent} frames sent, {errors} errors, converter {bup["state"]} {bup["mode"]}')
                    report_at += 5

                time.sleep(0.002)

        except KeyboardInterrupt:
            print("stopped")


if __name__ == "__main__":
    main()
