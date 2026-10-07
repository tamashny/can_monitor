"""Operator commands of the command line.

Two kinds:

- built-in commands of the dashboard, they do not send CAN frames:
    /ports                      list the serial (COM) ports in the event log
    /connect <port> [bitrate]   open the SLCAN adapter on the port,
                                bitrate of the CAN bus in bit/s (or 500k)
    /disconnect                 close the adapter

- commands from config/commands.yaml. Such a command has a name, a
  description, the CAN ID of its frame and the values of the frame
  parameters; the byte layout of the frame is described in
  config/canmap.yaml. None are defined yet, and sending frames is not
  implemented.

execute() returns (ok, message) for the event log.
"""

import yaml
from serial.tools import list_ports

from settings import CAN_BITRATE, COMMANDS_FILE

from . import reader


def load_commands():

    with open(COMMANDS_FILE, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    return data.get("commands") or []


COMMANDS = load_commands()


# =================================================
# SERIAL PORTS
# =================================================

def serial_ports():
    """
    Active serial ports: [(device, description), ...]
    """

    return [
        (port.device, port.description)
        for port in sorted(list_ports.comports(), key=lambda port: port.device)
    ]


def parse_bitrate(text):
    """
    "500000" or "500k" -> 500000, None when it is not a number.
    """

    text = text.lower()
    factor = 1

    if text.endswith("k"):
        text, factor = text[:-1], 1000

    try:
        return round(float(text) * factor)
    except ValueError:
        return None


# =================================================
# BUILT-IN COMMANDS
# =================================================

def ports_command(arguments):

    ports = serial_ports()

    if not ports:
        return False, "no serial ports found"

    return True, "  ".join(f"{device} ({description})" for device, description in ports)


def connect_command(arguments):

    if reader.READER is None:
        return False, "no adapter in --debug mode"

    if not arguments:
        return False, "usage: /connect <port> [bitrate]"

    port = arguments[0]
    bitrate = reader.READER.bitrate

    if len(arguments) > 1:

        bitrate = parse_bitrate(arguments[1])

        if bitrate not in reader.SLCAN_BITRATES:
            rates = ", ".join(str(rate) for rate in reader.SLCAN_BITRATES)
            return False, f"bitrate must be one of: {rates}"

    reader.READER.connect(port, bitrate)

    return True, f"connecting to {port} at {bitrate // 1000} kbit/s"


def disconnect_command(arguments):

    if reader.READER is None:
        return False, "no adapter in --debug mode"

    reader.READER.disconnect()

    return True, "adapter disconnected"


BUILTIN_COMMANDS = {
    "/ports": ports_command,
    "/connect": connect_command,
    "/disconnect": disconnect_command,
}


# =================================================
# COMMAND LINE
# =================================================

def command_names():
    """
    Suggestions for the command line: a ready /connect line for every
    active port, the other built-in commands, then commands.yaml.
    """

    bitrate = reader.READER.bitrate if reader.READER else CAN_BITRATE

    names = ["/ports"]
    names += [f"/connect {device} {bitrate}" for device, _ in serial_ports()]
    names += ["/disconnect"]
    names += [command["name"] for command in COMMANDS]

    return names


def find_command(text):

    for command in COMMANDS:

        if command["name"] == text:
            return command

    return None


def execute(text):
    """
    Run a typed command. Returns (ok, message) for the event log.
    """

    word, *arguments = text.split()

    builtin = BUILTIN_COMMANDS.get(word)

    if builtin:
        return builtin(arguments)

    if find_command(text) is None:
        return False, "unknown command"

    # Encoding the frame by canmap.yaml and sending it comes later
    return False, "sending is not implemented yet"
