#!/usr/bin/env python3
"""ASCII landscape generator - voxel-based with 2D projection."""

import random

from landscape.biomes import BIOMES, Biome
from landscape.generation import (
    generate_biome_map,
    generate_height_map,
    generate_tree_map,
)
from landscape.rendering import make_depth_buffer, render_with_depth, rgb_to_ansi

# TODO: Standardize haze (use gradients for biome height mapping)
# TODO: Generalize tree detailing mechanism
# TODO: Add beach
# TODO: Add time of day
# TODO: Add seasons
# TODO: Add weather
# TODO: Add shadows!?


def render_plan(biome_map, tree_map):
    width = len(biome_map)
    depth = len(biome_map[0])

    rows = []
    for z in range(depth, 0, -1):
        row = []
        for x in range(width):
            biome: Biome = biome_map[x][z - 1][0]
            c = "^" if tree_map[x][z - 1] else biome.name[0]
            row.append(rgb_to_ansi(*biome.color_lo))
            row.append(c)
        rows.append("".join(row))
    print("\n".join(rows))


def render_depth_buffer(depth_map):
    width = len(depth_map[0])
    height = len(depth_map)

    for y in range(height - 1, -1, -1):
        row = []
        for x in range(width):
            d = 255 - (depth_map[y][x][0] * 8)
            d = min(255, max(0, d))
            row.append(rgb_to_ansi(d, d, d))
            row.append("█")
        print("".join(row))


# Predefined multi-biome combinations (near -> far)
LANDSCAPES = {
    "coastal": ["ocean", "plains", "forest"],
    "mountain_valley": ["plains", "forest", "mountains"],
    "alpine_lake": ["ocean", "alpine", "mountains"],
    "tropical": ["ocean", "jungle"],
    "arctic": ["ocean", "ice"],
    "desert_oasis": ["plains", "desert", "mountains"],
    "fjord": ["ocean", "mountains"],
    "highlands": ["plains", "alpine"],
}


def main():
    import shutil
    import sys

    landscape_name = None
    # Parse biome(s) from command line
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "list":
            print("Biomes:")
            for name, biome in BIOMES.items():
                print(f"  {name}: {biome.name}")
            print("\nLandscape presets:")
            for name, biome_list in LANDSCAPES.items():
                print(f"  {name}: {' + '.join(biome_list)}")
            print("\nCustom: python landscape.py ocean,forest,mountains")
            print("(Always uses 2+ biomes with organic blending)")
            return
        elif arg in LANDSCAPES:
            biome_names = LANDSCAPES[arg]
        elif "," in arg:
            # Custom comma-separated biomes
            biome_names = [b.strip() for b in arg.split(",")]
            for name in biome_names:
                if name not in BIOMES:
                    print(f"Unknown biome: {name}")
                    print(f"Available: {', '.join(BIOMES.keys())}")
                    return
        elif arg in BIOMES:
            # Single biome specified - pair with a complementary one
            complements = {
                "ocean": ["plains", "forest"],
                "forest": ["plains", "mountains"],
                "mountains": ["alpine", "forest"],
                "jungle": ["ocean", "plains"],
                "ice": ["ocean", "mountains"],
                "plains": ["forest", "mountains"],
                "desert": ["plains", "mountains"],
                "alpine": ["mountains", "forest"],
            }
            partner = random.choice(complements.get(arg, list(BIOMES.keys())))
            biome_names = [arg, partner]
        else:
            print(f"Unknown biome/landscape: {arg}")
            print("Use 'list' to see options")
            return
    else:
        # Random landscape
        landscape_name = random.choice(list(LANDSCAPES.keys()))
        biome_names = LANDSCAPES[landscape_name]

    biomes = [BIOMES[name] for name in biome_names]

    term_size = shutil.get_terminal_size((120, 30))
    width = term_size.columns
    height = max(8, term_size.lines - 10)  # Leave room for prompt/status
    depth = width

    # Scale depth, oblique, and height to fit terminal
    seed = random.randint(0, 100000)
    label = " + ".join(b.name for b in biomes)
    if landscape_name:
        label += f" ({landscape_name})"
    print(f"{label} | {width}x{height} | {seed} ")

    # Generate landscape
    biome_map = generate_biome_map(width, depth, biomes, seed)
    tree_map = generate_tree_map(width, depth, biome_map, seed)
    height_map = generate_height_map(width, depth, height, biome_map, seed)
    depth_buffer = make_depth_buffer(height_map, height)

    if False:
        render_plan(biome_map, tree_map)
    if False:
        render_depth_buffer(depth_buffer)

    render_with_depth(depth_buffer, height_map, biome_map, tree_map)


if __name__ == "__main__":
    main()
