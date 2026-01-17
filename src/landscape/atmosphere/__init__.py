from enum import Enum

from landscape.atmosphere.filters import (
    CellFilter,
    ColorGradeFilter,
    FilterPipeline,
    HazeFilter,
    PrecipitationFilter,
)
from landscape.atmosphere.season import Season
from landscape.atmosphere.time import TimeOfDay
from landscape.atmosphere.weather import Weather


class AtmospherePreset(Enum):
    """Named atmosphere preset combinations."""

    CLEAR_DAY = (TimeOfDay.NOON, Season.MID_SUMMER, Weather.CLEAR)
    FOGGY_DAY = (TimeOfDay.NOON, Season.MID_SUMMER, Weather.FOGGY)
    RAINY_DAY = (TimeOfDay.NOON, Season.MID_SUMMER, Weather.RAINY)
    SNOWY_DAY = (TimeOfDay.NOON, Season.MID_WINTER, Weather.SNOWY)
    CLEAR_NIGHT = (TimeOfDay.NIGHT, Season.MID_SUMMER, Weather.CLEAR)
    APRICOT_DAWN = (TimeOfDay.DAWN, Season.MID_SUMMER, Weather.CLEAR)
    OMINOUS_SUNSET = (TimeOfDay.DUSK, Season.LATE_AUTUMN, Weather.CLEAR)

    @property
    def time(self) -> TimeOfDay:
        return self.value[0]

    @property
    def season(self) -> Season:
        return self.value[1]

    @property
    def weather(self) -> Weather:
        return self.value[2]


__all__ = [
    "AtmospherePreset",
    "CellFilter",
    "ColorGradeFilter",
    "FilterPipeline",
    "HazeFilter",
    "PrecipitationFilter",
    "Season",
    "TimeOfDay",
    "Weather",
]
