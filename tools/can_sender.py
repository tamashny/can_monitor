"""Sends the frames of config/canmap.yaml through an SLCAN adapter.

The values come from the simulator of the dashboard (app/simulation), so
the bus carries a "working" storage: states, voltages, currents, cells.
Every frame with cycle_ms is sent with its period; the cell data frames
0x297 go round: voltage frames 1..N, then temperature frames 1..M.

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
from parameters import PARAMETERS
from settings import CAN_BITRATE, CAN_SERIAL_BAUDRATE
from simulation.simulator import TICK, Simulator

CELL_DATA_FRAME = 0x297
CELLS_PER_FRAME = 7
# One cell data frame every ... s
CELL_FRAME_PERIOD = 0.05


def cell_frames(cc):
    """
    Values of all cell data frames, in the order they are sent.
    """

    frames = []

    for kind, key in (("VOLTAGE", "cell_voltages"), ("TEMPERATURE", "cell_temperatures")):

        cells = cc[key]

        for number in range(1, len(cells) // CELLS_PER_FRAME + 1):

            start = (number - 1) * CELLS_PER_FRAME
            values = {"parse_type": kind, "parse_index": number}

            for i in range(CELLS_PER_FRAME):
                values[f"parse_data_{i + 1}"] = cells[start + i]

            frames.append(values)

    return frames


def main():

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", required=True, help="serial port of the adapter, e.g. COM7")
    parser.add_argument("--bitrate", type=int, default=CAN_BITRATE, help="CAN bitrate, bit/s")
    parser.add_argument("--verbose", action="store_true", help="print every frame")
    arguments = parser.parse_args()

    simulator = Simulator(PARAMETERS)

    # Periodic frames: (CAN ID, device, period s)
    periodic = [
        (frame_id, device, frame["cycle_ms"] / 1000)
        for frame_id, (device, frame) in protocol.FRAMES.items()
        if "cycle_ms" in frame
    ]

    now = time.monotonic()
    next_send = {frame_id: now for frame_id, _, _ in periodic}
    next_tick = now
    next_cell = now
    cell_index = 0

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

            data = protocol.encode(frame_id, values)
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

                for frame_id, device, period in periodic:

                    if now >= next_send[frame_id]:
                        send(frame_id, PARAMETERS[device])
                        next_send[frame_id] += period

                if now >= next_cell:

                    frames = cell_frames(PARAMETERS["cc"])
                    send(CELL_DATA_FRAME, frames[cell_index % len(frames)])

                    cell_index += 1
                    next_cell += CELL_FRAME_PERIOD

                if now >= report_at:
                    mode = PARAMETERS["bup"]["dc_status"]
                    print(f"{sent} frames sent, {errors} errors, converter {mode}")
                    report_at += 5

                time.sleep(0.002)

        except KeyboardInterrupt:
            print("stopped")


if __name__ == "__main__":
    main()
