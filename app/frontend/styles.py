from nicegui import ui

THEME_CSS = '''
/* =====================================================
   THEME VARIABLES
   ===================================================== */

:root {
    --bg-color: #0C0C0C;
    --fg-color: #FFFFFF;
    --border-color: #7C7C7C;
    --panel-bg: #1C1C1C;
    --placeholder-color: #888888;
    --segment-off-color: #444444;
    --scrollbar-thumb: #555555;
    --scrollbar-thumb-hover: #707070;
}

body.theme-light {
    --bg-color: #F2F2F2;
    --fg-color: #111111;
    --border-color: #A0A0A0;
    --panel-bg: #E2E2E2;
    --placeholder-color: #666666;
    --segment-off-color: #CCCCCC;
    --scrollbar-thumb: #B0B0B0;
    --scrollbar-thumb-hover: #909090;
}
'''

COMMAND_LINE_CSS = '''
/* =====================================================
   COMMAND LIST SCROLLBAR
   ===================================================== */

.command-list {
    scrollbar-width: auto;
    scrollbar-color: var(--scrollbar-thumb) var(--panel-bg);
}

/* Chrome / Edge / Chromium */

.command-list::-webkit-scrollbar {
    width: 16px;
}

.command-list::-webkit-scrollbar-track {
    background: var(--panel-bg);
}

.command-list::-webkit-scrollbar-thumb {
    background: var(--scrollbar-thumb);
    border-radius: 5px;
}

.command-list::-webkit-scrollbar-thumb:hover {
    background: var(--scrollbar-thumb-hover);
}

/* Убираем стрелки scrollbar */

.command-list::-webkit-scrollbar-button {
    display: none;
    width: 0;
    height: 0;
}


/* =====================================================
   COMMAND BUTTONS
   ===================================================== */

.command-list .q-btn {
    justify-content: flex-start !important;
    text-align: left !important;

    color: var(--fg-color) !important;

    font-family: "DejaVu Sans Mono", monospace !important;
    font-size: 16px !important;
    line-height: 1.5 !important;

    text-transform: none !important;

    width: 100% !important;

    height: 27px !important;
    min-height: 27px !important;

    padding: 0 8px !important;

    border-radius: 0 !important;
}

.command-list .q-btn__content {
    justify-content: flex-start !important;
    text-align: left !important;

    width: 100% !important;

    color: var(--fg-color) !important;
}


/* =====================================================
   COMMAND INPUT
   ===================================================== */

.command-input {
    background: var(--panel-bg) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

.command-input.command-input-open {
    border-radius: 0 0 10px 10px !important;
}

.command-input .q-field__control {
    background: transparent !important;

    padding: 0 16px !important;

    border: none !important;
    box-shadow: none !important;
}

.command-input .q-field__control:before,
.command-input .q-field__control:after {
    border: none !important;
    box-shadow: none !important;
}

.command-input.q-field--focused .q-field__control:before,
.command-input.q-field--focused .q-field__control:after {
    border: none !important;
    box-shadow: none !important;
}

.command-input input,
.command-input .q-field__native {
    color: var(--fg-color) !important;
    caret-color: var(--fg-color) !important;

    font-family: "DejaVu Sans Mono", monospace !important;
    font-size: 16px !important;

    text-transform: none !important;
}

.command-input input::placeholder,
.command-input .q-field__native::placeholder {
    color: var(--placeholder-color) !important;
    opacity: 1 !important;
}
'''


def apply_global_styles():

    # removing space around page
    ui.query('.nicegui-content').style(
        'padding: 0; margin: 0;'
    )

    ui.query('body').style(
        '''
        background: var(--bg-color);
        color: var(--fg-color);
        font-family: "DejaVu Sans Mono", monospace;
        font-size: 16px;
        line-height: 1.5;
        '''
    )

    ui.add_css(THEME_CSS + COMMAND_LINE_CSS)
