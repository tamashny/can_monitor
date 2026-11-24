"""Decoding and encoding of CAN frames by the signal map (canmap.py)."""

from canmap import FRAMES, SERVICE_SIGNALS, signal_key, signal_keys
from parameters import MEASURE_ERROR, NO_DATA

# Text of a flag that has no names in the map: (bit is 0, bit is 1)
FLAG_TEXT = {
    "fault": ("OK", "ALARM"),
    "internal_error": ("OK", "ALARM"),
    "warn": ("OK", "WARNING"),
}
DEFAULT_FLAG_TEXT = ("OFF", "ON")


def find_frame(frame_id):
    """
    Frame description by CAN ID.
    """

    return FRAMES.get(frame_id)


# =================================================
# FIELDS
# =================================================

def field_position(signal):
    """
    First bit of the field in the frame and its length in bits.
    """

    start = signal["byte"] * 8 + signal.get("bit", 0)
    size = signal.get("bit_length") or signal.get("byte_length", 1) * 8

    return start, size


def swap_bytes(raw, size):

    length = size // 8

    return int.from_bytes(raw.to_bytes(length, "little"), "big")


def read_field(data, signal):
    """
    Raw value of the field, None when the frame is too short for it.
    """

    start, size = field_position(signal)

    if start + size > len(data) * 8:
        return None

    raw = (int.from_bytes(data, "little") >> start) & ((1 << size) - 1)

    if signal.get("byte_order") == "big_endian":
        raw = swap_bytes(raw, size)

    return raw


def invalid_codes(signal):
    """
    Raw codes that are not a measurement -> what they mean.
    """

    invalid = signal.get("invalid_raw")

    if invalid is None:
        return {}

    if isinstance(invalid, int):
        return {invalid: NO_DATA}

    return {
        invalid["not_available"]: NO_DATA,
        invalid["error"]: MEASURE_ERROR,
    }


# =================================================
# CRC AND FRAME COUNTER
# =================================================

def crc8(frame_id, data):
    """
    CRC-8/SAE-J1850 over the low and high byte of the CAN ID and `data`.
    """

    crc = 0xFF

    for byte in bytes((frame_id & 0xFF, frame_id >> 8)) + bytes(data):

        crc ^= byte

        for _ in range(8):
            crc = ((crc << 1) ^ 0x1D) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF

    return crc ^ 0xFF


def crc_valid(frame, data):
    """
    Length and CRC of a frame; frames without a CRC field always pass.
    """

    signal = frame["crc_signal"]

    if signal is None:
        return True

    if len(data) != frame.get("length"):
        return False

    return read_field(data, signal) == crc8(frame["id"], data[:signal["byte"]])


def frame_counter(frame, data):
    """
    CNT of the frame, None when it has no such field.
    """

    signal = frame["cnt_signal"]

    return None if signal is None else read_field(data, signal)


# =================================================
# DECODING
# =================================================

def decode_number(raw, signal):

    _, size = field_position(signal)

    representation = signal.get("representation")
    sign_bit = 1 << (size - 1)

    if representation == "twos_complement" and raw & sign_bit:
        raw -= 1 << size

    elif representation == "sign_magnitude" and raw & sign_bit:
        raw = -(raw & (sign_bit - 1))

    value = raw * signal.get("factor", 1) + signal.get("offset", 0)

    # 0.1 * 3 is 0.30000000000000004
    return round(value, 6)


def flag_text(signal, flag, bit):

    if flag["names"]:
        return flag["names"].get(bit, f"UNKNOWN({bit})")

    return FLAG_TEXT.get(signal["name"], DEFAULT_FLAG_TEXT)[bit]


def decode_signal(frame, signal, data):
    """
    {key: value} of one signal.
    """

    keys = signal_keys(frame, signal)

    if not keys:
        return {}

    raw = read_field(data, signal)

    if raw is None:
        return {key: NO_DATA for key in keys}

    if signal.get("encoding") == "bitfield":

        return {
            signal_key(frame, signal, flag): flag_text(
                signal, flag, (raw >> flag["bit"]) & 1
            )
            for flag in signal.get("flags") or []
        }

    invalid = invalid_codes(signal)

    if raw in invalid:
        return {keys[0]: invalid[raw]}

    if signal.get("encoding") == "enum" and signal["names"]:
        return {keys[0]: signal["names"].get(raw, f"UNKNOWN({raw})")}

    return {keys[0]: decode_number(raw, signal)}


def decode(message):
    """
    Decode one CAN frame. Returns {key in PARAMETERS[device]: value}.
    """

    frame = find_frame(message.arbitration_id)

    if frame is None:
        return {}

    data = bytes(message.data)
    values = {}

    for signal in frame["signals"]:
        values.update(decode_signal(frame, signal, data))

    return values


# =================================================
# ENCODING: values -> frame data (the reverse of decode)
# =================================================

def encode_number(value, signal):

    _, size = field_position(signal)

    invalid = invalid_codes(signal)

    # The largest codes may be reserved for "no data" and "error"
    reserved = len(invalid)

    raw = round(
        (value - signal.get("offset", 0)) / signal.get("factor", 1)
    )

    representation = signal.get("representation")
    limit = (1 << (size - 1)) - 1

    if representation == "twos_complement":
        raw = max(-limit - 1, min(raw, limit - reserved))
        return raw & ((1 << size) - 1)

    if representation == "sign_magnitude":
        magnitude = min(abs(raw), limit - reserved)
        return magnitude | ((limit + 1) if raw < 0 else 0)

    return max(0, min(raw, (1 << size) - 1 - reserved))


def encode_flags(frame, signal, values):

    raw = 0

    for flag in signal.get("flags") or []:

        value = values.get(signal_key(frame, signal, flag), NO_DATA)

        if flag["names"]:
            on = flag["names"].get(1)
        else:
            on = FLAG_TEXT.get(signal["name"], DEFAULT_FLAG_TEXT)[1]

        if value == on:
            raw |= 1 << flag["bit"]

    return raw


def encode_signal(frame, signal, values):
    """
    Raw value of the field. Without a value: the "no data" code, if the
    signal has one, otherwise 0.
    """

    # ERR_REG is sent as 0, CNT and CRC are filled in by encode()
    if signal["name"] in SERVICE_SIGNALS:
        return 0

    if signal.get("encoding") == "bitfield":
        return encode_flags(frame, signal, values)

    value = values.get(signal_key(frame, signal), NO_DATA)

    if value in (NO_DATA, MEASURE_ERROR):

        for code, meaning in invalid_codes(signal).items():
            if meaning == value:
                return code

        return 0

    if signal.get("encoding") == "enum" and signal["names"]:

        for number, name in signal["names"].items():
            if name == value:
                return number

        raise ValueError(f'no code for {value!r} in {signal["name"]}')

    return encode_number(value, signal)


def encode(frame_id, values, cnt=0):
    """
    Build the data of a frame from values named as in PARAMETERS[device],
    with the frame counter `cnt` and the CRC when the frame has them.
    """

    frame = find_frame(frame_id)

    if frame is None:
        raise ValueError(f"frame 0x{frame_id:03X} is not in the CAN map")

    length = frame.get("length") or max(
        (field_position(signal)[0] + field_position(signal)[1] + 7) // 8
        for signal in frame["signals"]
    )

    data = 0

    for signal in frame["signals"]:

        start, size = field_position(signal)
        raw = encode_signal(frame, signal, values)

        if signal.get("byte_order") == "big_endian":
            raw = swap_bytes(raw, size)

        data |= (raw & ((1 << size) - 1)) << start

    if frame["cnt_signal"] is not None:

        start, size = field_position(frame["cnt_signal"])
        data |= (cnt & ((1 << size) - 1)) << start

    result = bytearray(data.to_bytes(length, "little"))

    if frame["crc_signal"] is not None:

        byte = frame["crc_signal"]["byte"]
        result[byte] = crc8(frame_id, result[:byte])

    return bytes(result)
