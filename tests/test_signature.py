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
    def test_produces_12_hex_chars(self):
        config = GenerateParams(
            seed=0,
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        assert len(config.encode()) == 12

    def test_seed_in_low_bits(self):
        config = GenerateParams(
            seed=0x3FFF,  # max seed
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        value = int(config.encode(), 16)
        assert value & 0x3FFF == 0x3FFF

    def test_seed_clamped_to_max(self):
        config = GenerateParams(
            seed=99999,  # exceeds MAX_SEED
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        value = int(config.encode(), 16)
        assert value & 0x3FFF == GenerateParams.MAX_SEED

    def test_version_in_high_bits(self):
        config = GenerateParams(
            seed=0,
            biomes=(BIOMES["ocean"],),
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        value = int(config.encode(), 16)
        version = (value >> 44) & 0xF
        assert version == GenerateParams.VERSION

    def test_empty_slots_filled_with_0xF(self):
        config = GenerateParams(
            seed=0,
            biomes=(BIOMES["forest"],),  # only 1 biome
            atmosphere=ATMOSPHERES["apricot_dawn"],
        )
        value = int(config.encode(), 16)
        # Slots 2-5 should be EMPTY (0xF)
        assert (value >> 26) & 0xF == 0xF  # B2
        assert (value >> 22) & 0xF == 0xF  # B3
        assert (value >> 18) & 0xF == 0xF  # B4
        assert (value >> 14) & 0xF == 0xF  # B5


class TestGenerateParamsDecode:
    def test_invalid_version_raises(self):
        # Version 1 in high bits
        invalid = f"{1 << 44:012X}"
        with pytest.raises(ValueError, match="Unknown signature version"):
            GenerateParams.decode(invalid)

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
