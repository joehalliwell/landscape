import pytest

from landscape.atmospheres import ATMOSPHERES
from landscape.biomes import BIOMES, BiomeCode
from landscape.signature import (
    BIOME_CODE_TO_NAME,
    BIOME_NAME_TO_CODE,
    GenerateParams,
    Season,
    TimeOfDay,
    Weather,
)
from landscape.utils import base58_encode


class TestBiomeCode:
    def test_values_are_sequential(self):
        assert BiomeCode.OCEAN == 0
        assert BiomeCode.ALPINE == 7
        assert BiomeCode.EMPTY == 15

    def test_all_biomes_fit_in_4_bits(self):
        for code in BiomeCode:
            assert 0 <= code <= 15


class TestTimeOfDay:
    def test_values_fit_in_3_bits(self):
        for code in TimeOfDay:
            assert 0 <= code <= 7


class TestSeason:
    def test_twelve_seasons(self):
        assert Season.EARLY_SPRING == 0
        assert Season.LATE_WINTER == 11

    def test_values_fit_in_4_bits(self):
        for code in Season:
            assert 0 <= code <= 15


class TestWeather:
    def test_values_fit_in_3_bits(self):
        for code in Weather:
            assert 0 <= code <= 7


class TestLookupTables:
    def test_all_biomes_have_mapping(self):
        for code in BiomeCode:
            if code != BiomeCode.EMPTY:
                assert code in BIOME_CODE_TO_NAME

    def test_bidirectional_mapping(self):
        for name, code in BIOME_NAME_TO_CODE.items():
            assert BIOME_CODE_TO_NAME[code] == name


class TestGenerateParamsEncode:
    def test_produces_prefixed_base58_string(self):
        config = GenerateParams(
            seed=0,
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        encoded = config.encode()
        assert encoded.startswith("L")
        # 48 bits fits in 9 base58 chars + 1 prefix
        assert len(encoded) == 10

    def test_seed_clamped_to_max(self):
        config = GenerateParams(
            seed=99999,  # exceeds MAX_SEED
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        decoded = GenerateParams.decode(config.encode())
        assert decoded.seed == GenerateParams.MAX_SEED


class TestGenerateParamsDecode:
    def test_invalid_prefix_raises(self):
        with pytest.raises(ValueError, match="Signature must start with"):
            GenerateParams.decode("X12345678")

    def test_invalid_base58_raises(self):
        with pytest.raises(ValueError, match="Invalid signature format"):
            # L + invalid base58 char (0, O, I, l)
            GenerateParams.decode("L0OIl")

    def test_invalid_version_raises(self):
        # Version 1 in high bits
        # 1 << 44
        val = 1 << 44
        sig = "L" + base58_encode(val)

        with pytest.raises(ValueError, match="Unknown signature version"):
            GenerateParams.decode(sig)

    def test_filters_empty_biomes(self):
        config = GenerateParams(
            seed=100,
            biomes=(BIOMES["ocean"], BIOMES["ice"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        decoded = GenerateParams.decode(config.encode())
        assert len(decoded.biomes) == 2
        assert decoded.biomes == config.biomes


class TestRoundTrip:
    @pytest.mark.parametrize("seed", [0, 1, 100, 12345, 16383])
    def test_seed_round_trips(self, seed):
        config = GenerateParams(
            seed=seed,
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        decoded = GenerateParams.decode(config.encode())
        assert decoded.seed == seed

    @pytest.mark.parametrize(
        "biomes",
        [
            (BIOMES["ocean"],),
            (BIOMES["forest"], BIOMES["mountains"]),
            (BIOMES["ocean"], BIOMES["ice"], BIOMES["ocean"]),
            (BIOMES["ocean"], BIOMES["ice"], BIOMES["ocean"], BIOMES["ice"]),
            (
                BIOMES["plains"],
                BIOMES["forest"],
                BIOMES["mountains"],
                BIOMES["alpine"],
                BIOMES["ice"],
            ),
        ],
    )
    def test_biomes_round_trip(self, biomes):
        config = GenerateParams(
            seed=42,
            biomes=biomes,
            atmosphere=ATMOSPHERES["clear_day"],
        )
        decoded = GenerateParams.decode(config.encode())
        assert decoded.biomes == biomes

    @pytest.mark.parametrize("atmosphere", list(ATMOSPHERES.values()))
    def test_atmosphere_round_trips(self, atmosphere):
        config = GenerateParams(
            seed=0,
            biomes=(BIOMES["ocean"],),
            atmosphere=atmosphere,
        )
        decoded = GenerateParams.decode(config.encode())
        # Note: multiple atmospheres might share components, so we check components
        assert decoded.atmosphere.time == atmosphere.time
        assert decoded.atmosphere.season == atmosphere.season
        assert decoded.atmosphere.weather == atmosphere.weather


class TestFromParams:
    def test_converts_biome_names(self):
        config = GenerateParams.from_params(
            seed=100,
            biome_names=["ocean", "forest"],
            atmosphere_name="clear_day",
        )
        assert config.biomes == (BIOMES["ocean"], BIOMES["forest"])

    def test_maps_atmosphere_to_object(self):
        config = GenerateParams.from_params(
            seed=100,
            biome_names=["ocean"],
            atmosphere_name="apricot_dawn",
        )
        assert config.atmosphere == ATMOSPHERES["apricot_dawn"]


class TestToBiomeNames:
    def test_converts_objects_to_names(self):
        config = GenerateParams(
            seed=0,
            biomes=(BIOMES["ocean"], BIOMES["mountains"], BIOMES["alpine"]),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        assert config.to_biome_names() == ["ocean", "mountains", "alpine"]


class TestToAtmosphereName:
    def test_exact_match(self):
        config = GenerateParams(
            seed=0,
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        assert config.to_atmosphere_name() == "clear_day"


class TestFromRuntimeArgsAtmosphere:
    def test_atmosphere_preset_fuzzy_match(self):
        """Test that -a dawn fuzzy matches to apricot_dawn."""
        config = GenerateParams.from_runtime_args(
            seed=100,
            biome_names=["ocean"],
            atmosphere_name="dawn",
        )
        assert config.atmosphere.time == TimeOfDay.DAWN
        assert config.atmosphere.season == Season.MID_SUMMER
        assert config.atmosphere.weather == Weather.CLEAR

    def test_atmosphere_preset_with_weather_override(self):
        """Test that -a dawn --weather rain uses dawn's time/season but rainy weather."""
        config = GenerateParams.from_runtime_args(
            seed=100,
            biome_names=["ocean"],
            atmosphere_name="dawn",
            weather="rain",
        )
        assert config.atmosphere.time == TimeOfDay.DAWN
        assert config.atmosphere.season == Season.MID_SUMMER
        assert config.atmosphere.weather == Weather.RAINY

    def test_atmosphere_preset_with_time_override(self):
        """Test that -a dawn --time night overrides the time."""
        config = GenerateParams.from_runtime_args(
            seed=100,
            biome_names=["ocean"],
            atmosphere_name="dawn",
            time_of_day="night",
        )
        assert config.atmosphere.time == TimeOfDay.NIGHT
        assert config.atmosphere.season == Season.MID_SUMMER
        assert config.atmosphere.weather == Weather.CLEAR

    def test_component_only_weather(self):
        """Test that --weather alone picks random time/season."""
        config = GenerateParams.from_runtime_args(
            seed=100,
            biome_names=["ocean"],
            weather="stormy",
        )
        assert config.atmosphere.weather == Weather.STORMY

    def test_component_only_time(self):
        """Test that --time alone picks random season/weather."""
        config = GenerateParams.from_runtime_args(
            seed=100,
            biome_names=["ocean"],
            time_of_day="dusk",
        )
        assert config.atmosphere.time == TimeOfDay.DUSK


def test_large_seed_clamped_in_from_runtime_args():
    """Test that seeds exceeding MAX_SEED are clamped."""
    config = GenerateParams.from_runtime_args(
        seed=50000,
        biome_names=["ocean"],
        atmosphere_name="clear_day",
    )
    assert config.seed == GenerateParams.MAX_SEED


def test_clamped_seed_round_trips():
    """Test that clamped seeds round-trip correctly through encode/decode."""
    config = GenerateParams.from_runtime_args(
        seed=99999,
        biome_names=["ocean"],
        atmosphere_name="clear_day",
    )
    decoded = GenerateParams.decode(config.encode())
    assert decoded.seed == config.seed == GenerateParams.MAX_SEED


def test_valid_seed_unchanged():
    """Test that seeds within range are not modified."""
    config = GenerateParams.from_runtime_args(
        seed=1000,
        biome_names=["ocean"],
        atmosphere_name="clear_day",
    )
    assert config.seed == 1000


class TestCascadeOverride:
    """Test the cascade override pattern for signature + CLI flags."""

    def test_signature_only_returns_decoded(self):
        """Signature alone should return decoded values unchanged."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["forest"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(signature=sig)

        assert config.seed == 1234
        assert config.biomes == (BIOMES["ocean"], BIOMES["forest"])
        assert config.atmosphere.time == TimeOfDay.NOON

    def test_signature_with_seed_override(self):
        """--seed should override signature seed."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["forest"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(signature=sig, seed=9999)

        assert config.seed == 9999
        # Other values preserved
        assert config.biomes == original.biomes
        assert config.atmosphere.time == original.atmosphere.time

    def test_signature_with_biome_override(self):
        """--biome should override signature biomes."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["mountains"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(signature=sig, biome_names=["forest"])

        # Biome replaced, complement added
        assert BIOMES["forest"] in config.biomes
        assert len(config.biomes) == 2  # complement pairing still applies
        # Seed preserved
        assert config.seed == 1234

    def test_signature_with_time_override(self):
        """--time should override signature atmosphere time."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["forest"]),
            atmosphere=ATMOSPHERES["clear_day"],  # NOON
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(signature=sig, time_of_day="dusk")

        assert config.atmosphere.time == TimeOfDay.DUSK
        # Other atmosphere components preserved from signature
        assert config.atmosphere.season == Season.MID_SUMMER
        assert config.atmosphere.weather == Weather.CLEAR

    def test_signature_with_weather_override(self):
        """--weather should override signature atmosphere weather."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["forest"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(signature=sig, weather="rainy")

        assert config.atmosphere.weather == Weather.RAINY
        # Other atmosphere components preserved
        assert config.atmosphere.time == TimeOfDay.NOON
        assert config.atmosphere.season == Season.MID_SUMMER

    def test_signature_with_atmosphere_preset_override(self):
        """--atmosphere should override all signature atmosphere components."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["forest"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(
            signature=sig, atmosphere_name="apricot_dawn"
        )

        # All components from apricot_dawn
        assert config.atmosphere.time == TimeOfDay.DAWN
        assert config.atmosphere.season == Season.MID_SUMMER
        assert config.atmosphere.weather == Weather.CLEAR
        # Biomes and seed preserved
        assert config.biomes == original.biomes
        assert config.seed == 1234

    def test_signature_with_atmosphere_and_component_override(self):
        """--atmosphere + --weather should layer correctly."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["forest"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(
            signature=sig,
            atmosphere_name="apricot_dawn",  # DAWN, MID_SUMMER, CLEAR
            weather="rainy",
        )

        # Time/season from preset, weather overridden
        assert config.atmosphere.time == TimeOfDay.DAWN
        assert config.atmosphere.season == Season.MID_SUMMER
        assert config.atmosphere.weather == Weather.RAINY

    def test_preset_overrides_signature_biomes(self):
        """--preset should override signature biomes but not other fields."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["ice"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(signature=sig, preset_name="coastal")

        # Biomes from preset
        assert config.to_biome_names() == ["ocean", "plains", "forest", "plains"]
        # Seed preserved from signature
        assert config.seed == 1234
        # Atmosphere preserved from signature
        assert config.atmosphere.time == TimeOfDay.NOON

    def test_cli_biomes_override_preset_and_signature(self):
        """--biome should override both signature and preset biomes."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["ice"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(
            signature=sig,
            preset_name="coastal",
            biome_names=["desert", "mountains"],
        )

        # CLI biomes win
        assert config.to_biome_names() == ["desert", "mountains"]
        # Seed preserved
        assert config.seed == 1234

    def test_multiple_overrides(self):
        """Multiple CLI flags should each override their respective components."""
        original = GenerateParams(
            seed=1234,
            biomes=(BIOMES["ocean"], BIOMES["ice"]),
            atmosphere=ATMOSPHERES["clear_day"],
        )
        sig = original.encode()

        config = GenerateParams.from_runtime_args(
            signature=sig,
            seed=5678,
            biome_names=["forest"],
            time_of_day="dusk",
            weather="foggy",
        )

        assert config.seed == 5678
        assert BIOMES["forest"] in config.biomes
        assert config.atmosphere.time == TimeOfDay.DUSK
        assert config.atmosphere.weather == Weather.FOGGY
        # Season preserved from signature
        assert config.atmosphere.season == Season.MID_SUMMER
