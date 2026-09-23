import yaml


def load_pattern(pattern_file):

    with open(pattern_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def build_grid_template(layout):

    columns = layout["columns"]
    rows = layout["rows"]
    areas = layout["areas"]

    if isinstance(columns, list):
        grid_columns = " ".join(
            f"minmax(0, {value}fr)"
            for value in columns
        )
    else:
        grid_columns = " ".join(
            ["minmax(0, 1fr)"] * columns
        )

    if isinstance(rows, list):
        grid_rows = " ".join(
            f"minmax(0, {value}fr)"
            for value in rows
        )
    else:
        grid_rows = " ".join(
            ["minmax(0, 1fr)"] * rows
        )

    grid_areas = " ".join(
        f'"{" ".join(row)}"'
        for row in areas
    )

    return grid_columns, grid_rows, grid_areas
