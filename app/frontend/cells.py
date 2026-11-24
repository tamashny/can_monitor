import math
from datetime import datetime
from types import SimpleNamespace

from nicegui import ui

from canbus.commands import execute
from canmap import temperature_grid, temperature_sensor
from parameters import DEVICES, NO_DATA
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
from summary import active_flags, lost_buses, working_buses

from .colors import (
    BOX_COLORS,
    DIM,
    GREEN,
    METER_BG,
    NO_DATA_COLOR,
    RED,
    YELLOW,
    cell_temperature_color,
    cell_voltage_color,
    current_color,
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
    pretty,
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
    Row of blocks. All lit blocks have one colour, that of the current value.
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

        lit_color = color(value) if lit else METER_BG

        for i, segment in enumerate(self.segments):

            background = lit_color if i < lit else METER_BG

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


def render_metric(label, unit, minimum, maximum, color, minimum_segments=0, magnitude=False):
    """
    "Label  value" line with a meter under it. Returns a setter.
    With magnitude=True the meter ignores the sign of the value.
    """

    value_label = render_kv(label)
    meter = Meter()

    def set_value(value):

        value_label.set(
            fmt(value, unit, '.0f'),
            color(value) if is_number(value) else DIM,
        )

        shown = abs(value) if magnitude and is_number(value) else value

        meter.set(shown, minimum, maximum, color, minimum_segments)

    return set_value


# =================================================
# WIDGETS
# =================================================

BUS_STATE_COLORS = {
    "CONNECTED": GREEN,
    "DISCONNECTED": RED,
    "SIMULATION": YELLOW,
}

BUS_STATE_TEXT = {
    "DISCONNECTED": "offline",
    "SIMULATION": "simulation",
}


def render_can_status(parameters, box):

    bus = parameters["bus"]

    ports = render_kv('Ports')
    bitrate = render_kv('Bitrate')
    main = render_kv('CAN1')
    reserve = render_kv('CAN2')

    def bus_text(state, fps):
        """
        Frames per second of a working adapter, otherwise its state.
        """

        if state == "CONNECTED" and is_number(fps):
            return f'● {fps} fr/s'

        return f'● {BUS_STATE_TEXT.get(state, text(state))}'

    def update_bus():

        if bus["port"] == bus["reserve_port"]:
            ports.set(text(bus["port"]))
        else:
            ports.set(f'{bus["port"]} / {bus["reserve_port"]}')

        rate = bus["bitrate"]
        bitrate.set(fmt(rate / 1000, ' kbit/s') if is_number(rate) else '—')

        main.set(
            bus_text(bus["state"], bus["frames_per_second"]),
            BUS_STATE_COLORS.get(bus["state"], DIM),
        )
        reserve.set(
            bus_text(bus["reserve_state"], bus["reserve_frames_per_second"]),
            BUS_STATE_COLORS.get(bus["reserve_state"], DIM),
        )

    live(box, update_bus)

    with box.right:
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
    system = render_kv('System')
    warnings = render_kv('Warnings')
    errors = render_kv('Errors')

    def update():

        state.set(f'● {bune["overall"]}', state_color(bune["overall"]))
        system.set(pretty(bune["state"]))
        warnings.set(*count(bune["total_warnings"], YELLOW))
        errors.set(*count(bune["total_errors"], RED))

    live(box, update)


def setpoint_text(bup):
    """
    The setpoint of БУП is a voltage or a current, depending on the mode.
    """

    mode = bup["cmd.req_mode"]
    unit = ''

    if isinstance(mode, str) and mode.endswith("_SET_V"):
        unit = 'V'
    elif isinstance(mode, str) and mode.endswith("_SET_I"):
        unit = 'A'

    return fmt(bup["cmd.set"], unit)


# Flags of status_bup shown as words: bright when set
BUP_FLAGS = {
    "flags.pulses_enabled": "pulses",
    "flags.dc_link_charged": "link",
    "flags.voltages_in_window": "window",
}


def render_converter(parameters, box):

    bup = parameters["bup"]

    state = render_kv('State')
    mode = render_kv('Mode')
    requested = render_kv('Req')
    setpoint = render_kv('Set')

    # One line per side of the converter: voltage, current
    # Bus 780V  -870A
    # ESS 900V  -780A
    flow = {}

    with ui.element('div').classes('table').style(
        'grid-template-columns: auto 1fr 1fr; column-gap: 1ch;'
    ):

        for side, voltage, current in (
            ('Bus', "u_dc", "i_dc"),
            ('ESS', "u_ess", "i_ess"),
        ):

            ui.label(side).classes('k')
            flow[voltage] = Value(ui.label().classes('v text-right'))
            flow[current] = Value(ui.label().classes('v text-right'))

    flags = {}

    with ui.element('div').classes('kv'):

        for key, name in BUP_FLAGS.items():
            flags[key] = (name, Value(ui.label()))

    def update():

        state.set(pretty(bup["state"]), state_color(bup["state"]) if bup["state"] == "FAULT" else None)
        mode.set(pretty(bup["mode"]))
        requested.set(pretty(bup["cmd.req_mode"]))
        setpoint.set(setpoint_text(bup))

        for key, value in flow.items():
            value.set(fmt(bup[key], 'A' if key.startswith('i') else 'V'))

        for key, (name, label) in flags.items():
            label.set(name, GREEN if bup[key] == "ON" else DIM)

    live(box, update)


# Short texts of the "systems" table, so that it fits a narrow box
HEALTH_TEXT = {"WARNING": "WARN"}

NMT_TEXT = {
    "OPERATIONAL": "OP",
    "PRE_OPERATIONAL": "PRE",
    "STOPPED": "STOP",
    "BOOT_UP": "BOOT",
}


def set_tip(tooltip, names):
    """
    Tooltip with a list of names, redrawn only when it changes.
    """

    content = ', '.join(names) or 'none'

    if tooltip.text != content:
        tooltip.set_text(content)


def render_systems_states(parameters, box):

    bus = parameters["bus"]

    rows = []

    # Header stays on top, the device list scrolls under it
    with ui.element('div').classes('scroll-area'):

        with ui.element('div').classes('scroll'):

            # State first, then which device, what is wrong, and the link last.
            # Columns are spread evenly over the width, rows over the height
            with ui.element('div').classes('table sticky-head systems-table'):

                for header, hint in (
                    ('State', None),
                    ('Dev', None),
                    ('ID', None),
                    ('Err', None),
                    ('Wrn', None),
                    ('NMT', None),
                    ('Link', 'ms between the last two contacts of the device, on any bus'),
                ):

                    with ui.label(header).classes('th'):
                        if hint:
                            ui.tooltip(hint)

                for key, name, can_id, link_max in DEVICES:

                    state = Value(ui.label())
                    ui.label(name).classes('k')
                    ui.label(can_id).classes('dim')

                    # The tooltips name the active faults and warnings
                    with ui.label().classes('v text-right') as errors_label:
                        errors_tip = ui.tooltip()

                    with ui.label().classes('v text-right') as warnings_label:
                        warnings_tip = ui.tooltip()

                    nmt = Value(ui.label().classes('v'))
                    link = Value(ui.label().classes('v text-right'))

                    rows.append((
                        key, parameters[key], link_max, state, nmt, link,
                        Value(errors_label), errors_tip,
                        Value(warnings_label), warnings_tip,
                    ))

    def link_cell(device, link_max):
        """
        Period of the last contact, ms: red when it is longer than the
        timeout. × when the device is lost on all buses, a dash without
        adapters or before its second contact.
        """

        working = working_buses(bus)

        if not working:
            return '—', DIM

        if len(lost_buses(device, bus, link_max)) == working:
            return '×', RED

        period = device["link"]

        if not is_number(period):
            return '—', DIM

        return str(period), RED if period > link_max else None

    def update():

        for (
            key, device, link_max, state, nmt, link,
            errors, errors_tip, warnings, warnings_tip,
        ) in rows:

            health = device["health"]

            state.set(f'● {HEALTH_TEXT.get(health, health)}', state_color(health))

            # СКИ has no heartbeat
            nmt_state = device.get("nmt_state", NO_DATA)

            nmt.set(
                NMT_TEXT.get(nmt_state, '—'),
                GREEN if nmt_state == "OPERATIONAL" else YELLOW if nmt_state in NMT_TEXT else DIM,
            )

            errors.set(*count(device["errors"], RED))
            warnings.set(*count(device["warnings"], YELLOW))

            # СКИ has its own error flags instead of the common FAULT
            fault_signal = "internal_error" if key == "imd" else "fault"

            set_tip(errors_tip, active_flags(device, fault_signal, "ALARM"))
            set_tip(
                warnings_tip,
                active_flags(device, "warn", "WARNING") + lost_buses(device, bus, link_max),
            )

            # × means no valid frames: a timeout, or wrong DLC, CRC or CNT
            link.set(*link_cell(device, link_max))

    live(box, update)


def render_soc(parameters, box):

    bune = parameters["bune"]

    soc = render_metric('SoC', '%', SOC_MIN, SOC_MAX, soc_color, minimum_segments=1)
    soh = render_metric('SoH', '%', SOH_MIN, SOH_MAX, soh_color, minimum_segments=1)

    charge_limit = render_kv('Chg limit')
    discharge_limit = render_kv('Dch limit')
    charge = render_kv('Charge')

    def update():

        soc(bune["soc"])
        soh(bune["soh"])

        charge_limit.set(fmt(bune["i_chg_max"], ' A'))
        discharge_limit.set(fmt(bune["i_dch_max"], ' A'))
        charge.set(fmt(parameters["bem"]["q"], ' Ah', '.1f'))

    live(box, update)


def first_number(*values):
    """
    The first real measurement: the same value can come from two devices.
    """

    return next((value for value in values if is_number(value)), NO_DATA)


def storage_temperatures(cc):
    """
    The sensors inside the storage (storage_t_cc) that have data.
    """

    return [
        cc[f"t_storage_{i}"]
        for i in range(1, 6)
        if is_number(cc[f"t_storage_{i}"])
    ]


def render_v_i_t(parameters, box):

    bup = parameters["bup"]
    bem = parameters["bem"]
    cc = parameters["cc"]

    voltage = render_metric(
        'Voltage', 'V', VOLTAGE_MIN, VOLTAGE_MAX, voltage_color, minimum_segments=1,
    )
    # + charge, - discharge; the meter shows the magnitude
    current = render_metric(
        'Current', 'A', CURRENT_MIN, CURRENT_MAX,
        lambda value: current_color(abs(value)), magnitude=True,
    )
    temperature = render_metric(
        'Temp avg', 'C', TEMPERATURE_MIN, TEMPERATURE_MAX, temperature_color, minimum_segments=1,
    )
    temperature_min, temperature_max = render_pairs(['min', 'max'])

    def update():

        voltage(first_number(bup["u_ess"], bem["u"]))
        current(first_number(bem["i"], bup["i_ess"]))

        numbers = storage_temperatures(cc)

        temperature(sum(numbers) / len(numbers) if numbers else NO_DATA)

        for label, pick in ((temperature_min, min), (temperature_max, max)):

            if numbers:
                label.set(fmt(pick(numbers), 'C'), temperature_color(pick(numbers)))
            else:
                label.set('—')

    live(box, update)


def render_contactors(parameters, box):

    puer = parameters["puer"]

    # Commands only: the contactors have no feedback.
    # К1 is switched by БУНЭ itself (output DO1), its command is not on CAN
    # (document 02), so there is nothing to show until the map gets a signal.
    # The k1 bit of command_puer is not used: ПУЭР switches only К2.
    k1 = render_kv('K1 cmd')
    k2 = render_kv('K2 cmd')

    k1.set('—', DIM)

    with k1.label:
        ui.tooltip('БУНЭ switches K1 directly, the command is not sent over CAN')

    def update():

        k2.set(text(puer["cmd.req_mode.k2"]))

    live(box, update)


def render_isolation(parameters, box):

    imd = parameters["imd"]

    plus, minus = render_pairs(['R+', 'R-'])
    voltage = render_kv('Utrain')

    def update():

        # Without the "calculated" flag the values mean nothing
        resistance_ready = imd["resistance_calculated"] == "CALCULATED"
        voltage_ready = imd["bus_voltage_calculated"] == "CALCULATED"

        plus.set(fmt(imd["resistance_plus"], ' kOhm') if resistance_ready else '—')
        minus.set(fmt(imd["resistance_minus"], ' kOhm') if resistance_ready else '—')
        voltage.set(fmt(imd["bus_voltage"], 'V') if voltage_ready else '—')

    live(box, update)


def damper_text(bust_b):
    """
    Position of the shutter of БУСТ-Б from its two end switches.
    """

    opened = bust_b["damper_fb.open"]
    closed = bust_b["damper_fb.closed"]

    if opened == NO_DATA or closed == NO_DATA:
        return '—'

    if opened == "ON" and closed == "ON":
        return 'error'

    if opened == "ON":
        return 'open'

    return 'closed' if closed == "ON" else 'moving'


def render_cooling(parameters, box):

    bust_a = parameters["bust_a"]
    bust_b = parameters["bust_b"]

    # БУСТ-А: six fans with one power command and a feedback per fan.
    # БУСТ-Б: the shutter and the fan of the converter
    fans = render_pairs([f'F{i}' for i in range(1, 7)])

    fan_set, conv_fan, shutter = render_pairs(['Fset', 'Fconv', 'Shutter'])

    def update():

        for i, fan in enumerate(fans, start=1):
            fan.set(fmt(bust_a[f"fan_{i}_fb"], '%'))

        fan_set.set(fmt(bust_a["cmd.fan_set"], '%'))
        conv_fan.set(fmt(bust_b["conv_fan_fb"], '%'))
        shutter.set(damper_text(bust_b))

    live(box, update)


# mode: (border label, parameters key, columns, unit, color function)
CELLS_MAP_MODES = {
    "voltage": ("voltage", "cell_voltages", CELL_VOLTAGE_COLUMNS, "V", cell_voltage_color),
    "temperature": ("temp", "cell_temperatures", CELL_TEMPERATURE_COLUMNS, "C", cell_temperature_color),
    "free": ("free", "free_temperatures", CELL_TEMPERATURE_COLUMNS, "C", cell_temperature_color),
}

# Tab of the free sensors: the full name, or a short one in a narrow window
FREE_TAB = (
    ('free temp sensors', 'title tab-full'),
    ('free', 'title tab-short'),
)


def tile_names(mode, place):
    """
    Text on a tile and its name in the tooltip. Temperature sensors are
    numbered in the map as 1-Wire bus and sensor on it.
    """

    if mode == "temperature":
        bus, sensor = temperature_sensor(place)
        return f'{bus}.{sensor}', f'Bus {bus} sensor {sensor}'

    return str(place), f'Group {place}'


def cells_map_summary(mode, values, free=()):
    """
    Border labels with the key figures: [(text, css, colour), ...] per label.
    Max and min also count the free sensors, "no data" only the known places.
    """

    _, _, _, unit, color = CELLS_MAP_MODES[mode]

    _, _, no_data = cells_summary(values)
    maximum, minimum, _ = cells_summary(list(values) + list(free))

    # Full names, or arrows in a narrow window
    max_key = [('max ', 'k tab-full'), ('↑', 'k tab-short')]
    min_key = [('min ', 'k tab-full'), ('↓', 'k tab-short')]

    if maximum is None:
        labels = [
            min_key + [('—', 'v')],
            max_key + [('—', 'v')],
        ]
    else:
        labels = [
            min_key + [(f'{minimum:.2f}{unit}', 'v', color(minimum))],
            max_key + [(f'{maximum:.2f}{unit}', 'v', color(maximum))],
        ]

    labels.append([
        ('no data ', 'k tab-full'),
        ('n/d ', 'k tab-short'),
        (no_data, 'v'),
    ])

    return labels


def render_cells_map(parameters, box):

    cc = parameters["cc"]

    tabs = {}

    with box.left:

        for mode, (label, *_) in CELLS_MAP_MODES.items():

            parts = FREE_TAB if mode == "free" else ((label, 'title'),)

            tabs[mode] = border_tab(*parts).classes('clickable').on(
                'click', lambda e, mode=mode: show(mode)
            )

    with box.right:
        summary = ui.element('div').classes('box-bar-side')

    grid = ui.element('div').classes('cells-map-grid')

    # What is on screen now
    view = SimpleNamespace(mode=None, tiles=[], summary=None, free_shown=None)

    def new_tile(label):

        with ui.label(label).classes('cells-map-cell') as tile:
            tooltip = ui.tooltip()

        # tile, tooltip, what they show now
        return [tile, tooltip, None]

    def paint(entry, name, value, unit, color):

        if is_number(value):
            shown = (color(value), 'lit', f'{name}: {value:g}{unit}')
        else:
            shown = (NO_DATA_COLOR, 'off', f'{name}: {value}')

        if shown == entry[2]:
            return

        tile, tooltip, _ = entry
        background, lit, tooltip_text = shown

        tile.style(f'background: {background};')
        tile.classes(add=lit, remove='off' if lit == 'lit' else 'lit')
        tooltip.set_text(tooltip_text)

        entry[2] = shown

    def show(mode):
        """
        Build the tiles of a mode; their colours come from update().
        """

        _, key, columns, _, _ = CELLS_MAP_MODES[mode]

        # Free sensors use the grid of the known ones, so the tiles are the
        # same size. There are never more of them than places in that grid
        size_key = "cell_temperatures" if mode == "free" else key
        rows = math.ceil(len(cc[size_key]) / columns)

        for tab_mode, tab in tabs.items():

            if tab_mode == mode:
                tab.classes(add='active')
            else:
                tab.classes(remove='active')

        grid.style(f'--cols: {columns}; --rows: {rows};')
        grid.clear()

        view.tiles = []
        view.free_shown = None

        if mode != "free":

            with grid:

                for number in range(len(cc[key])):

                    entry = new_tile(tile_names(mode, number)[0])

                    if mode == "temperature":
                        row, column = temperature_grid(number)
                        entry[0].style(f'grid-row: {row}; grid-column: {column};')

                    view.tiles.append(entry)

        view.mode = mode
        view.summary = None

        update()

    def update_free(free, unit, color):
        """
        Tiles of the sensors with an unknown ROM code, rebuilt when the set
        of sensors changes. Without such sensors the field is empty.
        """

        places = [place for place, _ in free]

        if places != view.free_shown:

            grid.clear()

            view.tiles = []
            view.free_shown = places

            with grid:

                for _, (bus, _) in free:
                    view.tiles.append(new_tile(f'{bus or "?"}.?'))

        for entry, (_, (bus, value)) in zip(view.tiles, free):

            name = f'Free sensor, bus {bus}' if bus else 'Free sensor, bus unknown'

            paint(entry, name, value, unit, color)

    def update():

        _, key, _, unit, color = CELLS_MAP_MODES[view.mode]

        free = sorted(list(cc["free_temperatures"].items()), key=lambda item: item[0])
        free_values = [value for _, (_, value) in free]

        if view.mode == "free":

            update_free(free, unit, color)

            labels = cells_map_summary(view.mode, free_values)

        else:

            values = cc[key]

            for number, (entry, value) in enumerate(zip(view.tiles, values)):
                paint(entry, tile_names(view.mode, number)[1], value, unit, color)

            # Max and min of the temperatures include the free sensors
            extra = free_values if view.mode == "temperature" else ()

            labels = cells_map_summary(view.mode, values, extra)

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
            (f'  {event.source:<7}', 'k'),
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
    "isolation": render_isolation,
    "cooling": render_cooling,
    "cells_map": render_cells_map,
    "event_log": render_event_log,
}
