"""The CAN signal map (mapcan v2) from the ESMS CAN map repository.

The path to its main file is set in config/settings.yaml (can.map_file).
The main file lists the device files in `include`; frames of every bus are
loaded. Their CAN IDs do not overlap, so one table serves both buses.

On bus 1 (CANopen) a CAN ID follows from the frame type (`canopen`) and the
node_id of the device, by CiA 301. On bus 2 the map writes it as `id`.
Frames sent by УМ itself (`command_monitor`) are not monitored.

Decoded values are stored in PARAMETERS[device] under these keys:

    state                 signal of a frame sent by the device
    fault.u_dc_high       flag of a bitfield signal
    cmd.req_mode          signal of a command frame sent to the device by БУНЭ
"""

import yaml

from settings import CANMAP_FILE

# Frame type -> base of the CAN ID. SDO frames are not monitored.
COB_BASE = {
    "emcy": 0x080,
    "pdo_tx1": 0x180,
    "pdo_rx1": 0x200,
    "pdo_tx2": 0x280,
    "pdo_tx3": 0x380,
    "pdo_tx4": 0x480,
    "heartbeat": 0x700,
}

# TIME has one fixed CAN ID, without the node number
TIME_COB_ID = 0x100

# Service signals, not shown on the dashboard
SERVICE_SIGNALS = {"cnt", "crc", "err_reg"}

# Multiplexed frames of КК: frame -> (array in PARAMETERS["cc"], fields).
# A voltage field is (number in the array, value),
# a temperature field is (1-Wire bus, sensor on the bus, value).
CELL_ARRAYS = {
    "array_cc_v": (
        "cell_voltages",
        (("v_array_number_a", "u_1"), ("v_array_number_b", "u_2")),
    ),
    "array_cc_t": (
        "cell_temperatures",
        (("t_bus_a", "t_sensor_a", "t_1"), ("t_bus_b", "t_sensor_b", "t_2")),
    ),
}

# Places of array_cc_t on the 1-Wire buses 1..6, in the order of the array
TEMPERATURE_BUS_SIZES = (14, 20, 14, 20, 14, 20)


def temperature_place(bus, sensor):
    """
    Place in the temperature array, None for an unknown bus or sensor
    (bus 7, sensor 31): the frame does not say which place such a sensor took.
    """

    if not 1 <= bus <= len(TEMPERATURE_BUS_SIZES):
        return None

    if not 1 <= sensor <= TEMPERATURE_BUS_SIZES[bus - 1]:
        return None

    return sum(TEMPERATURE_BUS_SIZES[:bus - 1]) + sensor - 1


def temperature_sensor(place):
    """
    Place in the temperature array -> (1-Wire bus, sensor on the bus).
    """

    for bus, size in enumerate(TEMPERATURE_BUS_SIZES, start=1):

        if place < size:
            return bus, place + 1

        place -= size

    raise IndexError("no such place in the temperature array")


def temperature_grid(place):
    """
    Place in the temperature array -> (row, column) on the screen, from 1.
    Every bus takes two rows; odd buses are on the left, even on the right:

        1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2
        1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2
        3 3 3 ...
    """

    bus, sensor = temperature_sensor(place)

    per_row = TEMPERATURE_BUS_SIZES[bus - 1] // 2
    left = 0 if bus % 2 else TEMPERATURE_BUS_SIZES[bus - 2] // 2

    row = (bus - 1) // 2 * 2 + (sensor - 1) // per_row + 1
    column = left + (sensor - 1) % per_row + 1

    return row, column


def cell_place(values, field):
    """
    Place in the array for one field of a multiplexed frame, or None.
    """

    numbers = [values.get(key) for key in field[:-1]]

    if not all(isinstance(number, int) for number in numbers):
        return None

    if len(numbers) == 2:
        return temperature_place(*numbers)

    return numbers[0]


def read_yaml(path):

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# The dashboard itself: its own frames are not monitored
MONITOR = "monitor"


def load_devices():
    """
    Value structures of every bus and (bus name, device) of every file.
    """

    main = read_yaml(CANMAP_FILE)

    structures = {bus["name"]: bus.get("structures") or {} for bus in main["buses"]}
    devices = [(bus["name"], device) for bus in main["buses"] for device in bus.get("devices") or []]

    for include in main.get("include") or []:

        part = read_yaml(CANMAP_FILE.parent / include)

        for part_bus in part.get("buses") or []:
            devices += [(part_bus["name"], device) for device in part_bus.get("devices") or []]

    return structures, devices


def value_names(values, structures):
    """
    `values` of a signal -> {number: name}.
    """

    if isinstance(values, str) and values.startswith("structure:"):
        values = structures[values.split(":", 1)[1]]["values"]

    return {
        number: entry["name"] if isinstance(entry, dict) else entry
        for number, entry in (values or {}).items()
    }


def cob_id(frame, node_id):

    if frame.get("id") is not None:
        return frame["id"]

    if frame.get("canopen") == "time":
        return TIME_COB_ID

    base = COB_BASE.get(frame.get("canopen"))

    if base is None or node_id is None:
        return None

    return base + node_id


def load_frames():
    """
    CAN ID -> frame, with device, sender and value names filled in.
    """

    structures, devices = load_devices()

    frames = {}
    node_ids = {}
    short_names = {}

    for bus_name, device in devices:

        name = device["name"]

        if name == MONITOR:
            continue

        if device.get("node_id") is not None:
            node_ids.setdefault(name, device["node_id"])

        short_names.setdefault(name, device.get("short", name))

        for frame in device.get("frames") or []:

            frame_id = cob_id(frame, device.get("node_id"))

            if frame_id is None:
                continue

            if frame_id in frames:
                raise ValueError(f"CAN ID 0x{frame_id:03X} is used by two frames of the map")

            frame["id"] = frame_id
            frame["bus"] = bus_name
            frame["device"] = name
            frame["canopen"] = frame.get("canopen") or ""

            # pdo_rx is always a command to the device. Not every such frame
            # names its sender in the map (feedback_imd): only БУНЭ commands
            frame["is_command"] = frame["canopen"].startswith("pdo_rx")
            frame["sender"] = "bune" if frame["is_command"] else name

            frame["signals"] = frame.get("signals") or []

            # Frames without these fields (СКИ, heartbeat, TIME) are not checked
            by_name = {signal["name"]: signal for signal in frame["signals"]}
            frame["cnt_signal"] = by_name.get("cnt")
            frame["crc_signal"] = by_name.get("crc")

            # Expected frame length; heartbeat has no `length` in the map
            frame["dlc"] = frame.get("length") or max(
                (signal["byte"] + signal.get("byte_length", 1) for signal in frame["signals"]),
                default=None,
            )

            for signal in frame["signals"]:

                signal["names"] = value_names(signal.get("values"), structures[bus_name])

                for flag in signal.get("flags") or []:
                    flag["names"] = value_names(flag.get("values"), structures[bus_name])

            frames[frame_id] = frame

    return frames, node_ids, short_names


FRAMES, NODE_IDS, SHORT_NAMES = load_frames()


def signal_key(frame, signal, flag=None):
    """
    Key of a signal or a flag in PARAMETERS[device].
    """

    key = signal["name"] if flag is None else f'{signal["name"]}.{flag["name"]}'

    return f"cmd.{key}" if frame["is_command"] else key


def signal_keys(frame, signal):
    """
    Keys of one signal: one per flag for a bitfield.
    """

    if signal["name"] in SERVICE_SIGNALS:
        return []

    if signal.get("encoding") == "bitfield":
        return [signal_key(frame, signal, flag) for flag in signal.get("flags") or []]

    return [signal_key(frame, signal)]


def parameter_keys(device):
    """
    Everything the dashboard keeps for a device. Events (EMCY) go to the
    log and multiplexed frames to the cell arrays.
    """

    return [
        key
        for frame in FRAMES.values()
        if frame["device"] == device
        and frame["canopen"] != "emcy"
        and frame["name"] not in CELL_ARRAYS
        for signal in frame["signals"]
        for key in signal_keys(frame, signal)
    ]
