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
