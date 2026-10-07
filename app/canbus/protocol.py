import yaml

# All bits set (0xFF in every byte) means "value not available"
from parameters import NO_DATA
from settings import CANMAP_FILE

# Load CAN protocol description
with open(CANMAP_FILE, "r", encoding="utf-8") as file:
    canmap = yaml.safe_load(file)

# CAN ID -> (device, frame description)
FRAMES = {
    frame["id"]: (device["device"], frame)
    for device in canmap["map"]
    for frame in device["frames"]
}


def find_frame(frame_id):
    """
    Find frame description by CAN ID.
    """

    return FRAMES.get(frame_id, (None, None))[1]


def find_device(frame_id):
    """
    Device that sends the frame, as named in canmap.yaml (imd, cc, bup, ...).
    """

    return FRAMES.get(frame_id, (None, None))[0]


def is_no_data(raw_data):
    """
    Check whether every byte of the field is 0xFF.
    """

    return len(raw_data) > 0 and all(
        b == 0xFF for b in raw_data
    )


def decode_code(data, item):
    """
    Decode a code.
    """

    byte = item["byte"]
    length = item["length"]

    raw_data = data[byte:byte + length]

    if is_no_data(raw_data):
        return NO_DATA

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

    if is_no_data(raw_data):
        return NO_DATA

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

    # Sign-magnitude ("прямой код"): MSB is the sign
    if item.get("encoding") == "sign_magnitude":

        sign_bit = 1 << (length * 8 - 1)

        if value & sign_bit:
            value = -(value & (sign_bit - 1))

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

    if value == 0xFF:

        for parameter in item["parameters"]:
            result[parameter["parameter"]] = NO_DATA

        return result

    for parameter in item["parameters"]:

        bit = parameter["bit"]
        length = parameter.get("length", 1)

        bit_value = (value >> bit) & ((1 << length) - 1)

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

        # The frame is shorter than its description: no data for the field
        if item["byte"] + item["length"] > len(frame.data):

            if data_type == "bitfield":
                for bit in item["parameters"]:
                    parameters[bit["parameter"]] = NO_DATA
            else:
                parameters[item["parameter"]] = NO_DATA

            continue

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


# =================================================
# ENCODING: values -> frame data (the reverse of decode)
# =================================================

def raw_code(value, values):
    """
    Name of a code ("OK") -> its number by the "values" table of canmap.yaml.
    """

    if values is None:
        return int(value)

    for number, name in values.items():

        # YAML may turn names like YES into booleans: compare as text
        if str(name).upper() == str(value).upper():
            return number

    raise ValueError(f"no code for {value!r}")


def scale_of(item):

    scale = item.get("scale", 1)

    if isinstance(scale, str):
        scale = float(scale.replace(",", "."))

    return scale


def encode_metric(value, item):

    length = item["length"]
    scale = scale_of(item)

    raw = value * scale if scale >= 1 else value / scale
    raw = round(raw)

    if item.get("encoding") == "sign_magnitude":

        sign_bit = 1 << (length * 8 - 1)
        magnitude = min(abs(raw), sign_bit - 1)
        raw = magnitude | (sign_bit if raw < 0 else 0)

    # All ones means "no data": the largest real value is one less
    raw = max(0, min(raw, (1 << (length * 8)) - 2))

    order = "big" if item.get("byte_order") == "big_endian" else "little"

    return raw.to_bytes(length, byteorder=order)


def encode(frame_id, values):
    """
    Build the data of a frame from parameter values named as in canmap.yaml.
    Values that are missing or NO_DATA are sent as all ones (0xFF...).
    """

    frame_description = find_frame(frame_id)

    if frame_description is None:
        raise ValueError(f"frame 0x{frame_id:03X} is not in canmap.yaml")

    size = max(item["byte"] + item["length"] for item in frame_description["data"])
    data = bytearray(b"\xFF" * size)

    for item in frame_description["data"]:

        byte = item["byte"]
        length = item["length"]
        data_type = item["type"]

        if data_type == "bitfield":

            bits = item["parameters"]

            if all(values.get(bit["parameter"], NO_DATA) == NO_DATA for bit in bits):
                continue

            field = 0

            for bit in bits:

                value = values.get(bit["parameter"], NO_DATA)

                if value != NO_DATA:
                    field |= raw_code(value, bit.get("values")) << bit["bit"]

            data[byte] = field

            continue

        value = values.get(item["parameter"], NO_DATA)

        if value == NO_DATA:
            continue

        if data_type == "code":
            raw = raw_code(value, item.get("values"))
            data[byte:byte + length] = raw.to_bytes(length, byteorder="little")

        elif data_type == "metric":
            data[byte:byte + length] = encode_metric(value, item)

    return bytes(data)
