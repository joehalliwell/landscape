"""Signature encoding for landscape generation parameters.

A signature is a 12-character hexadecimal string (48 bits) that encodes all
generation parameters needed to precisely reconstruct a landscape.

Bit allocation:
    Ver (4) | Time (3) | Season (4) | Weather (3) | B1-B5 (4 each) | Seed (14)
    47-44   | 43-41    | 40-37      | 36-34       | 33-14          | 13-0
"""

from dataclasses import dataclass
from enum import IntEnum


class BiomeCode(IntEnum):
    """Biome codes for signature encoding."""

    OCEAN = 0
    FOREST = 1
    MOUNTAINS = 2
    JUNGLE = 3
    ICE = 4
    PLAINS = 5
    DESERT = 6
    ALPINE = 7
    # 8-14 reserved for future biomes
    EMPTY = 15  # Slot unused


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


# Lookup tables for biome name <-> code conversion
BIOME_NAME_TO_CODE = {
    "ocean": BiomeCode.OCEAN,
    "forest": BiomeCode.FOREST,
    "mountains": BiomeCode.MOUNTAINS,
    "jungle": BiomeCode.JUNGLE,
    "ice": BiomeCode.ICE,
    "plains": BiomeCode.PLAINS,
    "desert": BiomeCode.DESERT,
    "alpine": BiomeCode.ALPINE,
}
BIOME_CODE_TO_NAME = {v: k for k, v in BIOME_NAME_TO_CODE.items()}

# Map current atmospheres to (time, season, weather) components
ATMO_TO_COMPONENTS = {
    "clear_day": (TimeOfDay.NOON, Season.MID_SUMMER, Weather.CLEAR),
    "clear_night": (TimeOfDay.NIGHT, Season.MID_SUMMER, Weather.CLEAR),
    "apricot_dawn": (TimeOfDay.DAWN, Season.MID_SUMMER, Weather.CLEAR),
    "ominous_sunset": (TimeOfDay.DUSK, Season.LATE_AUTUMN, Weather.STORMY),
}
COMPONENTS_TO_ATMO = {v: k for k, v in ATMO_TO_COMPONENTS.items()}


@dataclass
class GenerationConfig:
    """Encapsulates all generation parameters with encode/decode capability."""

    seed: int
    biomes: tuple[BiomeCode, ...]  # Up to 5 biomes, near to far
    time_of_day: TimeOfDay
    season: Season
    weather: Weather

    VERSION = 0
    MAX_SEED = (1 << 14) - 1  # 16383
    MAX_BIOMES = 5

    def encode(self) -> str:
        """Encode to 12-char hex signature."""
        seed = min(self.seed, self.MAX_SEED)
        # Pad biomes to 5 slots with EMPTY
        slots = list(self.biomes) + [BiomeCode.EMPTY] * (5 - len(self.biomes))
        value = (
            (self.VERSION << 44)
            | (self.time_of_day << 41)
            | (self.season << 37)
            | (self.weather << 34)
            | (slots[0] << 30)
            | (slots[1] << 26)
            | (slots[2] << 22)
            | (slots[3] << 18)
            | (slots[4] << 14)
            | seed
        )
        return f"{value:012X}"

    @classmethod
    def decode(cls, signature: str) -> "GenerationConfig":
        """Decode 12-char hex signature to GenerationConfig."""
        value = int(signature, 16)
        version = (value >> 44) & 0xF
        if version != cls.VERSION:
            raise ValueError(
                f"Unknown signature version {version}. "
                "Please update landscape to decode this signature."
            )
        # Extract biome slots, filter out EMPTY
        slots = [
            BiomeCode((value >> 30) & 0xF),
            BiomeCode((value >> 26) & 0xF),
            BiomeCode((value >> 22) & 0xF),
            BiomeCode((value >> 18) & 0xF),
            BiomeCode((value >> 14) & 0xF),
        ]
        biomes = tuple(b for b in slots if b != BiomeCode.EMPTY)
        return cls(
            seed=(value & 0x3FFF),
            biomes=biomes,
            time_of_day=TimeOfDay((value >> 41) & 0x7),
            season=Season((value >> 37) & 0xF),
            weather=Weather((value >> 34) & 0x7),
        )

    @classmethod
    def from_params(
        cls,
        seed: int,
        biome_names: list[str],
        atmosphere_name: str,
    ) -> "GenerationConfig":
        """Create from resolved parameter names."""
        biome_codes = tuple(BIOME_NAME_TO_CODE[name] for name in biome_names)
        time, season, weather = ATMO_TO_COMPONENTS.get(
            atmosphere_name,
            (TimeOfDay.NOON, Season.MID_SUMMER, Weather.CLEAR),
        )
        return cls(
            seed=seed,
            biomes=biome_codes,
            time_of_day=time,
            season=season,
            weather=weather,
        )

    def to_atmosphere_name(self) -> str:
        """Get the closest matching atmosphere name for current components."""
        key = (self.time_of_day, self.season, self.weather)
        if key in COMPONENTS_TO_ATMO:
            return COMPONENTS_TO_ATMO[key]
        # Fallback: find closest match based on time of day
        if self.time_of_day in (TimeOfDay.NIGHT, TimeOfDay.LATE_NIGHT):
            return "clear_night"
        elif self.time_of_day == TimeOfDay.DAWN:
            return "apricot_dawn"
        elif self.time_of_day in (TimeOfDay.DUSK, TimeOfDay.EVENING):
            if self.weather == Weather.STORMY:
                return "ominous_sunset"
            return "apricot_dawn"  # Closest match for dusk
        else:
            return "clear_day"

    def to_biome_names(self) -> list[str]:
        """Convert biome codes to names."""
        return [BIOME_CODE_TO_NAME[b] for b in self.biomes]
