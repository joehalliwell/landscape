import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from cyclopts import Parameter

from landscape.atmosphere.composition import get_filter_pipeline, get_sky_texture
from landscape.atmosphere.filters import FilterContext
from landscape.biomes import Biome
from landscape.utils import (
    RGB,
    clamp,
    contrasting_text_color,
    lerp,
    lerp_color,
    rgb,
)

if TYPE_CHECKING:
    from landscape.generation import Scene

TERM_SIZE = shutil.get_terminal_size((120, 30))
DEFAULT_WIDTH = TERM_SIZE.columns
DEFAULT_HEIGHT = min(
    max(
        8,
        TERM_SIZE.lines - 5,  # Leave room for prompt/status
    ),
    DEFAULT_WIDTH // 8,
)


@dataclass
class RenderParams:
    width: Annotated[
        int,
        Parameter(
            name=["--width", "-w"],
            help="Display width in character cells; defaults to full width.",
        ),
    ] = DEFAULT_WIDTH
    height: Annotated[
        int,
        Parameter(name=["--height", "-h"], help="Display height in character cells"),
    ] = DEFAULT_HEIGHT
    spherical: float = 0.1
    elevation: float = 0.5  # TODO: 0 = head on, 1 = plan view
    horizon: float = 0.5


def rgb_to_ansi(r: int, g: int, b: int) -> str:
    """Convert RGB to 24-bit ANSI foreground color code."""
    return f"\033[38;2;{r};{g};{b}m"


def rgb_to_ansi_fg_bg(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> str:
    """Convert RGB to 24-bit ANSI foreground and background color codes."""
    return f"\033[38;2;{fg[0]};{fg[1]};{fg[2]};48;2;{bg[0]};{bg[1]};{bg[2]}m"


RESET = "\033[m"


def render(
    scene: "Scene",
    render_params: RenderParams,
    show_landscape=True,
    signature: str | None = None,
) -> None:
    """Render 2D heightmap with depth shading and oblique projection.

    oblique: how much to shift y per z unit (0 = front view, 1 = steep oblique)
    """
    height_map = scene.height_map
    biome_map = scene.biome_map
    seed = scene.seed

    # Build sky texture and filter pipeline from atmosphere
    sky = get_sky_texture(scene.time, scene.season, scene.weather)
    filters = get_filter_pipeline(scene.time, scene.season, scene.weather)

    depth_buffer = make_depth_buffer(render_params, height_map)

    width, screen_height = render_params.width, render_params.height
    depth = len(biome_map[0])

    rows = [
        [("X", rgb("#ff00ff"), rgb("#ff00ff")) for _ in range(width)]
        for _ in range(screen_height)
    ]

    def get_color_at_point(x: int, z: int, y: int) -> tuple[str, RGB, RGB]:
        """Get blended color for a given point using biome map."""
        # Sky
        if not show_landscape or z > depth:
            ny = (y - screen_height * render_params.horizon) / (
                screen_height * render_params.horizon
            )
            return sky.texture(x, ny, ny, seed)

        biome1, biome2, blend = biome_map[x][z]
        nx = x / width
        nz = z / depth

        ny = height_map[x][z]
        cell1 = biome1.texture(nx, nz, ny, seed)
        cell2 = biome2.texture(nx, nz, ny, seed)

        # Base details on dominant biome prior to recalculating
        # the blend
        dominant = cell1 if blend < 0.5 else cell2

        # Recompute blend based on height This prevents e.g., the blue of the
        # ocean being dragged up too high into mountains
        if biome1.base_height > biome2.base_height:
            blend = lerp(
                1.0
                - (
                    clamp(ny, biome2.base_height, biome1.base_height)
                    - biome2.base_height
                )
                / (biome1.base_height - biome2.base_height),
                blend,
                0.5,
            )

        elif biome2.base_height > biome1.base_height:
            blend = lerp(
                (clamp(ny, biome1.base_height, biome2.base_height) - biome1.base_height)
                / (biome2.base_height - biome1.base_height),
                blend,
                0.5,
            )

        bg = lerp_color(cell1[2], cell2[2], blend)
        return (dominant[0], dominant[1], bg)

    # Convert to rows with color and edge detection
    for y in range(screen_height - 1, -1, -1):
        for x in range(width):
            z = depth_buffer[y][x]

            # Terrain - check for edges
            cell = get_color_at_point(x, z, y)

            char, fg, bg = cell

            # Edge detection/highlighting
            lz = depth_buffer[y][max(0, x - 1)]
            rz = depth_buffer[y][min(x + 1, width - 1)]

            min_delta = 1.0
            if z <= depth and char == " ":
                if lz - z > min_delta or lz > depth:
                    _, __, bg = get_color_at_point(x, lz, y)
                    char = "🭋"
                    if rz - z > min_delta or rz > depth:
                        char = "🭯"
                    # bg = MAGENTA
                elif rz - z > min_delta or rz > depth:
                    _, _, bg = get_color_at_point(x, rz, y)
                    char = "🭀"
                    # bg = MAGENTA

            rows[y][x] = (char, fg, bg)

    # Add haze and filter
    for y in range(screen_height):
        ny = (y - screen_height * render_params.horizon) / (
            screen_height * render_params.horizon
        )
        for x in range(width):
            z = depth_buffer[y][x]
            depth_fraction = 1.0 * z / depth

            cell = rows[y][x]
            ctx: FilterContext = {
                "x": x,
                "y": y,
                "z": z,
                "ny": ny,
                "depth_fraction": depth_fraction,
                "seed": seed,
            }
            rows[y][x] = filters.apply(cell, ctx)

    if signature and screen_height > 1:
        # Overlay signature in bottom right
        sig_text = f" {signature} "
        bg = rows[1][width - len(sig_text)][2]
        fg = contrasting_text_color(bg)
        for i, char in enumerate(sig_text):
            idx = width - len(sig_text) + i
            if 0 <= idx < width:
                current = rows[1][idx]
                # fg_color = contrasting_text_color(current[2])
                rows[1][idx] = (char, fg, lerp_color(bg, current[2], 0.5))

    _render_rows(rows)


def _render_rows(lines):
    height = len(lines)
    width = len(lines[0])
    for y in range(height - 1, -1, -1):
        for x in range(width):
            c, fg, bg = lines[y][x]
            print(rgb_to_ansi_fg_bg(fg, bg), end="")
            print(c, end="")
        print(RESET)


def make_depth_buffer(render_params: RenderParams, height_map, *, horizon=0.5):
    """
    Project the height map to a depth buffer.
    """
    width, height = render_params.width, render_params.height
    spherical = render_params.spherical

    depth = len(height_map[0])

    # Calculate the projection -- think slightly spherical!
    oblique = (height * horizon) / depth
    background_shrink = 2.0
    foreground_shrink = 0.5

    max_height = height // 2

    buffer = [[depth + 1 for _ in range(width)] for _ in range(height)]

    # Render back-to-front for proper occlusion
    for z in range(depth - 1, -1, -1):
        # Approximating looking down onto a sphere
        proj_scale = 1 / (z / depth + 1) ** background_shrink
        proj_scale *= (z / depth) ** foreground_shrink

        for x in range(width):
            # Basic oblique projection
            proj_offset = z * oblique
            # Drop the edges to hint at a sphere
            proj_offset *= 1.0 - spherical * ((x - width / 2) / (width / 2)) ** 2

            terrain_height = int(
                height_map[x][z] * max_height * proj_scale + proj_offset
            )

            for y in range(min(terrain_height, height)):
                buffer[y][x] = z

    # render_depth_buffer(buffer)
    return buffer


def render_depth_buffer(depth_map):
    width = len(depth_map[0])
    height = len(depth_map)
    max_depth = max(max(r) for r in depth_map)
    lines = []
    for y in range(height):
        row = []
        for x in range(width):
            d = depth_map[y][x] / max_depth
            col = lerp_color(rgb("#000044"), rgb("#ff0000"), 1.0 - d)
            cell = (" ", col, col)
            row.append(cell)
        lines.append(row)
    _render_rows(lines)


def render_plan(biome_map, seed: int) -> None:
    width = len(biome_map)
    depth = len(biome_map[0])

    rows = []
    for z in range(depth):
        row = []
        for x in range(width):
            biome: Biome = biome_map[x][z][0]
            cell = biome.texture(x, z, 1.0, seed)
            row.append(cell)
        rows.append(row)
    _render_rows(rows)
