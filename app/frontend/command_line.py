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


def build_command_line(on_command=None):
    """
    Command input with a pop-up list of commands.
    Enter passes the typed text to on_command(text).
    """

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

    with ui.element('div').classes('command-line'):

        # =================================================
        # COMMAND LIST (pops up above the input)
        # =================================================

        with ui.element('div').classes('command-popup') as command_popup:

            with ui.element('div').classes('command-list'):

                for command in COMMANDS:

                    ui.button(
                        command,
                        color=None,
                    ).props(
                        'flat dense no-caps'
                    ).on(
                        'click',
                        lambda e, command=command:
                            command_input.set_value(command)
                    )

        # =================================================
        # COMMAND INPUT
        # =================================================

        ui.label('>').classes('command-prompt')

        command_input = ui.input(
            placeholder='/command line...'
        ).props(
            'borderless dense'
        ).classes(
            'command-input'
        )

        # =================================================
        # OPEN COMMAND LIST
        # =================================================

        def open_commands():
            command_popup.style('display: block;')
            click_outside_overlay.style('display: block;')

        # =================================================
        # CLOSE COMMAND LIST
        # =================================================

        def close_commands():
            command_popup.style('display: none;')
            click_outside_overlay.style('display: none;')

            command_input.set_value('')

            command_input.run_method(
                'blur'
            )

        # =================================================
        # ENTER — SEND COMMAND
        # =================================================

        def submit():
            command = (command_input.value or '').strip()

            if command and on_command:
                on_command(command)

            close_commands()

        command_input.on(
            'keydown.enter',
            lambda e: submit()
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
