import yaml


CANMAP_FILE = "../canmap.yaml"


# Load CAN protocol description
with open(CANMAP_FILE, "r", encoding="utf-8") as file:
    canmap = yaml.safe_load(file)


def find_frame(frame_id):
    """
    Find frame description by CAN ID.
    """

    for device in canmap["map"]:

        for frame in device["frames"]:

            if frame["id"] == frame_id:
                return frame

    return None


def decode_code(data, item):
    """
    Decode a code.
    """

    byte = item["byte"]
    length = item["length"]

    raw_data = data[byte:byte + length]

    value = int.from_bytes(
        raw_data,
        byteorder="little"
    )

    if "values" in item:
        value = item["values"].get(
            value,
            f"UNKNOWN({value})"
        )

    return value


def decode_metric(data, item):
    """
    Decode a numeric scale.
    """

    byte = item["byte"]
    length = item["length"]

    raw_data = data[byte:byte + length]

    if item.get("byte_order") == "big_endian":
        value = int.from_bytes(
            raw_data,
            byteorder="big"
        )
    else:
        value = int.from_bytes(
            raw_data,
            byteorder="little"
        )

    if "scale" in item:

        scale = item["scale"]

        if isinstance(scale, str):
            scale = float(
                scale.replace(",", ".")
            )

        if scale >= 1:
            value = value / scale
        else:
            value = value * scale

    return value


def decode_bitfield(data, item):
    """
    Decode individual bits.
    """

    byte = item["byte"]
    value = data[byte]

    result = {}

    for parameter in item["parameters"]:

        bit = parameter["bit"]

        bit_value = (value >> bit) & 1

        if "values" in parameter:
            bit_value = parameter["values"].get(
                bit_value,
                f"UNKNOWN({bit_value})"
            )

        result[parameter["parameter"]] = bit_value

    return result


def decode(frame):
    """
    Decode one CAN frame using canmap.yaml.

    Returns a dictionary with decoded parameters.
    """

    frame_description = find_frame(
        frame.arbitration_id
    )

    if frame_description is None:
        return {}

    parameters = {}

    for item in frame_description["data"]:

        data_type = item["type"]

        if data_type == "code":

            parameter = item["parameter"]

            parameters[parameter] = decode_code(
                frame.data,
                item
            )

        elif data_type == "metric":

            parameter = item["parameter"]

            parameters[parameter] = decode_metric(
                frame.data,
                item
            )

        elif data_type == "bitfield":

            bitfield_parameters = decode_bitfield(
                frame.data,
                item
            )

            parameters.update(
                bitfield_parameters
            )

    return parameters
