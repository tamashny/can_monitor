import can
import protocol

from nicegui import ui


# Connect to CAN interface
bus = can.Bus(
    interface="socketcan",
    channel="vcan0"
)


# Current values of all known parameters
parameters = {}


ui.label("CAN Dashboard").classes("text-2xl")

value_label = ui.label(
    "Waiting for CAN data..."
).classes("text-3xl")


def read_can():

    frame = bus.recv(timeout=0.1)

    if frame is None:
        return

    decoded = protocol.decode(frame)

    if not decoded:
        return

    # Update current parameter values
    parameters.update(decoded)

    print(parameters)

    value_label.text = str(parameters)


ui.timer(0.1, read_can)


ui.run(
    host="0.0.0.0",
    port=8080
)


