"""Live dashboard values, grouped by the device that sends them.

Source: can_map.xlsx, bus 1 ("Адрессация / Содержание шины 1").
Device keys and parameter names match canmap.yaml, so the output of
protocol.decode() goes into PARAMETERS[device] as is.

Every value starts as NO_DATA and is overwritten at runtime by the program
that feeds this dashboard (CAN reader, simulator, ...).

Every device except БУНЭ also has a summary for the "systems" table:
    state  — NONE / OK / WARNING / ALARM
    errors — number of active errors
    link   — time since the last frame from the device, ms
"""

from .config import (
    BYPASS_LINK_MAX,
    CAPACITORS_LINK_MAX,
    CELL_TEMPERATURE_COUNT,
    CELL_VOLTAGE_COUNT,
    CONVERTER_LINK_MAX,
    COOLING_LINK_MAX,
    ISOLATION_LINK_MAX,
    NO_DATA,
)


def device_summary():

    return {
        "state": "NONE",
        "errors": 0,
        "link": NO_DATA,
    }


PARAMETERS = {

    # =================================================
    # СКИ — система контроля изоляции (BMS IMD), ID 0x16
    # =================================================

    "imd": {
        **device_summary(),

        # 0x196 — states, 100 ms
        "insulation_status": NO_DATA,       # NO_DATA / OK / WARNING / ALARM
        "low_bus_voltage_error": NO_DATA,   # internal errors: OK / ALARM
        "timeout_error": NO_DATA,
        "anomaly_error": NO_DATA,
        "self_test_error": NO_DATA,
        "imd_status": NO_DATA,              # NOT_WORKING / WORKING / CRITICAL_FAULT

        # 0x296 — data, 100 ms
        "resistance_calculated": NO_DATA,   # NOT / YES
        "resistance_plus": NO_DATA,         # kOhm, 0..10000
        "resistance_minus": NO_DATA,        # kOhm, 0..10000
        "bus_voltage_calculated": NO_DATA,  # NOT / YES
        "bus_voltage": NO_DATA,             # V

        # 0x596 — reply to a setting (CANopen SDO)
        "setting_reply": NO_DATA,           # ALARM_RESISTANCE / WARNING_RESISTANCE
    },

    # =================================================
    # КК — контроллер конденсаторов, ID 0x17
    # =================================================

    "cc": {
        **device_summary(),

        # 0x197 — states, 50 ms
        "cc_status": NO_DATA,                      # NO_DATA / OK / WARNING / ALARM
        "cell_overvoltage": NO_DATA,               # system flags: OK / ALARM
        "cell_undervoltage": NO_DATA,
        "cell_disbalance": NO_DATA,
        "voltage_sensor_connection": NO_DATA,
        "cell_overheat": NO_DATA,
        "cell_overcooling": NO_DATA,
        "temperature_sensor_connection": NO_DATA,

        # 0x097 — event, sent when it happens
        "event_type": NO_DATA,      # same list as the 0x197 flags
        "event_source": NO_DATA,    # VOLTAGE_MODULES / TEMPERATURE_SENSORS
        "event_object": NO_DATA,    # module or sensor number

        # 0x297 — cell data on request, 7 values per frame
        "cell_voltages": [NO_DATA] * CELL_VOLTAGE_COUNT,          # V
        "cell_temperatures": [NO_DATA] * CELL_TEMPERATURE_COUNT,  # °C
    },

    # =================================================
    # БУП — блок управления преобразователем, ID 0x18
    # =================================================

    "bup": {
        **device_summary(),

        # 0x198 — states, 100 ms
        "dc_status": NO_DATA,               # DC_INIT / DC_PRECHARGE / DC_IDLE / DC_CHARGE /
                                            # DC_DISCHARGE / DC_DIRECT_CHARGE / DC_DIRECT_DISCHARGE
        "dc_error_none": NO_DATA,           # error code flags: NO / YES
        "dc_overvoltage": NO_DATA,          # OK / ALARM
        "dc_undervoltage": NO_DATA,
        "dc_overcurrent": NO_DATA,
        "dc_igbt_driver_error": NO_DATA,

        # 0x298 — data, 100 ms
        "dc_output_voltage": NO_DATA,       # V
        "dc_input_voltage": NO_DATA,        # V
        "dc_output_current": NO_DATA,       # A
        "dc_input_current": NO_DATA,        # A
    },

    # =================================================
    # ПУСК — ID 0x19
    # =================================================

    "pusk": {
        **device_summary(),

        # 0x299 — key mode and error state
        # (byte layout is not described in can_map yet)
    },

    # =================================================
    # СО — система охлаждения, ID 0x1A
    # =================================================

    "so": {
        **device_summary(),

        # 0x29A — fan rotation and shutters
        # (byte layout is not described in can_map yet)
        "fan1_rpm": NO_DATA,
        "fan2_rpm": NO_DATA,
        "fan3_rpm": NO_DATA,
        "fan4_rpm": NO_DATA,
        "fan5_rpm": NO_DATA,
        "fan6_rpm": NO_DATA,
        "shutters": NO_DATA,    # OPEN / CLOSED
    },

    # =================================================
    # БУНЭ — блок управления накопителем энергии (bus master)
    # =================================================

    "bune": {

        # Commands to the devices
        # 0x216 → СКИ, 100 ms
        "imd_allow_work": NO_DATA,          # DENY / ALLOW
        "imd_force_selftest": NO_DATA,      # AUTO / FORCED
        # 0x616 → СКИ, settings (CANopen SDO)
        "imd_alarm_resistance": NO_DATA,    # kOhm
        "imd_warning_resistance": NO_DATA,  # kOhm
        # 0x217 → КК
        "cc_data_request": NO_DATA,         # STATES / FULL_PARSING /
                                            # REPEAT_VOLTAGE_FRAME / REPEAT_TEMPERATURE_FRAME
        "cc_frame_request": NO_DATA,        # number of the frame to repeat
        # 0x218 → БУП, 50 ms
        "bup_requested_mode": NO_DATA,      # same list as bup.dc_status
        "bup_target_voltage": NO_DATA,      # V
        # 0x219 → ПУСК (bypass mode) and 0x21A → СО (fan power, shutters):
        # byte layout is not described in can_map yet

        # Internal values of the control unit (not in can_map)
        "state": "NONE",                    # NONE / OK / WARNING / ALARM
        "warnings": NO_DATA,
        "errors": NO_DATA,
        "cycles": NO_DATA,                  # full charge cycles

        "soc": NO_DATA,                     # %
        "soh": NO_DATA,                     # %
        "storage_energy": NO_DATA,          # kWh
        "storage_energy_max": NO_DATA,      # kWh

        "voltage": NO_DATA,                 # V
        "current": NO_DATA,                 # A
        "temperature": NO_DATA,             # °C

        "contactor1": NO_DATA,              # OPEN / CLOSED
        "contactor2": NO_DATA,
        "converter_contactor": NO_DATA,
    },
}

# Devices of the "systems" table: (key in PARAMETERS, name, CAN ID, link timeout, ms)
DEVICES = [
    ("imd", "isolation", "0x16", ISOLATION_LINK_MAX),
    ("cc", "capacitors", "0x17", CAPACITORS_LINK_MAX),
    ("bup", "converter", "0x18", CONVERTER_LINK_MAX),
    ("pusk", "bypass", "0x19", BYPASS_LINK_MAX),
    ("so", "cooling", "0x1A", COOLING_LINK_MAX),
]

# Names of the BUP error flags (0x198, byte 1), shown in the converter box
BUP_ERRORS = {
    "dc_overvoltage": "overvoltage",
    "dc_undervoltage": "undervoltage",
    "dc_overcurrent": "overcurrent",
    "dc_igbt_driver_error": "igbt driver",
}
