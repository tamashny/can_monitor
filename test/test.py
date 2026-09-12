from nicegui import ui

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
# GRID
# =================================================

with ui.element('div').classes(
    'w-full h-dvh p-2 '
    'grid grid-cols-[1fr_2fr_1fr] '
    'grid-rows-[1fr_2fr_1fr] '
    'gap-2'
):

    # -------------------------------------------------
    # CELL 1
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 1')


    # -------------------------------------------------
    # CELL 2
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 2')


    # -------------------------------------------------
    # CELL 3
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 3')


    # =================================================
    # SPECIAL CELL
    # =================================================

    with ui.element('div').classes(
        'border border-cyan-400 rounded-md p-2'
    ):

        # -------------------------------------------------
        # LINE 1
        # -------------------------------------------------

        with ui.element('div').classes(
            'flex items-center w-full'
        ):

            ui.label('square blue').style(
                'color: #6fa8ff; font-size: 18px;'
            )

            ui.element('div').classes(
                'ml-auto w-3 h-3'
            ).style(
                'background: #6fa8ff;'
            )


        # -------------------------------------------------
        # LINE 2
        # -------------------------------------------------

        with ui.element('div').classes(
            'flex items-center w-full'
        ):

            ui.label('square red').style(
                'color: #ff6b7a; font-size: 20px;'
            )

            ui.element('div').classes(
                'ml-auto w-3 h-3'
            ).style(
                'background: #ff6b7a;'
            )


        # -------------------------------------------------
        # LINE 3
        # -------------------------------------------------

        with ui.element('div').classes(
            'flex items-center w-full'
        ):

            ui.label('dot green').style(
                'color: #7fd36b; font-size: 16px;'
            )

            ui.element('div').classes(
                'ml-auto w-3 h-3 rounded-full'
            ).style(
                'background: #7fd36b;'
            )


    # -------------------------------------------------
    # CELL 5
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 5')


    # -------------------------------------------------
    # CELL 6
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 6')


    # -------------------------------------------------
    # CELL 7
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 7')


    # -------------------------------------------------
    # CELL 8
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 8')


    # -------------------------------------------------
    # CELL 9
    # -------------------------------------------------

    with ui.element('div').classes(
        'border border-slate-500 rounded-md p-2'
    ):
        ui.label('CELL 9')


ui.run()