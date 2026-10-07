import math
from datetime import datetime
from types import SimpleNamespace

from nicegui import ui

from canbus.commands import execute
from parameters import BUP_ERRORS, DEVICES, NO_DATA
from settings import (
    CELL_TEMPERATURE_COLUMNS,
    CELL_VOLTAGE_COLUMNS,
    CURRENT_MAX,
    CURRENT_MIN,
    EVENT_LOG_SIZE,
    METER_SEGMENTS,
    SOC_MAX,
    SOC_MIN,
    SOH_MAX,
    SOH_MIN,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    VOLTAGE_MAX,
    VOLTAGE_MIN,
)

from .colors import (
    BOX_COLORS,
    DIM,
    GREEN,
    METER_BG,
    NO_DATA_COLOR,
    RED,
    YELLOW,
    cell_voltage_color,
    current_color,
    meter_color,
    soc_color,
    soh_color,
    state_color,
    temperature_color,
    voltage_color,
)
from .command_line import build_command_line
from .events import EVENTS, log_command
from .helpers import (
    cells_summary,
    fmt,
    get_segments,
    is_number,
    link_value,
    pretty,
    segment_value,
    spans_html,
)

SUPERSCRIPTS = '⁰¹²³⁴⁵⁶⁷⁸⁹'


# =================================================
# BOX FRAME
# =================================================

def superscript(number):

    return ''.join(SUPERSCRIPTS[int(digit)] for digit in str(number))


def tab_html(*parts):
    """
    Border label ┐...┌ built from (text, css class[, colour]) parts.
    """

    return f'<span class="tick">┐</span>{spans_html(parts)}<span class="tick">┌</span>'


def border_tab(*parts):

    return ui.html(
        tab_html(*parts),
        sanitize=False,
    ).classes('box-tab')


def render_box(area, cell, number, parameters, updates, debug=False):
    """
    Draw one dashboard box. The widget adds its update functions to
    `updates`; the page calls them on a timer to show fresh values.
    """

    color = BOX_COLORS.get(cell.get("color"), BOX_COLORS["gray"])

    with ui.element('div').classes('box').style(
        f'grid-area: {area}; --box: {color};'
    ):

        with ui.element('div').classes('box-bar'):
            left = ui.element('div').classes('box-bar-side')
            right = ui.element('div').classes('box-bar-side')

        with left:
            border_tab(
                (superscript(number), 'num'),
                (cell["title"], 'title'),
            )

        box = SimpleNamespace(left=left, right=right, updates=updates, debug=debug)

        widget = cell.get("widget")
        renderer = CELL_RENDERERS.get(widget)

        if renderer is None:
            ui.label(f'unknown widget: {widget}').classes('dim')
            return

        renderer(parameters, box)


def live(box, update):
    """
    Show the current values now and keep them fresh.
    """

    update()
    box.updates.append(update)


# =================================================
# BUILDING BLOCKS
# =================================================

class Value:
    """
    Value label that is redrawn only when its text or colour changes.
    """

    def __init__(self, label):

        self.label = label
        self.shown = None

    def set(self, text, color=None):

        if (text, color) == self.shown:
            return

        self.shown = (text, color)

        self.label.set_text(text)
        self.label.style(f'color: {color or "var(--title)"};')


class Meter:
    """
    Row of blocks. Every lit block takes the colour of the value it stands
    for and gets darker / brighter along the scale, like btop meters.
    """

    def __init__(self):

        with ui.element('div').classes('meter'):
            self.segments = [
                ui.element('div').classes('meter-seg')
                for _ in range(METER_SEGMENTS)
            ]

        self.colors = [None] * METER_SEGMENTS

    def set(self, value, minimum, maximum, color, minimum_segments=0):

        lit = get_segments(
            value, minimum, maximum, METER_SEGMENTS, minimum_segments
        )

        for i, segment in enumerate(self.segments):

            if i < lit:
                background = meter_color(
                    color(segment_value(i, minimum, maximum, METER_SEGMENTS)),
                    i / (METER_SEGMENTS - 1),
                )
            else:
                background = METER_BG

            if background != self.colors[i]:
                self.colors[i] = background
                segment.style(f'background: {background};')


def text(value):
    """
    Text value for display: lower case, a dash when there is no data.
    """

    if value == NO_DATA:
        return '—'

    return str(value).lower()


def count(value, color):
    """
    Counter text and colour: the colour only when it is above zero.
    """

    return fmt(value), color if is_number(value) and value > 0 else None


def render_kv(key):

    with ui.element('div').classes('kv'):

        ui.label(key).classes('k')

        return Value(ui.label().classes('v'))


def render_pairs(keys):
    """
    One line of "key value" pairs spread across the width.
    """

    values = []

    with ui.element('div').classes('kv'):

        for key in keys:

            with ui.element('div'):
                ui.label(key).classes('k inline')
                ui.label(' ').classes('inline whitespace-pre')
                values.append(Value(ui.label().classes('v inline')))

    return values


def render_metric(label, unit, minimum, maximum, color, minimum_segments=0):
    """
    "Label  value" line with a meter under it. Returns a setter.
    """

    value_label = render_kv(label)
    meter = Meter()

    def set_value(value):

        value_label.set(
            fmt(value, unit, '.0f'),
            color(value) if is_number(value) else DIM,
        )

        meter.set(value, minimum, maximum, color, minimum_segments)

    return set_value


# =================================================
# WIDGETS
# =================================================

BUS_STATE_COLORS = {
    "CONNECTED": GREEN,
    "DISCONNECTED": RED,
    "SIMULATION": YELLOW,
}


def render_can_status(parameters, box):

    bus = parameters["bus"]

    source = render_kv('Source')
    bitrate = render_kv('Bitrate')
    state = render_kv('State')

    def update_bus():

        source.set('—' if bus["source"] == NO_DATA else bus["source"])

        rate = bus["bitrate"]
        bitrate.set(fmt(rate / 1000, ' kbit/s') if is_number(rate) else '—')

        # Frames per second only make sense for the real adapter
        fps = bus["frames_per_second"]
        suffix = f'  {fps} fr/s' if bus["state"] == "CONNECTED" and is_number(fps) else ''

        state.set(
            f'● {text(bus["state"])}{suffix}',
            BUS_STATE_COLORS.get(bus["state"], DIM),
        )

    live(box, update_bus)

    with box.right:

        # Values are imitated by the simulator (--debug)
        if box.debug:
            border_tab(('simulation', 'title', YELLOW))

        clock = border_tab()

    shown = None

    def update():

        nonlocal shown

        now = datetime.now().strftime('%H:%M:%S')

        if now != shown:
            shown = now
            clock.set_content(tab_html((now, 'title')))

    live(box, update)


def render_ec_status(parameters, box):

    bune = parameters["bune"]

    state = render_kv('State')
    warnings = render_kv('Warnings')
    errors = render_kv('Errors')
    cycles = render_kv('Full cycles')

    def update():

        state.set(f'● {bune["state"]}', state_color(bune["state"]))
        warnings.set(*count(bune["warnings"], YELLOW))
        errors.set(*count(bune["errors"], RED))
        cycles.set(fmt(bune["cycles"]))

    live(box, update)


def render_converter(parameters, box):

    bup = parameters["bup"]
    bune = parameters["bune"]

    mode = render_kv('Mode')

    # U1 0V < 0V U2
    # I1 0A -> 0A I2
    flow = {}

    with ui.element('div').classes('table').style(
        'grid-template-columns: auto 1fr auto 1fr auto;'
    ):

        for left_key, left, sign, right, right_key in (
            ('U1', "dc_input_voltage", '<', "dc_output_voltage", 'U2'),
            ('I1', "dc_input_current", '->', "dc_output_current", 'I2'),
        ):

            ui.label(left_key).classes('k')
            flow[left] = Value(ui.label().classes('v text-right'))
            ui.label(sign).classes('dim text-center')
            flow[right] = Value(ui.label().classes('v'))
            ui.label(right_key).classes('k')

    errors = render_kv('Errors')
    contactor = render_kv('Contactor')

    def update():

        mode.set(pretty(bup["dc_status"]))

        for key, value in flow.items():
            value.set(fmt(bup[key], 'A' if 'current' in key else 'V'))

        # Active error flags of 0x198
        active = [name for key, name in BUP_ERRORS.items() if bup[key] == "ALARM"]

        if all(bup[key] == NO_DATA for key in BUP_ERRORS):
            errors.set('—')
        elif active:
            errors.set(', '.join(active), RED)
        else:
            errors.set('None')

        contactor.set(text(bune["converter_contactor"]))

    live(box, update)


def render_systems_states(parameters, box):

    rows = []

    # Header stays on top, the device list scrolls under it
    with ui.element('div').classes('scroll-area'):

        with ui.element('div').classes('scroll'):

            # Device names give way first when the box is narrow
            with ui.element('div').classes('table sticky-head').style(
                'grid-template-columns: auto minmax(0, 1fr) auto auto auto;'
                'column-gap: 1.5ch;'
            ):

                for header in ('State', 'Device', 'ID', 'Errors', 'Link'):
                    ui.label(header).classes('th')

                for key, name, can_id, link_max in DEVICES:

                    state = Value(ui.label())
                    ui.label(name).classes('k truncate')
                    ui.label(can_id).classes('dim')
                    errors = Value(ui.label().classes('v'))
                    link = Value(ui.label().classes('v text-right'))

                    rows.append((parameters[key], link_max, state, errors, link))

    def update():

        for device, link_max, state, errors, link in rows:

            state.set(f'● {device["state"]}', state_color(device["state"]))

            if device["errors"] == 0:
                errors.set('None')
            else:
                errors.set(*count(device["errors"], RED))

            # "None" means the link timed out or there is no data yet
            link_text = link_value(device["link"], link_max)
            link.set(link_text, RED if link_text == "None" else None)

    live(box, update)


def render_soc(parameters, box):

    bune = parameters["bune"]

    soc = render_metric('SoC', '%', SOC_MIN, SOC_MAX, soc_color, minimum_segments=1)
    soh = render_metric('SoH', '%', SOH_MIN, SOH_MAX, soh_color, minimum_segments=1)

    energy = render_kv('Storage energy')
    energy_max = render_kv('Max storage energy')

    def update():

        soc(bune["soc"])
        soh(bune["soh"])

        energy.set(fmt(bune["storage_energy"], ' kWh'))
        energy_max.set(fmt(bune["storage_energy_max"], ' kWh'))

    live(box, update)


def render_v_i_t(parameters, box):

    bune = parameters["bune"]

    voltage = render_metric(
        'Voltage', 'V', VOLTAGE_MIN, VOLTAGE_MAX, voltage_color, minimum_segments=1,
    )
    current = render_metric(
        'Current', 'A', CURRENT_MIN, CURRENT_MAX, current_color,
    )
    temperature = render_metric(
        'Temperature', 'C', TEMPERATURE_MIN, TEMPERATURE_MAX, temperature_color, minimum_segments=1,
    )

    def update():

        voltage(bune["voltage"])
        current(bune["current"])
        temperature(bune["temperature"])

    live(box, update)


def render_contactors(parameters, box):

    bune = parameters["bune"]

    contactor1, contactor2 = render_pairs(['Contactor 1', 'Contactor 2'])

    def update():

        contactor1.set(text(bune["contactor1"]))
        contactor2.set(text(bune["contactor2"]))

    live(box, update)


def render_cooling(parameters, box):

    so = parameters["so"]

    *fans, shutters = render_pairs(
        [f'F{i}' for i in range(1, 7)] + ['Shutters']
    )

    def update():

        for i, fan in enumerate(fans, start=1):
            fan.set(fmt(so[f"fan{i}_rpm"], 'rpm'))

        shutters.set(text(so["shutters"]))

    live(box, update)


# mode: (border label, parameters key, columns, unit, color function)
CELLS_MAP_MODES = {
    "voltage": ("voltage", "cell_voltages", CELL_VOLTAGE_COLUMNS, "V", cell_voltage_color),
    "temperature": ("temperature", "cell_temperatures", CELL_TEMPERATURE_COLUMNS, "C", temperature_color),
}


def cells_map_summary(mode, values):
    """
    Border labels with the key figures: [(text, css, colour), ...] per label.
    """

    _, _, _, unit, color = CELLS_MAP_MODES[mode]

    maximum, minimum, no_data = cells_summary(values)

    if maximum is None:
        labels = [
            [('max ', 'k'), ('—', 'v')],
            [('min ', 'k'), ('—', 'v')],
        ]
    else:
        labels = [
            [('max ', 'k'), (f'{maximum:g}{unit}', 'v', color(maximum))],
            [('min ', 'k'), (f'{minimum:g}{unit}', 'v', color(minimum))],
        ]

    if mode == "voltage":
        imbalance = '—' if maximum is None else f'{maximum - minimum:g}{unit}'
        labels.append([('imbalance ', 'k'), (imbalance, 'v')])

    labels.append([('no data ', 'k'), (no_data, 'v')])

    return labels


def render_cells_map(parameters, box):

    cc = parameters["cc"]

    tabs = {}

    with box.left:

        for mode, (label, *_) in CELLS_MAP_MODES.items():

            tabs[mode] = border_tab(
                (label, 'title'),
            ).classes('clickable').on(
                'click', lambda e, mode=mode: show(mode)
            )

    with box.right:
        summary = ui.element('div').classes('box-bar-side')

    grid = ui.element('div').classes('cells-map-grid')

    # What is on screen now
    view = SimpleNamespace(mode=None, tiles=[], summary=None)

    def show(mode):
        """
        Build the tiles of a mode; their colours come from update().
        """

        _, key, columns, _, _ = CELLS_MAP_MODES[mode]
        rows = math.ceil(len(cc[key]) / columns)

        for tab_mode, tab in tabs.items():

            if tab_mode == mode:
                tab.classes(add='active')
            else:
                tab.classes(remove='active')

        grid.style(f'--cols: {columns}; --rows: {rows};')
        grid.clear()

        view.tiles = []

        with grid:

            for number in range(1, len(cc[key]) + 1):

                with ui.label(str(number)).classes('cells-map-cell') as tile:
                    tooltip = ui.tooltip()

                # tile, tooltip, what they show now
                view.tiles.append([tile, tooltip, None])

        view.mode = mode
        view.summary = None

        update()

    def update():

        _, key, _, unit, color = CELLS_MAP_MODES[view.mode]
        values = cc[key]

        for number, (entry, value) in enumerate(zip(view.tiles, values), start=1):

            if is_number(value):
                shown = (color(value), 'lit', f'Cell {number}: {value:g}{unit}')
            else:
                shown = (NO_DATA_COLOR, 'off', f'Cell {number}: No data')

            if shown == entry[2]:
                continue

            tile, tooltip, _ = entry
            background, lit, tooltip_text = shown

            tile.style(f'background: {background};')
            tile.classes(add=lit, remove='off' if lit == 'lit' else 'lit')
            tooltip.set_text(tooltip_text)

            entry[2] = shown

        labels = cells_map_summary(view.mode, values)

        if labels != view.summary:

            view.summary = labels
            summary.clear()

            with summary:
                for parts in labels:
                    border_tab(*parts)

    show("voltage")

    box.updates.append(update)


def event_html(event):

    return spans_html(
        [
            (event.time, 'dim'),
            (f'  {event.source:<11}', 'k'),
        ]
        + event.parts
    )


def run_command(text):

    ok, result = execute(text)
    log_command(text, result, ok)


def render_event_log(parameters, box):

    # Newest entry at the bottom, next to the command line:
    # the list is column-reverse, so new rows are inserted first
    with ui.element('div').classes('scroll-area'):
        lines = ui.element('div').classes('log-lines')

    with ui.element('div').classes('log-input'):
        build_command_line(on_command=run_command)

    shown = 0

    def update():

        nonlocal shown

        for event in [event for event in EVENTS if event.seq > shown]:

            with lines:
                row = ui.html(event_html(event), sanitize=False).classes('log-line')

            row.move(lines, target_index=0)

            shown = event.seq

        rows = lines.default_slot.children

        while len(rows) > EVENT_LOG_SIZE:
            lines.remove(rows[-1])

    live(box, update)


CELL_RENDERERS = {
    "can_status": render_can_status,
    "ec_status": render_ec_status,
    "converter": render_converter,
    "systems_states": render_systems_states,
    "soc": render_soc,
    "v_i_t": render_v_i_t,
    "contactors": render_contactors,
    "cooling": render_cooling,
    "cells_map": render_cells_map,
    "event_log": render_event_log,
}
