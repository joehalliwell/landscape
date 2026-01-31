from typing import Callable

from landscape.atmosphere.filters import (
    CellFilter,
    ColorGradeFilter,
    FilterPipeline,
    HazeFilter,
    PrecipitationFilter,
)
from landscape.atmosphere.season import SEASON_ADJUSTMENTS, Season
from landscape.atmosphere.time import (
    STAR_VISIBILITY,
    TIME_ADJUSTMENTS,
    TIME_SKY_PALETTES,
    TimeOfDay,
)
from landscape.atmosphere.weather import (
    HAZE_SETTINGS,
    PRECIPITATION,
    WEATHER_BRIGHTNESS,
    WEATHER_SKY_OVERRIDES,
    Weather,
)
from landscape.textures import Detail, Texture
from landscape.utils import RGB, clamp_col, cmap


def _make_post_processor(
    time: TimeOfDay, season: Season, weather: Weather
) -> Callable[[float, float, float, RGB], RGB]:
    """Create post-processor combining time, season, and weather effects."""
    time_brightness, warmth, blue = TIME_ADJUSTMENTS[time]
    weather_mult = WEATHER_BRIGHTNESS[weather]
    season_mult, season_r, season_g, season_b = SEASON_ADJUSTMENTS[season]
    final_brightness = time_brightness * weather_mult * season_mult

    def processor(x: float, z: float, y: float, c: RGB) -> RGB:
        return clamp_col(
            (
                int(c[0] * final_brightness + warmth + season_r),
                int(c[1] * final_brightness + season_g),
                int(c[2] * final_brightness + blue + season_b),
            )
        )

    return processor


def _make_star_details(visibility: float) -> list[Detail]:
    """Create star details with given visibility (lower = more visible)."""
    if visibility >= 1.0:
        return []
    return [
        Detail(
            name="Bright Stars",
            chars=".·˙",
            density=0.05,
            frequency=500,
            color_map=cmap("#ffffff"),
            blend=visibility * 0.1,
        ),
        Detail(
            name="Dim Stars",
            chars=".·˙",
            density=0.1,
            frequency=500,
            color_map=cmap("#ffffff", "#cccccc"),
            blend=visibility * 0.4 + 0.3,
        ),
    ]


def get_sky_texture(time: TimeOfDay, season: Season, weather: Weather) -> Texture:
    """Build sky texture from atmosphere components."""
    # Sky color: weather override or time-based
    color_map = WEATHER_SKY_OVERRIDES.get(weather) or TIME_SKY_PALETTES[time]

    # Stars for clear/partly cloudy at appropriate times
    details: list[Detail] = []
    if weather in (Weather.CLEAR, Weather.PARTLY_CLOUDY):
        details = _make_star_details(STAR_VISIBILITY[time])

    return Texture(color_map=color_map, details=details)


def get_filter_pipeline(
    time: TimeOfDay, season: Season, weather: Weather
) -> FilterPipeline:
    """Build filter pipeline from atmosphere components."""
    # Sky color for haze
    color_map = WEATHER_SKY_OVERRIDES.get(weather) or TIME_SKY_PALETTES[time]

    filters: list[CellFilter] = []

    # Haze filter
    haze_power, haze_intensity = HAZE_SETTINGS[weather]
    filters.append(
        HazeFilter(color_map=color_map, power=haze_power, intensity=haze_intensity)
    )

    # Color grading filter
    processor = _make_post_processor(time, season, weather)
    filters.append(ColorGradeFilter(processor=processor))

    # Precipitation filter (if applicable)
    precip = PRECIPITATION.get(weather)
    if precip:
        filters.append(
            PrecipitationFilter(
                chars=precip["char"],
                color=precip["color"],
                density=precip["density"],
            )
        )

    return FilterPipeline(filters=filters)
