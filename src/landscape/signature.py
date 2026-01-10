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
    ATMOSPHERES,
    Atmosphere,
    Season,
    TimeOfDay,
    Weather,
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

# Map current atmospheres to (time, season, weather) components
ATMO_TO_COMPONENTS = {
    slug: (atmo.time, atmo.season, atmo.weather) for slug, atmo in ATMOSPHERES.items()
}
COMPONENTS_TO_ATMO = {v: k for k, v in ATMO_TO_COMPONENTS.items()}


def _resolve_atmosphere(
    time: TimeOfDay, season: Season, weather: Weather
) -> Atmosphere:
    """Find the best matching Atmosphere object for the given components."""
    key = (time, season, weather)
    if key in COMPONENTS_TO_ATMO:
        return ATMOSPHERES[COMPONENTS_TO_ATMO[key]]

    # Fallback: find closest match based on time of day
    if time in (TimeOfDay.NIGHT, TimeOfDay.LATE_NIGHT):
        name = "clear_night"
    elif time == TimeOfDay.DAWN:
        name = "apricot_dawn"
    elif time in (TimeOfDay.DUSK, TimeOfDay.EVENING):
        if weather == Weather.STORMY:
            name = "ominous_sunset"
        else:
            name = "apricot_dawn"  # Closest match for dusk
    else:
        name = "clear_day"

    return ATMOSPHERES[name]


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
        signature: str | None = None,
    ) -> "GenerateParams":
        """Resolve all runtime arguments into a config."""

        if signature:
            return cls.decode(signature)

        if seed is None:
            seed = random.randint(0, 100000)

        # If neither biomes nor preset specified, pick a random preset
        if not biome_names:
            preset_name = (
                fuzzy_match(preset_name, list(PRESETS), seed)
                if preset_name is not None
                else rand_choice(list(PRESETS), seed)
            )

        if preset_name and not biome_names:
            biome_names = PRESETS[preset_name]
            if atmosphere_name is None:
                atmosphere_name = rand_choice(list(ATMOSPHERES), seed)

        # Resolve biome names
        biome_names = [fuzzy_match(name, list(BIOMES), seed) for name in biome_names]

        if len(biome_names) == 1:
            # Single biome specified - pair with a complementary one
            partner = rand_choice(COMPLEMENTS[biome_names[0]], seed)
            biome_names.append(partner)

        # Resolve atmosphere
        if atmosphere_name is None:
            atmosphere_name = rand_choice(list(ATMOSPHERES), seed)
        else:
            atmosphere_name = fuzzy_match(atmosphere_name, list(ATMOSPHERES), seed)

        return cls.from_params(seed, biome_names, atmosphere_name)

    def to_atmosphere_name(self) -> str:
        """Get the atmosphere name."""
        return slugify(self.atmosphere.name)

    def to_biome_names(self) -> list[str]:
        """Get the biome names."""
        return [BIOME_CODE_TO_NAME[b.code] for b in self.biomes]
