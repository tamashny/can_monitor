import html

from parameters import NO_DATA


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
    CHARGE_DIRECT -> Charge direct; anything non-text as is.
    """

    if not isinstance(value, str):
        return fmt(value)

    if value == NO_DATA:
        return '—'

    return value.replace("_", " ").capitalize()


def get_segments(value, minimum, maximum, total, minimum_segments=0):

    if not is_number(value):
        return 0

    value = max(minimum, min(value, maximum))

    segments = round(
        (value - minimum) / (maximum - minimum) * total
    )

    return max(segments, minimum_segments)


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
