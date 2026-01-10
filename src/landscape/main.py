#!/usr/bin/env python3
"""Landscape: A landscape generator for the terminal."""

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
from landscape.signature import GenerationConfig
from landscape.utils import clear_console, rand_choice, slugify

app = App(help="Generated landscapes for the terminal.")


# Predefined multi-biome combinations (near -> far)
PRESETS = {
    "coastal": ["ocean", "plains", "forest", "plains"],
    "mountain_valley": ["plains", "forest", "mountains"],
    "alpine_lake": ["ocean", "alpine", "mountains"],
    "tropical": ["ocean", "jungle", "forest"],
    "arctic": ["ocean", "ice", "ocean", "ice"],
    "desert_oasis": ["desert", "mountains"],
    "fjord": ["ocean", "mountains"],
    "highlands": ["plains", "alpine", "mountains"],
    "tropical_island": ["ocean", "jungle", "ocean"],
}

COMPLEMENTS = {
    "ocean": ["plains", "forest"],
    "forest": ["plains", "mountains"],
    "mountains": ["alpine", "forest"],
    "jungle": ["ocean", "plains"],
    "ice": ["ocean", "mountains"],
    "plains": ["forest", "mountains"],
    "desert": ["plains", "mountains"],
    "alpine": ["mountains", "forest"],
}


def _fuzzy_match(input: str, options: list[str], seed: int) -> str:
    input = slugify(input)
    matching = [option for option in options if input in option]
    if len(matching) == 0:
        raise ValueError(
            f"Could not find option matching '{input}' in: {', '.join(options)}"
        )
    return rand_choice(matching, seed)


def _get_biomes(biome_names: list[str], seed: int) -> tuple[list[Biome], list[str]]:
    biome_names = [_fuzzy_match(name, list(BIOMES), seed) for name in biome_names]

    if len(biome_names) == 1:
        # Single biome specified - pair with a complementary one
        partner = rand_choice(COMPLEMENTS[biome_names[0]], seed)
        biome_names += [partner]

    biomes = [BIOMES[name] for name in biome_names]
    return biomes, biome_names


def _get_atmosphere(atmosphere_name: str, seed: int):
    if atmosphere_name is None:
        atmosphere_name = rand_choice(list(ATMOSPHERES), seed)
    return ATMOSPHERES[_fuzzy_match(atmosphere_name, list(ATMOSPHERES), seed)]


def _get_preset(preset_name: str, seed: int):
    biomes = PRESETS[_fuzzy_match(preset_name, list(PRESETS), seed)]
    atmospheres = list(ATMOSPHERES)
    atmosphere = rand_choice(atmospheres, seed)
    return biomes, atmosphere


def _show_command(render_params, preset_name, biomes, atmosphere, seed):
    def param(parameter, val):
        if val is None:
            return ""
        return f"\033[2m--{parameter}\033[m {slugify(str(val))}"

    bits = [
        "landscape",
        param("seed", seed),
        param("preset", preset_name),
        *([param("biome", biome.name) for biome in biomes] if not preset_name else []),
        param("atmosphere", atmosphere.name),
    ]
    print(" ".join(bit for bit in bits if bit))


@app.default
def main(
    preset_name: Annotated[
        str | None,
        Parameter(
            name=["--preset", "-p"],
            help=f"Specify preset. Options: {', '.join(PRESETS)}.",
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
    signature: Annotated[
        str | None,
        Parameter(
            name=["--signature", "-S"],
            help="Regenerate from a signature code.",
            show_default=False,
        ),
    ] = None,
    show_command: Annotated[
        bool, Parameter(help="Show a canonical command to reproduce the scene.")
    ] = True,
    show_plan: Annotated[
        bool, Parameter(help="Show a top-down plan of the biomes.")
    ] = False,
    clear: Annotated[bool, Parameter(help="Clear console before displaying.")] = True,
):
    # STEP 1: Handle command line arguments
    _preset_name = None
    try:
        # If signature provided, decode and use those parameters
        if signature:
            config = GenerationConfig.decode(signature)
            seed = config.seed
            biome_names = config.to_biome_names()
            atmosphere_name = config.to_atmosphere_name()
        elif seed is None:
            seed = random.randint(0, 100000)
            # logger.info(f"Using random seed {seed}")
        assert seed is not None

        width, height = render_params.width, render_params.height
        depth = max(width // 4, height)

        # If neither biomes nor preset specified, pick a random preset
        if not signature:
            _preset_name = (
                _fuzzy_match(preset_name, list(PRESETS), seed)
                if preset_name is not None
                else rand_choice(list(PRESETS), seed)
            )
            _biome_names, _atmosphere_name = _get_preset(_preset_name, seed)
            if biome_names == []:
                biome_names = _biome_names
            if atmosphere_name is None:
                atmosphere_name = _atmosphere_name

        assert biome_names is not None
        assert atmosphere_name is not None
        biomes, biome_keys = _get_biomes(biome_names, seed)
        atmosphere = _get_atmosphere(atmosphere_name, seed)
    except ValueError as e:
        print(f"ERROR: {e}")
        raise SystemExit(1)

    # STEP 2: Generate landscape
    biome_map = generate_biome_map(width, depth, biomes, seed)
    tree_map = generate_tree_map(width, depth, biome_map, seed)
    height_map = generate_height_map(width, depth, height, biome_map, seed)

    # STEP 3: Display outputs
    if clear:
        clear_console()
    if show_plan:
        render_plan(biome_map, tree_map, seed)

    if show_command:
        # Generate and display signature
        config = GenerationConfig.from_params(
            seed=seed,
            biome_names=biome_keys,
            atmosphere_name=slugify(atmosphere.name),
        )
        print(f"\033[2mSignature:\033[m {config.encode()}")

        _show_command(
            render_params,
            _preset_name if (preset_name and not signature) else None,
            biomes,
            atmosphere,
            seed,
        )

    render_with_depth(render_params, height_map, biome_map, tree_map, atmosphere, seed)


if __name__ == "__main__":
    app()
