from dataclasses import dataclass, field
from enum import Enum, IntEnum
from functools import cached_property

from landscape.textures import Detail, Texture
from landscape.utils import RGB, Colormap, cmap, slugify


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


# Tree characters - triangular shapes
TREE_CHARS = ["△", "▲", "▴", "◭", "◮"]


TREE_CMAP = cmap(
    "#0a290a",  # Deep shadow green
    "#1e6414",  # Forest green
    "#154f30",  # Blue-ish pine
    "#32a01e",  # Vibrant green
    "#4a6b12",  # Olive
    "#6b8c21",  # Lighter yellow-green
)


def tree_detail(density: float) -> Detail:
    return Detail(
        name="Trees",
        chars="".join(TREE_CHARS),
        density=density,
        frequency=20,
        color_map=TREE_CMAP,
        blend=0.6,
        height=0.05,
    )


@dataclass(kw_only=True)
class Biome(Texture):
    """Defines a landscape biome with colors and terrain properties."""

    code: BiomeCode
    name: str = "Anonymous"

    # Terrain generation parameters
    roughness: float = 0.5  # Higher = more jagged
    base_height: float = 0.3  # Minimum terrain height (0-1)
    height_scale: float = 0.7  # Height to add

    # Texture config
    color_map: Colormap = field(default_factory=lambda: cmap("#000000", "#ffffff"))

    # Single character details to add
    details: list[Detail] = field(default_factory=list)

    def texture(
        self,
        x: float,
        z: float,
        y: float,
        seed: int,
        # ascii_only=False,
    ) -> tuple[str, RGB, RGB]:
        ny = (y - self.base_height) / self.height_scale
        return super().texture(x, z, ny, seed)

    @cached_property
    def slug(self):
        return slugify(self.name)


BIOMES = {
    b.slug: b
    for b in [
        Biome(
            code=BiomeCode.OCEAN,
            name="Ocean",
            color_map=cmap("#002F4F", "#005c7e"),
            roughness=0.2,
            height_scale=0.05,
            base_height=0.1,
            details=[
                Detail(
                    name="Rollers",
                    chars="∼∽",
                    density=1.0,
                    color_map=cmap("#eeeeff", "#003337"),
                    blend=0,
                )
            ],
        ),
        Biome(
            code=BiomeCode.FOREST,
            name="Forest",
            color_map=cmap("#002800", "#086200"),
            roughness=0.1,
            height_scale=0.4,
            base_height=0.4,
            details=[tree_detail(0.7)],
        ),
        Biome(
            code=BiomeCode.MOUNTAINS,
            name="Mountains",
            color_map=cmap("#383838", "#ffffff"),  # Snowy peaks / sky
            roughness=0.8,
            height_scale=1.0,
            base_height=0.5,
            details=[
                tree_detail(0.05),
                Detail(
                    name="Shadows",
                    chars="🭋🭯🭀/\\",
                    frequency=50,
                    density=0.2,
                    color_map=cmap("#101010", "#505050"),
                    blend=0.8,
                ),
                Detail(
                    name="Highlights",
                    chars="🭋🭯🭀/\\",
                    frequency=40,
                    density=0.1,
                    color_map=cmap("#a0a0a0", "#dddddd"),
                    blend=0.5,
                ),
                Detail(
                    name="Boulders",
                    chars="🭁🭂🭃🭄🭅🭌🭍🭎🭏.xX",
                    frequency=40,
                    density=0.1,
                    color_map=cmap("#401010", "#efdddd"),
                    blend=0.2,
                ),
            ],
        ),
        Biome(
            code=BiomeCode.JUNGLE,
            name="Jungle",
            color_map=cmap("#56971D", "#21410d"),
            roughness=0.6,
            height_scale=0.3,
            base_height=0.4,
            details=[
                Detail(
                    name="Flower",
                    chars="*",
                    frequency=400,
                    density=0.05,
                    color_map=cmap("#c6009b", "#ff8c00"),
                ),
                Detail(
                    name="Flower2",
                    chars="+",
                    frequency=400,
                    density=0.05,
                    color_map=cmap("#5600c6", "#ff8c00"),
                ),
                Detail(
                    name="Banana",
                    chars="⸨",
                    frequency=400,
                    density=0.02,
                    color_map=cmap("#c67a00", "#fffb00"),
                ),
                tree_detail(0.85),
            ],
        ),
        Biome(
            code=BiomeCode.ICE,
            name="Ice",
            color_map=cmap("#b3c3f4", "#f0faff"),
            roughness=0.4,
            height_scale=0.2,
            base_height=0.2,
            details=[
                Detail(
                    name="Explorer's Flag",
                    chars="⚑",
                    frequency=50,
                    density=0.02,
                    color_map=cmap("#a00000", "#a00000"),
                )
            ],
        ),
        Biome(
            code=BiomeCode.PLAINS,
            name="Plains",
            color_map=cmap("#489c33", "#73A400"),
            roughness=0.2,
            height_scale=0.4,
            base_height=0.3,
            details=[
                Detail(
                    name="Grasses",
                    chars='"',
                    frequency=2,
                    density=0.5,
                    color_map=cmap("#489c33", "#5F8506"),  # Hazy yellow-green
                ),
                tree_detail(0.15),
            ],
        ),
        Biome(
            code=BiomeCode.DESERT,
            name="Desert",
            color_map=cmap("#aa8266", "#ffedd3"),
            roughness=0.3,
            height_scale=0.2,
            base_height=0.3,
            details=[
                Detail(
                    name="Catcus",
                    chars="Ψ",
                    frequency=50,
                    density=0.05,
                    color_map=cmap("#055e00", "#08a000"),
                ),
                tree_detail(0.02),
            ],
        ),
        Biome(
            code=BiomeCode.ALPINE,
            name="Alpine",
            color_map=cmap("#333C31", "#748372"),
            roughness=0.7,
            height_scale=0.8,
            base_height=0.6,
            details=[tree_detail(0.6)],
        ),
    ]
}


class BiomePreset(Enum):
    """Predefined multi-biome combinations (near -> far)."""

    COASTAL = ("ocean", "plains", "forest", "plains")
    MOUNTAIN_VALLEY = ("plains", "forest", "mountains")
    ALPINE_LAKE = ("ocean", "alpine", "mountains")
    TROPICAL = ("ocean", "jungle", "forest")
    ARCTIC = ("ocean", "ice", "ocean", "ice")
    DESERT_OASIS = ("desert", "mountains")
    FJORD = ("ocean", "mountains")
    HIGHLANDS = ("plains", "alpine", "mountains")
    TROPICAL_ISLAND = ("ocean", "jungle", "ocean")

    @property
    def biomes(self) -> tuple[str, ...]:
        """Get the biome slugs for this preset."""
        return self.value


COMPLEMENTS = {
    "ocean": ["plains", "forest"],
    "forest": ["plains", "mountains"],
    "mountains": ["alpine", "forest"],
    "jungle": ["ocean", "plains"],
    "ice": ["ocean", "mountains"],
    "plains": ["forest", "mountains"],
    "desert": ["plains", "mountains"],
    "alpine": ["mountains", "forest"],
}
