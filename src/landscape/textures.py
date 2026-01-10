from dataclasses import dataclass, field

from landscape.utils import RGB, Colormap, cmap, lerp_color, noise_2d, rand_choice


@dataclass
class Detail:
    """Decorative elements for a biome"""

    name: str
    chars: str | None
    frequency: float = 50.0
    density: float = 0.1
    height: float = 0.0
    color_map: Colormap = field(default_factory=Colormap)
    blend: float = 0.5  # Amount of background to blend in


@dataclass
class Texture:
    # Texture config
    color_map: Colormap = field(default_factory=lambda: cmap("#000000", "#ffffff"))

    # Single character details to add
    details: list[Detail] = field(default_factory=list)

    def _get_active_detail(
        self, x: float, z: float, seed: int
    ) -> tuple[Detail, float] | None:
        for i, detail in enumerate(self.details):
            p = noise_2d(x * 4 * detail.frequency, z * detail.frequency, seed * i)

            if p <= detail.density:
                return detail, p
        return None

    def get_height_mod(self, x: float, z: float, seed: int) -> float:
        match = self._get_active_detail(x, z, seed)
        if match:
            return match[0].height
        return 0.0

    def texture(
        self,
        x: float,
        z: float,
        y: float,
        seed: int,
        # ascii_only=False,
    ) -> tuple[str, RGB, RGB]:
        bg = self.color_map.val(y)
        fg = bg
        c = " "

        match = self._get_active_detail(x, z, seed)
        if match:
            detail, p = match
            c = rand_choice(detail.chars, int(1024 * p))
            fg = detail.color_map.val(
                noise_2d(
                    x * 4 * detail.frequency,
                    z * 4 * detail.frequency,
                    seed + 100,
                )
            )
            fg = lerp_color(fg, bg, detail.blend)

        return (c, fg, bg)
