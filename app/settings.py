"""User settings from config/settings.yaml, plus the project paths.

Values are exposed as module constants, e.g. SOC_RED_MAX or CAN_PORT.
"""

from pathlib import Path

import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_DIR / "config"

SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
PATTERN_FILE = CONFIG_DIR / "pattern.yaml"
COMMANDS_FILE = CONFIG_DIR / "commands.yaml"

with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
    _settings = yaml.safe_load(file)

# Main file of the CAN map; a relative path starts at the project folder
CANMAP_FILE = (PROJECT_DIR / _settings["can"]["map_file"]).resolve()


# =================================================
# CAN ADAPTER
# =================================================

_can = _settings["can"]

CAN_INTERFACE = _can["interface"]
CAN_PORT = _can["port"]
CAN_RESERVE_PORT = _can["reserve_port"]
CAN_BITRATE = _can["bitrate"]
CAN_SERIAL_BAUDRATE = _can["serial_baudrate"]
CAN_RECONNECT_INTERVAL = _can["reconnect_interval"]
CAN_INVALID_LIMIT = _can["invalid_limit"]
CAN_RESTORE_COUNT = _can["restore_count"]

# =================================================
# DASHBOARD
# =================================================

_dashboard = _settings["dashboard"]

DASHBOARD_PORT = _dashboard["port"]
DASHBOARD_REFRESH_INTERVAL = _dashboard["refresh_interval"]
METER_SEGMENTS = _dashboard["meter_segments"]

# =================================================
# EVENT LOG
# =================================================

EVENT_LOG_SIZE = _settings["event_log"]["size"]
EVENT_WATCH_INTERVAL = _settings["event_log"]["watch_interval"]

# =================================================
# LINK TIMEOUTS, ms, by device key
# =================================================

LINK_TIMEOUTS = _settings["link_timeouts"]

# =================================================
# THRESHOLDS
# =================================================

_soc = _settings["soc"]

SOC_MIN = _soc["min"]
SOC_MAX = _soc["max"]
SOC_RED_MAX = _soc["red_max"]
SOC_YELLOW_MAX = _soc["yellow_max"]

_soh = _settings["soh"]

SOH_MIN = _soh["min"]
SOH_MAX = _soh["max"]
SOH_RED_MAX = _soh["red_max"]
SOH_YELLOW_MAX = _soh["yellow_max"]

_voltage = _settings["voltage"]

VOLTAGE_MIN = _voltage["min"]
VOLTAGE_MAX = _voltage["max"]
VOLTAGE_RED_LOW = _voltage["red_low"]
VOLTAGE_YELLOW = _voltage["yellow"]
VOLTAGE_GREEN_MAX = _voltage["green_max"]

_current = _settings["current"]

CURRENT_MIN = _current["min"]
CURRENT_MAX = _current["max"]
CURRENT_GREEN_MAX = _current["green_max"]
CURRENT_YELLOW_MAX = _current["yellow_max"]

_temperature = _settings["temperature"]

TEMPERATURE_MIN = _temperature["min"]
TEMPERATURE_MAX = _temperature["max"]
TEMPERATURE_CELLS_MIN = _temperature["cells_min"]
TEMPERATURE_CYAN = _temperature["cyan"]
TEMPERATURE_LIME = _temperature["lime"]
TEMPERATURE_GREEN = _temperature["green"]
TEMPERATURE_YELLOW = _temperature["yellow"]

# =================================================
# CELLS MAP
# =================================================

_cells = _settings["cells"]

CELL_VOLTAGE_COUNT = _cells["voltage_count"]
CELL_TEMPERATURE_COUNT = _cells["temperature_count"]
CELL_VOLTAGE_COLUMNS = _cells["voltage_columns"]
CELL_TEMPERATURE_COLUMNS = _cells["temperature_columns"]
CELL_VOLTAGE_RED_LOW = _cells["voltage_red_low"]
CELL_VOLTAGE_YELLOW = _cells["voltage_yellow"]
CELL_VOLTAGE_GREEN_MAX = _cells["voltage_green_max"]
CELL_VOLTAGE_YELLOW_MAX = _cells["voltage_yellow_max"]
