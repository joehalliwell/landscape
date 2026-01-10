#!/usr/bin/env python3
"""Landscape: A landscape generator for the terminal."""

from typing import Annotated

from cyclopts import App, Parameter

from landscape.atmospheres import ATMOSPHERES
from landscape.biomes import BIOMES, PRESETS
from landscape.generation import generate
from landscape.rendering import (
    RenderParams,
    render,
    render_plan,
)
from landscape.signature import GenerateParams
from landscape.utils import clear_console, slugify

app = App(help="Generated landscapes for the terminal.")


def _show_command(render_params, config: GenerateParams):
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
    ] = False,
    show_plan: Annotated[
        bool, Parameter(help="Show a top-down plan of the biomes.")
    ] = False,
    clear: Annotated[bool, Parameter(help="Clear console before displaying.")] = True,
):
    # STEP 1: Handle command line arguments
    try:
        config = GenerateParams.from_runtime_args(
            preset_name=preset_name,
            seed=seed,
            biome_names=biome_names,
            atmosphere_name=atmosphere_name,
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
        render_plan(landscape.biome_map, landscape.tree_map, landscape.seed)

    if show_command:
        _show_command(render_params, config)

    render(landscape, render_params, signature=config.encode())


if __name__ == "__main__":
    app()
