from settings import (
    CELL_VOLTAGE_GREEN_MAX,
    CELL_VOLTAGE_RED_LOW,
    CELL_VOLTAGE_YELLOW,
    CURRENT_GREEN_MAX,
    CURRENT_YELLOW_MAX,
    SOC_RED_MAX,
    SOC_YELLOW_MAX,
    SOH_RED_MAX,
    SOH_YELLOW_MAX,
    TEMPERATURE_BLUE_DARK_MAX,
    TEMPERATURE_BLUE_MAX,
    TEMPERATURE_CYAN_MAX,
    TEMPERATURE_WHITE_MAX,
    TEMPERATURE_YELLOW_MAX,
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
WHITE = '#eeeeee'

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


def shade(color, amount):
    """
    Darken (amount < 0) or lighten (amount > 0) a #rrggbb colour,
    amount in -1..1 is the share of black / white mixed in.
    """

    target = 255 if amount > 0 else 0
    amount = abs(amount)

    channels = (
        int(color[i:i + 2], 16)
        for i in (1, 3, 5)
    )

    return '#' + ''.join(
        f'{round(c + (target - c) * amount):02x}'
        for c in channels
    )


def meter_color(color, position):
    """
    btop-like gradient along a meter: darker at the start, brighter
    at the end. position is 0..1 along the whole scale.
    """

    if position < 0.5:
        return shade(color, -0.9 * (0.5 - position))

    return shade(color, 0.6 * (position - 0.5))


STATE_COLORS = {
    "OK": GREEN,
    "WARN": YELLOW,
    "WARNING": YELLOW,
    "ALARM": RED,
    "CRITICAL_FAULT": RED,
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

    return RED


def current_color(value):

    if value <= CURRENT_GREEN_MAX:
        return GREEN

    if value <= CURRENT_YELLOW_MAX:
        return YELLOW

    return RED


def temperature_color(value):

    if value <= TEMPERATURE_BLUE_DARK_MAX:
        return BLUE

    if value <= TEMPERATURE_BLUE_MAX:
        return BLUE

    if value <= TEMPERATURE_CYAN_MAX:
        return CYAN

    if value <= TEMPERATURE_WHITE_MAX:
        return WHITE

    if value <= TEMPERATURE_YELLOW_MAX:
        return YELLOW

    return RED
