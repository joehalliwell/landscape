from dataclasses import dataclass
from typing import TYPE_CHECKING

from landscape.atmosphere import Season, TimeOfDay, Weather
from landscape.biomes import Biome
from landscape.utils import fractal_noise_2d, lerp

if TYPE_CHECKING:
    from landscape.signature import SceneConfig


@dataclass
class Scene:
    width: int
    depth: int
    biome_map: list[list[tuple[Biome, Biome, float]]]
    height_map: list[list[float]]
    time: TimeOfDay
    season: Season
    weather: Weather
    seed: int


def generate(config: "SceneConfig", width: int, depth: int, max_height: int) -> Scene:
    """Generate a complete landscape from configuration."""
    biome_map = generate_biome_map(width, depth, list(config.biomes), config.seed)
    height_map = generate_height_map(width, depth, max_height, biome_map, config.seed)

    return Scene(
        width=width,
        depth=depth,
        biome_map=biome_map,
        height_map=height_map,
        time=config.time,
        season=config.season,
        weather=config.weather,
        seed=config.seed,
    )


def generate_biome_map(
    width: int, depth: int, biomes: list[Biome], seed: int
) -> list[list[tuple[Biome, Biome, float]]]:
    """Generate a 2D biome map with smooth transitions.

    Returns a 2D array of (primary_biome, secondary_biome, blend_factor) tuples.
    Uses noise to create organic biome regions that also trend by depth.
    """
    # Create biome influence maps using noise
    # Each biome gets a noise field; highest value "wins" at each point
    biome_noise = []
    for i, biome in enumerate(biomes):
        noise_field = []
        for x in range(width):
            brow = []
            for z in range(depth):
                # Base noise for this biome
                n = fractal_noise_2d(
                    x,
                    z,
                    octaves=2,
                    persistence=0.5,
                    scale=0.025,
                    seed=seed + i * 1000,
                )

                # Add depth bias: earlier biomes prefer near, later prefer far
                depth_bias = (i / (len(biomes) - 1)) if len(biomes) > 1 else 0.5
                z_normalized = z / depth
                # Bias strength - how much depth matters vs noise
                bias_strength = 0.4
                n += (1.0 - abs(z_normalized - depth_bias) * 2) * bias_strength

                brow.append(n)
            noise_field.append(brow)
        biome_noise.append(noise_field)

    # Build biome map by finding top 2 biomes at each point
    biome_map = []
    for x in range(width):
        row: list[tuple[Biome, Biome, float]] = []
        for z in range(depth):
            # Get noise values for all biomes at this point
            values = [(biome_noise[i][x][z], biomes[i]) for i in range(len(biomes))]
            values.sort(key=lambda v: v[0], reverse=True)

            # Top two biomes
            primary = values[0][1]
            secondary = values[1][1] if len(values) > 1 else primary

            # Blend factor based on difference between top two
            diff = values[0][0] - values[1][0] if len(values) > 1 else 1.0

            # Sharper transitions - less blending
            blend_width = 0.05
            blend = max(0.0, min(1.0, 1.0 - diff / blend_width))

            row.append((primary, secondary, blend))
        biome_map.append(row)

    return biome_map


def generate_height_map(
    width: int,
    depth: int,
    max_height: int,
    biome_map: list[list[tuple[Biome, Biome, float]]],
    seed: int,
) -> list[list[float]]:
    """Generate 2D terrain heights using fractal noise, shaped by biome map."""

    raw = []
    for x in range(width):
        row = []
        for z in range(depth):
            biome1, biome2, blend = biome_map[x][z]

            # Large-scale rolling hills
            h1 = fractal_noise_2d(
                x, z, octaves=2, persistence=0.5, scale=0.02, seed=seed
            )
            # Medium detail
            h2 = fractal_noise_2d(
                x, z, octaves=3, persistence=0.6, scale=0.06, seed=seed + 100
            )
            # Fine detail for roughness
            h3 = fractal_noise_2d(
                x, z, octaves=2, persistence=0.4, scale=0.2, seed=seed + 200
            )

            # Blend roughness between biomes
            rough = lerp(biome1.roughness, biome2.roughness, blend)
            h = (
                h1 * (0.6 - rough * 0.2)
                + h2 * (0.3 + rough * 0.1)
                + h3 * (0.1 + rough * 0.1)
            )
            row.append(h)
        raw.append(row)

    # Find global min/max for normalization
    all_vals = [h for row in raw for h in row]
    min_r, max_r = min(all_vals), max(all_vals)

    heights = []
    for x in range(width):
        row = []
        for z in range(depth):
            biome1, biome2, blend = biome_map[x][z]

            normed = (raw[x][z] - min_r) / (max_r - min_r)
            y1 = normed * biome1.height_scale + biome1.base_height
            y2 = normed * biome2.height_scale + biome2.base_height
            result = lerp(y1, y2, blend)

            # Add detail height
            nx = x / width
            nz = z / depth
            h_mod1 = biome1.get_height_mod(nx, nz, seed)
            h_mod2 = biome2.get_height_mod(nx, nz, seed)
            result += lerp(h_mod1, h_mod2, blend)

            row.append(result)
        heights.append(row)

    return heights
