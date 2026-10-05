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


def is_number(value):

    return isinstance(value, (int, float)) and not isinstance(value, bool)


def cells_summary(values):

    numbers = [value for value in values if is_number(value)]

    no_data = len(values) - len(numbers)

    if not numbers:
        return None, None, no_data

    return max(numbers), min(numbers), no_data
