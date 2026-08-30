from dataclasses import dataclass
from enum import IntEnum
import struct


class SystemStatus(IntEnum):
    OK = 0
    WARNING = 1
    ALARM = 2


STATUS_TEXT = {
    SystemStatus.OK: "OK",
    SystemStatus.WARNING: "Warning",
    SystemStatus.ALARM: "Alarm",
}


@dataclass
class ElectricalValues:
    voltage_v: float
    current_a: float


@dataclass
class SystemStates:
    ne: SystemStatus
    insulation: SystemStatus
    cell_controller: SystemStatus
    converter: SystemStatus
    cooling: SystemStatus

def decode(frame):

    message_id = frame["id"]
    data = frame["data"]

    # 0x217 — напряжение и ток
    if message_id == 0x217:

        voltage_raw = data[0] + data[1] * 256
        current_raw = data[2] + data[3] * 256

        return {
            "voltage": voltage_raw / 10,
            "current": current_raw / 10
        }

    # 0x187 — состояния систем
    elif message_id == 0x187:

        return {
            "ne": data[0],
            "insulation": data[1],
            "cell_controller": data[2],
            "converter": data[3],
            "cooling": data[4]
        }

    # Этот ID нам пока неизвестен
    return None
