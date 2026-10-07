"""Reads CAN frames from an SLCAN adapter on a serial port.

A background thread opens the port with python-can, decodes every frame by
config/canmap.yaml (protocol.py) and writes the values into
PARAMETERS[device]. When the port is missing or the adapter is unplugged,
the thread retries every CAN_RECONNECT_INTERVAL seconds.

A timer in the web server loop turns the time of the last frame of every
device into its link time, counts frames per second and updates the device
summaries.
"""

import threading
import time

import can
from nicegui import app

from parameters import DEVICES, NO_DATA
from settings import (
    CAN_BITRATE,
    CAN_INTERFACE,
    CAN_PORT,
    CAN_RECONNECT_INTERVAL,
    CAN_SERIAL_BAUDRATE,
)
from summary import update_summaries

from . import protocol

# Cell data on request: byte 0 — kind and number of the frame (from 1),
# bytes 1..7 — one cell each
CELL_DATA_FRAME = 0x297
CELLS_PER_FRAME = 7

CELL_ARRAYS = {
    "VOLTAGE": "cell_voltages",
    "TEMPERATURE": "cell_temperatures",
}

# How often link times and summaries are updated, s
TICK = 0.25

# CAN bitrates an SLCAN adapter can be set to, bit/s
SLCAN_BITRATES = (10000, 20000, 50000, 83300, 100000, 125000, 250000, 500000, 750000, 1000000)

# The running reader, for the /connect and /disconnect commands
# (None in --debug mode)
READER = None


class CanReader:

    def __init__(self, parameters, port=CAN_PORT, interface=CAN_INTERFACE):

        self.p = parameters
        self.port = port
        self.interface = interface
        self.bitrate = CAN_BITRATE

        # False after /disconnect: the port stays closed until /connect
        self.enabled = True

        # Device key -> time.monotonic() of its last frame
        self.last_seen = {}

        self.frames = 0
        self.frames_counted = 0
        self.counted_at = time.monotonic()

        self.stopping = threading.Event()
        # Set when the port or bitrate changed: reopen the bus now
        self.changed = threading.Event()
        self.thread = None

        self.show_source()
        self.p["bus"].update(state="DISCONNECTED", frames_per_second=0)

    def show_source(self):

        self.p["bus"].update(
            source=f"{self.interface} {self.port}",
            bitrate=self.bitrate,
        )

    # =================================================
    # COMMANDS (/connect, /disconnect)
    # =================================================

    def connect(self, port, bitrate):

        self.port = port
        self.bitrate = bitrate
        self.enabled = True

        self.show_source()
        self.changed.set()

    def disconnect(self):

        self.enabled = False
        self.changed.set()

    # =================================================
    # THREAD
    # =================================================

    def start(self):

        self.thread = threading.Thread(
            target=self.run,
            name="can-reader",
            daemon=True,
        )
        self.thread.start()

    def stop(self):

        self.stopping.set()
        self.changed.set()

        if self.thread:
            self.thread.join(timeout=2)

    def open_bus(self):

        options = {}

        if self.interface == "slcan":
            options["tty_baudrate"] = CAN_SERIAL_BAUDRATE

        return can.Bus(
            interface=self.interface,
            channel=self.port,
            bitrate=self.bitrate,
            **options,
        )

    def wait(self, seconds):
        """
        Pause, but wake up at once on /connect, /disconnect or stop.
        """

        self.changed.wait(seconds)

    def run(self):

        bus_status = self.p["bus"]

        while not self.stopping.is_set():

            self.changed.clear()

            if not self.enabled:
                bus_status.update(state="DISCONNECTED", error="disconnected by the operator")
                self.wait(1)
                continue

            try:

                with self.open_bus() as bus:

                    bus_status.update(state="CONNECTED", error=NO_DATA)

                    while not self.stopping.is_set() and not self.changed.is_set():

                        message = bus.recv(timeout=0.5)

                        if message is not None:
                            self.handle(message)

                bus_status["state"] = "DISCONNECTED"

            # Port missing, busy or unplugged: try again later
            except (can.CanError, OSError, ValueError) as error:

                bus_status.update(state="DISCONNECTED", error=str(error))

                self.wait(CAN_RECONNECT_INTERVAL)

    # =================================================
    # FRAMES
    # =================================================

    def handle(self, message):

        self.frames += 1

        if message.is_error_frame or message.is_remote_frame:
            return

        frame_id = message.arbitration_id
        device = protocol.find_device(frame_id)

        if device not in self.p:
            return

        values = protocol.decode(message)

        self.last_seen[device] = time.monotonic()

        if frame_id == CELL_DATA_FRAME:
            self.store_cells(self.p[device], values)
        else:
            self.p[device].update(values)

    def store_cells(self, device, values):
        """
        Put the 7 values of a cell data frame into their places in the array.
        """

        key = CELL_ARRAYS.get(values.get("parse_type"))
        number = values.get("parse_index")

        if key is None or not isinstance(number, int) or number < 1:
            return

        cells = device[key]
        start = (number - 1) * CELLS_PER_FRAME

        for i in range(CELLS_PER_FRAME):

            if start + i < len(cells):
                cells[start + i] = values.get(f"parse_data_{i + 1}", NO_DATA)

    # =================================================
    # LINK TIMES AND SUMMARIES
    # =================================================

    def tick(self):

        now = time.monotonic()

        for key, *_ in DEVICES:

            seen = self.last_seen.get(key)

            self.p[key]["link"] = round((now - seen) * 1000) if seen else NO_DATA

        if now - self.counted_at >= 1:

            self.p["bus"]["frames_per_second"] = round(
                (self.frames - self.frames_counted) / (now - self.counted_at)
            )

            self.frames_counted = self.frames
            self.counted_at = now

        update_summaries(self.p)


def start_reader(parameters, port=CAN_PORT):
    """
    Read the bus while the web server runs.
    """

    global READER

    reader = CanReader(parameters, port)
    READER = reader

    # Only in the process that serves the page: with auto-reload the
    # parent process must not hold the serial port
    app.on_startup(reader.start)
    app.on_shutdown(reader.stop)

    app.timer(TICK, reader.tick)

    return reader
