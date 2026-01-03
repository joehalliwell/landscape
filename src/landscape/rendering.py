import random

from landscape.biomes import TREE_CHARS, Biome
from landscape.utils import lerp_color, noise_2d, rgb


def rgb_to_ansi(r: int, g: int, b: int) -> str:
    """Convert RGB to 24-bit ANSI foreground color code."""
    return f"\033[38;2;{r};{g};{b}m"


def rgb_to_ansi_fg_bg(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> str:
    """Convert RGB to 24-bit ANSI foreground and background color codes."""
    return f"\033[38;2;{fg[0]};{fg[1]};{fg[2]};48;2;{bg[0]};{bg[1]};{bg[2]}m"


RESET = "\033[0m"


def render_with_depth(
    depth_buffer: list[list[int]],
    height_map: list[list[float]],
    biome_map: list[list[tuple[Biome, Biome, float]]],
    tree_map: list[list[bool]],
) -> None:
    """Render 2D heightmap with depth shading and oblique projection.

    oblique: how much to shift y per z unit (0 = front view, 1 = steep oblique)
    """
    width = len(tree_map)
    depth = len(biome_map[0])
    screen_height = len(depth_buffer)

    lines = [
        [(".", rgb("#ff00ff"), rgb("#ff00ff")) for _ in range(width)]
        for _ in range(screen_height)
    ]

    haze = rgb("#aabbff")

    def get_color_at_point(x: int, z: int) -> tuple[int, int, int]:
        """Get blended color for a given point using biome map."""

        if z > depth:
            # FIXME: Handle sky box properly
            return rgb("#aabbff")

        biome1, biome2, blend = biome_map[x][z]

        # Heightmap color variation
        y = height_map[x][z]
        # assert y >= 0 and y <= 1, y

        y1 = (height_map[x][z] - biome1.base_height) / biome1.height_scale
        y2 = (height_map[x][z] - biome2.base_height) / biome2.height_scale

        # Get colors for current depth in each biome
        c1 = lerp_color(biome1.color_lo, biome1.color_hi, y1)
        c2 = lerp_color(biome2.color_lo, biome2.color_hi, y2)
        c3 = lerp_color(c1, c2, blend)
        return c3

    # Convert to lines with color and edge detection
    for y in range(screen_height - 1, -1, -1):
        for x in range(width):
            z = depth_buffer[y][x]
            if z > depth:
                # Sky
                bg = lerp_color(rgb("#aabbff"), rgb("#64a5ff"), y / screen_height)
                fg = lerp_color(rgb("#aabbff"), rgb("#8899ff"), y / screen_height)
                lines[y][x] = (".", fg, bg)
                continue

            # Terrain - check for edges
            color = get_color_at_point(x, z)

            # Interior - use biome chars if defined
            biome1, biome2, blend = biome_map[x][z]
            dominant = biome1 if blend <= 0.5 else biome2
            # dominant = biome1
            if dominant.chars:
                # char = dominant.chars[(x + y + z) % len(dominant.chars)]
                char = random.choice(dominant.chars)

                # Highlight foreground, biome color background
                highlight = (
                    min(255, int(color[0] * 1.0 + 40)),
                    min(255, int(color[1] * 1.0 + 40)),
                    min(255, int(color[2] * 1.0 + 40)),
                )
                lines[y][x] = (char, highlight, color)
                continue

            char = "█"
            fg = color
            bg = color
            lz = depth_buffer[y][max(0, x - 1)]
            rz = depth_buffer[y][min(x + 1, width - 1)]
            if lz > z:
                bg = get_color_at_point(x, lz)
                char = "🭋"
                if rz > z:
                    char = "🭯"
            elif rz > z:
                bg = get_color_at_point(x, rz)
                char = "🭀"

            lines[y][x] = (char, fg, bg)

    # Add trees
    for y in range(screen_height - 1, -1, -1):
        for x in range(width):
            z = depth_buffer[y][x]
            has_tree = tree_map[x][z] if z <= depth else False
            above = min(screen_height - 1, y + 1)
            if has_tree:
                current = lines[y][x]
                current_above = lines[above][x]
                char = random.choice(TREE_CHARS)
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
                f = 0.6
                bg = (
                    int(current[2][0] * f),
                    int(current[2][1] * f),
                    int(current[2][2] * f),
                )
                lines[y][x] = (current[0], current[1], bg)
                lines[above][x] = (char, fg, current_above[2])

    # Add haze
    for y in range(screen_height):
        for x in range(width):
            z = depth_buffer[y][x]
            # if z > depth:
            #     continue
            hf = (0.7 * z / depth) ** 2
            cell = lines[y][x]
            haze = lerp_color(rgb("#aabbff"), rgb("#64a5ff"), y / screen_height)
            fg = lerp_color(cell[1], haze, hf)
            bg = lerp_color(cell[2], haze, hf)
            lines[y][x] = (cell[0], fg, bg)

    for y in range(screen_height - 1, -1, -1):
        for x in range(width):
            c, fg, bg = lines[y][x]
            print(rgb_to_ansi_fg_bg(fg, bg), end="")
            print(c, end="")
        print()


def make_depth_buffer(height_map, height, horizon=0.5):
    """
    Project the height map to a depth buffer.
    """
    width = len(height_map)
    depth = len(height_map[0])

    # Calculate the projection -- think slightly spherical!
    oblique = (height * horizon) / depth
    background_shrink = 2.0
    foreground_shrink = 0.5
    spherical = 0.2

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

    return buffer
