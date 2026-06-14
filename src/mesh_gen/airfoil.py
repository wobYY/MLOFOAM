"""We use this to generate the airfoil and its domain"""

import pathlib
from typing import TypedDict

from ..utils.custom_logging import get_logger
from ..utils.helpers import is_number

log = get_logger()

# isort: off
# ruff: disable[F811]
import random
from icecream import ic, argumentToString
# import pandas as pd

ic.configureOutput(includeContext=True)

# Register a function to summarize Pandas DataFrames and Series
# @argumentToString.register(pd.DataFrame)
# def _(obj: pd.DataFrame):
#     return f"Pandas DataFrame with shape {obj.shape} with columns {obj.columns.to_list()}"

# @argumentToString.register(pd.Series)
# def _(obj: pd.Series):
#     return f"Pandas Series with shape {obj.shape} with index {obj.index.to_list()}"

# @argumentToString.register(pd.Index)
# def _(obj: pd.Index):
#     return f"Pandas Index with values {obj.to_list()}"


@argumentToString.register(list)
def _(obj: list):
    return f"List with {len(obj)} elements: {random.sample(obj, min(len(obj), 20))}"


@argumentToString.register(tuple)
def _(obj: tuple):
    return f"Tuple with {len(obj)} elements: {random.sample(obj, min(len(obj), 20))}"


# ruff: enable[F811]
# isort: on


def _extract_coords_from_dat(
    file_lines: list[str],
    multiplier: float,
) -> list[tuple[float, float]]:
    coords = []
    for line in file_lines:
        if not is_number(line.strip().split(" ")[0].strip()):
            log.info(ic("Found non-numeric line: %s", line.strip()))
            continue

        x, y = [
            coord.strip()
            for coord in line.strip().split(" ")
            if is_number(coord.strip())
        ][0:2]

        x = x.strip()
        y = y.strip()

        coords.append((float(x) * multiplier, float(y) * multiplier))

    return coords


def _deduplicate_coords(
    coords: list[tuple[float, float]],
    tolerance: float,
) -> list[tuple[float, float]]:
    deduped_coords: list[tuple[float, float]] = []
    for x, y in coords:
        last_coord = deduped_coords[-1] if deduped_coords else None
        if last_coord is None:
            deduped_coords.append((x, y))
            continue

        if abs(x - last_coord[0]) <= tolerance and abs(y - last_coord[1]) <= tolerance:
            log.info(ic(f"Skipping coordinate: ({x}, {y})"))
            continue

        deduped_coords.append((x, y))

    return deduped_coords


class AirfoilCoords(TypedDict):
    naca_id: str
    coordinates: list[tuple[float, float]]


def extract_airfoil_coords(
    file_path: pathlib.Path,
    tolerance: float = 1e-8,
    multiplier: float = 1,
) -> AirfoilCoords:
    """Extracts the coordinates of an airfoil from a .dat file, deduplicates them based on a specified tolerance, and returns the deduplicated coordinates.

    Args:
        file_path (pathlib.Path): The path to the .dat file containing the airfoil coordinates.
        tolerance (float, optional): The tolerance for deduplicating coordinates. Defaults to 1e-8.
        multiplier (float, optional): A multiplier for the extracted coordinates. Defaults to 1.

    Returns:
        dict[str, Union[str, list[tuple[float, float]]]]: A dictionary containing the NACA ID (if available) and the deduplicated coordinates.
    """
    with open(file_path, "r") as f:
        dat_lines: list[str] = f.readlines()

        naca_id = ""
        coords = _extract_coords_from_dat(
            file_lines=dat_lines,
            multiplier=multiplier,
        )

        # Deduplicate coordinates
        return {
            "naca_id": naca_id,
            "coordinates": _deduplicate_coords(coords, tolerance),
        }


def generate_rectangular_domain_coords(
    airfoil_coords: AirfoilCoords,
    x_min_offset_multiplier: float = 5,
    x_max_offset_multiplier: float = 10,
    y_min_offset_multiplier: float = 10,
    y_max_offset_multiplier: float = 10,
) -> list[tuple[float, float]]:
    """Generates the coordinates of a rectangular domain around the airfoil based on the airfoil's coordinates and specified offset multipliers.

    Args:
        airfoil_coords (AirfoilCoords): A dictionary containing the airfoil information.
        x_min_offset_multiplier (float, optional): The multiplier for the minimum x-offset (front). Defaults to 5.
        x_max_offset_multiplier (float, optional): The multiplier for the maximum x-offset (back). Defaults to 10.
        y_min_offset_multiplier (float, optional): The multiplier for the minimum y-offset (bottom). Defaults to 10.
        y_max_offset_multiplier (float, optional): The multiplier for the maximum y-offset (top). Defaults to 10.

    Returns:
        list[tuple[float, float]]: A list of tuples representing the coordinates of the rectangular domain in the order: bottom-left, bottom-right, top-right, top-left.
    """
    x_coords: list[float] = [x for x, _ in airfoil_coords["coordinates"]]
    y_coords: list[float] = [y for _, y in airfoil_coords["coordinates"]]

    x_min = abs(max(x_coords) - min(x_coords)) * -x_min_offset_multiplier
    x_max = abs(max(x_coords) - min(x_coords)) * x_max_offset_multiplier
    y_min = abs(max(y_coords) - min(y_coords)) * -y_min_offset_multiplier
    y_max = abs(max(y_coords) - min(y_coords)) * y_max_offset_multiplier

    return [
        (x_min, y_min),
        (x_max, y_min),
        (x_max, y_max),
        (x_min, y_max),
    ]
