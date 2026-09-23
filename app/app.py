from pathlib import Path

from nicegui import ui

from .cells import cell_style, render_cell
from .layout import build_grid_template, load_pattern
from .parameters import PARAMETERS
from .styles import apply_global_styles

PATTERN_FILE = Path(__file__).resolve().parent.parent / "pattern.yaml"


def build_dashboard(pattern, parameters):

    apply_global_styles()

    grid_columns, grid_rows, grid_areas = build_grid_template(pattern["layout"])
    cells = pattern["cells"]

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

            with ui.element('div').style(cell_style(name, cell)):
                render_cell(cell, parameters)


def main():

    pattern = load_pattern(PATTERN_FILE)

    @ui.page('/')
    def index():
        build_dashboard(pattern, PARAMETERS)

    ui.run()
