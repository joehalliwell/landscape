from dataclasses import dataclass
from typing import Callable

from landscape.textures import Detail, Texture
from landscape.utils import RGB, cmap, slugify


@dataclass(kw_only=True)
class Atmosphere(Texture):
    name: str = "Anonymous"
    filter: Callable[[float, float, float, RGB], RGB] | None = None


ATMOSPHERES = {
    slugify(a.name): a
    for a in [
        Atmosphere(name="Clear day", color_map=cmap("#aabbff", "#003a8c")),
        Atmosphere(
            name="Clear night",
            color_map=cmap("#000080", "#000000"),
            details=[
                Detail(
                    name="Bright Stars",
                    chars=".",
                    density=0.01,
                    color_map=cmap("#ffffff"),
                    blend=0.2,
                ),
                Detail(
                    name="Dim Stars",
                    chars=".",
                    density=0.05,
                    color_map=cmap("#ffffff", "#cccccc"),
                    blend=0.7,
                ),
            ],
            filter=lambda x, z, y, c: (
                int(c[0] * 0.35),
                int(c[1] * 0.35),
                int(c[2] * 0.4 + 20),
            ),
        ),
        Atmosphere(
            name="Dawn",
            color_map=cmap(
                "#ecb8ec", "#F6FF8F", "#1C5768", *["#083563" for _ in range(5)]
            ),
            details=[
                Detail(
                    name="Bright Stars",
                    chars=".",
                    density=0.01,
                    color_map=cmap("#ffffff"),
                    blend=0.2,
                ),
                Detail(
                    name="Dim Stars",
                    chars=".",
                    density=0.05,
                    color_map=cmap("#ffffff", "#cccccc"),
                    blend=0.7,
                ),
            ],
            filter=lambda x, z, y, c: (
                int(c[0] * 0.9 + 20),
                int(c[1] * 0.7 + 10),
                int(c[2] * 0.6),
            ),
        ),
    ]
}


def get_atmosphere(key: str):
    return ATMOSPHERES[slugify(key)]
