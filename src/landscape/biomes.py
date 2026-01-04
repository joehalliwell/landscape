from dataclasses import dataclass, field

from landscape.textures import Detail, Texture
from landscape.utils import RGB, Colormap, cmap


@dataclass(kw_only=True)
class Biome(Texture):
    """Defines a landscape biome with colors and terrain properties."""

    name: str = "Anonymous"

    # Terrain generation parameters
    roughness: float = 0.5  # Higher = more jagged
    base_height: float = 0.3  # Minimum terrain height (0-1)
    height_scale: float = 0.7  # Height to add

    tree_density: float = 0.0  # Tree coverage (0-1)

    # Texture cponfig
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


BIOMES = {
    "ocean": Biome(
        name="Ocean",
        color_map=cmap("#002F4F", "#005c7e"),
        roughness=0.2,
        height_scale=0.05,
        base_height=0.1,
        tree_density=0.0,
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
    "forest": Biome(
        name="Forest",
        color_map=cmap("#002800", "#086200"),
        roughness=0.1,
        height_scale=0.4,
        base_height=0.4,
        tree_density=0.7,
    ),
    "mountains": Biome(
        name="Mountains",
        color_map=cmap("#151515", "#ffffff"),  # Snowy peaks / sky
        roughness=0.8,
        height_scale=1.0,
        base_height=0.5,
        tree_density=0.05,
        details=[
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
    "jungle": Biome(
        name="Jungle",
        color_map=cmap("#56971D", "#21410d"),
        roughness=0.6,
        height_scale=0.3,
        base_height=0.4,
        tree_density=0.85,
        details=[
            Detail(
                name="Flower",
                chars="*",
                frequency=400,
                density=0.08,
                color_map=cmap("#c6009b", "#ff8c00"),
            ),
            Detail(
                name="Flower2",
                chars="+",
                frequency=400,
                density=0.08,
                color_map=cmap("#5600c6", "#ff8c00"),
            ),
            Detail(
                name="Banana",
                chars="⸨",
                frequency=400,
                density=0.02,
                color_map=cmap("#c67a00", "#fffb00"),
            ),
        ],
    ),
    "ice": Biome(
        name="Ice",
        color_map=cmap("#b3c3f4", "#f0faff"),
        roughness=0.4,
        height_scale=0.3,
        base_height=0.3,
        tree_density=0.0,
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
    "plains": Biome(
        name="Plains",
        color_map=cmap("#489c33", "#73A400"),
        roughness=0.2,
        height_scale=0.4,
        base_height=0.3,
        tree_density=0.15,
        details=[
            Detail(
                name="Grasses",
                chars='"',
                frequency=2,
                density=0.5,
                color_map=cmap("#489c33", "#5F8506"),  # Hazy yellow-green
            )
        ],
    ),
    "desert": Biome(
        name="Desert",
        color_map=cmap("#aa8266", "#ffedd3"),
        roughness=0.3,
        height_scale=0.2,
        base_height=0.3,
        tree_density=0.02,
        details=[
            Detail(
                name="Catcus",
                chars="Ψ",
                frequency=50,
                density=0.05,
                color_map=cmap("#055e00", "#08a000"),
            )
        ],
    ),
    "alpine": Biome(
        name="Alpine Forest",
        color_map=cmap("#333C31", "#748372"),
        roughness=0.7,
        height_scale=0.8,
        base_height=0.6,
        tree_density=0.6,
    ),
}

# Tree characters - triangular shapes
TREE_CHARS = ["△", "▲", "▴", "◭", "◮"]
