#!/usr/bin/env python3
"""ASCII landscape generator - voxel-based with 2D projection."""

import random
from typing import Annotated

from cyclopts import App, Parameter

from landscape.biomes import BIOMES, Biome
from landscape.generation import (
    generate_biome_map,
    generate_height_map,
    generate_tree_map,
)
from landscape.rendering import (
    RenderParams,
    render_with_depth,
    rgb_to_ansi,
)
from landscape.utils import rand_choice

# TODO: Standardize haze (use gradients for biome height mapping)
# TODO: Generalize tree detailing mechanism
# TODO: Add beach
# TODO: Add time of day
# TODO: Add seasons
# TODO: Add weather
# TODO: Add shadows!?

app = App(help="Generated landscapes for the terminal")


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


# Predefined multi-biome combinations (near -> far)
LANDSCAPES = {
    "coastal": ["ocean", "plains", "forest"],
    "mountain_valley": ["plains", "forest", "mountains"],
    "alpine_lake": ["ocean", "alpine", "mountains"],
    "tropical": ["ocean", "jungle", "forest"],
    "arctic": ["ocean", "ice"],
    "desert_oasis": ["desert", "mountains"],
    "fjord": ["ocean", "mountains"],
    "highlands": ["plains", "alpine", "mountains"],
    "tropical_island": ["ocean", "jungle", "ocean"],
}


def _get_biomes(biome_names: list[str], seed) -> list[Biome]:
    if biome_names == []:
        # Random landscape
        landscape_name = rand_choice(list(LANDSCAPES.keys()), seed)
        biome_names = LANDSCAPES[landscape_name]

    biome_names = [name.lower() for name in biome_names]
    for name in biome_names:
        if name not in BIOMES:
            print(f"Available: {', '.join(BIOMES.keys())}")
            raise ValueError(f"Unknown biome: {name}")

    if len(biome_names) == 1:
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
        partner = rand_choice(
            complements.get(biome_names[0], list(BIOMES.keys())), seed
        )
        biome_names += [partner]

    biomes = [BIOMES[name] for name in biome_names]
    assert len(biomes) > 1
    return biomes


def _clear_console():
    "Clear the screen"
    print("\033[0;0H", end="")  # Move cursor
    print("\033[2J", end="")  # Clear screen


@app.default
def main(
    render_params: Annotated[
        RenderParams, Parameter(name="*", group="Render parameters")
    ] = RenderParams(),
    list_biomes: Annotated[
        bool, Parameter(help="Display biomes and exit.", negative="")
    ] = False,
    biome_names: Annotated[
        list[str],
        Parameter(
            name="biome",
            help="Specify biomes; may provide multiple; order is important.",
            show_default=False,
            negative_iterable="",
        ),
    ] = [],
    seed: Annotated[
        int | None, Parameter(help="Random seed.", show_default=False)
    ] = None,
    clear: Annotated[
        bool, Parameter(help="Clear console before displaying.")
    ] = True,
):
    if seed is None:
        seed = random.randint(0, 100000)
        # logger.info(f"Using random seed {seed}")
    assert seed is not None

    # Parse biome(s) from command line
    if list_biomes:
        print("Biomes:")
        for name, biome in BIOMES.items():
            print(f"  {name}: {biome.name}")
        print("\nLandscape presets:")
        for name, biome_list in LANDSCAPES.items():
            print(f"  {name}: {' + '.join(biome_list)}")
        return

    width, height = render_params.width, render_params.height
    depth = width

    biomes = _get_biomes(biome_names, seed)

    # Generate landscape
    biome_map = generate_biome_map(width, depth, biomes, seed)
    tree_map = generate_tree_map(width, depth, biome_map, seed)
    height_map = generate_height_map(width, depth, height, biome_map, seed)
    if clear:
        _clear_console()
    if False:
        render_plan(biome_map, tree_map)

    # Scale depth, oblique, and height to fit terminal
    label = " + ".join(b.name for b in biomes)
    print(f"{label} | {width}x{height} | {seed} ")

    # render_params = RenderParams(width, height)
    render_with_depth(render_params, height_map, biome_map, tree_map, seed)


if __name__ == "__main__":
    app()
