import math
from datetime import datetime
from types import SimpleNamespace

from nicegui import ui

from canbus.commands import execute
from canmap import temperature_sensor
from parameters import DEVICES, MEASURE_ERROR, NO_DATA
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
from .events import EVENTS, SOURCE_WIDTH, log_command
from .helpers import (
    cells_summary,
    fmt,
    get_segments,
    is_number,
    pretty,
    spans_html,
)

SUPERSCRIPTS = '⁰¹²³⁴⁵⁶⁷⁸⁹'

# Special values of the parameters as they are shown in tooltips
VALUE_TEXT = {NO_DATA: 'нет данных', MEASURE_ERROR: 'ошибка измерения'}


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
            ui.label(f'неизвестный виджет: {widget}').classes('dim')
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


def render_pairs(keys, hints=None):
    """
    One line of "key value" pairs spread across the width.
    hints: optional tooltip per key.
    """

    values = []

    with ui.element('div').classes('kv'):

        for key, hint in zip(keys, hints or [None] * len(keys)):

            with ui.element('div'):

                with ui.label(key).classes('k inline'):
                    if hint:
                        ui.tooltip(hint)

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
    "CONNECTED": "подключен",
    "DISCONNECTED": "отключен",
    "SIMULATION": "имитация",
}

# Overall states of a device or of the whole storage
HEALTH_NAMES = {
    "OK": "норма",
    "WARNING": "предупреждение",
    "ALARM": "авария",
    "NONE": "нет связи",
}


def render_can_status(parameters, box):

    bus = parameters["bus"]

    ports = render_kv('Порты')
    bitrate = render_kv('Скорость')
    main = render_kv('CAN1')
    reserve = render_kv('CAN2')

    def bus_text(state, fps):
        """
        Frames per second of a working adapter, otherwise its state.
        """

        if state == "CONNECTED" and is_number(fps):
            return f'● подключен, {fps} кадр/с'

        return f'● {BUS_STATE_TEXT.get(state, text(state))}'

    def update_bus():

        if bus["port"] == bus["reserve_port"]:
            ports.set(text(bus["port"]))
        else:
            ports.set(f'{bus["port"]} / {bus["reserve_port"]}')

        rate = bus["bitrate"]
        bitrate.set(fmt(rate / 1000, ' кбит/с') if is_number(rate) else '—')

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

    state = render_kv('Статус')
    system = render_kv('Система')
    warnings = render_kv('Предупреждения')
    errors = render_kv('Ошибки')

    def update():

        state.set(f'● {HEALTH_NAMES.get(bune["overall"], bune["overall"])}', state_color(bune["overall"]))
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
        unit = 'В'
    elif isinstance(mode, str) and mode.endswith("_SET_I"):
        unit = 'А'

    return fmt(bup["cmd.set"], unit)


# Flags of status_bup shown as words: bright when set
BUP_FLAGS = {
    "flags.pulses_enabled": "пульсы",
    "flags.dc_link_charged": "связь",
    "flags.voltages_in_window": "окно",
}


def render_converter(parameters, box):

    bup = parameters["bup"]

    state = render_kv('Статус')
    mode = render_kv('Режим')
    requested = render_kv('Уставка')
    setpoint = render_kv('Цель')

    # One line per side of the converter: voltage, current
    # Сеть 780В  -870А
    # НЭ   900В  -780А
    flow = {}

    with ui.element('div').classes('table').style(
        'grid-template-columns: auto 1fr 1fr; column-gap: 1ch;'
    ):

        for side, voltage, current in (
            ('Сеть', "u_dc", "i_dc"),
            ('НЭ', "u_ess", "i_ess"),
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
            value.set(fmt(bup[key], 'А' if key.startswith('i') else 'В'))

        for key, (name, label) in flags.items():
            label.set(name, GREEN if bup[key] == "ON" else DIM)

    live(box, update)


# Short texts of the "systems" table, so that it fits a narrow box
HEALTH_TEXT = {"OK": "норма", "WARNING": "предупр", "ALARM": "авария", "NONE": "нет"}

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

    content = ', '.join(names) or 'нет'

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
                    ('Статус', None),
                    ('Устр', None),
                    ('ID', None),
                    ('Ав', 'аварии'),
                    ('Пр', 'предупреждения'),
                    ('NMT', None),
                    ('Связь', 'мс между двумя последними выходами устройства на связь, по любой шине'),
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

    charge_limit = render_kv('Ток заряда макс')
    discharge_limit = render_kv('Ток разряда макс')

    def update():

        soc(bune["soc"])
        soh(bune["soh"])

        charge_limit.set(fmt(bune["i_chg_max"], ' А'))
        discharge_limit.set(fmt(bune["i_dch_max"], ' А'))

    live(box, update)


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
    cc = parameters["cc"]

    voltage = render_metric(
        'Напряжение', 'В', VOLTAGE_MIN, VOLTAGE_MAX, voltage_color, minimum_segments=1,
    )
    # + charge, - discharge; the meter shows the magnitude
    current = render_metric(
        'Ток', 'А', CURRENT_MIN, CURRENT_MAX,
        lambda value: current_color(abs(value)), magnitude=True,
    )
    temperature = render_metric(
        'Т средняя', '°C', TEMPERATURE_MIN, TEMPERATURE_MAX, temperature_color, minimum_segments=1,
    )
    temperature_min, temperature_max = render_pairs(['мин', 'макс'])

    def update():

        voltage(bup["u_ess"])
        current(bup["i_ess"])

        numbers = storage_temperatures(cc)

        temperature(sum(numbers) / len(numbers) if numbers else NO_DATA)

        for label, pick in ((temperature_min, min), (temperature_max, max)):

            if numbers:
                label.set(fmt(pick(numbers), '°C'), temperature_color(pick(numbers)))
            else:
                label.set('—')

    live(box, update)


CONTACTOR_TEXT = {"OPEN": "открыт", "CLOSE": "закрыт"}


def render_contactors(parameters, box):

    puer = parameters["puer"]

    # Commands only: the contactors have no feedback.
    # К1 is switched by БУНЭ itself (output DO1), its command is not on CAN
    # (document 02), so there is nothing to show until the map gets a signal.
    # The k1 bit of command_puer is not used: ПУЭР switches only К2.
    k1 = render_kv('К1 уст.')
    k2 = render_kv('К2 уст.')

    k1.set('—', DIM)

    with k1.label:
        ui.tooltip('К1 коммутирует БУНЭ напрямую, его команды в CAN нет')

    def update():

        k2.set(CONTACTOR_TEXT.get(puer["cmd.req_mode.k2"], text(puer["cmd.req_mode.k2"])))

    live(box, update)


def render_isolation(parameters, box):

    imd = parameters["imd"]

    plus, minus = render_pairs(['R+', 'R-'])
    voltage = render_kv('U поезда')

    def update():

        # Without the "calculated" flag the values mean nothing
        resistance_ready = imd["resistance_calculated"] == "CALCULATED"
        voltage_ready = imd["bus_voltage_calculated"] == "CALCULATED"

        plus.set(fmt(imd["resistance_plus"], ' кОм') if resistance_ready else '—')
        minus.set(fmt(imd["resistance_minus"], ' кОм') if resistance_ready else '—')
        voltage.set(fmt(imd["bus_voltage"], 'В') if voltage_ready else '—')

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
        return 'ошибка'

    if opened == "ON":
        return 'открыт'

    return 'закрыт' if closed == "ON" else 'движение'


def render_cooling(parameters, box):

    bust_a = parameters["bust_a"]
    bust_b = parameters["bust_b"]

    # Two parts side by side, two lines each. The setpoint comes first,
    # its name over its value, then the feedbacks as "name value":
    #   2/3 БУСТ-А:  Уст 1  Вент 1 x  Вент 3 x  Вент 5 x
    #                x      Вент 2 x  Вент 4 x  Вент 6 x
    #   1/3 БУСТ-Б:  Уст 2  Вент ППН x
    #                x      Шибер    x
    def setpoint(name, hint):
        """
        Name over the value.
        """

        with ui.element('div').classes('cooling-group'):

            with ui.label(name).classes('k'):
                ui.tooltip(hint)

            return Value(ui.label().classes('v'))

    def feedbacks(pairs):
        """
        Two "name value" lines with the names and the values aligned.
        """

        with ui.element('div').classes('cooling-group'):

            for name, hint in pairs:
                with ui.label(name).classes('k'):
                    if hint:
                        ui.tooltip(hint)

            return [Value(ui.label().classes('v')) for _ in pairs]

    with ui.element('div').classes('cooling'):

        with ui.element('div').classes('cooling-part'):

            fan_set = setpoint('Уст 1', 'уставка вентиляторов 1–6 (БУСТ-А)')

            fans = []

            for first in (1, 3, 5):
                fans += feedbacks([(f'Вент {first}', None), (f'Вент {first + 1}', None)])

        with ui.element('div').classes('cooling-part cooling-side'):

            conv_fan_set = setpoint('Уст 2', 'уставка вентилятора преобразователя (БУСТ-Б)')

            conv_fan, shutter = feedbacks([
                ('Вент ППН', 'обратная связь вентилятора преобразователя (БУСТ-Б)'),
                ('Шибер', 'положение шибера по концевикам (БУСТ-Б)'),
            ])

    def update():

        fan_set.set(fmt(bust_a["cmd.fan_set"], '%'))
        conv_fan_set.set(fmt(bust_b["cmd.conv_fan_set"], '%'))
        shutter.set(damper_text(bust_b))

        for i, fan in enumerate(fans, start=1):
            fan.set(fmt(bust_a[f"fan_{i}_fb"], '%'))

        conv_fan.set(fmt(bust_b["conv_fan_fb"], '%'))

    live(box, update)


# mode: (border label, parameters key, columns, unit, color function)
CELLS_MAP_MODES = {
    "voltage": ("напряжение", "cell_voltages", CELL_VOLTAGE_COLUMNS, "В", cell_voltage_color),
    "temperature": ("температура", "cell_temperatures", CELL_TEMPERATURE_COLUMNS, "°C", cell_temperature_color),
}


def temperature_tiles(cc):
    """
    All temperature sensors on the 1-Wire buses that send data, without a
    layout by address: [(id, tooltip name, value), ...]. The bound sensors
    first, in the order of their addresses, then the unbound ones.
    """

    tiles = []

    for place, value in enumerate(cc["cell_temperatures"]):

        if value == NO_DATA:
            continue

        bus, sensor = temperature_sensor(place)
        tiles.append((('bound', place), f'Адрес {bus}.{sensor}', value))

    free = sorted(list(cc["free_temperatures"].items()), key=lambda item: item[0])

    for place, (bus, value) in free:

        name = f'Не привязан, шина {bus}' if bus else 'Не привязан'
        tiles.append((('free', place), name, value))

    return tiles


def tile_text(mode, place, value):
    """
    Text on a tile: the group number for voltages, the value for temperatures.
    """

    if mode == "voltage":
        return str(place)

    if is_number(value):
        return f'{value:.1f}'

    return 'ош' if value == MEASURE_ERROR else '—'


def cells_map_summary(mode, values, sensors=None):
    """
    Border labels with the key figures: [(text, css, colour), ...] per label.
    For voltages the last label counts the groups without data, for
    temperatures it counts the sensors on the buses.
    """

    _, _, _, unit, color = CELLS_MAP_MODES[mode]

    maximum, minimum, no_data = cells_summary(values)

    # Full names, or arrows in a narrow window
    max_key = [('макс ', 'k tab-full'), ('↑', 'k tab-short')]
    min_key = [('мин ', 'k tab-full'), ('↓', 'k tab-short')]

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

    if sensors is None:
        labels.append([
            ('нет данных ', 'k tab-full'),
            ('н/д ', 'k tab-short'),
            (no_data, 'v'),
        ])
    else:
        labels.append([
            ('датчиков ', 'k tab-full'),
            ('дт ', 'k tab-short'),
            (sensors, 'v'),
        ])

    return labels


def render_cells_map(parameters, box):

    cc = parameters["cc"]

    tabs = {}

    with box.left:

        for mode, (label, *_) in CELLS_MAP_MODES.items():

            tabs[mode] = border_tab((label, 'title')).classes('clickable').on(
                'click', lambda e, mode=mode: show(mode)
            )

    with box.right:
        summary = ui.element('div').classes('box-bar-side')

    grid = ui.element('div').classes('cells-map-grid')

    # What is on screen now: tiles and, for temperatures, the ids of the
    # sensors they show
    view = SimpleNamespace(mode=None, tiles=[], summary=None, sensors_shown=None)

    def new_tile():

        with ui.label().classes('cells-map-cell') as tile:
            tooltip = ui.tooltip()

        # tile, tooltip, what they show now
        return [tile, tooltip, None]

    def paint(entry, text, name, value, unit, color):

        if is_number(value):
            shown = (text, color(value), 'lit', f'{name}: {value:g}{unit}')
        else:
            shown = (text, NO_DATA_COLOR, 'off', f'{name}: {VALUE_TEXT.get(value, value)}')

        if shown == entry[2]:
            return

        tile, tooltip, _ = entry
        tile_label, background, lit, tooltip_text = shown

        tile.set_text(tile_label)
        tile.style(f'background: {background};')
        tile.classes(add=lit, remove='off' if lit == 'lit' else 'lit')
        tooltip.set_text(tooltip_text)

        entry[2] = shown

    def set_grid(columns, count):

        rows = max(1, math.ceil(count / columns))
        grid.style(f'--cols: {columns}; --rows: {rows};')

    def show(mode):
        """
        Build the tiles of a mode; their texts and colours come from update().
        """

        _, key, columns, _, _ = CELLS_MAP_MODES[mode]

        for tab_mode, tab in tabs.items():

            if tab_mode == mode:
                tab.classes(add='active')
            else:
                tab.classes(remove='active')

        # The temperature tiles keep the size of the full set of places
        set_grid(columns, len(cc[key]))
        grid.clear()

        view.tiles = []
        view.sensors_shown = None

        if mode == "voltage":

            with grid:
                view.tiles = [new_tile() for _ in cc[key]]

        view.mode = mode
        view.summary = None

        update()

    def update_temperatures(unit, color):
        """
        One tile per sensor that sends data, rebuilt when the set of sensors
        changes. Returns the values of the sensors.
        """

        sensors = temperature_tiles(cc)
        ids = [sensor_id for sensor_id, _, _ in sensors]

        if ids != view.sensors_shown:

            grid.clear()

            set_grid(CELL_TEMPERATURE_COLUMNS, max(len(cc["cell_temperatures"]), len(ids)))

            view.sensors_shown = ids

            with grid:
                view.tiles = [new_tile() for _ in sensors]

        for entry, ((_, place), name, value) in zip(view.tiles, sensors):
            paint(entry, tile_text("temperature", place, value), name, value, unit, color)

        return [value for _, _, value in sensors]

    def update():

        _, key, _, unit, color = CELLS_MAP_MODES[view.mode]

        if view.mode == "temperature":

            values = update_temperatures(unit, color)

            labels = cells_map_summary(view.mode, values, sensors=len(values))

        else:

            values = cc[key]

            for number, (entry, value) in enumerate(zip(view.tiles, values)):
                paint(entry, tile_text(view.mode, number, value), f'Группа {number}', value, unit, color)

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
            (f'  {event.source:<{SOURCE_WIDTH}}  ', 'k'),
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
