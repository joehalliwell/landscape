from dataclasses import dataclass
from typing import Callable

from landscape.textures import Detail, Texture
from landscape.utils import RGB, clamp_col, cmap, slugify


@dataclass(kw_only=True)
class Atmosphere(Texture):
    name: str = "Anonymous"
    filter: Callable[[float, float, float, RGB], RGB] | None = None


ATMOSPHERES = {
    slugify(a.name): a
    for a in [
        Atmosphere(
            name="Clear day",
            color_map=cmap("#aabbff", "#006aff", "#0069fc"),
            filter=lambda x, z, y, c: clamp_col((c[0] * 1.1, c[1] * 1.1, c[2] * 1.1)),
        ),
        Atmosphere(
            name="Clear night",
            color_map=cmap("#06063A", "#000000"),
            details=[
                Detail(
                    name="Bright Stars",
                    chars=".",
                    density=0.01,
                    color_map=cmap("#ffffff"),
                    blend=0.1,
                ),
                Detail(
                    name="Dim Stars",
                    chars=".",
                    density=0.05,
                    color_map=cmap("#ffffff", "#cccccc"),
                    blend=0.4,
                ),
            ],
            filter=lambda x, z, y, c: clamp_col(
                (c[0] * 0.4 - 20, c[1] * 0.4 - 20, c[2] * 0.45 + 20)
            ),
        ),
        Atmosphere(
            name="Dawn",
            color_map=cmap(
                "#ecb8ec",
                "#F6FF8F",
                "#1C5768",
                "#083563",
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
            filter=lambda x, z, y, c: clamp_col(
                (
                    int(c[0] * 0.9 + 20),
                    int(c[1] * 0.7 + 10),
                    int(c[2] * 0.6),
                )
            ),
        ),
        Atmosphere(
            name="Sunset",
            color_map=cmap(
                "#FFD500",
                "#ff0800",
                # "#FF8800",
                # "#FF8A7B",
                # "#690000",
                "#480000",
            ),
            details=[
                Detail(
                    name="Bright Stars",
                    chars=".",
                    density=0.01,
                    color_map=cmap("#ffffff"),
                    blend=0.0,
                ),
                Detail(
                    name="Dim Stars",
                    chars=".",
                    density=0.05,
                    color_map=cmap("#ffffff", "#cccccc"),
                    blend=0.3,
                ),
            ],
            filter=lambda x, z, y, c: clamp_col(
                (
                    int(c[0] * 0.3),
                    int(c[1] * 0.2 - 20),
                    int(c[2] * 0.3 - 10),
                )
            ),
        ),
    ]
}


def get_atmosphere(key: str):
    return ATMOSPHERES[slugify(key)]
