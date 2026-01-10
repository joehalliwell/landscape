import pytest

from landscape.signature import (
    ATMO_TO_COMPONENTS,
    BIOME_CODE_TO_NAME,
    BIOME_NAME_TO_CODE,
    BiomeCode,
    GenerationConfig,
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


class TestGenerationConfigEncode:
    def test_produces_12_hex_chars(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        assert len(config.encode()) == 12

    def test_seed_in_low_bits(self):
        config = GenerationConfig(
            seed=0x3FFF,  # max seed
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        value = int(config.encode(), 16)
        assert value & 0x3FFF == 0x3FFF

    def test_seed_clamped_to_max(self):
        config = GenerationConfig(
            seed=99999,  # exceeds MAX_SEED
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        value = int(config.encode(), 16)
        assert value & 0x3FFF == GenerationConfig.MAX_SEED

    def test_version_in_high_bits(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        value = int(config.encode(), 16)
        version = (value >> 44) & 0xF
        assert version == GenerationConfig.VERSION

    def test_empty_slots_filled_with_0xF(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.FOREST,),  # only 1 biome
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        value = int(config.encode(), 16)
        # Slots 2-5 should be EMPTY (0xF)
        assert (value >> 26) & 0xF == 0xF  # B2
        assert (value >> 22) & 0xF == 0xF  # B3
        assert (value >> 18) & 0xF == 0xF  # B4
        assert (value >> 14) & 0xF == 0xF  # B5


class TestGenerationConfigDecode:
    def test_invalid_version_raises(self):
        # Version 1 in high bits
        invalid = f"{1 << 44:012X}"
        with pytest.raises(ValueError, match="Unknown signature version"):
            GenerationConfig.decode(invalid)

    def test_filters_empty_biomes(self):
        config = GenerationConfig(
            seed=100,
            biomes=(BiomeCode.OCEAN, BiomeCode.ICE),
            time_of_day=TimeOfDay.NOON,
            season=Season.MID_SUMMER,
            weather=Weather.CLEAR,
        )
        decoded = GenerationConfig.decode(config.encode())
        assert len(decoded.biomes) == 2
        assert BiomeCode.EMPTY not in decoded.biomes


class TestRoundTrip:
    @pytest.mark.parametrize("seed", [0, 1, 100, 12345, 16383])
    def test_seed_round_trips(self, seed):
        config = GenerationConfig(
            seed=seed,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        decoded = GenerationConfig.decode(config.encode())
        assert decoded.seed == seed

    @pytest.mark.parametrize(
        "biomes",
        [
            (BiomeCode.OCEAN,),
            (BiomeCode.FOREST, BiomeCode.MOUNTAINS),
            (BiomeCode.OCEAN, BiomeCode.ICE, BiomeCode.OCEAN),
            (BiomeCode.OCEAN, BiomeCode.ICE, BiomeCode.OCEAN, BiomeCode.ICE),
            (
                BiomeCode.PLAINS,
                BiomeCode.FOREST,
                BiomeCode.MOUNTAINS,
                BiomeCode.ALPINE,
                BiomeCode.ICE,
            ),
        ],
    )
    def test_biomes_round_trip(self, biomes):
        config = GenerationConfig(
            seed=42,
            biomes=biomes,
            time_of_day=TimeOfDay.NOON,
            season=Season.MID_SUMMER,
            weather=Weather.CLEAR,
        )
        decoded = GenerationConfig.decode(config.encode())
        assert decoded.biomes == biomes

    @pytest.mark.parametrize("time", list(TimeOfDay))
    def test_time_of_day_round_trips(self, time):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=time,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        decoded = GenerationConfig.decode(config.encode())
        assert decoded.time_of_day == time

    @pytest.mark.parametrize("season", list(Season))
    def test_season_round_trips(self, season):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=season,
            weather=Weather.CLEAR,
        )
        decoded = GenerationConfig.decode(config.encode())
        assert decoded.season == season

    @pytest.mark.parametrize("weather", list(Weather))
    def test_weather_round_trips(self, weather):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=weather,
        )
        decoded = GenerationConfig.decode(config.encode())
        assert decoded.weather == weather


class TestFromParams:
    def test_converts_biome_names(self):
        config = GenerationConfig.from_params(
            seed=100,
            biome_names=["ocean", "forest"],
            atmosphere_name="clear_day",
        )
        assert config.biomes == (BiomeCode.OCEAN, BiomeCode.FOREST)

    def test_maps_atmosphere_to_components(self):
        config = GenerationConfig.from_params(
            seed=100,
            biome_names=["ocean"],
            atmosphere_name="apricot_dawn",
        )
        expected = ATMO_TO_COMPONENTS["apricot_dawn"]
        assert config.time_of_day == expected[0]
        assert config.season == expected[1]
        assert config.weather == expected[2]

    def test_unknown_atmosphere_defaults(self):
        config = GenerationConfig.from_params(
            seed=100,
            biome_names=["ocean"],
            atmosphere_name="unknown_atmosphere",
        )
        assert config.time_of_day == TimeOfDay.NOON
        assert config.season == Season.MID_SUMMER
        assert config.weather == Weather.CLEAR


class TestToBiomeNames:
    def test_converts_codes_to_names(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN, BiomeCode.MOUNTAINS, BiomeCode.ALPINE),
            time_of_day=TimeOfDay.DAWN,
            season=Season.EARLY_SPRING,
            weather=Weather.CLEAR,
        )
        assert config.to_biome_names() == ["ocean", "mountains", "alpine"]


class TestToAtmosphereName:
    def test_exact_match(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.NOON,
            season=Season.MID_SUMMER,
            weather=Weather.CLEAR,
        )
        assert config.to_atmosphere_name() == "clear_day"

    def test_night_fallback(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.LATE_NIGHT,
            season=Season.EARLY_WINTER,
            weather=Weather.FOGGY,
        )
        assert config.to_atmosphere_name() == "clear_night"

    def test_dawn_fallback(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DAWN,
            season=Season.LATE_AUTUMN,
            weather=Weather.CLOUDY,
        )
        assert config.to_atmosphere_name() == "apricot_dawn"

    def test_stormy_dusk_matches_ominous(self):
        config = GenerationConfig(
            seed=0,
            biomes=(BiomeCode.OCEAN,),
            time_of_day=TimeOfDay.DUSK,
            season=Season.LATE_AUTUMN,
            weather=Weather.STORMY,
        )
        assert config.to_atmosphere_name() == "ominous_sunset"
