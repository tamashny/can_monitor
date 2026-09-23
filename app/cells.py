from nicegui import ui

from .colors import (
    current_color,
    soc_color,
    soh_color,
    state_color,
    temperature_color,
    voltage_color,
)
from .command_line import build_command_line
from .config import (
    CURRENT_MAX,
    CURRENT_MIN,
    SOC_MAX,
    SOC_MIN,
    SOH_MAX,
    SOH_MIN,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    VOLTAGE_MAX,
    VOLTAGE_MIN,
)
from .helpers import get_segments, link_value
from .parameters import SYSTEMS

NO_BORDER_TITLES = ("Command line", "CAN status")


def cell_style(name, cell):

    is_command_line = cell["title"] == "Command line"

    cell_border = 'none' if cell["title"] in NO_BORDER_TITLES else '1px solid var(--border-color)'
    cell_flex = 'display: flex; align-items: center; justify-content: center;' if is_command_line else ''

    return f'''
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


def render_segmented_row(label, value_text, color, segments, label_width='40px'):

    with ui.element('div').classes(
        'flex items-center w-full'
    ):

        ui.label(label).style(
            f'width: {label_width};'
        )

        for i in range(7):

            background = color if i < segments else 'var(--segment-off-color)'

            ui.element('div').style(
                f'''
                width: 12px;
                height: 12px;
                margin-right: 5px;
                background: {background};
                '''
            )

        ui.label(
            value_text
        ).classes('ml-auto')


def render_can_status(parameters):

    with ui.row().classes('w-full items-center justify-between'):

        ui.label('CAN-BUS: VCAN,    500 kbit/s')

        theme_toggle = ui.button(
            icon='dark_mode',
        ).props('flat dense round')

    is_light_theme = False

    def toggle_theme():
        nonlocal is_light_theme
        is_light_theme = not is_light_theme

        if is_light_theme:
            ui.query('body').classes(add='theme-light')
            theme_toggle.set_icon('light_mode')
        else:
            ui.query('body').classes(remove='theme-light')
            theme_toggle.set_icon('dark_mode')

    theme_toggle.on_click(toggle_theme)


def render_ec_status(parameters):

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


def render_converter(parameters):

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


def render_systems_states(parameters):

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

        for name, state_key, errors_key, link_key, link_max in SYSTEMS:

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


def render_soc(parameters):

    # SoC
    soc = parameters["soc"]

    render_segmented_row(
        'SoC',
        f'{soc:.0f}%',
        soc_color(soc),
        get_segments(soc, SOC_MIN, SOC_MAX, minimum_segments=1),
    )

    # SoH
    soh = parameters["soh"]

    render_segmented_row(
        'SoH',
        f'{soh:.0f}%',
        soh_color(soh),
        get_segments(soh, SOH_MIN, SOH_MAX, minimum_segments=1),
    )

    # Storage energy
    ui.label(
        f'Storage energy: {parameters["storage_energy"]} kWh'
    )

    ui.label(
        f'Max storage energy: {parameters["storage_energy_max"]} kWh'
    )


def render_v_i_t(parameters):

    # Voltage
    voltage = parameters["voltage1"]

    render_segmented_row(
        'U',
        f'{voltage:.0f}V',
        voltage_color(voltage),
        get_segments(voltage, VOLTAGE_MIN, VOLTAGE_MAX, minimum_segments=1),
        label_width='25px',
    )

    # Current
    current = parameters["current1"]

    render_segmented_row(
        'I',
        f'{current:.0f}A',
        current_color(current),
        get_segments(current, CURRENT_MIN, CURRENT_MAX),
        label_width='25px',
    )

    # Temperature
    temperature = parameters["temperature1"]

    render_segmented_row(
        'T',
        f'{temperature:.0f}C',
        temperature_color(temperature),
        get_segments(temperature, TEMPERATURE_MIN, TEMPERATURE_MAX, minimum_segments=1),
        label_width='25px',
    )


def render_contactors(parameters):

    ui.label(
        f'Contactor 1: {parameters["contactor1"].lower()} | '
        f'Contactor 2: {parameters["contactor2"].lower()}'
    )


def render_cooling(parameters):

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


def render_default(cell):
    ui.label(cell["title"])


CELL_RENDERERS = {
    "CAN status": render_can_status,
    "EC status": render_ec_status,
    "Converter": render_converter,
    "Systems states": render_systems_states,
    "SoC": render_soc,
    "V I T": render_v_i_t,
    "Contactors": render_contactors,
    "Coolling system": render_cooling,
}


def render_cell(cell, parameters):

    title = cell["title"]

    if title == "Command line":
        build_command_line()
        return

    renderer = CELL_RENDERERS.get(title)

    if renderer is None:
        render_default(cell)
        return

    renderer(parameters)
