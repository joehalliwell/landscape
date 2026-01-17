#!/usr/bin/env python3
"""Landscape: A landscape generator for the terminal."""

import types
from enum import Enum
from typing import Annotated, Union, get_args, get_origin

from cyclopts import App, Group, Parameter, Token

from landscape.atmosphere import (
    AtmospherePreset,
    Season,
    TimeOfDay,
    Weather,
)
from landscape.biomes import BIOMES, BiomePreset
from landscape.generation import generate
from landscape.rendering import (
    RenderParams,
    render,
    render_plan,
)
from landscape.signature import SceneConfig
from landscape.utils import clear_console, find_shortcode_match, slugify

app = App(help="Generate landscapes for the terminal.")
app.register_install_completion_command()

GENERATION_GROUP = Group.create_ordered("Generation parameters")
RENDER_GROUP = Group.create_ordered("Rendering parameters")
DISPLAY_GROUP = Group.create_ordered("Display parameters")


def _show_command(render_params, config: SceneConfig):
    def param(parameter, val):
        if val is None:
            return ""
        return f"\033[2m--{parameter}\033[m {slugify(str(val))}"

    biome_names = config.to_biome_names()
    atmosphere_name = config.to_atmosphere_name()

    bits = [
        "landscape",
        param("seed", config.seed),
        *([param("biome", name) for name in biome_names]),
        param("atmosphere", atmosphere_name),
    ]
    print(" ".join(bit for bit in bits if bit))


@Parameter(n_tokens=1, accepts_keys=False)
def convert_shortcode(target_type, tokens: tuple[Token]):
    """Cyclopts converter to handle single/multiple enum conversion with shortcode matching."""
    assert isinstance(tokens, tuple), "expected tuple of tokens"

    origin = get_origin(target_type)
    args = get_args(target_type)

    # Handle Union types (e.g., MyEnum | None)
    if origin is Union or origin is types.UnionType:
        enum_candidates = [a for a in args if a is not type(None)]
        if len(enum_candidates) == 1 and issubclass(enum_candidates[0], Enum):
            enum_type = enum_candidates[0]
            is_sequence = False
        else:
            raise ValueError(f"Unsupported union type: {target_type}")
    # Handle sequence types (e.g., list[MyEnum])
    elif origin in (list, tuple):
        enum_type = args[0]
        is_sequence = True
    # Handle direct enum type
    elif isinstance(target_type, type) and issubclass(target_type, Enum):
        enum_type = target_type
        is_sequence = False
    else:
        raise ValueError(f"Unsupported type: {target_type}")

    options = [v.name for v in enum_type]
    matches = [find_shortcode_match(token.value, options) for token in tokens]
    result = [enum_type[m] for m in matches]

    return result if is_sequence else result[0]


@app.default
def main(
    signature: Annotated[
        str | None,
        Parameter(
            name=["--signature", "-S"],
            help="Regenerate from a signature code.",
            show_default=False,
            group=GENERATION_GROUP,
        ),
    ] = None,
    *,
    preset: Annotated[
        BiomePreset | None,
        Parameter(
            name=["--preset", "-p"],
            help=f"Specify preset. Options: {', '.join(p.name.lower() for p in BiomePreset)}.",
            group=GENERATION_GROUP,
            converter=convert_shortcode,
        ),
    ] = None,
    seed: Annotated[
        int | None,
        Parameter(
            name=["--seed", "-s"],
            help="Random seed.",
            show_default=False,
            group=GENERATION_GROUP,
        ),
    ] = None,
    render_params: Annotated[
        RenderParams, Parameter(name="*", group=RENDER_GROUP)
    ] = RenderParams(),
    biome_names: Annotated[
        list[str],
        Parameter(
            name=["--biome", "-b"],
            help=f"Specify biomes; may provide multiple; order is important.Options: {', '.join(BIOMES)}.",
            show_default=False,
            negative_iterable="",
            group=GENERATION_GROUP,
        ),
    ] = [],
    atmosphere: Annotated[
        AtmospherePreset | None,
        Parameter(
            name=["--atmosphere", "-a"],
            help=f"Specify atmosphere preset. Options: {', '.join(p.name.lower() for p in AtmospherePreset)}.",
            group=GENERATION_GROUP,
            converter=convert_shortcode,
        ),
    ] = None,
    time_of_day: Annotated[
        TimeOfDay | None,
        Parameter(
            name=["--time", "-t"],
            help=f"Time of day. Options: {', '.join(t.name.lower() for t in TimeOfDay)}.",
            group=GENERATION_GROUP,
            converter=convert_shortcode,
        ),
    ] = None,
    season: Annotated[
        Season | None,
        Parameter(
            name=["--season"],
            help=f"Season. Options: {', '.join(s.name.lower() for s in Season)}.",
            group=GENERATION_GROUP,
            converter=convert_shortcode,
        ),
    ] = None,
    weather: Annotated[
        Weather | None,
        Parameter(
            name=["--weather"],
            help=f"Weather. Options: {', '.join(w.name.lower() for w in Weather)}.",
            group=GENERATION_GROUP,
            converter=convert_shortcode,
        ),
    ] = None,
    show_command: Annotated[
        bool,
        Parameter(
            help="Show a canonical command to reproduce the scene.", group=DISPLAY_GROUP
        ),
    ] = False,
    show_plan: Annotated[
        bool, Parameter(help="Show a top-down plan of the biomes.", group=DISPLAY_GROUP)
    ] = False,
    clear: Annotated[
        bool, Parameter(help="Clear console before displaying.", group=DISPLAY_GROUP)
    ] = True,
):
    # STEP 1: Handle command line arguments
    try:
        config = SceneConfig.from_runtime_args(
            preset=preset,
            seed=seed,
            biome_names=biome_names,
            atmosphere=atmosphere,
            time_of_day=time_of_day,
            season=season,
            weather=weather,
            signature=signature,
        )

        width, height = render_params.width, render_params.height
        depth = max(width // 4, height)
    except ValueError as e:
        print(f"ERROR: {e}")
        raise SystemExit(1)

    # STEP 2: Generate landscape
    landscape = generate(config, width, depth, height)

    # STEP 3: Display outputs
    if clear:
        clear_console()

    if show_plan:
        render_plan(landscape.biome_map, landscape.seed)

    if show_command:
        _show_command(render_params, config)

    render(landscape, render_params, signature=config.encode())


if __name__ == "__main__":
    app()
