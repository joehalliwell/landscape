#!/usr/bin/env python3
"""ASCII landscape generator - voxel-based with 2D projection."""

import random
from typing import Annotated

from cyclopts import App, Parameter

from landscape.atmospheres import ATMOSPHERES
from landscape.biomes import BIOMES, Biome
from landscape.generation import (
    generate_biome_map,
    generate_height_map,
    generate_tree_map,
)
from landscape.rendering import (
    RenderParams,
    render_plan,
    render_with_depth,
)
from landscape.utils import clear_console, rand_choice, slugify

# TODO: Standardize haze (use gradients for biome height mapping)
# TODO: Generalize tree detailing mechanism
# TODO: Add beach
# TODO: Add time of day
# TODO: Add seasons
# TODO: Add weather
# TODO: Add shadows!?

app = App(help="Generated landscapes for the terminal")


# Predefined multi-biome combinations (near -> far)
PRESETS = {
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


def _get_atmosphere(atmosphere_name, seed):
    if atmosphere_name is None:
        atmosphere_name = rand_choice(list(ATMOSPHERES), seed)
    return ATMOSPHERES[slugify(atmosphere_name)]


def _get_preset(preset_name: str, seed):
    biomes = PRESETS[preset_name]
    atmospheres = list(ATMOSPHERES)
    atmosphere = rand_choice(atmospheres, seed)
    return biomes, atmosphere


def _show_command(render_params, preset_name, biomes, atmosphere, seed):
    def param(parameter, val):
        return (
            f"\033[2m--{parameter}\033[m {slugify(str(val))}" if val is not None else ""
        )

    bits = [
        "landscape",
        param("seed", seed),
        param("preset", preset_name),
        *([param("biome", biome.name) for biome in biomes] if not preset_name else []),
        param("atmosphere", atmosphere.name),
    ]
    print(" ".join(bits))


@app.default
def main(
    preset_name: Annotated[
        str | None,
        Parameter(
            name="preset", help=f"Specify preset. Options: {', '.join(PRESETS)}."
        ),
    ] = None,
    seed: Annotated[
        int | None,
        Parameter(name=["--seed", "-s"], help="Random seed.", show_default=False),
    ] = None,
    *,
    render_params: Annotated[
        RenderParams, Parameter(name="*", group="Render parameters")
    ] = RenderParams(),
    biome_names: Annotated[
        list[str],
        Parameter(
            name=["--biome", "-b"],
            help=f"Specify biomes; may provide multiple; order is important.Options: {', '.join(BIOMES)}.",
            show_default=False,
            negative_iterable="",
        ),
    ] = [],
    atmosphere_name: Annotated[
        str | None,
        Parameter(
            name=["--atmosphere", "-a"],
            help=f"Specify atmosphere. Options: {', '.join(ATMOSPHERES)}.",
        ),
    ] = None,
    show_command: bool = True,
    show_plan: bool = False,
    clear: Annotated[bool, Parameter(help="Clear console before displaying.")] = True,
):
    if seed is None:
        seed = random.randint(0, 100000)
        # logger.info(f"Using random seed {seed}")
    assert seed is not None

    width, height = render_params.width, render_params.height
    depth = max(width // 4, height)

    # If neither biomes nor preset specified, pick a random preset
    if not biome_names and not preset_name:
        preset_name = rand_choice(list(PRESETS), seed)

    if preset_name is not None:
        assert preset_name is not None
        _biome_names, _atmosphere_name = _get_preset(preset_name, seed)
        if biome_names == []:
            biome_names = _biome_names
        if atmosphere_name is None:
            atmosphere_name = _atmosphere_name

    biomes = _get_biomes(biome_names, seed)
    atmosphere = _get_atmosphere(atmosphere_name, seed)

    # Generate landscape
    biome_map = generate_biome_map(width, depth, biomes, seed)
    tree_map = generate_tree_map(width, depth, biome_map, seed)
    height_map = generate_height_map(width, depth, height, biome_map, seed)

    if clear:
        clear_console()
    if show_plan:
        render_plan(biome_map, tree_map, seed)

    if show_command:
        _show_command(render_params, preset_name, biomes, atmosphere, seed)

    render_with_depth(render_params, height_map, biome_map, tree_map, atmosphere, seed)


if __name__ == "__main__":
    app()
