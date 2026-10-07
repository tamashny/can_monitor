from nicegui import ui

from .colors import BG, DIM, FG, HI, METER_BG, SELECTED_BG, TITLE

THEME_CSS = f'''
/* =====================================================
   THEME VARIABLES (btop-like, dark only)
   ===================================================== */

:root {{
    --bg: {BG};
    --fg: {FG};
    --title: {TITLE};
    --dim: {DIM};
    --hi: {HI};
    --selected-bg: {SELECTED_BG};
    --meter-bg: {METER_BG};
    --div-line: #303030;

    --mono: "DejaVu Sans Mono", Consolas, "Cascadia Mono", monospace;
}}
'''

BOX_CSS = '''
/* =====================================================
   BOXES
   ===================================================== */

/* Every dashboard cell is a box with a thin border, --box is its colour */
.box {
    position: relative;

    display: flex;
    flex-direction: column;
    gap: 2px;

    min-width: 0;
    min-height: 0;

    padding: 12px 12px 8px;

    border: 1px solid var(--box);
    border-radius: 6px;

    box-sizing: border-box;
}

/* Labels that sit on the top border line: ┐¹title┌ */
.box-bar {
    position: absolute;

    top: calc(-0.5em - 0.5px);
    left: 10px;
    right: 10px;

    display: flex;
    justify-content: space-between;

    line-height: 1;
    white-space: pre;

    pointer-events: none;
}

.box-bar-side {
    display: flex;
    gap: 1ch;
}

.box-tab {
    background: var(--bg);
    color: var(--fg);

    pointer-events: auto;
}

.box-tab .tick {
    color: var(--box);
}

.box-tab .num {
    color: var(--hi);
}

.box-tab .title {
    color: var(--title);
    font-weight: bold;
}

.box-tab.clickable {
    cursor: pointer;
}

.box-tab.clickable:not(.active) .title {
    color: var(--dim);
    font-weight: normal;
}

.box-tab.clickable:hover .title {
    color: var(--title);
}


/* =====================================================
   TEXT
   ===================================================== */

.kv {
    display: flex;
    justify-content: space-between;
    gap: 1ch;

    min-width: 0;
    overflow: hidden;

    white-space: nowrap;
}

.k {
    color: var(--fg);
}

.v {
    color: var(--title);
}

.dim {
    color: var(--dim);
}

.th {
    color: var(--title);
    font-weight: bold;
}


/* =====================================================
   METERS: row of blocks like btop's ■■■■■■
   ===================================================== */

.meter {
    display: flex;
    align-items: center;
    gap: 2px;

    height: 1.4em;
}

.meter-seg {
    flex: 1 1 0;
    min-width: 0;
    height: 0.7em;
}


/* =====================================================
   TABLE
   ===================================================== */

.table {
    display: grid;
    column-gap: 2ch;

    white-space: nowrap;
}

/* Header row stays on top while the rows scroll */
.sticky-head .th {
    position: sticky;
    top: 0;

    background: var(--bg);
}


/* =====================================================
   SCROLLING LISTS
   ===================================================== */

/* Takes the free space of the box without growing it:
   the scrolling child is positioned absolutely */
.scroll-area {
    position: relative;

    flex: 1;
    min-height: 0;
}

.scroll,
.log-lines {
    position: absolute;
    inset: 0;

    overflow-y: auto;
    overflow-x: hidden;

    scrollbar-width: thin;
    scrollbar-color: var(--meter-bg) transparent;
}


/* =====================================================
   EVENT LOG
   ===================================================== */

/* Newest row is the first child and is drawn at the bottom */
.log-lines {
    display: flex;
    flex-direction: column-reverse;
}

.log-line {
    flex: none;

    white-space: pre;
    overflow: hidden;
    text-overflow: ellipsis;
}

.log-input {
    margin-top: 4px;
    padding-top: 4px;

    border-top: 1px solid var(--div-line);
}


/* =====================================================
   TOOLTIP
   ===================================================== */

.q-tooltip {
    background: var(--bg) !important;
    color: var(--title) !important;

    border: 1px solid var(--dim);
    border-radius: 0 !important;

    font-family: var(--mono) !important;
    font-size: 14px !important;

    padding: 2px 8px !important;
}
'''

COMMAND_LINE_CSS = '''
/* =====================================================
   COMMAND LINE
   ===================================================== */

.command-line {
    position: relative;

    display: flex;
    align-items: center;
    gap: 1ch;

    width: 100%;

    z-index: 1000;
}

.command-prompt {
    color: var(--hi);
    font-weight: bold;
}

.command-popup {
    position: absolute;

    /* pops up above the input, over the log */
    left: 0;
    bottom: calc(100% + 9px);

    width: min(480px, 100%);
    max-height: 216px;

    display: none;

    background: var(--bg);

    border: 1px solid var(--box);
    border-radius: 6px;

    box-sizing: border-box;
    overflow: hidden;

    z-index: 1000;
}

.command-list {
    width: 100%;
    max-height: 214px;

    overflow-y: auto;
    overflow-x: hidden;

    scrollbar-width: thin;
    scrollbar-color: var(--meter-bg) var(--bg);
}

.command-list .q-btn {
    justify-content: flex-start !important;

    width: 100% !important;
    height: 26px !important;
    min-height: 26px !important;

    padding: 0 12px !important;

    color: var(--fg) !important;

    font-family: var(--mono) !important;
    font-size: 15px !important;
    text-transform: none !important;

    border-radius: 0 !important;
}

.command-list .q-btn .q-focus-helper {
    display: none !important;
}

.command-list .q-btn:hover {
    background: var(--selected-bg) !important;
    color: var(--title) !important;
}

.command-list .q-btn__content {
    justify-content: flex-start !important;
    width: 100% !important;
}

.command-input {
    flex: 1;
}

.command-input .q-field__control,
.command-input .q-field__native {
    min-height: 1.4em !important;
    height: 1.4em !important;
    padding: 0 !important;
}

.command-input .q-field__control:before,
.command-input .q-field__control:after {
    display: none !important;
}

.command-input input {
    color: var(--title) !important;
    caret-color: var(--title) !important;

    font-family: var(--mono) !important;
    font-size: 15px !important;
}

.command-input input::placeholder {
    color: var(--dim) !important;
    opacity: 1 !important;
}
'''

CELLS_MAP_CSS = '''
/* =====================================================
   CELLS MAP
   ===================================================== */

/* Grid stretches over the whole box */
.cells-map-grid {
    flex: 1;
    min-height: 0;

    display: grid;
    grid-template-columns: repeat(var(--cols), 1fr);
    grid-template-rows: repeat(var(--rows), 1fr);
    gap: 3px;

    margin-top: 4px;
}

/* Same look as the meter segments: no border, no rounding.
   The cell number sits in the middle. */
.cells-map-cell {
    display: flex;
    align-items: center;
    justify-content: center;

    min-width: 0;
    min-height: 0;
    overflow: hidden;

    font-size: 12px;
    line-height: 1;
}

.cells-map-cell.lit {
    color: rgba(0, 0, 0, 0.6);
}

.cells-map-cell.off {
    color: rgba(255, 255, 255, 0.3);
}

.cells-map-cell:hover {
    outline: 1px solid var(--title);
    outline-offset: -1px;
}
'''


def apply_global_styles():

    # removing space around page
    ui.query('.nicegui-content').style(
        'padding: 0; margin: 0;'
    )

    ui.query('body').style(
        '''
        background: var(--bg);
        color: var(--fg);
        font-family: var(--mono);
        font-size: 15px;
        line-height: 1.4;
        overflow: hidden;
        '''
    )

    ui.add_css(THEME_CSS + BOX_CSS + COMMAND_LINE_CSS + CELLS_MAP_CSS)
