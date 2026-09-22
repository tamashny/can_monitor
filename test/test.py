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
    background: var(--bg-color);
    color: var(--fg-color);
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 16px;
    line-height: 1.5;
    '''
)

# =================================================
# DEFINES
# =================================================

CONVERTER_LINK_MAX = 50
CAPACITORS_LINK_MAX = 50
ISOLATION_LINK_MAX = 100
COOLING_LINK_MAX = 100

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
# PARAMETERS
# =================================================

parameters = {
    "ec_state": "OK",
    "ec_warnings": 2,
    "ec_errors": 0,
    "ec_cycles": 12543,

    "converter_state": "OK",
    "converter_errors": 0,
    "converter_link": 35,

    "capacitors_state": "WARN",
    "capacitors_errors": 2,
    "capacitors_link": 48,

    "isolation_state": "NONE",
    "isolation_errors": 0,
    "isolation_link": 600,

    "cooling_state": "ALARM",
    "cooling_errors": 1,
    "cooling_link": 120,

    "converter_mode": "NONE",
    "converter_v1": 300,
    "converter_v2": 400,
    "converter_i1": 100,
    "converter_i2": 50,
    "converter_contactor": "closed",

    "soc": 30,
    "soh": 30,
    "storage_energy": 10,
    "storage_energy_max": 20,
    "voltage1": 300,
    "current1": 0,
    "temperature1": -2000,

    "contactor1": "CLOSED",
    "contactor2": "OPEN",

    "fan1_rpm": 1200,
    "fan2_rpm": 1180,
    "fan3_rpm": 1210,
    "fan4_rpm": 1190,
    "fan5_rpm": 1200,
    "fan6_rpm": 1170,
    "shutters": "OPEN",
}

systems = [
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

# =================================================
# FUNCTIONS
# =================================================

def link_value(value, maximum):

    if value > maximum:
        return "None"

    return f"{value} ms"

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

def get_segments(value, minimum, maximum, minimum_segments=0):

    value = max(minimum, min(value, maximum))

    segments = round(
        (value - minimum) / (maximum - minimum) * 7
    )

    return max(segments, minimum_segments)

# =====================================================
# CSS
# =====================================================

ui.add_css('''
/* =====================================================
   THEME VARIABLES
   ===================================================== */

:root {
    --bg-color: #0C0C0C;
    --fg-color: #FFFFFF;
    --border-color: #7C7C7C;
    --panel-bg: #1C1C1C;
    --placeholder-color: #888888;
    --segment-off-color: #444444;
    --scrollbar-thumb: #555555;
    --scrollbar-thumb-hover: #707070;
}

body.theme-light {
    --bg-color: #F2F2F2;
    --fg-color: #111111;
    --border-color: #A0A0A0;
    --panel-bg: #E2E2E2;
    --placeholder-color: #666666;
    --segment-off-color: #CCCCCC;
    --scrollbar-thumb: #B0B0B0;
    --scrollbar-thumb-hover: #909090;
}

/* =====================================================
   COMMAND LIST SCROLLBAR
   ===================================================== */

.command-list {
    scrollbar-width: auto;
    scrollbar-color: var(--scrollbar-thumb) var(--panel-bg);
}

/* Chrome / Edge / Chromium */

.command-list::-webkit-scrollbar {
    width: 16px;
}

.command-list::-webkit-scrollbar-track {
    background: var(--panel-bg);
}

.command-list::-webkit-scrollbar-thumb {
    background: var(--scrollbar-thumb);
    border-radius: 5px;
}

.command-list::-webkit-scrollbar-thumb:hover {
    background: var(--scrollbar-thumb-hover);
}

/* Убираем стрелки scrollbar */

.command-list::-webkit-scrollbar-button {
    display: none;
    width: 0;
    height: 0;
}


/* =====================================================
   COMMAND BUTTONS
   ===================================================== */

.command-list .q-btn {
    justify-content: flex-start !important;
    text-align: left !important;

    color: var(--fg-color) !important;

    font-family: "DejaVu Sans Mono", monospace !important;
    font-size: 16px !important;
    line-height: 1.5 !important;

    text-transform: none !important;

    width: 100% !important;

    height: 27px !important;
    min-height: 27px !important;

    padding: 0 8px !important;

    border-radius: 0 !important;
}

.command-list .q-btn__content {
    justify-content: flex-start !important;
    text-align: left !important;

    width: 100% !important;

    color: var(--fg-color) !important;
}


/* =====================================================
   COMMAND INPUT
   ===================================================== */

.command-input {
    background: var(--panel-bg) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

.command-input.command-input-open {
    border-radius: 0 0 10px 10px !important;
}

.command-input .q-field__control {
    background: transparent !important;

    padding: 0 16px !important;

    border: none !important;
    box-shadow: none !important;
}

.command-input .q-field__control:before,
.command-input .q-field__control:after {
    border: none !important;
    box-shadow: none !important;
}

.command-input.q-field--focused .q-field__control:before,
.command-input.q-field--focused .q-field__control:after {
    border: none !important;
    box-shadow: none !important;
}

.command-input input,
.command-input .q-field__native {
    color: var(--fg-color) !important;
    caret-color: var(--fg-color) !important;

    font-family: "DejaVu Sans Mono", monospace !important;
    font-size: 16px !important;

    text-transform: none !important;
}

.command-input input::placeholder,
.command-input .q-field__native::placeholder {
    color: var(--placeholder-color) !important;
    opacity: 1 !important;
}
''')

# =================================================
# GRID SETTINGS
# =================================================

if isinstance(columns, list):
    grid_columns = " ".join(
        f"minmax(0, {value}fr)"
        for value in columns
    )
else:
    grid_columns = " ".join(
        ["minmax(0, 1fr)"] * columns
    )

if isinstance(rows, list):
    grid_rows = " ".join(
        f"minmax(0, {value}fr)"
        for value in rows
    )
else:
    grid_rows = " ".join(
        ["minmax(0, 1fr)"] * rows
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

        is_command_line = cell["title"] == "Command line"

        no_border_titles = ("Command line", "CAN status")
        cell_border = 'none' if cell["title"] in no_border_titles else '1px solid var(--border-color)'
        cell_flex = 'display: flex; align-items: center; justify-content: center;' if is_command_line else ''

        with ui.element('div').style(
            f'''
            grid-area: {name};

            position: relative;
            overflow: visible;

            min-width: 0;
            min-height: 0;

            border: {cell_border};
            border-radius: 10px;
            padding: 15px;

            {cell_flex}

            box-sizing: border-box;
            '''
        ):
            
            if cell["title"] == "CAN status":

                with ui.row().classes('w-full items-center justify-between'):

                    ui.label('CAN-BUS: VCAN,    500 kbit/s')

                    theme_toggle = ui.button(
                        icon='dark_mode',
                        on_click=lambda: toggle_theme(),
                    ).props('flat dense round')

            elif cell["title"] == "EC status":

                # EC status
                with ui.element('div').classes('flex items-center'):
                    state = parameters["ec_state"]

                    with ui.element('div').style(
                        f'''
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        background: {state_color(state)};
                        margin-right: 6px;
                        '''
                    ):
                        pass

                    ui.label(f'EC status: {state}')

                # Warnings / Errors
                with ui.element('div').classes('flex items-center'):
                    ui.label(
                        f'Warnings: {parameters["ec_warnings"]}'
                    ).style('margin-right: 20px;')

                    ui.label(
                        f'Errors: {parameters["ec_errors"]}'
                    )

                # Full cycles
                ui.label(
                    f'Full cycles: {parameters["ec_cycles"]}'
                )

            elif cell["title"] == "Converter":

                ui.label(
                    f'Converter mode: {parameters["converter_mode"].capitalize()}'
                )

                ui.label(
                    f'U1 {parameters["converter_v1"]}V < {parameters["converter_v2"]}V U2'
                )

                ui.label(
                    f'I1 {parameters["converter_i1"]}A -> {parameters["converter_i2"]}A I2'
                )

                ui.label(
                    f'Contactor {parameters["converter_contactor"]}'
                )

            elif cell["title"] == "Systems states":

                with ui.element('div').style(
                    '''
                    display: grid;
                    grid-template-columns: 2fr 3fr 2fr 2fr;
                    width: 100%;
                    '''
                ):

                    ui.label('State')
                    ui.label('System')
                    ui.label('Errors')
                    ui.label('Link')

                    for name, state_key, errors_key, link_key, link_max in systems:

                        state = parameters[state_key]

                        with ui.element('div').classes('flex items-center'):

                            with ui.element('div').style(
                                f'''
                                width: 12px;
                                height: 12px;
                                border-radius: 50%;
                                background: {state_color(state)};
                                margin-right: 5px;
                                '''
                            ):
                                pass

                            ui.label(state)

                        ui.label(name)

                        errors = parameters[errors_key]

                        ui.label(
                            'None' if errors == 0 else str(errors)
                        )

                        ui.label(
                            link_value(
                                parameters[link_key],
                                link_max
                            )
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
                            background = 'var(--segment-off-color)'

                        ui.element('div').style(
                            f'''
                            width: 12px;
                            height: 12px;
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
                            background = 'var(--segment-off-color)'

                        ui.element('div').style(
                            f'''
                            width: 12px;
                            height: 12px;
                            margin-right: 5px;
                            background: {background};
                            '''
                        )

                    ui.label(
                        f'{soh:.0f}%'
                    ).classes('ml-auto')

                # Storage energy
                ui.label(
                    f'Storage energy: {parameters["storage_energy"]} kWh'
                )

                ui.label(
                    f'Max storage energy: {parameters["storage_energy_max"]} kWh'
                )

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
                            background = 'var(--segment-off-color)'

                        ui.element('div').style(
                            f'''
                            width: 12px;
                            height: 12px;
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
                            background = 'var(--segment-off-color)'

                        ui.element('div').style(
                            f'''
                            width: 12px;
                            height: 12px;
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
                            background = 'var(--segment-off-color)'

                        ui.element('div').style(
                            f'''
                            width: 12px;
                            height: 12px;
                            margin-right: 5px;
                            background: {background};
                            '''
                        )

                    ui.label(
                        f'{temperature:.0f}C'
                    ).classes('ml-auto')

            elif cell["title"] == "Contactors":

                ui.label(
                    f'Contactor 1: {parameters["contactor1"].lower()} | '
                    f'Contactor 2: {parameters["contactor2"].lower()}'
                )

            elif cell["title"] == "Coolling system":

                fan_parts = [
                    f'F{i}:{parameters[f"fan{i}_rpm"]}rpm'
                    for i in range(1, 7)
                ]

                fan_parts.append(
                    f'Sh:{parameters["shutters"]}'
                )

                ui.label(
                    ' | '.join(fan_parts)
                )

            elif cell["title"] == "Command line":

                commands = [
                    '/restart',
                    '/close contactors',
                    '/open contactors',
                    '/status',
                    '/shutdown',
                    '/reset',
                    '/start cooling',
                    '/stop cooling',
                ]

                # =================================================
                # CLICK-OUTSIDE OVERLAY
                # =================================================

                click_outside_overlay = ui.element('div').style(
                    '''
                    position: fixed;
                    inset: 0;

                    display: none;

                    z-index: 999;
                    '''
                )

                # =================================================
                # COMMAND LINE CONTAINER
                # =================================================

                with ui.element('div').style(
                    '''
                    position: relative;
                    width: calc(100% - 20px);

                    z-index: 1000;
                    '''
                ):

                    # =================================================
                    # COMMAND LIST
                    # =================================================

                    with ui.element('div').style(
                        '''
                        position: absolute;

                        left: 0;
                        right: 0;

                        bottom: 100%;

                        width: 100%;

                        height: 144px;

                        display: none;

                        background: var(--panel-bg);

                        border: none;
                        border-radius: 10px 10px 0 0;

                        box-sizing: border-box;
                        overflow: hidden;

                        z-index: 1000;
                        '''
                    ) as command_list:

                        with ui.element('div').classes(
                            'command-list'
                        ).style(
                            '''
                            width: 100%;
                            height: 100%;

                            overflow-y: auto;
                            overflow-x: hidden;
                            '''
                        ):

                            for command in commands:

                                ui.button(
                                    command
                                ).props(
                                    'flat dense'
                                ).classes(
                                    'w-full justify-start'
                                ).on(
                                    'click',
                                    lambda e, command=command:
                                        command_input.set_value(command)
                                )

                    # =================================================
                    # COMMAND INPUT
                    # =================================================

                    command_input = ui.input(
                        placeholder='/Command line...'
                    ).props(
                        'borderless dense'
                    ).classes(
                        'w-full command-input'
                    )

                    # =================================================
                    # OPEN COMMAND LIST
                    # =================================================

                    def open_commands():
                        command_list.style(
                            '''
                            display: block;
                            '''
                        )

                        command_input.classes(
                            add='command-input-open'
                        )

                        click_outside_overlay.style(
                            '''
                            display: block;
                            '''
                        )

                    # =================================================
                    # CLOSE COMMAND LIST
                    # =================================================

                    def close_commands():
                        command_list.style(
                            '''
                            display: none;
                            '''
                        )

                        command_input.classes(
                            remove='command-input-open'
                        )

                        click_outside_overlay.style(
                            '''
                            display: none;
                            '''
                        )

                        command_input.set_value('')

                        command_input.run_method(
                            'blur'
                        )

                    # =================================================
                    # OPEN ON FOCUS
                    # =================================================

                    command_input.on(
                        'focus',
                        lambda e: open_commands()
                    )

                    # =================================================
                    # CLICK OUTSIDE — CLOSE COMMAND LINE
                    # =================================================

                    click_outside_overlay.on(
                        'click',
                        lambda e: close_commands()
                    )

                    # =================================================
                    # ESC — CLOSE COMMAND LINE (even while typing)
                    # =================================================

                    def handle_key(e):
                        if e.action.keydown and e.key == 'Escape':
                            close_commands()

                    ui.keyboard(
                        on_key=handle_key,
                        ignore=[]
                    )

            else:

                ui.label(cell["title"])

# =================================================
# THEME TOGGLE
# =================================================

is_light_theme = False

def toggle_theme():
    global is_light_theme

    is_light_theme = not is_light_theme

    if is_light_theme:
        ui.query('body').classes(add='theme-light')
        theme_toggle.set_icon('light_mode')
    else:
        ui.query('body').classes(remove='theme-light')
        theme_toggle.set_icon('dark_mode')

ui.run()
