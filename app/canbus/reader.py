"""Reads the two CAN buses of the storage from two SLCAN adapters.

The system works on the main (CAN1) and the reserve (CAN2) bus at the same
time. Every bus has its own adapter and background thread. The thread opens
the port with python-can and retries every CAN_RECONNECT_INTERVAL seconds
when the port is missing or the adapter is unplugged.

Frames are checked separately on every bus (document 03, section 1): DLC, CRC
and CNT. A valid frame from either bus updates PARAMETERS[device]; the same
frame from the other bus just writes the same values again.

A timer in the web server loop turns the time of the last frame of every
device into its link time on each bus, clears values whose frames stopped
coming on both buses, counts frames per second and updates the summaries.
"""

import threading
import time

import can
from nicegui import app

from canmap import CELL_ARRAYS, FRAMES, TEMPERATURE_BUS_SIZES, cell_place, signal_keys
from frontend.events import log_emcy
from parameters import DEVICES, NO_DATA
from settings import (
    CAN_BITRATE,
    CAN_INTERFACE,
    CAN_INVALID_LIMIT,
    CAN_PORT,
    CAN_RESTORE_COUNT,
    CAN_RECONNECT_INTERVAL,
    CAN_RESERVE_PORT,
    CAN_SERIAL_BAUDRATE,
)
from summary import update_summaries

from . import protocol

# How often link times and summaries are updated, s
TICK = 0.25

# A full pass of array_cc_t takes 510 ms: a cell value missing for two passes
# has no data, s
CELL_STALE = 1.1

# Values of a frame are cleared after its timeout_ms, but not sooner than
# this: a PC and a USB adapter deliver frames with delays, s
FRAME_STALE_MIN = 0.5

# The same frame from the other bus within this time is a copy, not a new one, s
DUPLICATE_WINDOW = 0.05

# Frames of a device closer than this are one contact: it sends several
# frames in one cycle, and a USB adapter delivers them in a burst, s
CONTACT_MERGE = 0.003

# CAN bitrates an SLCAN adapter can be set to, bit/s
SLCAN_BITRATES = (10000, 20000, 50000, 83300, 100000, 125000, 250000, 500000, 750000, 1000000)

# The running reader, for the /connect and /disconnect commands
# (None in --debug mode)
READER = None


class BusChannel:
    """
    One CAN bus: its adapter, its thread and the state of its frames.
    """

    def __init__(self, reader, port, status_prefix, link_key):

        self.reader = reader
        self.port = port

        # Keys of this bus in PARAMETERS
        self.port_key = f"{status_prefix}port"
        self.state_key = f"{status_prefix}state"
        self.error_key = f"{status_prefix}error"
        self.fps_key = f"{status_prefix}frames_per_second"
        self.link_key = link_key

        self.frames = 0
        self.frames_counted = 0

        # Where the next value of array_cc_t goes: unknown sensors do not
        # say their place, it follows from the order of the values
        self.temperature_cursor = 0

        # Set when the port or bitrate changed: reopen the bus now
        self.changed = threading.Event()
        self.thread = None

        self.reset_frames()

    def reset_frames(self):
        """
        Counters and timeouts of the previous connection mean nothing now.
        """

        self.last_seen = {}         # device key -> time of its last valid frame
        self.frame_seen = {}        # CAN ID of a periodic frame -> same
        self.last_counts = {}       # CAN ID -> CNT of the last valid frame
        self.invalid_frames = {}    # CAN ID -> invalid frames in a row
        self.lost_frames = set()    # CAN IDs of the frames without link: timeout or invalid frames
        self.runs = {}              # CAN ID -> (valid frames in a row with CNT + 1, last CNT)

    # =================================================
    # THREAD
    # =================================================

    def start(self):

        self.thread = threading.Thread(
            target=self.run,
            name=f"can-{self.state_key}",
            daemon=True,
        )
        self.thread.start()

    def join(self):

        if self.thread:
            self.thread.join(timeout=2)

    def open_bus(self):

        options = {}

        if self.reader.interface == "slcan":
            options["tty_baudrate"] = CAN_SERIAL_BAUDRATE

        return can.Bus(
            interface=self.reader.interface,
            channel=self.port,
            bitrate=self.reader.bitrate,
            **options,
        )

    def run(self):

        reader = self.reader
        status = reader.p["bus"]

        while not reader.stopping.is_set():

            self.changed.clear()

            if not reader.enabled:
                status.update({
                    self.state_key: "DISCONNECTED",
                    self.error_key: "disconnected by the operator",
                })
                self.changed.wait(1)
                continue

            try:

                with self.open_bus() as bus:

                    with reader.lock:
                        self.reset_frames()

                    status.update({self.state_key: "CONNECTED", self.error_key: NO_DATA})

                    while not reader.stopping.is_set() and not self.changed.is_set():

                        message = bus.recv(timeout=0.5)

                        if message is not None:
                            reader.handle(self, message)

                status[self.state_key] = "DISCONNECTED"

            # Port missing, busy or unplugged: try again later
            except (can.CanError, OSError, ValueError) as error:

                status.update({self.state_key: "DISCONNECTED", self.error_key: str(error)})

                self.changed.wait(CAN_RECONNECT_INTERVAL)

    # =================================================
    # FRAMES OF THIS BUS
    # =================================================

    def frame_is_valid(self, frame, data):
        """
        Rules of the CAN protocol (document 03, section 1): a frame is invalid
        with a wrong DLC, a wrong CRC or a CNT equal to the previous one on
        this bus. A gap in CNT is not an error, the timeout covers lost frames.
        """

        if frame["dlc"] is not None and len(data) != frame["dlc"]:
            return False

        if not protocol.crc_valid(frame, data):
            return False

        cnt = protocol.frame_counter(frame, data)

        if cnt is None:
            return True

        if cnt == self.last_counts.get(frame["id"]):
            return False

        self.last_counts[frame["id"]] = cnt

        return True

    def devices_without_link(self):
        """
        Devices with a frame in timeout or with too many invalid frames in a row.
        """

        lost = {FRAMES[frame_id]["sender"] for frame_id in self.lost_frames}

        invalid = {
            FRAMES[frame_id]["sender"]
            for frame_id, count in self.invalid_frames.items()
            if count >= CAN_INVALID_LIMIT
        }

        return lost | invalid

    def expire_frames(self, now):

        for frame_id, seen in list(self.frame_seen.items()):

            if now - seen > frame_timeout(FRAMES[frame_id]):
                del self.frame_seen[frame_id]
                self.lost_frames.add(frame_id)
                self.runs.pop(frame_id, None)     # a timeout restarts the count, REQ-1-8

    def restored(self, frame, data):
        """
        Document 03, REQ-1-8: the link of a frame comes back after
        CAN_RESTORE_COUNT valid frames in a row, each with CNT one more than the
        previous one. Frames without CNT only need no invalid frame between.
        """

        cnt = protocol.frame_counter(frame, data)
        run, last = self.runs.get(frame["id"], (0, None))

        if cnt is None:
            run += 1
        elif run and last is not None and cnt == (last + 1) & 0x0F:
            run += 1
        else:
            run = 1

        run = min(run, CAN_RESTORE_COUNT)
        self.runs[frame["id"]] = (run, cnt)

        return run >= CAN_RESTORE_COUNT

    def update_links(self, now):
        """
        Time since the last valid frame of every device on this bus, ms.
        """

        connected = self.reader.p["bus"][self.state_key] == "CONNECTED"
        without_link = self.devices_without_link()

        for key, *_ in DEVICES:

            seen = self.last_seen.get(key)

            if not connected or seen is None or key in without_link:
                self.reader.p[key][self.link_key] = NO_DATA
            else:
                self.reader.p[key][self.link_key] = round((now - seen) * 1000)


def frame_timeout(frame):

    timeout = frame.get("timeout_ms", frame["cycle_ms"] * 3) / 1000

    return max(timeout, FRAME_STALE_MIN)


class CanReader:

    def __init__(
        self,
        parameters,
        port=CAN_PORT,
        reserve_port=CAN_RESERVE_PORT,
        interface=CAN_INTERFACE,
    ):

        self.p = parameters
        self.interface = interface
        self.bitrate = CAN_BITRATE

        # False after /disconnect: the ports stay closed until /connect
        self.enabled = True

        # The two threads and the timer work with the same values
        self.lock = threading.Lock()

        self.main = BusChannel(self, port, "", "link_main")
        self.reserve = BusChannel(self, reserve_port, "reserve_", "link_reserve")
        self.channels = (self.main, self.reserve)

        # CAN ID of a periodic frame -> time of its last valid copy on any bus
        self.frame_seen = {}

        # Cell array -> time of the last value of every place
        cc = parameters["cc"]
        self.cell_seen = {
            key: [None] * len(cc[key])
            for key in ("cell_voltages", "cell_temperatures")
        }
        # Same for the sensors with an unknown ROM code, by the place they took
        self.free_seen = [None] * len(cc["cell_temperatures"])

        # CAN ID -> (data, time, bus) of the last frame that was not a copy
        self.last_frames = {}

        # Device key -> time of its last contact on any bus
        self.last_contact = {}

        self.counted_at = time.monotonic()

        self.stopping = threading.Event()

        self.show_source()

        for channel in self.channels:
            self.p["bus"].update({channel.state_key: "DISCONNECTED", channel.fps_key: 0})

    def show_source(self):

        self.p["bus"]["bitrate"] = self.bitrate

        for channel in self.channels:
            self.p["bus"][channel.port_key] = channel.port

    # =================================================
    # COMMANDS (/connect, /disconnect)
    # =================================================

    def connect(self, port, bitrate):
        """
        Open the main bus on `port`. Both buses have the same bitrate, the
        port of the reserve bus comes from the settings.
        """

        self.main.port = port
        self.bitrate = bitrate
        self.enabled = True

        self.show_source()

        for channel in self.channels:
            channel.changed.set()

    def disconnect(self):

        self.enabled = False

        for channel in self.channels:
            channel.changed.set()

    # =================================================
    # THREADS
    # =================================================

    def start(self):

        for channel in self.channels:
            channel.start()

    def stop(self):

        self.stopping.set()

        for channel in self.channels:
            channel.changed.set()

        for channel in self.channels:
            channel.join()

    # =================================================
    # FRAMES
    # =================================================

    def handle(self, channel, message):

        channel.frames += 1

        if message.is_error_frame or message.is_remote_frame:
            return

        frame = protocol.find_frame(message.arbitration_id)

        if frame is None or frame["device"] not in self.p:
            return

        frame_id = frame["id"]
        data = bytes(message.data)

        with self.lock:

            # An invalid frame is dropped and does not extend the timeout
            if not channel.frame_is_valid(frame, data):
                count = channel.invalid_frames.get(frame_id, 0) + 1
                channel.invalid_frames[frame_id] = count
                channel.runs.pop(frame_id, None)

                if count >= CAN_INVALID_LIMIT:
                    channel.lost_frames.add(frame_id)
                return

            channel.invalid_frames.pop(frame_id, None)

            # REQ-1-8: a lost frame needs several valid frames in a row to come back
            if channel.restored(frame, data):
                channel.lost_frames.discard(frame_id)

            values = protocol.decode(message)

            now = time.monotonic()

            # A command frame shows that БУНЭ is alive, not the device it is for
            channel.last_seen[frame["sender"]] = now

            if "cycle_ms" in frame:
                channel.frame_seen[frame_id] = now
                self.frame_seen[frame_id] = now

            device = frame["device"]

            is_copy = self.is_copy(channel, frame_id, data, now)

            if not is_copy:
                self.note_contact(frame["sender"], now)

            if frame["canopen"] == "emcy":

                if not is_copy:
                    log_emcy(device, values)

            elif frame["name"] in CELL_ARRAYS:
                self.store_cells(channel, self.p[device], frame["name"], values, now)

            else:
                self.p[device].update(values)

    def is_copy(self, channel, frame_id, data, now):
        """
        Devices send every frame to both buses: the second one is a copy.
        """

        last = self.last_frames.get(frame_id)

        copy = (
            last is not None
            and last[0] == data
            and last[2] is not channel
            and now - last[1] <= DUPLICATE_WINDOW
        )

        if not copy:
            self.last_frames[frame_id] = (data, now, channel)

        return copy

    def note_contact(self, device, now):
        """
        Link of a device: time between its last two contacts on any bus, ms.
        """

        last = self.last_contact.get(device)

        self.last_contact[device] = now

        if last is not None and now - last >= CONTACT_MERGE:
            self.p[device]["link"] = round((now - last) * 1000)

    def store_cells(self, channel, device, frame_name, values, now):
        """
        Put the two values of a multiplexed frame into their places.
        """

        key, fields = CELL_ARRAYS[frame_name]
        cells = device[key]

        for field in fields:

            place = cell_place(values, field)
            value = values.get(field[-1], NO_DATA)

            if key == "cell_temperatures":

                if place is None:
                    self.store_free_sensor(channel, device, values[field[0]], value, now)
                    continue

                # A known sensor stands on its own place
                device["free_temperatures"].pop(place, None)
                self.free_seen[place] = None
                channel.temperature_cursor = (place + 1) % len(cells)

            if place is None or not 0 <= place < len(cells):
                continue

            cells[place] = value
            self.cell_seen[key][place] = now

    def store_free_sensor(self, channel, device, bus, value, now):
        """
        A sensor with an unknown ROM code, on the next place of the pass.
        Its 1-Wire bus may be unknown too (7).
        """

        place = channel.temperature_cursor

        known_bus = bus if isinstance(bus, int) and 1 <= bus <= len(TEMPERATURE_BUS_SIZES) else None

        device["free_temperatures"][place] = (known_bus, value)
        self.free_seen[place] = now

        channel.temperature_cursor = (place + 1) % len(self.free_seen)

    def expire_cells(self, now):
        """
        A number that does not come for two passes has no data: for
        temperatures, its place was taken by an unknown sensor.
        """

        cc = self.p["cc"]

        for key, times in self.cell_seen.items():

            for place, seen in enumerate(times):

                if seen is not None and now - seen > CELL_STALE:
                    cc[key][place] = NO_DATA
                    times[place] = None

        for place, seen in enumerate(self.free_seen):

            if seen is not None and now - seen > CELL_STALE:
                cc["free_temperatures"].pop(place, None)
                self.free_seen[place] = None

    def expire_frames(self, now):
        """
        Values of a frame that stopped coming on both buses must not stay
        on the screen.
        """

        for channel in self.channels:
            channel.expire_frames(now)

        for frame_id, seen in list(self.frame_seen.items()):

            frame = FRAMES[frame_id]

            if now - seen <= frame_timeout(frame):
                continue

            del self.frame_seen[frame_id]

            # Cell arrays expire place by place, see expire_cells()
            if frame["name"] in CELL_ARRAYS:
                continue

            device = self.p[frame["device"]]

            for signal in frame["signals"]:
                for key in signal_keys(frame, signal):
                    device[key] = NO_DATA

    # =================================================
    # LINK TIMES AND SUMMARIES
    # =================================================

    def tick(self):

        now = time.monotonic()

        with self.lock:

            self.expire_frames(now)
            self.expire_cells(now)

            for channel in self.channels:
                channel.update_links(now)

        if now - self.counted_at >= 1:

            for channel in self.channels:

                self.p["bus"][channel.fps_key] = round(
                    (channel.frames - channel.frames_counted) / (now - self.counted_at)
                )

                channel.frames_counted = channel.frames

            self.counted_at = now

        update_summaries(self.p)


def start_reader(parameters, port=CAN_PORT, reserve_port=CAN_RESERVE_PORT):
    """
    Read both buses while the web server runs.
    """

    global READER

    reader = CanReader(parameters, port, reserve_port)
    READER = reader

    # Only in the process that serves the page: with auto-reload the
    # parent process must not hold the serial ports
    app.on_startup(reader.start)
    app.on_shutdown(reader.stop)

    app.timer(TICK, reader.tick)

    return reader
