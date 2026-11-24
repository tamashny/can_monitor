"""Summaries for the "systems" table and for the whole storage.

The CAN reader and the simulator call update_summaries() after they have
written new values into PARAMETERS. For every device it derives:

    health   — NONE / OK / WARNING / ALARM, NONE when the link is lost
    errors   — number of active faults
    warnings — number of active warnings

and for the storage (in PARAMETERS["bune"]): the worst health of the
devices and the total numbers of warnings and errors.
"""

from parameters import DEVICES, NO_DATA

# STATE values that mean an active failure
FAULT_STATES = ("FAULT",)

# States of a bus adapter that delivers frames
CONNECTED_STATES = ("CONNECTED", "SIMULATION")

# (link of a device, state of the bus adapter, name of the bus)
BUS_LINKS = (
    ("link_main", "state", "no link on CAN1"),
    ("link_reserve", "reserve_state", "no link on CAN2"),
)

IMD_ERRORS = (
    "internal_error.low_bus_voltage_error",
    "internal_error.timeout_error",
    "internal_error.anomaly_error",
    "internal_error.self_test_error",
)


def active_flags(device, signal, active):
    """
    Names of the active flags of a signal. Devices whose bits are not named
    in the map send it as a plain number: every set bit counts.
    """

    value = device.get(signal)

    if isinstance(value, int):
        return [f"bit {bit}" for bit in range(value.bit_length()) if value >> bit & 1]

    prefix = f"{signal}."

    return [
        key[len(prefix):]
        for key, flag in list(device.items())
        if key.startswith(prefix) and flag == active
    ]


def count_flags(device, signal, active):

    return len(active_flags(device, signal, active))


def imd_summary(imd):
    """
    СКИ has its own frames, without the common STATE / WARN / FAULT.
    """

    status = imd["insulation_status"]

    health = status if status in ("OK", "WARNING", "ALARM") else "NONE"

    if imd["state"] == "CRITICAL_FAULT":
        health = "ALARM"

    errors = sum(imd[key] == "ALARM" for key in IMD_ERRORS) + (health == "ALARM")

    return health, errors, int(health == "WARNING")


def profile_summary(device):
    """
    Devices with the common status frame of the CAN protocol.
    """

    if device["state"] == NO_DATA:
        # БУНЭ sends its status on bus 2: on bus 1 only its heartbeat is seen
        alive = device.get("nmt_state", NO_DATA) != NO_DATA
        return ("OK" if alive else "NONE"), 0, 0

    errors = count_flags(device, "fault", "ALARM")
    warnings = count_flags(device, "warn", "WARNING")

    if errors or device["state"] in FAULT_STATES:
        health = "ALARM"
    elif warnings:
        health = "WARNING"
    else:
        health = "OK"

    return health, errors, warnings


def link_alive(link, link_max):

    return isinstance(link, (int, float)) and link <= link_max


def bus_is_on(bus, state_key):
    """
    The adapter of this bus works, so its links mean something.
    """

    return bus[state_key] in CONNECTED_STATES


def working_buses(bus):
    """
    How many bus adapters deliver frames.
    """

    return sum(bus_is_on(bus, state_key) for _, state_key, _ in BUS_LINKS)


def lost_buses(device, bus, link_max):
    """
    Names of the working buses on which the device has no link.
    """

    return [
        name
        for link_key, state_key, name in BUS_LINKS
        if bus_is_on(bus, state_key) and not link_alive(device[link_key], link_max)
    ]


def update_summaries(parameters):

    bus = parameters["bus"]

    states = []
    errors_total = 0
    warnings_total = 0

    for key, _, _, link_max in DEVICES:

        device = parameters[key]

        summary = imd_summary if key == "imd" else profile_summary
        health, errors, warnings = summary(device)

        lost = lost_buses(device, bus, link_max)
        working = working_buses(bus)

        # No link on any bus: nothing is known about the device.
        # No link on one of two: it still works, this is a warning
        if len(lost) == working:
            health = "NONE"

        elif lost:
            warnings += len(lost)

            if health == "OK":
                health = "WARNING"

        device.update(health=health, errors=errors, warnings=warnings)

        states.append(health)
        errors_total += errors
        warnings_total += warnings

    if "ALARM" in states:
        overall = "ALARM"
    elif "WARNING" in states:
        overall = "WARNING"
    elif "OK" in states:
        overall = "OK"
    else:
        overall = "NONE"

    parameters["bune"].update(
        overall=overall,
        total_warnings=warnings_total,
        total_errors=errors_total,
    )
