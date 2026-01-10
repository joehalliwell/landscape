from dataclasses import dataclass
from enum import IntEnum
from typing import Callable

from landscape.textures import Detail, Texture
from landscape.utils import RGB, clamp_col, cmap, slugify


class TimeOfDay(IntEnum):
    """Time of day codes (3 bits)."""

    DAWN = 0
    MORNING = 1
    NOON = 2
    AFTERNOON = 3
    DUSK = 4
    EVENING = 5
    NIGHT = 6
    LATE_NIGHT = 7


class Season(IntEnum):
    """Season codes (4 bits)."""

    EARLY_SPRING = 0
    MID_SPRING = 1
    LATE_SPRING = 2
    EARLY_SUMMER = 3
    MID_SUMMER = 4
    LATE_SUMMER = 5
    EARLY_AUTUMN = 6
    MID_AUTUMN = 7
    LATE_AUTUMN = 8
    EARLY_WINTER = 9
    MID_WINTER = 10
    LATE_WINTER = 11
    # 12-15 reserved


class Weather(IntEnum):
    """Weather condition codes (3 bits)."""

    CLEAR = 0
    PARTLY_CLOUDY = 1
    CLOUDY = 2
    FOGGY = 3
    RAINY = 4
    STORMY = 5
    # 6-7 reserved


@dataclass(kw_only=True)
class Atmosphere(Texture):
    name: str = "Anonymous"
    time: TimeOfDay = TimeOfDay.NOON
    season: Season = Season.MID_SUMMER
    weather: Weather = Weather.CLEAR
    filter: Callable[[float, float, float, RGB], RGB] | None = None


ATMOSPHERES = {
    slugify(a.name): a
    for a in [
        Atmosphere(
            name="Clear day",
            time=TimeOfDay.NOON,
            season=Season.MID_SUMMER,
            weather=Weather.CLEAR,
            color_map=cmap("#aabbff", "#006aff", "#0069fc"),
            filter=lambda x, z, y, c: clamp_col((c[0] * 1.1, c[1] * 1.1, c[2] * 1.1)),
        ),
        Atmosphere(
            name="Clear night",
            time=TimeOfDay.NIGHT,
            season=Season.MID_SUMMER,
            weather=Weather.CLEAR,
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
            name="Apricot dawn",
            time=TimeOfDay.DAWN,
            season=Season.MID_SUMMER,
            weather=Weather.CLEAR,
            color_map=cmap(
                "#ecb8ec",
                "#F6FF8F",
                "#99CCDA",
                "#77AEBD",
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
            name="Ominous sunset",
            time=TimeOfDay.DUSK,
            season=Season.LATE_AUTUMN,
            weather=Weather.STORMY,
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
