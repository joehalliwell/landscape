"""Signature encoding for landscape generation parameters.

A signature is a compact Base58-encoded string (48 bits) prefixed with 'L'
that encodes all generation parameters needed to precisely reconstruct a landscape.

Bit allocation:
    Ver (4) | Time (3) | Season (4) | Weather (3) | B1-B5 (4 each) | Seed (14)
    47-44   | 43-41    | 40-37      | 36-34       | 33-14          | 13-0
"""

import random
from dataclasses import dataclass

from landscape.atmosphere import AtmospherePreset, Season, TimeOfDay, Weather
from landscape.biomes import BIOMES, COMPLEMENTS, Biome, BiomeCode, BiomePreset
from landscape.utils import (
    base58_decode,
    base58_encode,
    find_shortcode_match,
    rand_choice,
)

# Lookup tables for biome name <-> code conversion
BIOME_NAME_TO_CODE = {name: biome.code for name, biome in BIOMES.items()}
BIOME_CODE_TO_NAME = {biome.code: name for name, biome in BIOMES.items()}

# Lookup tables for preset enums by lowercase name
ATMOSPHERE_PRESETS = {p.name.lower(): p for p in AtmospherePreset}
BIOME_PRESETS = {p.name.lower(): p for p in BiomePreset}

# Reverse lookup: (time, season, weather) -> preset
COMPONENTS_TO_PRESET = {p.value: p for p in AtmospherePreset}


@dataclass
class SceneConfig:
    """Configuration parameters for scene generation."""

    seed: int
    biomes: tuple[Biome, ...]  # Up to 5 biomes, near to far
    time: TimeOfDay
    season: Season
    weather: Weather

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
            | (self.time << 41)
            | (self.season << 37)
            | (self.weather << 34)
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
    def decode(cls, signature: str) -> "SceneConfig":
        """Decode signature to SceneConfig."""
        if not signature.startswith(cls.PREFIX):
            raise ValueError(f"Signature must start with '{cls.PREFIX}'")

        encoded = signature[len(cls.PREFIX) :]
        try:
            value = base58_decode(encoded)
        except ValueError as e:
            raise ValueError("Invalid signature format") from e

        return cls._from_int_value(value)

    @classmethod
    def _from_int_value(cls, value: int) -> "SceneConfig":
        """Internal helper to create config from the integer value."""
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

        return cls(
            seed=(value & 0x3FFF),
            biomes=biomes,
            time=TimeOfDay((value >> 41) & 0x7),
            season=Season((value >> 37) & 0xF),
            weather=Weather((value >> 34) & 0x7),
        )

    @classmethod
    def from_params(
        cls,
        seed: int,
        biome_names: list[str],
        atmosphere_name: str,
    ) -> "SceneConfig":
        """Create from resolved parameter names."""
        biomes = tuple(BIOMES[name] for name in biome_names)
        preset = ATMOSPHERE_PRESETS[atmosphere_name]
        return cls(
            seed=seed,
            biomes=biomes,
            time=preset.time,
            season=preset.season,
            weather=preset.weather,
        )

    @classmethod
    def from_runtime_args(
        cls,
        preset: BiomePreset | None = None,
        seed: int | None = None,
        biome_names: list[str] = [],
        atmosphere: AtmospherePreset | None = None,
        time_of_day: TimeOfDay | None = None,
        season: Season | None = None,
        weather: Weather | None = None,
        signature: str | None = None,
    ) -> "SceneConfig":
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
            base_time = decoded.time
            base_season = decoded.season
            base_weather = decoded.weather

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
                find_shortcode_match(name, list(BIOMES)) for name in biome_names
            ]
        elif preset is not None:
            # Preset overrides signature biomes
            resolved_biome_names = list(preset.biomes)
            # Random atmosphere only if using a preset with no other atmosphere args
            if (
                base_time is None
                and atmosphere is None
                and not any([time_of_day, season, weather])
            ):
                use_random_atmosphere = True
        elif base_biome_names is not None:
            # Use signature biomes
            resolved_biome_names = base_biome_names
        else:
            # Random preset
            random_preset = rand_choice(list(BiomePreset), final_seed)
            resolved_biome_names = list(random_preset.biomes)
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
        if atmosphere is not None:
            resolved_time = atmosphere.time
            resolved_season = atmosphere.season
            resolved_weather = atmosphere.weather

        # Apply CLI component overrides (enums used directly)
        if time_of_day is not None:
            resolved_time = time_of_day
        if season is not None:
            resolved_season = season
        if weather is not None:
            resolved_weather = weather

        # Fill in any remaining None values with random choices
        if resolved_time is None:
            resolved_time = rand_choice(list(TimeOfDay), final_seed)
        if resolved_season is None:
            resolved_season = rand_choice(list(Season), final_seed + 1)
        if resolved_weather is None:
            resolved_weather = rand_choice(list(Weather), final_seed + 2)

        if use_random_atmosphere and not any(
            [time_of_day, season, weather, atmosphere, base_time]
        ):
            # Fully random atmosphere from presets (no signature, no CLI args)
            atmo_preset = rand_choice(list(AtmospherePreset), final_seed)
            resolved_time = atmo_preset.time
            resolved_season = atmo_preset.season
            resolved_weather = atmo_preset.weather

        biomes = tuple(BIOMES[name] for name in resolved_biome_names)
        return cls(
            seed=final_seed,
            biomes=biomes,
            time=resolved_time,
            season=resolved_season,
            weather=resolved_weather,
        )

    def to_atmosphere_name(self) -> str:
        """Get the atmosphere name from components."""
        key = (self.time, self.season, self.weather)
        if key in COMPONENTS_TO_PRESET:
            return COMPONENTS_TO_PRESET[key].name.lower()
        return f"{self.weather.name.lower()}_{self.time.name.lower()}"

    def to_biome_names(self) -> list[str]:
        """Get the biome names."""
        return [BIOME_CODE_TO_NAME[b.code] for b in self.biomes]
