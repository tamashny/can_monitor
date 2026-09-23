from nicegui import ui

COMMANDS = [
    '/restart',
    '/close contactors',
    '/open contactors',
    '/status',
    '/shutdown',
    '/reset',
    '/start cooling',
    '/stop cooling',
]


def build_command_line():

    # =================================================
    # CLICK-OUTSIDE OVERLAY
    # =================================================

    click_outside_overlay = ui.element('div').style(
        '''
        position: fixed;
        inset: 0;

        display: none;

        z-index: 999;
        '''
    )

    # =================================================
    # COMMAND LINE CONTAINER
    # =================================================

    with ui.element('div').style(
        '''
        position: relative;
        width: calc(100% - 20px);

        z-index: 1000;
        '''
    ):

        # =================================================
        # COMMAND LIST
        # =================================================

        with ui.element('div').style(
            '''
            position: absolute;

            left: 0;
            right: 0;

            bottom: 100%;

            width: 100%;

            height: 144px;

            display: none;

            background: #1C1C1C;

            border: none;
            border-radius: 10px 10px 0 0;

            box-sizing: border-box;
            overflow: hidden;

            z-index: 1000;
            '''
        ) as command_list:

            with ui.element('div').classes(
                'command-list'
            ).style(
                '''
                width: 100%;
                height: 100%;

                overflow-y: auto;
                overflow-x: hidden;
                '''
            ):

                for command in COMMANDS:

                    ui.button(
                        command
                    ).props(
                        'flat dense'
                    ).classes(
                        'w-full justify-start'
                    ).on(
                        'click',
                        lambda e, command=command:
                            command_input.set_value(command)
                    )

        # =================================================
        # COMMAND INPUT
        # =================================================

        command_input = ui.input(
            placeholder='/Command line...'
        ).props(
            'borderless dense'
        ).classes(
            'w-full command-input'
        )

        # =================================================
        # OPEN COMMAND LIST
        # =================================================

        def open_commands():
            command_list.style(
                '''
                display: block;
                '''
            )

            command_input.classes(
                add='command-input-open'
            )

            click_outside_overlay.style(
                '''
                display: block;
                '''
            )

        # =================================================
        # CLOSE COMMAND LIST
        # =================================================

        def close_commands():
            command_list.style(
                '''
                display: none;
                '''
            )

            command_input.classes(
                remove='command-input-open'
            )

            click_outside_overlay.style(
                '''
                display: none;
                '''
            )

            command_input.set_value('')

            command_input.run_method(
                'blur'
            )

        # =================================================
        # OPEN ON FOCUS
        # =================================================

        command_input.on(
            'focus',
            lambda e: open_commands()
        )

        # =================================================
        # CLICK OUTSIDE — CLOSE COMMAND LINE
        # =================================================

        click_outside_overlay.on(
            'click',
            lambda e: close_commands()
        )

        # =================================================
        # ESC — CLOSE COMMAND LINE (even while typing)
        # =================================================

        def handle_key(e):
            if e.action.keydown and e.key == 'Escape':
                close_commands()

        ui.keyboard(
            on_key=handle_key,
            ignore=[]
        )
