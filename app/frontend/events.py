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

from parameters import DEVICES
from settings import EVENT_LOG_SIZE, EVENT_WATCH_INTERVAL

from .colors import DIM, HI, event_color
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
SOURCES["bune"] = "control"


def log_event(source, parts):

    EVENTS.append(
        Event(
            seq=next(_next_seq),
            time=datetime.now().strftime('%H:%M:%S'),
            source=source,
            parts=parts,
        )
    )


def log_command(command):

    # Sending to the CAN bus is not implemented yet, the command is only logged
    log_event('cmd', [(command, 'v', HI)])


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

    log_event('system', [('dashboard started', 'dim', DIM)])

    app.timer(EVENT_WATCH_INTERVAL, check)
