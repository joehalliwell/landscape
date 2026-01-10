from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from typing import Callable

from landscape.textures import Detail, Texture
from landscape.utils import (
    RGB,
    Colormap,
    clamp_col,
    cmap,
    lerp_color,
    noise_2d,
    rand_choice,
    rgb,
    slugify,
)


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
    SNOWY = 5
    STORMY = 6
    # 6-7 reserved


@dataclass(kw_only=True)
class Atmosphere(Texture):
    name: str = "Anonymous"
    time: TimeOfDay = TimeOfDay.NOON
    season: Season = Season.MID_SUMMER
    weather: Weather = Weather.CLEAR
    haze_power: float = 2.0
    haze_intensity: float = 0.5
    post_process: Callable[[float, float, float, RGB], RGB] | None = None

    @cached_property
    def slug(self):
        return slugify(self.name)

    def filter(
        self,
        x: int,
        y: int,
        z: float,
        ny: float,
        cell: tuple[str, RGB, RGB],
        depth_fraction: float,
        seed: int,
    ) -> tuple[str, RGB, RGB]:
        char, fg, bg = cell

        # Apply haze
        hf = (depth_fraction**self.haze_power) * self.haze_intensity
        if hf > 0:
            haze_color = self.color_map.val(ny)
            fg = lerp_color(fg, haze_color, hf)
            bg = lerp_color(bg, haze_color, hf)

        # Apply post-proc
        if self.post_process:
            fg = self.post_process(x, z, ny, fg)
            bg = self.post_process(x, z, ny, bg)

        return char, fg, bg


@dataclass
class RainyAtmosphere(Atmosphere):
    """Atmosphere with screen-space rain overlay."""

    rain_char: str = "/"
    rain_color: RGB = rgb("#7a97ba")
    rain_density: float = 0.12
    rain_frequency: float = 0.08

    def filter(
        self,
        x: int,
        y: int,
        z: float,
        ny: float,
        cell: tuple[str, RGB, RGB],
        depth_fraction: float,
        seed: int,
    ) -> tuple[str, RGB, RGB]:
        """Apply a screen space rain overlay"""
        char, fg, bg = super().filter(x, y, z, ny, cell, depth_fraction, seed)

        pc = noise_2d(x * 500, z * 500 + ny * 500, seed)

        replace_char = pc <= (
            0.5 * self.rain_density if char == " " else self.rain_density
        )
        # replace_char = True
        if not replace_char:
            return char, fg, bg

        p = noise_2d(z + x * 0.1, z + ny, seed)
        new_char = rand_choice(self.rain_char, seed + x + y * 57)
        return new_char, lerp_color(self.rain_color, fg, p), bg


# =============================================================================
# Building Blocks for Dynamic Atmosphere Generation
# =============================================================================

# Sky color palettes by time of day
TIME_SKY_PALETTES: dict[TimeOfDay, Colormap] = {
    TimeOfDay.DAWN: cmap("#ecb8ec", "#F6FF8F", "#99CCDA", "#77AEBD"),
    TimeOfDay.MORNING: cmap("#87CEEB", "#4A90D9", "#2E6BA6"),
    TimeOfDay.NOON: cmap("#aabbff", "#006aff", "#0069fc"),
    TimeOfDay.AFTERNOON: cmap("#87CEEB", "#5A9BD4", "#3A7BC0"),
    TimeOfDay.DUSK: cmap("#FFD500", "#ff0800", "#480000"),
    TimeOfDay.EVENING: cmap("#2E1A47", "#1A0A2E", "#0A0515"),
    TimeOfDay.NIGHT: cmap("#06063A", "#000000"),
    TimeOfDay.LATE_NIGHT: cmap("#020220", "#000000"),
}

# Weather overrides for sky color (None = use time-based palette)
# Fog is ground-level, so sky colors still visible - fog adds haze, not sky override
WEATHER_SKY_OVERRIDES: dict[Weather, Colormap | None] = {
    Weather.CLEAR: None,
    Weather.PARTLY_CLOUDY: None,
    Weather.CLOUDY: cmap("#8a8a9a", "#6a6a7a"),
    Weather.FOGGY: None,  # Fog adds haze but doesn't change sky color
    Weather.RAINY: cmap("#8090a8", "#6a7a92"),
    Weather.SNOWY: cmap("#eaeaea", "#ffffff"),
    Weather.STORMY: cmap("#4a4a5a", "#2a2a3a"),
}

# Haze settings: (power, intensity) by weather
HAZE_SETTINGS: dict[Weather, tuple[float, float]] = {
    Weather.CLEAR: (2.0, 0.0),
    Weather.PARTLY_CLOUDY: (2.0, 0.2),
    Weather.CLOUDY: (1.5, 0.4),
    Weather.FOGGY: (0.3, 0.9),
    Weather.RAINY: (1.5, 0.5),
    Weather.SNOWY: (2.0, 0.8),
    Weather.STORMY: (1.0, 0.7),
}

# Brightness/tone adjustments by time: (brightness_mult, warmth_shift, blue_shift)
TIME_ADJUSTMENTS: dict[TimeOfDay, tuple[float, int, int]] = {
    TimeOfDay.DAWN: (0.9, 20, -10),
    TimeOfDay.MORNING: (1.0, 5, 0),
    TimeOfDay.NOON: (1.1, 0, 0),
    TimeOfDay.AFTERNOON: (1.05, 5, -5),
    TimeOfDay.DUSK: (0.5, 15, -15),
    TimeOfDay.EVENING: (0.5, -10, 10),
    TimeOfDay.NIGHT: (0.4, -20, 20),
    TimeOfDay.LATE_NIGHT: (0.35, -25, 25),
}

# Weather brightness multipliers
WEATHER_BRIGHTNESS: dict[Weather, float] = {
    Weather.CLEAR: 1.0,
    Weather.PARTLY_CLOUDY: 0.95,
    Weather.CLOUDY: 0.85,
    Weather.FOGGY: 1.0,
    Weather.RAINY: 0.88,
    Weather.SNOWY: 0.85,
    Weather.STORMY: 0.7,
}

# Star visibility by time (0 = fully visible, 1 = invisible)
STAR_VISIBILITY: dict[TimeOfDay, float] = {
    TimeOfDay.DAWN: 0.7,
    TimeOfDay.MORNING: 1.0,
    TimeOfDay.NOON: 1.0,
    TimeOfDay.AFTERNOON: 1.0,
    TimeOfDay.DUSK: 0.5,
    TimeOfDay.EVENING: 0.2,
    TimeOfDay.NIGHT: 0.1,
    TimeOfDay.LATE_NIGHT: 0.1,
}

# Precipitation settings by weather
PRECIPITATION: dict[Weather, dict] = {
    Weather.RAINY: {"char": "/", "color": rgb("#7a97ba"), "density": 0.12},
    Weather.SNOWY: {"char": "❄*❅", "color": rgb("#979797"), "density": 0.2},
    Weather.STORMY: {"char": "/|", "color": rgb("#5a7a9a"), "density": 0.18},
}

# Season adjustments: (brightness_mult, red_shift, green_shift, blue_shift)
# Brightness multiplier applied to post-processing; color shifts tint the scene
SEASON_ADJUSTMENTS: dict[Season, tuple[float, int, int, int]] = {
    Season.EARLY_SPRING: (1.0, 0, 5, 5),  # Cool, fresh
    Season.MID_SPRING: (1.0, 5, 5, 0),  # Neutral-warm
    Season.LATE_SPRING: (1.0, 5, 5, -5),  # Warming
    Season.EARLY_SUMMER: (1.0, 5, 0, -5),  # Warm
    Season.MID_SUMMER: (1.0, 0, 0, 0),  # Neutral (baseline)
    Season.LATE_SUMMER: (0.95, 10, 5, -5),  # Golden, slightly dim
    Season.EARLY_AUTUMN: (0.9, 15, 5, -10),  # Warm, starting to darken
    Season.MID_AUTUMN: (0.8, 20, -5, -15),  # Darker, strong red-orange
    Season.LATE_AUTUMN: (0.3, 10, -15, -20),  # DRAMATIC: very dark, deep reds
    Season.EARLY_WINTER: (0.85, 0, 0, 10),  # Cool blue, shorter days
    Season.MID_WINTER: (0.8, -5, 0, 15),  # Cold blue, dark
    Season.LATE_WINTER: (0.85, -5, 5, 10),  # Cold but brightening
}


# =============================================================================
# Helper Functions
# =============================================================================


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
            chars=".",
            density=0.01,
            color_map=cmap("#ffffff"),
            blend=visibility * 0.1,
        ),
        Detail(
            name="Dim Stars",
            chars=".",
            density=0.05,
            color_map=cmap("#ffffff", "#cccccc"),
            blend=visibility * 0.4 + 0.3,
        ),
    ]


# =============================================================================
# Main Factory Function
# =============================================================================


def get_atmosphere(
    time: TimeOfDay,
    season: Season,
    weather: Weather,
    name: str | None = None,
) -> Atmosphere:
    """Create an atmosphere dynamically from time, season, and weather.

    Composition rules:
    - Sky color: weather override for heavy weather, else time-based palette
    - Haze: determined by weather
    - Post-processing: combines time brightness, weather dimming, season color shift
    - Stars: visible at night/dusk/dawn when weather is clear/partly cloudy
    - Precipitation: added for rainy/snowy/stormy weather
    """
    # Sky color: weather override or time-based
    color_map = WEATHER_SKY_OVERRIDES.get(weather) or TIME_SKY_PALETTES[time]

    # Haze from weather
    haze_power, haze_intensity = HAZE_SETTINGS[weather]

    # Post-processing from time + season + weather
    post_process = _make_post_processor(time, season, weather)

    # Stars for clear/partly cloudy at appropriate times
    details: list[Detail] = []
    if weather in (Weather.CLEAR, Weather.PARTLY_CLOUDY):
        details = _make_star_details(STAR_VISIBILITY[time])

    # Auto-generate name
    if name is None:
        name = f"{weather.name.replace('_', ' ').title()} {time.name.replace('_', ' ').lower()}"

    # Use RainyAtmosphere for precipitation weather
    precip = PRECIPITATION.get(weather)
    if precip:
        return RainyAtmosphere(
            name=name,
            time=time,
            season=season,
            weather=weather,
            color_map=color_map,
            haze_power=haze_power,
            haze_intensity=haze_intensity,
            post_process=post_process,
            details=details,
            rain_char=precip["char"],
            rain_color=precip["color"],
            rain_density=precip["density"],
        )

    return Atmosphere(
        name=name,
        time=time,
        season=season,
        weather=weather,
        color_map=color_map,
        haze_power=haze_power,
        haze_intensity=haze_intensity,
        post_process=post_process,
        details=details,
    )


# =============================================================================
# Presets and ATMOSPHERES Dictionary
# =============================================================================

# Named preset combinations (like biome PRESETS)
ATMOSPHERE_PRESETS: dict[str, tuple[TimeOfDay, Season, Weather]] = {
    "clear_day": (TimeOfDay.NOON, Season.MID_SUMMER, Weather.CLEAR),
    "foggy_day": (TimeOfDay.NOON, Season.MID_SUMMER, Weather.FOGGY),
    "rainy_day": (TimeOfDay.NOON, Season.MID_SUMMER, Weather.RAINY),
    "snowy_day": (TimeOfDay.NOON, Season.MID_WINTER, Weather.SNOWY),
    "clear_night": (TimeOfDay.NIGHT, Season.MID_SUMMER, Weather.CLEAR),
    "apricot_dawn": (TimeOfDay.DAWN, Season.MID_SUMMER, Weather.CLEAR),
    "ominous_sunset": (TimeOfDay.DUSK, Season.LATE_AUTUMN, Weather.CLEAR),
}

# Generate ATMOSPHERES dict from presets
ATMOSPHERES = {
    slug: get_atmosphere(*params, name=slug.replace("_", " ").title())
    for slug, params in ATMOSPHERE_PRESETS.items()
}
