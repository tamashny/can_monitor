"""Event log shared by all dashboard pages.

A watcher compares PARAMETERS with the previous snapshot and logs every
change of a non-numeric value: states, codes, flags, commands of БУНЭ,
data appearing or disappearing. Plain numbers going up and down and the
cell arrays are not logged. Commands typed in the command line are logged
too.
"""

import itertools
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from nicegui import app

from parameters import DEVICES, NO_DATA
from settings import EVENT_LOG_SIZE, EVENT_WATCH_INTERVAL

from .colors import DIM, HI, RED, YELLOW, event_color
from .helpers import fmt, is_number


@dataclass
class Event:
    seq: int        # increasing number, pages use it to find new entries
    time: str
    source: str
    parts: list     # [(text, css class[, colour]), ...]


EVENTS = deque(maxlen=EVENT_LOG_SIZE)

_next_seq = itertools.count(1)

# Names of the PARAMETERS sections in the log
SOURCES = {key: name for key, name, *_ in DEVICES}
SOURCES["bus"] = "адаптер"

# Width of the source column: the longest name, the gap is added on display
SOURCE_WIDTH = max(len(name) for name in [*SOURCES.values(), "система", "команда"])


def log_event(source, parts):

    EVENTS.append(
        Event(
            seq=next(_next_seq),
            time=datetime.now().strftime('%H:%M:%S'),
            source=source,
            parts=parts,
        )
    )


def log_command(command, result, ok):
    """
    Typed command and what happened with it (canbus/commands.py).
    """

    log_event('команда', [
        (command, 'v', HI),
        ('  ', ''),
        (result, 'v', None if ok else RED),
    ])


def log_emcy(device, values):
    """
    Event frame (EMCY) of a device. КК names its codes and sends EVENT_UP /
    EVENT_DOWN, the others send a number and the event flags.
    """

    code = values.get("eec")
    name = f'0x{code:04X}' if is_number(code) else str(code)

    if "event" in values:
        appeared = values["event"] == "EVENT_UP"
        warning = name.endswith("_W")
    else:
        appeared = values.get("event_flags.appeared") == "ON"
        warning = values.get("event_flags.is_fault") != "ON"

    color = DIM if not appeared else YELLOW if warning else RED

    parts = [
        ('EMCY ', 'k'),
        (name, 'v', color),
        (' возникло' if appeared else ' снято', 'dim'),
    ]

    number = values.get("object")

    if is_number(number) and number:
        parts.append((f' объект {number:g}', 'dim'))

    log_event(SOURCES.get(device, device), parts)


def show(value):

    return value if isinstance(value, str) else fmt(value)


def snapshot(parameters):

    return {
        (device, key): value
        for device, values in parameters.items()
        for key, value in values.items()
        if not isinstance(value, (list, dict))
    }


def start_event_watcher(parameters):

    previous = snapshot(parameters)

    def check():

        nonlocal previous

        current = snapshot(parameters)

        for (device, key), value in current.items():

            old = previous.get((device, key))

            if value == old or (is_number(value) and is_number(old)):
                continue

            # A lost device clears all its values at once: the log gets one
            # line about its health instead of a line per value
            if device != "bus" and NO_DATA in (value, old):
                continue

            log_event(
                SOURCES.get(device, device),
                [
                    (f'{key} ', 'k'),
                    (show(old), 'dim'),
                    (' → ', 'dim'),
                    (show(value), 'v', event_color(value)),
                ],
            )

        previous = current

    log_event('система', [('панель запущена', 'dim', DIM)])

    app.timer(EVENT_WATCH_INTERVAL, check)
