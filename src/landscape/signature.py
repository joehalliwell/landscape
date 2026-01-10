"""Signature encoding for landscape generation parameters.

A signature is a compact Base58-encoded string (48 bits) prefixed with 'L'
that encodes all generation parameters needed to precisely reconstruct a landscape.

Bit allocation:
    Ver (4) | Time (3) | Season (4) | Weather (3) | B1-B5 (4 each) | Seed (14)
    47-44   | 43-41    | 40-37      | 36-34       | 33-14          | 13-0
"""

import random
from dataclasses import dataclass

from landscape.atmospheres import (
    ATMOSPHERE_PRESETS,
    ATMOSPHERES,
    Atmosphere,
    Season,
    TimeOfDay,
    Weather,
    get_atmosphere,
)
from landscape.biomes import BIOMES, COMPLEMENTS, PRESETS, Biome, BiomeCode
from landscape.utils import (
    base58_decode,
    base58_encode,
    fuzzy_match,
    rand_choice,
    slugify,
)

# Lookup tables for biome name <-> code conversion
BIOME_NAME_TO_CODE = {name: biome.code for name, biome in BIOMES.items()}
BIOME_CODE_TO_NAME = {biome.code: name for name, biome in BIOMES.items()}

# Map atmosphere presets to (time, season, weather) components
ATMO_TO_COMPONENTS = dict(ATMOSPHERE_PRESETS)
COMPONENTS_TO_ATMO = {v: k for k, v in ATMO_TO_COMPONENTS.items()}


def _resolve_atmosphere(
    time: TimeOfDay, season: Season, weather: Weather
) -> Atmosphere:
    """Find or create an Atmosphere for the given components."""
    key = (time, season, weather)
    if key in COMPONENTS_TO_ATMO:
        return ATMOSPHERES[COMPONENTS_TO_ATMO[key]]

    # Dynamically generate atmosphere for non-preset combinations
    return get_atmosphere(time, season, weather)


def _resolve_atmosphere_from_args(
    time_of_day: str | None,
    season: str | None,
    weather: str | None,
    seed: int,
) -> Atmosphere:
    """Resolve atmosphere from string arguments, using defaults for unspecified."""
    # Build lookup dicts for fuzzy matching
    time_options = {t.name.lower(): t for t in TimeOfDay}
    season_options = {s.name.lower(): s for s in Season}
    weather_options = {w.name.lower(): w for w in Weather}

    # Resolve each component, defaulting to random if not specified
    if time_of_day is not None:
        time = time_options[fuzzy_match(time_of_day, list(time_options), seed)]
    else:
        time = rand_choice(list(TimeOfDay), seed)

    if season is not None:
        ssn = season_options[fuzzy_match(season, list(season_options), seed)]
    else:
        ssn = rand_choice(list(Season), seed + 1)

    if weather is not None:
        wthr = weather_options[fuzzy_match(weather, list(weather_options), seed)]
    else:
        wthr = rand_choice(list(Weather), seed + 2)

    return _resolve_atmosphere(time, ssn, wthr)


@dataclass
class GenerateParams:
    """Encapsulates all generation parameters with encode/decode capability."""

    seed: int
    biomes: tuple[Biome, ...]  # Up to 5 biomes, near to far
    atmosphere: Atmosphere

    VERSION = 0
    MAX_SEED = (1 << 14) - 1  # 16383
    MAX_BIOMES = 5
    PREFIX = "L"

    def encode(self) -> str:
        """Encode to 'L' prefixed Base58 signature."""
        seed = min(self.seed, self.MAX_SEED)

        # Get codes
        biome_codes = [b.code for b in self.biomes]

        # Pad biomes to 5 slots with EMPTY
        slots = biome_codes + [BiomeCode.EMPTY] * (5 - len(biome_codes))

        value = (
            (self.VERSION << 44)
            | (self.atmosphere.time << 41)
            | (self.atmosphere.season << 37)
            | (self.atmosphere.weather << 34)
            | (slots[0] << 30)
            | (slots[1] << 26)
            | (slots[2] << 22)
            | (slots[3] << 18)
            | (slots[4] << 14)
            | seed
        )

        encoded = base58_encode(value, length=9)
        return f"{self.PREFIX}{encoded}"

    @classmethod
    def decode(cls, signature: str) -> "GenerateParams":
        """Decode signature to GenerateParams."""
        if not signature.startswith(cls.PREFIX):
            raise ValueError(f"Signature must start with '{cls.PREFIX}'")

        encoded = signature[len(cls.PREFIX) :]
        try:
            value = base58_decode(encoded)
        except ValueError as e:
            raise ValueError("Invalid signature format") from e

        return cls._from_int_value(value)

    @classmethod
    def _from_int_value(cls, value: int) -> "GenerateParams":
        """Internal helper to create params from the integer value."""
        version = (value >> 44) & 0xF
        if version != cls.VERSION:
            raise ValueError(
                f"Unknown signature version {version}. "
                "Please update landscape to decode this signature."
            )

        # Extract biome slots
        slots = [
            BiomeCode((value >> 30) & 0xF),
            BiomeCode((value >> 26) & 0xF),
            BiomeCode((value >> 22) & 0xF),
            BiomeCode((value >> 18) & 0xF),
            BiomeCode((value >> 14) & 0xF),
        ]

        # Convert codes back to Biome objects
        biomes = tuple(
            BIOMES[BIOME_CODE_TO_NAME[code]]
            for code in slots
            if code != BiomeCode.EMPTY
        )

        # Extract atmosphere components
        time = TimeOfDay((value >> 41) & 0x7)
        season = Season((value >> 37) & 0xF)
        weather = Weather((value >> 34) & 0x7)

        atmosphere = _resolve_atmosphere(time, season, weather)

        return cls(
            seed=(value & 0x3FFF),
            biomes=biomes,
            atmosphere=atmosphere,
        )

    @classmethod
    def from_params(
        cls,
        seed: int,
        biome_names: list[str],
        atmosphere_name: str,
    ) -> "GenerateParams":
        """Create from resolved parameter names."""
        biomes = tuple(BIOMES[name] for name in biome_names)
        atmosphere = ATMOSPHERES[slugify(atmosphere_name)]
        return cls(
            seed=seed,
            biomes=biomes,
            atmosphere=atmosphere,
        )

    @classmethod
    def from_runtime_args(
        cls,
        preset_name: str | None = None,
        seed: int | None = None,
        biome_names: list[str] = [],
        atmosphere_name: str | None = None,
        time_of_day: str | None = None,
        season: str | None = None,
        weather: str | None = None,
        signature: str | None = None,
    ) -> "GenerateParams":
        """Resolve all runtime arguments into a config."""

        if signature:
            return cls.decode(signature)

        if seed is None:
            seed = random.randint(0, cls.MAX_SEED)
        else:
            seed = min(seed, cls.MAX_SEED)

        # If neither biomes nor preset specified, pick a random preset
        if not biome_names:
            preset_name = (
                fuzzy_match(preset_name, list(PRESETS), seed)
                if preset_name is not None
                else rand_choice(list(PRESETS), seed)
            )

        if preset_name and not biome_names:
            biome_names = PRESETS[preset_name]
            if atmosphere_name is None and not any([time_of_day, season, weather]):
                atmosphere_name = rand_choice(list(ATMOSPHERES), seed)

        # Resolve biome names
        biome_names = [fuzzy_match(name, list(BIOMES), seed) for name in biome_names]

        if len(biome_names) == 1:
            # Single biome specified - pair with a complementary one
            partner = rand_choice(COMPLEMENTS[biome_names[0]], seed)
            biome_names.append(partner)

        # Resolve atmosphere - start from preset if specified, then override components
        if atmosphere_name is not None:
            atmosphere_name = fuzzy_match(atmosphere_name, list(ATMOSPHERES), seed)
            base_time, base_season, base_weather = ATMOSPHERE_PRESETS[atmosphere_name]
        else:
            base_time, base_season, base_weather = None, None, None

        # If any components specified (or we have a preset base), use component system
        if any([time_of_day, season, weather, atmosphere_name]):
            atmosphere = _resolve_atmosphere_from_args(
                time_of_day
                or (base_time.name.lower() if base_time is not None else None),
                season
                or (base_season.name.lower() if base_season is not None else None),
                weather
                or (base_weather.name.lower() if base_weather is not None else None),
                seed,
            )
        else:
            atmosphere_name = rand_choice(list(ATMOSPHERES), seed)
            atmosphere = ATMOSPHERES[atmosphere_name]

        biomes = tuple(BIOMES[name] for name in biome_names)
        return cls(seed=seed, biomes=biomes, atmosphere=atmosphere)

    def to_atmosphere_name(self) -> str:
        """Get the atmosphere name."""
        return slugify(self.atmosphere.name)

    def to_biome_names(self) -> list[str]:
        """Get the biome names."""
        return [BIOME_CODE_TO_NAME[b.code] for b in self.biomes]
