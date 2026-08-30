from nicegui import ui
from app.can_reader import CanReader
from app.protocol import decode

import json
import time


# ---------- Настройки ----------

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

can_config = config["can"]

reader = None

try:
    reader = CanReader(
        port=can_config["port"],
        bitrate=can_config["can_bitrate"]
    )
except Exception as e:
    print(f"CAN: {e}")


# ---------- Текущее состояние ----------

last_frames = {}
values = {}

rx_count = 0
last_rx_time = None


# ---------- Цвета состояний ----------

STATUS_TEXT = {
    0: "OK",
    1: "WARNING",
    2: "ALARM",
}


# ---------- Интерфейс ----------

ui.dark_mode().enable()

ui.add_head_html("""
<style>

body {
    background: #101010;
    color: #dddddd;
    font-family: Consolas, monospace;
}

.monitor {
    max-width: 1400px;
    margin: auto;
}

.title {
    font-size: 22px;
    font-weight: bold;
}

.section {
    color: #888888;
    margin-top: 20px;
    margin-bottom: 5px;
}

.value {
    font-size: 32px;
    font-weight: bold;
}

.status-ok {
    color: #00ff66;
}

.status-warning {
    color: #ffff00;
}

.status-alarm {
    color: #ff4444;
}

.status-unknown {
    color: #888888;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    color: #888888;
    text-align: left;
    border-bottom: 1px solid #444;
    padding: 5px;
}

td {
    padding: 5px;
    border-bottom: 1px solid #222;
}

</style>
""")


with ui.column().classes("monitor w-full"):

    # ---------- Заголовок ----------

    with ui.row().classes("w-full items-center justify-between"):

        ui.label("ENERGY STORAGE MONITOR").classes("title")

        connection_label = ui.label("CAN: NO DATA")


    # ---------- Основные значения ----------

    ui.label("ELECTRICAL").classes("section")

    with ui.row().classes("w-full"):

        with ui.column().classes("w-1/3"):
            ui.label("VOLTAGE")
            voltage_label = ui.label("--.- V").classes("value")

        with ui.column().classes("w-1/3"):
            ui.label("CURRENT")
            current_label = ui.label("--.- A").classes("value")

        with ui.column().classes("w-1/3"):
            ui.label("POWER")
            power_label = ui.label("--.- kW").classes("value")


    # ---------- Состояния ----------

    ui.label("SYSTEM STATUS").classes("section")

    with ui.row().classes("w-full"):

        with ui.column().classes("w-1/5"):
            ui.label("НЭ")
            ne_label = ui.label("--")

        with ui.column().classes("w-1/5"):
            ui.label("INSULATION")
            insulation_label = ui.label("--")

        with ui.column().classes("w-1/5"):
            ui.label("CELL CONTROLLER")
            cell_controller_label = ui.label("--")

        with ui.column().classes("w-1/5"):
            ui.label("CONVERTER")
            converter_label = ui.label("--")

        with ui.column().classes("w-1/5"):
            ui.label("COOLING")
            cooling_label = ui.label("--")


    # ---------- CAN Monitor ----------

    ui.label("CAN BUS 1").classes("section")

    with ui.row().classes("w-full items-center"):

        rx_label = ui.label("RX: 0")
        last_rx_label = ui.label("LAST: --")


    with ui.element("table"):

        with ui.element("thead"):
            with ui.element("tr"):
                ui.element("th").text = "ID"
                ui.element("th").text = "DLC"
                ui.element("th").text = "DATA"

        table_body = ui.element("tbody")


# ---------- Обновление таблицы ----------

def update_can_table():
    table_body.clear()

    # Показываем последние известные кадры каждого ID
    for message_id, frame in sorted(last_frames.items()):

        with table_body:

            with ui.element("tr"):

                ui.element("td").text = f"0x{message_id:03X}"

                ui.element("td").text = str(len(frame))

                ui.element("td").text = frame.hex(" ")


# ---------- Обновление интерфейса ----------

def update():

    global rx_count
    global last_rx_time

    if reader is None:
        connection_label.text = "CAN: DISCONNECTED"
        return

    try:
        frame = reader.read()

        if frame is not None:

            rx_count += 1
            last_rx_time = time.time()

            message_id = frame["id"]
            data = frame["data"]

            # Запоминаем последний кадр каждого CAN ID
            last_frames[message_id] = data

            # Передаём кадр в декодер
            decoded = decode(frame)

            if decoded is not None:
                values.update(decoded)

            # ---------- Электрические параметры ----------

            if "voltage" in values:
                voltage_label.text = f"{values['voltage']:.1f} V"

            if "current" in values:
                current_label.text = f"{values['current']:.1f} A"

            if "voltage" in values and "current" in values:
                power = values["voltage"] * values["current"] / 1000
                power_label.text = f"{power:.1f} kW"


            # ---------- Состояния ----------

            if "ne" in values:
                ne_label.text = STATUS_TEXT.get(values["ne"], "?")

            if "insulation" in values:
                insulation_label.text = STATUS_TEXT.get(
                    values["insulation"], "?"
                )

            if "cell_controller" in values:
                cell_controller_label.text = STATUS_TEXT.get(
                    values["cell_controller"], "?"
                )

            if "converter" in values:
                converter_label.text = STATUS_TEXT.get(
                    values["converter"], "?"
                )

            if "cooling" in values:
                cooling_label.text = STATUS_TEXT.get(
                    values["cooling"], "?"
                )


            # ---------- CAN ----------

            rx_label.text = f"RX: {rx_count}"

            last_rx_label.text = (
                f"LAST: 0x{message_id:03X}"
            )

            connection_label.text = "CAN: CONNECTED"

            update_can_table()

    except Exception as e:
        connection_label.text = f"CAN: ERROR"


# Обновляем интерфейс 10 раз в секунду
ui.timer(0.1, update)


ui.run(
    title="Energy Storage Monitor",
    host="0.0.0.0",
    port=8080
)