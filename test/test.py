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
    background: #050a10;
    color: #d0d8e0;
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 16px;
    '''
)

# =================================================
# GRID SETTINGS
# =================================================

if isinstance(columns, list):
    grid_columns = " ".join(
        f"{value}fr"
        for value in columns
    )
else:
    grid_columns = " ".join(
        ["1fr"] * columns
    )

if isinstance(rows, list):
    grid_rows = " ".join(
        f"{value}fr"
        for value in rows
    )
else:
    grid_rows = " ".join(
        ["1fr"] * rows
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

        with ui.element('div').style(
            f'''
            grid-area: {name};

            border: 1px solid #64748b;
            border-radius: 6px;
            padding: 8px;
            '''
        ):
            ui.label(cell["title"])

ui.run()

    # # -------------------------------------------------
    # # CELL 1
    # # -------------------------------------------------

    # with ui.element('div').classes(
    #     'border border-slate-500 rounded-md p-2'
    # ):
    #     ui.label('CELL 1')

    # # =================================================
    # # SPECIAL CELL
    # # =================================================

    # with ui.element('div').classes(
    #     'border border-cyan-400 rounded-md p-2'
    # ):

    #     # -------------------------------------------------
    #     # LINE 1
    #     # -------------------------------------------------

    #     with ui.element('div').classes(
    #         'flex items-center w-full'
    #     ):

    #         ui.label('square blue').style(
    #             'color: #6fa8ff; font-size: 18px;'
    #         )

    #         ui.element('div').classes(
    #             'ml-auto w-3 h-3'
    #         ).style(
    #             'background: #6fa8ff;'
    #         )


    #     # -------------------------------------------------
    #     # LINE 2
    #     # -------------------------------------------------

    #     with ui.element('div').classes(
    #         'flex items-center w-full'
    #     ):

    #         ui.label('square red').style(
    #             'color: #ff6b7a; font-size: 20px;'
    #         )

    #         ui.element('div').classes(
    #             'ml-auto w-3 h-3'
    #         ).style(
    #             'background: #ff6b7a;'
    #         )


    #     # -------------------------------------------------
    #     # LINE 3
    #     # -------------------------------------------------

    #     with ui.element('div').classes(
    #         'flex items-center w-full'
    #     ):

    #         ui.label('dot green').style(
    #             'color: #7fd36b; font-size: 16px;'
    #         )

    #         ui.element('div').classes(
    #             'ml-auto w-3 h-3 rounded-full'
    #         ).style(
    #             'background: #7fd36b;'
    #         )