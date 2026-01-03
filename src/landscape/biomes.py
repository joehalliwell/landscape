from dataclasses import dataclass

from landscape.utils import RGB, lerp_color, rand_choice, rgb


@dataclass
class Biome:
    """Defines a landscape biome with colors and terrain properties."""

    name: str
    color_lo: tuple[int, int, int]
    color_hi: tuple[int, int, int]
    # Terrain generation parameters
    roughness: float = 0.5  # Higher = more jagged

    height_scale: float = 1.0  # Vertical exaggeration
    base_height: float = 0.3  # Minimum terrain height (0-1)

    tree_density: float = 0.0  # Tree coverage (0-1)
    chars: str | None = None  # Surface characters (None = solid block)

    def __post_init__(self):
        # assert self.height_scale >= self.base_height
        pass

    def texture(self, x: float, z: float, y: float, seed: int) -> tuple[str, RGB, RGB]:
        char = rand_choice(self.chars, x, z, seed) if self.chars else "█"
        color = lerp_color(self.color_lo, self.color_hi, y)
        return (char, color, color)


BIOMES = {
    "ocean": Biome(
        name="Ocean",
        color_lo=rgb("#002F4F"),  # Deep ocean blue
        color_hi=rgb("#005c7e"),  # Greener
        roughness=0.2,
        height_scale=0.05,
        base_height=0.1,
        tree_density=0.0,
        chars="∼∽",
    ),
    "forest": Biome(
        name="Forest",
        color_lo=rgb("#002800"),  # Dark forest green
        color_hi=rgb("#086200"),  # Pale blue-gray haze
        roughness=0.1,
        height_scale=0.4,
        base_height=0.4,
        tree_density=0.7,
    ),
    "mountains": Biome(
        name="Mountains",
        color_lo=rgb("#202020"),  # Dark granite
        color_hi=rgb("#eeeeee"),  # Snowy peaks / sky
        roughness=0.8,
        height_scale=0.8,
        base_height=0.6,
        tree_density=0.05,
        chars="              🭋🭯🭀",
    ),
    "jungle": Biome(
        name="Jungle",
        color_lo=rgb("#56971D"),  # Deep jungle green
        color_hi=rgb("#21410d"),  # Misty green haze
        roughness=0.6,
        height_scale=0.3,
        base_height=0.4,
        tree_density=0.85,
    ),
    "ice": Biome(
        name="Ice",
        color_lo=rgb("#8aa3f1"),  # Blue-white ice
        color_hi=rgb("#f0faff"),  # Bright snow/sky
        roughness=0.4,
        height_scale=0.3,
        base_height=0.3,
        tree_density=0.0,
    ),
    "plains": Biome(
        name="Plains",
        color_lo=rgb("#489c33"),  # Grassy green
        color_hi=rgb("#73A400"),  # Hazy yellow-green
        roughness=0.2,
        height_scale=0.4,
        base_height=0.3,
        tree_density=0.15,
        chars=",",
    ),
    "desert": Biome(
        name="Desert",
        color_lo=rgb("#aa8266"),  # Sandy tan
        color_hi=rgb("#ffedd3"),  # Pale dunes
        roughness=0.3,
        height_scale=0.2,
        base_height=0.3,
        tree_density=0.02,
    ),
    "alpine": Biome(
        name="Alpine Forest",
        color_lo=rgb("#24442D"),  # Dark pine
        color_hi=rgb("#426b57"),  # Mountain haze
        roughness=0.7,
        height_scale=0.4,
        base_height=0.6,
        tree_density=0.5,
    ),
}

# Tree characters - triangular shapes
TREE_CHARS = ["△", "▲", "▴", "◭", "◮"]
