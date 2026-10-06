"""CAN monitor dashboard.

    python app/main.py              read the bus from the SLCAN adapter
                                    (port and bitrate in config/settings.yaml)
    python app/main.py --port COM5  same, another serial port
    python app/main.py --debug      no adapter: every value is imitated
"""

import argparse
import sys
from pathlib import Path

# Make the app packages importable regardless of how this file is invoked
# (direct script execution, `python -m`, or NiceGUI's reload subprocess,
# which each populate sys.path differently).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nicegui import ui

from canbus.reader import start_reader
from frontend.cells import render_box
from frontend.events import start_event_watcher
from frontend.layout import build_grid_template, load_pattern
from frontend.styles import apply_global_styles
from parameters import PARAMETERS
from settings import CAN_PORT, DASHBOARD_PORT, DASHBOARD_REFRESH_INTERVAL, PATTERN_FILE
from simulation.simulator import start_simulator


def parse_arguments():

    parser = argparse.ArgumentParser(description="CAN monitor dashboard")

    parser.add_argument(
        "--debug",
        action="store_true",
        help="imitate a working system instead of reading the CAN adapter",
    )
    parser.add_argument(
        "--port",
        default=CAN_PORT,
        help=f"serial port of the SLCAN adapter (default: {CAN_PORT})",
    )

    # NiceGUI's reload process may add arguments of its own
    arguments, _ = parser.parse_known_args()

    return arguments


def build_dashboard(pattern, parameters, debug=False):

    apply_global_styles()

    grid_columns, grid_rows, grid_areas = build_grid_template(pattern["layout"])
    cells = pattern["cells"]

    # Widgets register here the functions that redraw their values
    updates = []

    with ui.element('div').classes(
        'w-full h-dvh grid'
    ).style(
        f'''
        grid-template-columns: {grid_columns};
        grid-template-rows: {grid_rows};
        grid-template-areas: {grid_areas};

        gap: 14px 6px;
        padding: 12px 6px 6px;
        box-sizing: border-box;
        '''
    ):

        for number, (name, cell) in enumerate(cells.items(), start=1):
            render_box(
                name, cell, cell.get("number", number), parameters, updates, debug,
            )

    def refresh():
        for update in updates:
            update()

    ui.timer(DASHBOARD_REFRESH_INTERVAL, refresh)


def main():

    arguments = parse_arguments()
    pattern = load_pattern(PATTERN_FILE)

    if arguments.debug:
        start_simulator(PARAMETERS)
    else:
        start_reader(PARAMETERS, arguments.port)

    # Logs state changes in PARAMETERS for the event log
    start_event_watcher(PARAMETERS)

    @ui.page('/')
    def index():
        build_dashboard(pattern, PARAMETERS, arguments.debug)

    ui.run(port=DASHBOARD_PORT, title="CAN monitor")


if __name__ in {"__main__", "__mp_main__"}:
    main()
