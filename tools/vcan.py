import time
import random
import subprocess

import can
import yaml


CANMAP_FILE = "../canmap.yaml"


# Load CAN map
with open(CANMAP_FILE, "r", encoding="utf-8") as file:
    canmap = yaml.safe_load(file)


CAN_INTERFACE = canmap["can"]["interface"]


def setup_vcan():
    """
    Create and activate the vcan interface if necessary.
    """

    result = subprocess.run(
        ["ip", "link", "show", CAN_INTERFACE],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        subprocess.run(
            ["sudo", "modprobe", "vcan"],
            check=True
        )

        subprocess.run(
            [
                "sudo",
                "ip",
                "link",
                "add",
                "dev",
                CAN_INTERFACE,
                "type",
                "vcan"
            ],
            check=True
        )

    subprocess.run(
        [
            "sudo",
            "ip",
            "link",
            "set",
            "up",
            CAN_INTERFACE
        ],
        check=True
    )

    print(f"{CAN_INTERFACE} is active")


def random_code(item):
    """
    Generate a random value for a code.
    """

    values = item.get("values")

    if not values:
        return random.randint(0, 255)

    return int(random.choice(list(values.keys())))


def random_metric(item):
    """
    Generate a random raw value for a metric.
    """

    length = item["length"]

    max_value = (1 << (length * 8)) - 1

    return random.randint(0, max_value)


def encode_value(value, length, byte_order):
    """
    Convert an integer to bytes.
    """

    if byte_order == "big_endian":
        return value.to_bytes(
            length,
            byteorder="big"
        )

    return value.to_bytes(
        length,
        byteorder="little"
    )


def build_frame(frame_config):
    """
    Build one CAN frame according to canmap.yaml.
    """

    data = bytearray(8)

    for item in frame_config["data"]:

        data_type = item["type"]
        byte = item["byte"]
        length = item["length"]

        if data_type == "code":

            value = random_code(item)

            encoded = encode_value(
                value,
                length,
                "little"
            )

            data[byte:byte + length] = encoded

        elif data_type == "metric":

            value = random_metric(item)

            encoded = encode_value(
                value,
                length,
                item.get("byte_order", "little_endian")
            )

            data[byte:byte + length] = encoded

        elif data_type == "bitfield":

            value = 0

            for parameter in item["parameters"]:

                bit = parameter["bit"]

                # 0 = OK, 1 = ALARM
                bit_value = random.randint(0, 1)

                if bit_value:
                    value |= (1 << bit)

            data[byte] = value

    return can.Message(
        arbitration_id=frame_config["id"],
        data=data,
        is_extended_id=False
    )


def get_frames():
    """
    Get all frame descriptions from canmap.yaml.
    """

    frames = []

    for device in canmap["map"]:

        for frame in device["frames"]:
            frames.append(frame)

    return frames


def main():

    setup_vcan()

    bus = can.Bus(
        interface="socketcan",
        channel=CAN_INTERFACE
    )

    frames = get_frames()

    # Next transmission time for every frame
    next_send = {}

    current_time = time.monotonic()

    for frame in frames:
        next_send[frame["id"]] = current_time

    print("CAN simulator started")

    try:

        while True:

            current_time = time.monotonic()

            for frame in frames:

                frame_id = frame["id"]

                if current_time >= next_send[frame_id]:

                    message = build_frame(frame)

                    bus.send(message)

                    print(
                        f"TX 0x{frame_id:03X}: "
                        f"{message.data.hex(' ')}"
                    )

                    cycle = frame["cycle_ms"] / 1000

                    next_send[frame_id] += cycle

            time.sleep(0.001)

    except KeyboardInterrupt:

        print("CAN simulator stopped")

    finally:

        bus.shutdown()


if __name__ == "__main__":
    main()
