import pathlib
import uuid

import gmsh

from ..utils.custom_logging import get_logger

log = get_logger()


def generate_gmsh_file(
    airfoil_dict: dict[str, str | list[tuple[float, float]]],
    domain_coords: list[tuple[float, float]],
    mesh_size_min: float = 0.05,
    mesh_size_max: float = 0.05,
    output_file: pathlib.Path | str | None = None,
    domain_shape: str = "rectangle",
    file_format: str = "geo",
) -> None:
    """
    Generates a GMSH .geo file for the airfoil and its domain.

    Parameters:
    - airfoil_dict: Dictionary containing the airfoil information.
    - domain_coords: List of tuples containing the (x, y) coordinates of the domain.
    - domain_shape: Shape of the domain. Currently supports "rectangle" or "custom".
    - output_file: Name of the output .geo file.
    """
    gmsh.initialize()
    gmsh.model.add("airfoil_domain")
    file_name = (
        airfoil_dict["naca_id"]
        if not airfoil_dict["naca_id"] == ""
        else str(uuid.uuid4())
    )
    airfoil_coords = airfoil_dict["coordinates"]
    output_file = output_file or pathlib.Path().cwd() / f"{file_name}.{file_format}"

    # Add airfoil points
    for i, (x, y) in enumerate(airfoil_coords):
        gmsh.model.geo.addPoint(x, y, 0, 1.0, i + 1)

    # Add domain points
    for i, (x, y) in enumerate(domain_coords):
        gmsh.model.geo.addPoint(x, y, 0, 1.0, len(airfoil_coords) + i + 1)

    # Airfoil lines as a spline
    gmsh.model.geo.addSpline([i + 1 for i in range(len(airfoil_coords))], 1)

    # Create lines for domain
    domain_lines = []
    for i in range(len(domain_coords)):
        start_point = len(airfoil_coords) + i + 1
        end_point = len(airfoil_coords) + (i + 1) % len(domain_coords) + 1
        line_tag = gmsh.model.geo.addLine(start_point, end_point)
        domain_lines.append(line_tag)

    # Domain lines as a closed loop of straight lines
    if domain_shape == "rectangle":
        gmsh.model.geo.addCurveLoop(domain_lines, 2)
        gmsh.model.geo.addPlaneSurface([2], 1)

    # Synchronize and write to file
    gmsh.model.geo.synchronize()

    # Set meshing options
    gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size_min)
    gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_max)

    # Generate the mesh and write to file
    gmsh.model.mesh.generate(2)
    gmsh.write(str(output_file))
    gmsh.finalize()
