from enum import IntEnum

from landscape.utils import RGB, Colormap, cmap, rgb


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
    Weather.RAINY: (1.5, 0.2),
    Weather.SNOWY: (2.0, 0.8),
    Weather.STORMY: (1.0, 0.7),
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

# Precipitation settings by weather
PRECIPITATION: dict[Weather, dict[str, str | RGB | float]] = {
    Weather.RAINY: {"char": "/", "color": rgb("#7a97ba"), "density": 0.2},
    Weather.SNOWY: {"char": "❄*❅", "color": rgb("#979797"), "density": 0.2},
    Weather.STORMY: {"char": "/|", "color": rgb("#5a7a9a"), "density": 0.18},
}
