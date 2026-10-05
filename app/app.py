import sys
from pathlib import Path

# Make the `frontend` package importable regardless of how this file is
# invoked (direct script execution, `python -m`, or NiceGUI's reload
# subprocess, which each populate sys.path differently).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nicegui import ui

from frontend.cells import render_box
from frontend.config import DASHBOARD_REFRESH_INTERVAL
from frontend.events import start_event_watcher
from frontend.layout import build_grid_template, load_pattern
from frontend.parameters import PARAMETERS
from frontend.styles import apply_global_styles
from simulator import start_simulator

PATTERN_FILE = Path(__file__).resolve().parent.parent / "pattern.yaml"

# python app/app.py --debug: every parameter imitates a working system
DEBUG = "--debug" in sys.argv


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

    pattern = load_pattern(PATTERN_FILE)

    if DEBUG:
        start_simulator(PARAMETERS)

    # Logs state changes in PARAMETERS for the event log
    start_event_watcher(PARAMETERS)

    @ui.page('/')
    def index():
        build_dashboard(pattern, PARAMETERS, DEBUG)

    ui.run()


if __name__ in {"__main__", "__mp_main__"}:
    main()
