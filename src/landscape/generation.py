from landscape.biomes import Biome
from landscape.utils import fractal_noise_2d, lerp


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
            row.append(result)
        heights.append(row)

    return heights


def generate_tree_map(
    width: int,
    depth: int,
    biome_map: list[list[tuple[Biome, Biome, float]]],
    seed: int,
) -> list[list[bool]]:
    """Generate a 2D tree placement map based on biome density."""
    tree_map = []
    for x in range(width):
        row = []
        for z in range(depth):
            biome1, biome2, blend = biome_map[x][z]
            density = lerp(biome1.tree_density, biome2.tree_density, blend)

            # Use noise for organic clustering
            n = fractal_noise_2d(
                x, z, octaves=2, persistence=0.6, scale=0.15, seed=seed + 5000
            )
            # Trees appear where noise exceeds threshold based on density
            threshold = 1.0 - density
            has_tree = n > threshold and density > 0
            row.append(has_tree)
        tree_map.append(row)
    return tree_map
