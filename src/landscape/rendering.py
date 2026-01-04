import random
import shutil
from dataclasses import dataclass
from typing import Annotated

from cyclopts import Parameter

from landscape.atmospheres import Atmosphere
from landscape.biomes import TREE_CHARS, Biome
from landscape.utils import RGB, lerp_color, noise_2d, rgb

TERM_SIZE = shutil.get_terminal_size((120, 30))
DEFAULT_WIDTH = TERM_SIZE.columns
DEFAULT_HEIGHT = max(8, TERM_SIZE.lines - 10)  # Leave room for prompt/status


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


def render_with_depth(
    render_params: RenderParams,
    height_map: list[list[float]],
    biome_map: list[list[tuple[Biome, Biome, float]]],
    tree_map: list[list[bool]],
    atmosphere: Atmosphere,
    seed,
    show_landscape=True,
) -> None:
    """Render 2D heightmap with depth shading and oblique projection.

    oblique: how much to shift y per z unit (0 = front view, 1 = steep oblique)
    """
    depth_buffer = make_depth_buffer(render_params, height_map)

    width, screen_height = render_params.width, render_params.height
    depth = len(biome_map[0])

    rows = [
        [("X", rgb("#ff00ff"), rgb("#ff00ff")) for _ in range(width)]
        for _ in range(screen_height)
    ]

    haze = rgb("#aabbff")

    def get_color_at_point(x: int, z: int) -> tuple[str, RGB, RGB]:
        """Get blended color for a given point using biome map."""

        biome1, biome2, blend = biome_map[x][z]
        nx = x / width
        nz = z / depth

        y = height_map[x][z]
        cell1 = biome1.texture(nx, nz, y, seed)
        cell2 = biome2.texture(nx, nz, y, seed)

        bg = lerp_color(cell1[2], cell2[2], blend)
        dominant = cell1 if blend < 0.5 else cell2
        return (dominant[0], dominant[1], bg)

    # Convert to lines with color and edge detection
    for y in range(screen_height - 1, -1, -1):
        for x in range(width):
            z = depth_buffer[y][x]

            # Sky
            if not show_landscape or z > depth:
                ny = (y - screen_height * render_params.horizon) / (
                    screen_height * render_params.horizon
                )
                rows[y][x] = atmosphere.texture(x, ny, ny, seed)
                continue

            # Terrain - check for edges
            cell = get_color_at_point(x, z)

            char, fg, bg = cell
            # FIXME: Renable this kind of edge detection
            # lz = depth_buffer[y][max(0, x - 1)]
            # rz = depth_buffer[y][min(x + 1, width - 1)]
            # if lz > z:
            #     bg = get_color_at_point(x, lz)
            #     char = "🭋"
            #     if rz > z:
            #         char = "🭯"
            # elif rz > z:
            #     bg = get_color_at_point(x, rz)
            #     char = "🭀"

            rows[y][x] = (char, fg, bg)

    # _render_lines(lines)

    # Add trees -- this is kinda hacky, to allow trees to protrude above
    # the horizon
    for y in range(screen_height - 1, -1, -1):
        for x in range(width):
            z = depth_buffer[y][x]
            has_tree = tree_map[x][z] if z <= depth else False
            if has_tree and rows[y][x][0] == " ":
                current = rows[y][x]
                char = random.choice(TREE_CHARS)
                char2 = random.choice(TREE_CHARS)
                t = z / depth  # 0 = near, 1 = far
                # Vary hue slightly (more yellow or more blue-green)
                hue_shift = noise_2d(x, z, seed=1234) * 40 - 20
                # Vary saturation/brightness
                bright_var = noise_2d(x, z, seed=5678) * 100 - (200 * t)

                fg = (
                    int(max(0, min(255, 30 + t * 40 + hue_shift * 0.5))),
                    int(max(0, min(255, 180 + t * 50 + bright_var))),
                    int(max(0, min(255, 20 + t * 30 - hue_shift * 0.3))),
                )
                f = 0.8
                bg = (
                    int(current[2][0] * f),
                    int(current[2][1] * f),
                    int(current[2][2] * f),
                )

                rows[y][x] = (char2, lerp_color(fg, current[2], 0.6), bg)
                # above = min(screen_height - 1, y + 1)
                # current_above = lines[above][x]
                # if depth_buffer[y][z] >= depth:
                #     fg = lerp_color(fg, current_above[2], 0.1)
                #     if atmosphere.filter:
                #         fg = atmosphere.filter(x, z, y, fg)
                #     lines[above][x] = (
                #         char,
                #         fg,
                #         current_above[2],
                #     )

    # Add haze and filter
    for y in range(screen_height):
        for x in range(width):
            z = depth_buffer[y][x]
            # if z > depth:
            #     continue
            hf = (0.2 * z / depth) ** 2
            cell = rows[y][x]
            fg = cell[1]
            bg = cell[2]
            if hf > 0:
                haze = lerp_color(rgb("#aabbff"), rgb("#64a5ff"), y / screen_height)
                fg = lerp_color(fg, haze, hf)
                bg = lerp_color(bg, haze, hf)
            if atmosphere.filter:
                fg = atmosphere.filter(x, z, y, fg)
                bg = atmosphere.filter(x, z, y, bg)
            rows[y][x] = (cell[0], fg, bg)

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


def render_plan(biome_map, tree_map, seed: int) -> None:
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
