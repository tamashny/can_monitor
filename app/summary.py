"""Summaries for the "systems" table and for БУНЭ.

The CAN reader and the simulator call update_summaries() after they have
written new values into PARAMETERS. For every device it derives:

    state  — NONE / OK / WARNING / ALARM from the device's own status,
             NONE when the link is lost
    errors — number of active error flags

and for БУНЭ: the worst state of the devices, the number of devices in
WARNING and the total number of errors.
"""

from parameters import BUP_ERRORS, DEVICES, NO_DATA

IMD_ERRORS = (
    "low_bus_voltage_error",
    "timeout_error",
    "anomaly_error",
    "self_test_error",
)

CC_ERRORS = (
    "cell_overvoltage",
    "cell_undervoltage",
    "cell_disbalance",
    "voltage_sensor_connection",
    "cell_overheat",
    "cell_overcooling",
    "temperature_sensor_connection",
)


def count_alarms(device, keys):

    return sum(device.get(key) == "ALARM" for key in keys)


def status_state(status):
    """
    NO_DATA / OK / WARNING / ALARM status code -> table state.
    """

    if status in ("OK", "WARNING", "ALARM"):
        return status

    return "NONE"


def imd_summary(imd):

    state = status_state(imd["insulation_status"])

    if imd["imd_status"] == "CRITICAL_FAULT":
        state = "ALARM"

    errors = count_alarms(imd, IMD_ERRORS) + (state in ("WARNING", "ALARM"))

    return state, errors


def cc_summary(cc):

    return status_state(cc["cc_status"]), count_alarms(cc, CC_ERRORS)


def bup_summary(bup):

    if bup["dc_status"] == NO_DATA:
        return "NONE", 0

    errors = count_alarms(bup, BUP_ERRORS)

    return ("ALARM" if errors else "OK"), errors


# Devices whose frames are described in canmap.yaml.
# The others are OK as long as their link is alive.
DEVICE_SUMMARIES = {
    "imd": imd_summary,
    "cc": cc_summary,
    "bup": bup_summary,
}


def link_alive(link, link_max):

    return isinstance(link, (int, float)) and link <= link_max


def update_summaries(parameters):

    states = []
    errors_total = 0

    for key, _, _, link_max in DEVICES:

        device = parameters[key]

        summary = DEVICE_SUMMARIES.get(key)
        state, errors = summary(device) if summary else ("OK", 0)

        if not link_alive(device["link"], link_max):
            state = "NONE"

        device.update(state=state, errors=errors)

        states.append(state)
        errors_total += errors

    if "ALARM" in states:
        overall = "ALARM"
    elif "WARNING" in states:
        overall = "WARNING"
    elif "OK" in states:
        overall = "OK"
    else:
        overall = "NONE"

    parameters["bune"].update(
        state=overall,
        warnings=states.count("WARNING"),
        errors=errors_total,
    )
