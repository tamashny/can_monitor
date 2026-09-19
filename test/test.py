from nicegui import ui
import yaml
from pathlib import Path

# =================================================
# LOAD PATTERN
# =================================================

PATTERN_FILE = Path(__file__).parent.parent / "pattern.yaml"

with open(PATTERN_FILE, "r", encoding="utf-8") as file:
    pattern = yaml.safe_load(file)

layout = pattern["layout"]

columns = layout["columns"]
rows = layout["rows"]
areas = layout["areas"]
cells = pattern["cells"]

# =================================================
# GLOBAL SETTINGS
# =================================================

# removing space around page
ui.query('.nicegui-content').style(
    'padding: 0; margin: 0;'
)

ui.query('body').style(
    '''
    background: #0C0C0C;
    color: #FFFFFF;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 16px;
    '''
)

# =================================================
# PARAMETERS
# =================================================

parameters = {
    "converter_mode": "NO DATA",
    "soc": 200,
    "soh": 200,
    "voltage1": 800,
    "current1": 100,
    "temperature1": 20,
}

# =================================================
# DEFINES
# =================================================

SOC_MIN = 0
SOC_MAX = 100

SOC_RED_MAX = 20
SOC_YELLOW_MAX = 60


SOH_MIN = 60
SOH_MAX = 100

SOH_RED_MAX = 75
SOH_YELLOW_MAX = 85

VOLTAGE_MIN = 500
VOLTAGE_MAX = 1000

VOLTAGE_RED_LOW = 600
VOLTAGE_YELLOW = 700
VOLTAGE_GREEN_MAX = 1000


CURRENT_MIN = 0
CURRENT_MAX = 1000

CURRENT_GREEN_MAX = 700
CURRENT_YELLOW_MAX = 900


TEMPERATURE_MIN = -40
TEMPERATURE_MAX = 80

TEMPERATURE_BLUE_DARK_MAX = -20
TEMPERATURE_BLUE_MAX = 0
TEMPERATURE_CYAN_MAX = 10
TEMPERATURE_WHITE_MAX = 40
TEMPERATURE_YELLOW_MAX = 60

# =================================================
# FUNCTIONS
# =================================================

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

def get_segments(value, minimum, maximum, minimum_segments=0):

    value = max(minimum, min(value, maximum))

    segments = round(
        (value - minimum) / (maximum - minimum) * 7
    )

    return max(segments, minimum_segments)
# =================================================
# GRID SETTINGS
# =================================================

if isinstance(columns, list):
    grid_columns = " ".join(
        f"{value}fr"
        for value in columns
    )
else:
    grid_columns = " ".join(
        ["1fr"] * columns
    )

if isinstance(rows, list):
    grid_rows = " ".join(
        f"{value}fr"
        for value in rows
    )
else:
    grid_rows = " ".join(
        ["1fr"] * rows
    )

grid_areas = " ".join(
    f'"{" ".join(row)}"'
    for row in areas
)

# =================================================
# GRID
# =================================================

with ui.element('div').classes(
    'w-full h-dvh p-2 grid gap-2'
).style(
    f'''
    grid-template-columns: {grid_columns};
    grid-template-rows: {grid_rows};
    grid-template-areas: {grid_areas};
    '''
):

    for name, cell in cells.items():

        with ui.element('div').style(
            f'''
            grid-area: {name};

            border: 1px solid #7C7C7C;
            border-radius: 10px;
            padding: 15px;
            '''
        ):

            if cell["title"] == "Converter":

                ui.label(
                    f'Converter: {parameters["converter_mode"]}'
                )

                ui.label(
                    f'{parameters["voltage1"]} V'
                )

                ui.label(
                    f'{parameters["current1"]} A'
                )

            elif cell["title"] == "SoC":

                # SoC
                with ui.element('div').classes(
                    'flex items-center w-full'
                ):

                    ui.label('SoC').style(
                        'width: 40px;'
                    )

                    soc = parameters["soc"]
                    color = soc_color(soc)

                    segments = get_segments(
                        soc,
                        SOC_MIN,
                        SOC_MAX,
                        minimum_segments=1
                    )

                    for i in range(7):

                        if i < segments:
                            background = color
                        else:
                            background = '#444444'

                        ui.element('div').style(
                            f'''
                            width: 15px;
                            height: 15px;
                            margin-right: 5px;
                            background: {background};
                            '''
                        )

                    ui.label(
                        f'{soc:.0f}%'
                    ).classes('ml-auto')


                # SoH
                with ui.element('div').classes(
                    'flex items-center w-full'
                ):

                    ui.label('SoH').style(
                        'width: 40px;'
                    )

                    soh = parameters["soh"]
                    color = soh_color(soh)

                    segments = get_segments(
                        soh,
                        SOH_MIN,
                        SOH_MAX,
                        minimum_segments=1
                    )

                    for i in range(7):

                        if i < segments:
                            background = color
                        else:
                            background = '#444444'

                        ui.element('div').style(
                            f'''
                            width: 15px;
                            height: 15px;
                            margin-right: 5px;
                            background: {background};
                            '''
                        )

                    ui.label(
                        f'{soh:.0f}%'
                    ).classes('ml-auto')

            elif cell["title"] == "V I T":

                # Voltage
                with ui.element('div').classes(
                    'flex items-center w-full'
                ):

                    ui.label('U').style(
                        'width: 25px;'
                    )

                    voltage = parameters["voltage1"]
                    color = voltage_color(voltage)
                    segments = get_segments(
                        voltage,
                        VOLTAGE_MIN,
                        VOLTAGE_MAX,
                        minimum_segments = 1
                    )

                    for i in range(7):

                        if i < segments:
                            background = color
                        else:
                            background = '#444444'

                        ui.element('div').style(
                            f'''
                            width: 15px;
                            height: 15px;
                            margin-right: 5px;
                            background: {background};
                            '''
                        )

                    ui.label(
                        f'{voltage:.0f}V'
                    ).classes('ml-auto')


                # Current
                with ui.element('div').classes(
                    'flex items-center w-full'
                ):

                    ui.label('I').style(
                        'width: 25px;'
                    )

                    current = parameters["current1"]
                    color = current_color(current)
                    segments = get_segments(
                        current,
                        CURRENT_MIN,
                        CURRENT_MAX
                    )

                    for i in range(7):

                        if i < segments:
                            background = color
                        else:
                            background = '#444444'

                        ui.element('div').style(
                            f'''
                            width: 15px;
                            height: 15px;
                            margin-right: 5px;
                            background: {background};
                            '''
                        )

                    ui.label(
                        f'{current:.0f}A'
                    ).classes('ml-auto')


                # Temperature
                with ui.element('div').classes(
                    'flex items-center w-full'
                ):

                    ui.label('T').style(
                        'width: 25px;'
                    )

                    temperature = parameters["temperature1"]
                    color = temperature_color(temperature)
                    segments = get_segments(
                        temperature,
                        TEMPERATURE_MIN,
                        TEMPERATURE_MAX,
                        minimum_segments = 1
                    )

                    for i in range(7):

                        if i < segments:
                            background = color
                        else:
                            background = '#444444'

                        ui.element('div').style(
                            f'''
                            width: 15px;
                            height: 15px;
                            margin-right: 5px;
                            background: {background};
                            '''
                        )

                    ui.label(
                        f'{temperature:.0f}C'
                    ).classes('ml-auto')

            else:

                ui.label(cell["title"])

ui.run()
