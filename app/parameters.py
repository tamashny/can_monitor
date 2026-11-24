"""Live dashboard values, grouped by device.

The list of values of every device comes from the CAN map (canmap.py), so
the output of protocol.decode() goes into PARAMETERS[device] as is. Every
value starts as NO_DATA and is overwritten at runtime by the CAN reader
(canbus/reader.py) or, with --debug, by the simulator.

Every device also has a summary for the "systems" table:
    health   — NONE / OK / WARNING / ALARM
    errors   — number of active faults
    warnings — number of active warnings
    link     — time between the last two contacts of the device on any bus, ms
    link_main, link_reserve — time since its last valid frame on each bus, ms
"""

from canmap import NODE_IDS, SHORT_NAMES, parameter_keys
from settings import (
    CELL_TEMPERATURE_COUNT,
    CELL_VOLTAGE_COUNT,
    LINK_TIMEOUTS,
)

# Value is not available: the "not available" code of the map, a field the
# frame is too short for, or nothing received yet
NO_DATA = "No data"

# The device reports that the measurement failed (the "error" code of the map)
MEASURE_ERROR = "Error"

# Devices of the "systems" table, by their keys in the map
DEVICE_KEYS = ("bune", "puer", "imd", "bem", "bup", "cc", "bust_a", "bust_b", "plod")


def device_values(key):

    return {
        "health": "NONE",
        "errors": 0,
        "warnings": 0,
        "link": NO_DATA,
        "link_main": NO_DATA,
        "link_reserve": NO_DATA,
        **{name: NO_DATA for name in parameter_keys(key)},
    }


PARAMETERS = {key: device_values(key) for key in DEVICE_KEYS}

# Multiplexed frames of КК: group voltages, V, and sensor temperatures, °C
PARAMETERS["cc"]["cell_voltages"] = [NO_DATA] * CELL_VOLTAGE_COUNT
PARAMETERS["cc"]["cell_temperatures"] = [NO_DATA] * CELL_TEMPERATURE_COUNT

# Sensors with an unknown ROM code: place they took -> (1-Wire bus or None, °C)
PARAMETERS["cc"]["free_temperatures"] = {}

# Summary of the whole storage (summary.py)
PARAMETERS["bune"].update(
    overall="NONE",
    total_warnings=NO_DATA,
    total_errors=NO_DATA,
)

# Source of the data: CAN adapter or simulator
PARAMETERS["bus"] = {
    "bitrate": NO_DATA,                 # bit/s, the same on both buses

    # Main bus, CAN1
    "port": NO_DATA,                    # e.g. "COM3" or "simulation"
    "state": "NONE",                    # NONE / CONNECTED / DISCONNECTED / SIMULATION
    "frames_per_second": NO_DATA,       # frames received in the last second
    "error": NO_DATA,                   # why the port could not be opened

    # Reserve bus, CAN2
    "reserve_port": NO_DATA,
    "reserve_state": "NONE",
    "reserve_frames_per_second": NO_DATA,
    "reserve_error": NO_DATA,
}

# (key in PARAMETERS, short name from the map, node ID, link timeout, ms)
DEVICES = [
    (key, SHORT_NAMES[key], f"0x{NODE_IDS[key]:02X}", LINK_TIMEOUTS[key])
    for key in DEVICE_KEYS
]
