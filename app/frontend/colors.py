from settings import (
    CELL_VOLTAGE_GREEN_MAX,
    CELL_VOLTAGE_RED_LOW,
    CELL_VOLTAGE_YELLOW,
    CELL_VOLTAGE_YELLOW_MAX,
    CURRENT_GREEN_MAX,
    CURRENT_YELLOW_MAX,
    SOC_RED_MAX,
    SOC_YELLOW_MAX,
    SOH_RED_MAX,
    SOH_YELLOW_MAX,
    TEMPERATURE_CELLS_MIN,
    TEMPERATURE_CYAN,
    TEMPERATURE_GREEN,
    TEMPERATURE_LIME,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    TEMPERATURE_YELLOW,
    VOLTAGE_GREEN_MAX,
    VOLTAGE_RED_LOW,
    VOLTAGE_YELLOW,
)

# =================================================
# PALETTE (btop "Default" theme)
# =================================================

BG = '#000000'
FG = '#cccccc'          # regular text
TITLE = '#eeeeee'       # titles, values
DIM = '#606060'         # secondary text
HI = '#b54040'          # box numbers in the border
SELECTED_BG = '#6a2f2f'
METER_BG = '#404040'    # unlit meter segments

GREEN = '#77ca9b'
YELLOW = '#cbc06c'
RED = '#dc4c4c'

BLUE = '#5474e8'
CYAN = '#74e6fc'
LIME = '#b5e86f'

# Box border colours, referenced by name from pattern.yaml
BOX_COLORS = {
    "cpu": '#556d59',
    "mem": '#6c6c4b',
    "net": '#5c588d',
    "proc": '#805252',
    "gray": '#505050',
}

# Same as the unlit meter segments in VIT
NO_DATA_COLOR = METER_BG


def mix(first, second, share):
    """
    #rrggbb colour between two others, share 0..1 of the second one.
    """

    return '#' + ''.join(
        f'{round(a + (b - a) * share):02x}'
        for a, b in (
            (int(first[i:i + 2], 16), int(second[i:i + 2], 16))
            for i in (1, 3, 5)
        )
    )


def gradient(value, points):
    """
    Colour of a value on a scale of (value, colour) points.
    """

    if value <= points[0][0]:
        return points[0][1]

    for (low, first), (high, second) in zip(points, points[1:]):

        if value <= high:
            return mix(first, second, (value - low) / (high - low))

    return points[-1][1]


STATE_COLORS = {
    "OK": GREEN,
    "WARNING": YELLOW,
    "ALARM": RED,
    "CRITICAL_FAULT": RED,
    "FAULT": RED,
    "EMERGENCY": RED,
    "LOST": YELLOW,             # reserve bus: the system still works on the main one
    "CHECK": YELLOW,
}


def state_color(state):

    return STATE_COLORS.get(state, DIM)


def event_color(value):
    """
    Colour of a new value in the event log.
    """

    if value in ("No data", "NO_DATA", "NONE"):
        return DIM

    return STATE_COLORS.get(value, TITLE)


def soc_color(value):

    if value < SOC_RED_MAX:
        return RED

    if value < SOC_YELLOW_MAX:
        return YELLOW

    return GREEN


def soh_color(value):

    if value < SOH_RED_MAX:
        return RED

    if value < SOH_YELLOW_MAX:
        return YELLOW

    return GREEN


def voltage_color(value):

    if value < VOLTAGE_RED_LOW:
        return RED

    if value < VOLTAGE_YELLOW:
        return YELLOW

    if value <= VOLTAGE_GREEN_MAX:
        return GREEN

    return RED


def cell_voltage_color(value):

    if value < CELL_VOLTAGE_RED_LOW:
        return RED

    if value < CELL_VOLTAGE_YELLOW:
        return YELLOW

    if value <= CELL_VOLTAGE_GREEN_MAX:
        return GREEN

    if value <= CELL_VOLTAGE_YELLOW_MAX:
        return YELLOW

    return RED


def current_color(value):

    if value <= CURRENT_GREEN_MAX:
        return GREEN

    if value <= CURRENT_YELLOW_MAX:
        return YELLOW

    return RED


# Common part of both temperature scales, they differ only in the cold end
WARM_POINTS = (
    (TEMPERATURE_CYAN, CYAN),
    (TEMPERATURE_LIME, LIME),
    (TEMPERATURE_GREEN, GREEN),
    (TEMPERATURE_YELLOW, YELLOW),
    (TEMPERATURE_MAX, RED),
)

STORAGE_TEMPERATURE_POINTS = ((TEMPERATURE_MIN, BLUE),) + WARM_POINTS
CELL_TEMPERATURE_POINTS = ((TEMPERATURE_CELLS_MIN, BLUE),) + WARM_POINTS


def temperature_color(value):
    """
    Temperature of the storage.
    """

    return gradient(value, STORAGE_TEMPERATURE_POINTS)


def cell_temperature_color(value):

    return gradient(value, CELL_TEMPERATURE_POINTS)
