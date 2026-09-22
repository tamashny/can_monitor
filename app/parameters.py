"""Live dashboard values.

All values start zeroed / neutral — they are overwritten at runtime by the
external program that feeds this dashboard (CAN reader, simulator, etc.).
"""

from .config import (
    CAPACITORS_LINK_MAX,
    CONVERTER_LINK_MAX,
    COOLING_LINK_MAX,
    ISOLATION_LINK_MAX,
)

PARAMETERS = {
    "ec_state": "NONE",
    "ec_warnings": 0,
    "ec_errors": 0,
    "ec_cycles": 0,

    "converter_state": "NONE",
    "converter_errors": 0,
    "converter_link": 0,

    "capacitors_state": "NONE",
    "capacitors_errors": 0,
    "capacitors_link": 0,

    "isolation_state": "NONE",
    "isolation_errors": 0,
    "isolation_link": 0,

    "cooling_state": "NONE",
    "cooling_errors": 0,
    "cooling_link": 0,

    "converter_mode": "NONE",
    "converter_v1": 0,
    "converter_v2": 0,
    "converter_i1": 0,
    "converter_i2": 0,
    "converter_contactor": "OPEN",

    "soc": 0,
    "soh": 0,
    "storage_energy": 0,
    "storage_energy_max": 0,
    "voltage1": 0,
    "current1": 0,
    "temperature1": 0,

    "contactor1": "OPEN",
    "contactor2": "OPEN",

    "fan1_rpm": 0,
    "fan2_rpm": 0,
    "fan3_rpm": 0,
    "fan4_rpm": 0,
    "fan5_rpm": 0,
    "fan6_rpm": 0,
    "shutters": "CLOSED",
}

SYSTEMS = [
    (
        "converter",
        "converter_state",
        "converter_errors",
        "converter_link",
        CONVERTER_LINK_MAX,
    ),
    (
        "capacitors",
        "capacitors_state",
        "capacitors_errors",
        "capacitors_link",
        CAPACITORS_LINK_MAX,
    ),
    (
        "isolation",
        "isolation_state",
        "isolation_errors",
        "isolation_link",
        ISOLATION_LINK_MAX,
    ),
    (
        "cooling",
        "cooling_state",
        "cooling_errors",
        "cooling_link",
        COOLING_LINK_MAX,
    ),
]
