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
        """Resolve all runtime arguments into a config.

        Implements a cascade where broader options provide base values and
        narrower options can override specific fields:

        Precedence (later overrides earlier):
        1. Signature (broadest) - provides base seed, biomes, atmosphere
        2. Preset - overrides biomes only
        3. Individual flags (narrowest):
           - --seed overrides seed
           - --biome overrides biomes
           - --atmosphere overrides all atmosphere components
           - --time, --season, --weather override individual components
        """
        # === LAYER 0: Initialize base values from signature ===
        base_seed: int | None = None
        base_biome_names: list[str] | None = None
        base_time: TimeOfDay | None = None
        base_season: Season | None = None
        base_weather: Weather | None = None

        if signature:
            decoded = cls.decode(signature)
            base_seed = decoded.seed
            base_biome_names = [BIOME_CODE_TO_NAME[b.code] for b in decoded.biomes]
            base_time = decoded.atmosphere.time
            base_season = decoded.atmosphere.season
            base_weather = decoded.atmosphere.weather

        # === LAYER 1: Seed resolution (CLI > signature > random) ===
        if seed is not None:
            final_seed = min(seed, cls.MAX_SEED)
        elif base_seed is not None:
            final_seed = base_seed
        else:
            final_seed = random.randint(0, cls.MAX_SEED)

        # === LAYER 2: Biome resolution (CLI > preset > signature > random) ===
        use_random_atmosphere = False

        if biome_names:
            # CLI biomes override everything
            resolved_biome_names = [
                fuzzy_match(name, list(BIOMES), final_seed) for name in biome_names
            ]
        elif preset_name is not None:
            # Preset overrides signature biomes
            preset_name = fuzzy_match(preset_name, list(PRESETS), final_seed)
            resolved_biome_names = list(PRESETS[preset_name])
            # Random atmosphere only if using a preset with no other atmosphere args
            if (
                base_time is None
                and atmosphere_name is None
                and not any([time_of_day, season, weather])
            ):
                use_random_atmosphere = True
        elif base_biome_names is not None:
            # Use signature biomes
            resolved_biome_names = base_biome_names
        else:
            # Random preset
            preset_name = rand_choice(list(PRESETS), final_seed)
            resolved_biome_names = list(PRESETS[preset_name])
            use_random_atmosphere = True

        # Complement pairing still applies for single biome
        if len(resolved_biome_names) == 1:
            partner = rand_choice(COMPLEMENTS[resolved_biome_names[0]], final_seed)
            resolved_biome_names.append(partner)

        # === LAYER 3: Atmosphere resolution ===
        # Priority: CLI component > CLI preset > signature > random
        resolved_time = base_time
        resolved_season = base_season
        resolved_weather = base_weather

        # Atmosphere preset overrides signature values
        if atmosphere_name is not None:
            atmosphere_name = fuzzy_match(
                atmosphere_name, list(ATMOSPHERES), final_seed
            )
            preset_t, preset_s, preset_w = ATMOSPHERE_PRESETS[atmosphere_name]
            resolved_time, resolved_season, resolved_weather = (
                preset_t,
                preset_s,
                preset_w,
            )

        # Apply CLI component overrides (fuzzy match strings to enums)
        time_options = {t.name.lower(): t for t in TimeOfDay}
        season_options = {s.name.lower(): s for s in Season}
        weather_options = {w.name.lower(): w for w in Weather}

        if time_of_day is not None:
            resolved_time = time_options[
                fuzzy_match(time_of_day, list(time_options), final_seed)
            ]
        if season is not None:
            resolved_season = season_options[
                fuzzy_match(season, list(season_options), final_seed)
            ]
        if weather is not None:
            resolved_weather = weather_options[
                fuzzy_match(weather, list(weather_options), final_seed)
            ]

        # Fill in any remaining None values with random choices
        if resolved_time is None:
            resolved_time = rand_choice(list(TimeOfDay), final_seed)
        if resolved_season is None:
            resolved_season = rand_choice(list(Season), final_seed + 1)
        if resolved_weather is None:
            resolved_weather = rand_choice(list(Weather), final_seed + 2)

        if use_random_atmosphere and not any(
            [time_of_day, season, weather, atmosphere_name, base_time]
        ):
            # Fully random atmosphere from presets (no signature, no CLI args)
            atmo_name = rand_choice(list(ATMOSPHERES), final_seed)
            atmosphere = ATMOSPHERES[atmo_name]
        else:
            # Resolve atmosphere from components
            atmosphere = _resolve_atmosphere(
                resolved_time, resolved_season, resolved_weather
            )

        biomes = tuple(BIOMES[name] for name in resolved_biome_names)
        return cls(seed=final_seed, biomes=biomes, atmosphere=atmosphere)

    def to_atmosphere_name(self) -> str:
        """Get the atmosphere name."""
        return slugify(self.atmosphere.name)

    def to_biome_names(self) -> list[str]:
        """Get the biome names."""
        return [BIOME_CODE_TO_NAME[b.code] for b in self.biomes]
