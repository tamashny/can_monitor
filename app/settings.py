# =================================================
# MARKERS
# =================================================

# Value is not available (same marker as protocol.NO_DATA)
NO_DATA = "No data"

# =================================================
# LINK TIMEOUTS
# =================================================

CONVERTER_LINK_MAX = 50
CAPACITORS_LINK_MAX = 50
ISOLATION_LINK_MAX = 100
COOLING_LINK_MAX = 100
BYPASS_LINK_MAX = 100

# =================================================
# SOC
# =================================================

SOC_MIN = 0
SOC_MAX = 100

SOC_RED_MAX = 20
SOC_YELLOW_MAX = 60

# =================================================
# SOH
# =================================================

SOH_MIN = 60
SOH_MAX = 100

SOH_RED_MAX = 75
SOH_YELLOW_MAX = 85

# =================================================
# VOLTAGE
# =================================================

VOLTAGE_MIN = 500
VOLTAGE_MAX = 1000

VOLTAGE_RED_LOW = 600
VOLTAGE_YELLOW = 700
VOLTAGE_GREEN_MAX = 1000

# =================================================
# CURRENT
# =================================================

CURRENT_MIN = 0
CURRENT_MAX = 1000

CURRENT_GREEN_MAX = 700
CURRENT_YELLOW_MAX = 900

# =================================================
# TEMPERATURE
# =================================================

TEMPERATURE_MIN = -40
TEMPERATURE_MAX = 80

TEMPERATURE_BLUE_DARK_MAX = -20
TEMPERATURE_BLUE_MAX = 0
TEMPERATURE_CYAN_MAX = 10
TEMPERATURE_WHITE_MAX = 40
TEMPERATURE_YELLOW_MAX = 60

# =================================================
# METERS
# =================================================

# Number of blocks in a meter bar
METER_SEGMENTS = 15

# =================================================
# CELLS MAP
# =================================================

CELL_VOLTAGE_COUNT = 70
CELL_TEMPERATURE_COUNT = 105

CELL_VOLTAGE_COLUMNS = 10
CELL_TEMPERATURE_COLUMNS = 15

# Placeholder thresholds, set real values
CELL_VOLTAGE_RED_LOW = 8
CELL_VOLTAGE_YELLOW = 10
CELL_VOLTAGE_GREEN_MAX = 14

# =================================================
# EVENT LOG
# =================================================

# Entries kept in memory and shown in the log
EVENT_LOG_SIZE = 500

# How often the parameters are checked for changes, s
EVENT_WATCH_INTERVAL = 0.5

# =================================================
# DASHBOARD
# =================================================

# How often the boxes redraw changed values, s
DASHBOARD_REFRESH_INTERVAL = 0.5
