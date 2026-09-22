def link_value(value, maximum):

    if value > maximum:
        return "None"

    return f"{value} ms"


def get_segments(value, minimum, maximum, minimum_segments=0):

    value = max(minimum, min(value, maximum))

    segments = round(
        (value - minimum) / (maximum - minimum) * 7
    )

    return max(segments, minimum_segments)
