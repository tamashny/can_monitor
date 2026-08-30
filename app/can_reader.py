import can

class CanReader:

    def __init__(self, port, bitrate):
        self.bus = can.Bus(
            interface="slcan",
            channel=port,
            bitrate=bitrate
        )

    def read(self):
        message = self.bus.recv()

        if message is None:
            return None

        return {
            "id": message.arbitration_id,
            "data": bytes(message.data)
        }

    def close(self):
        self.bus.shutdown()