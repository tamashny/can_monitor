from config import (
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


def state_color(state):

    if state == "NONE":
        return '#666666'

    if state == "OK":
        return '#7fd36b'

    if state == "WARN":
        return '#ffd166'

    if state == "ALARM":
        return '#ff6b7a'

    return '#666666'


def soc_color(value):

    if value < SOC_RED_MAX:
        return '#ff6b7a'

    if value < SOC_YELLOW_MAX:
        return '#ffd166'

    return '#7fd36b'


def soh_color(value):

    if value < SOH_RED_MAX:
        return '#ff6b7a'

    if value < SOH_YELLOW_MAX:
        return '#ffd166'

    return '#7fd36b'


def voltage_color(value):

    if value < VOLTAGE_RED_LOW:
        return '#ff6b7a'

    if value < VOLTAGE_YELLOW:
        return '#ffd166'

    if value <= VOLTAGE_GREEN_MAX:
        return '#7fd36b'

    return '#ff6b7a'


def current_color(value):

    if value <= CURRENT_GREEN_MAX:
        return '#7fd36b'

    if value <= CURRENT_YELLOW_MAX:
        return '#ffd166'

    return '#ff6b7a'


def temperature_color(value):

    if value <= TEMPERATURE_BLUE_DARK_MAX:
        return '#4d79ff'

    if value <= TEMPERATURE_BLUE_MAX:
        return '#4d79ff'

    if value <= TEMPERATURE_CYAN_MAX:
        return '#6fdcff'

    if value <= TEMPERATURE_WHITE_MAX:
        return '#ffffff'

    if value <= TEMPERATURE_YELLOW_MAX:
        return '#ffd166'

    return '#ff6b7a'
