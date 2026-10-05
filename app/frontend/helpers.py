import html

from .config import NO_DATA


def is_number(value):

    return isinstance(value, (int, float)) and not isinstance(value, bool)


def fmt(value, unit='', spec='g'):
    """
    Number with its unit, or a dash when there is no data.
    """

    if not is_number(value):
        return '—'

    return f'{value:{spec}}{unit}'


def pretty(value):
    """
    DC_DIRECT_CHARGE -> Direct charge; anything non-text as is.
    """

    if not isinstance(value, str):
        return fmt(value)

    if value == NO_DATA:
        return '—'

    if value.startswith("DC_"):
        value = value[3:]

    return value.replace("_", " ").capitalize()


def link_value(value, maximum):

    if not is_number(value) or value > maximum:
        return "None"

    return f"{value} ms"


def get_segments(value, minimum, maximum, total, minimum_segments=0):

    if not is_number(value):
        return 0

    value = max(minimum, min(value, maximum))

    segments = round(
        (value - minimum) / (maximum - minimum) * total
    )

    return max(segments, minimum_segments)


def segment_value(index, minimum, maximum, total):
    """Value in the middle of the meter segment `index`."""

    return minimum + (index + 0.5) * (maximum - minimum) / total


def cells_summary(values):

    numbers = [value for value in values if is_number(value)]

    no_data = len(values) - len(numbers)

    if not numbers:
        return None, None, no_data

    return max(numbers), min(numbers), no_data


def spans_html(parts):
    """
    HTML of (text, css class[, colour]) parts, one <span> each.
    """

    spans = []

    for text, css, *color in parts:

        style = f' style="color: {color[0]};"' if color and color[0] else ''

        spans.append(
            f'<span class="{css}"{style}>{html.escape(str(text))}</span>'
        )

    return ''.join(spans)
