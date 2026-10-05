import yaml


def load_pattern(pattern_file):

    with open(pattern_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def build_track(value):
    """
    Numbers are fr shares, strings ("auto", "48px") are CSS track sizes.
    """

    if isinstance(value, str):
        return value

    return f"minmax(0, {value}fr)"


def build_tracks(tracks):

    if isinstance(tracks, list):
        return " ".join(build_track(value) for value in tracks)

    return " ".join([build_track(1)] * tracks)


def build_grid_template(layout):

    grid_columns = build_tracks(layout["columns"])
    grid_rows = build_tracks(layout["rows"])

    grid_areas = " ".join(
        f'"{" ".join(row)}"'
        for row in layout["areas"]
    )

    return grid_columns, grid_rows, grid_areas
