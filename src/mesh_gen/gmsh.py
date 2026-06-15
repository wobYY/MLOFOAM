import pathlib
import uuid
from dataclasses import dataclass
from typing import Optional

import gmsh

from ..utils.custom_logging import get_logger

log = get_logger()


# TODO: Check which fields are required
@dataclass(frozen=True)
class RefinementParams:
    sampling: int | None = None
    size_min: float | None = None
    size_max: float | None = None
    dist_min: float | None = None
    dist_max: float | None = None

    def __post_init__(self): ...


# TODO: Check which fields are required
@dataclass(frozen=True)
class BoundaryLayerParams:
    size: float | None = None
    ratio: float | None = None
    thickness: float | None = None
    number_of_layers: int | None = None
    quads: int | None = None

    def __post_init__(self): ...


# TODO: Check which fields are required
@dataclass(frozen=True)
class TrailingEdgeParams:
    length: float | None = None
    angle: float | None = None
    distance: float | None = None
    size: float | None = None

    def __post_init__(self): ...


@dataclass
class MeshParams:
    mesh_size_min: float
    mesh_size_max: float
    refinement: Optional[list[RefinementParams]]
    boundary_layer: Optional[list[BoundaryLayerParams]]
    trailing_edge: Optional[TrailingEdgeParams]

    def __post_init__(self): ...

    def validate_mesh_params(self) -> None: ...

    def validate_refinement(self) -> None: ...

    def validate_trailing_edge(self) -> None: ...

    def validate_boundary_layer(self) -> None: ...


# TODO: Check which fields are required
def _create_refinement(
    location_tag: int,
    config: RefinementParams,
) -> None:
    distance_field = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(distance_field, "CurvesList", [location_tag])

    gmsh.model.mesh.field.setNumber(distance_field, "Sampling", config.sampling)

    # Define a threshold field to apply finer mesh size within refinement_distance
    threshold_field = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(threshold_field, "InField", distance_field)
    gmsh.model.mesh.field.setNumber(threshold_field, "SizeMin", config.size_min)
    if config.size_max is not None:
        gmsh.model.mesh.field.setNumber(threshold_field, "SizeMax", config.size_max)
    if config.dist_min is not None:
        gmsh.model.mesh.field.setNumber(threshold_field, "DistMin", config.dist_min)
    if config.dist_max is not None:
        gmsh.model.mesh.field.setNumber(threshold_field, "DistMax", config.dist_max)

    # Set the refinement field as the background mesh size field
    gmsh.model.mesh.field.setAsBackgroundMesh(threshold_field)

    return


# TODO: Check which fields are required
def _create_boundary_layer(
    location_tag: int,
    config: BoundaryLayerParams,
) -> None:
    bl_field = gmsh.model.mesh.field.add("BoundaryLayer")
    gmsh.model.mesh.field.setNumbers(bl_field, "CurvesList", [location_tag])

    gmsh.model.mesh.field.setNumber(bl_field, "Size", config.size)
    gmsh.model.mesh.field.setNumber(bl_field, "Ratio", config.ratio)
    gmsh.model.mesh.field.setNumber(bl_field, "Thickness", config.thickness)
    gmsh.model.mesh.field.setNumber(bl_field, "NbLayers", config.number_of_layers)
    gmsh.model.mesh.field.setNumber(bl_field, "Quads", config.quads)
    gmsh.model.mesh.field.setAsBoundaryLayer(bl_field)

    return


# TODO: Check which fields are required
def _create_trailing_edge(
    location_tag: int,
    config: TrailingEdgeParams,
) -> None:
    return


def generate_gmsh_file(
    airfoil_dict: dict[str, str | list[tuple[float, float]]],
    domain_coords: list[tuple[float, float]],
    mesh_params: MeshParams,
    output_file: pathlib.Path | str | None = None,
    # domain_shape: str = "rectangle",
    file_format: str = "geo",
) -> None:
    """
    Generates a GMSH .geo file for the airfoil and its domain.

    Parameters:
        TBA
    """
    gmsh.initialize()
    gmsh.model.add("airfoil_domain")
    file_name = (
        airfoil_dict["naca_id"]
        if not airfoil_dict["naca_id"] == ""
        else str(uuid.uuid4())
    )
    airfoil_coords = airfoil_dict["coordinates"]
    output_file = (
        output_file
        or pathlib.Path().cwd() / "../mesh_files/" / f"{file_name}.{file_format}"
    )

    # Create airfoil geometry
    airfoil_max_x, airfoil_min_x, airfoil_max_y, airfoil_min_y = None, None, None, None
    for i, (x, y) in enumerate(airfoil_coords):
        airfoil_max_x = max(airfoil_max_x, x) if airfoil_max_x is not None else x
        airfoil_min_x = min(airfoil_min_x, x) if airfoil_min_x is not None else x
        airfoil_max_y = max(airfoil_max_y, y) if airfoil_max_y is not None else y
        airfoil_min_y = min(airfoil_min_y, y) if airfoil_min_y is not None else y
        gmsh.model.geo.addPoint(x, y, 0, 1.0, i + 1)

    # Create domain boundary geometry
    airfoil_point_tags: list[int] = []
    domain_max_x, domain_min_x, domain_max_y, domain_min_y = None, None, None, None
    for i, (x, y) in enumerate(domain_coords):
        domain_max_x = max(domain_max_x, x) if domain_max_x is not None else x
        domain_min_x = min(domain_min_x, x) if domain_min_x is not None else x
        domain_max_y = max(domain_max_y, y) if domain_max_y is not None else y
        domain_min_y = min(domain_min_y, y) if domain_min_y is not None else y
        airfoil_point_tags.append(
            gmsh.model.geo.addPoint(x, y, 0, 1.0, len(airfoil_coords) + i + 1)
        )

    # Create airfoil spline curve
    airfoil_spline = gmsh.model.geo.addSpline(airfoil_point_tags, 1)

    # Create a curve loop from the airfoil spline (tag airfoil_spline)
    airfoil_loop: int = gmsh.model.geo.addCurveLoop([airfoil_spline])

    # Create domain boundary lines
    domain_lines = []
    base = len(airfoil_coords) + 1
    n_domain = len(domain_coords)
    for i in range(n_domain):
        start_point = base + i
        end_point = base + ((i + 1) % n_domain)
        domain_lines.append(gmsh.model.geo.addLine(start_point, end_point))

    # Create main domain surface
    domain_loop: int = gmsh.model.geo.addCurveLoop(domain_lines)

    # Create a plane surface with outer domain loop and airfoil loop as a hole
    gmsh.model.geo.addPlaneSurface([domain_loop, airfoil_loop])

    # Create first layer boundary layer around airfoil
    gmsh.model.geo.synchronize()

    if mesh_params.refinement:
        for refinement in mesh_params.refinement:
            _create_refinement(airfoil_loop, refinement)

    if mesh_params.boundary_layer:
        for boundary_layer in mesh_params.boundary_layer:
            _create_boundary_layer(airfoil_loop, boundary_layer)

    if mesh_params.trailing_edge:
        ...
        # _create_trailing_edge(trailing_edge)

    # Set global meshing options
    gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_params.mesh_size_min)
    gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_params.mesh_size_max)

    # Generate 2D mesh
    gmsh.model.mesh.generate(dim=2)

    # Write mesh to file
    gmsh.write(str(output_file))

    # Clean up and finalize
    gmsh.finalize()
