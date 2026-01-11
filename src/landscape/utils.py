import math
import re
from dataclasses import dataclass
from functools import cache
from typing import Any, Sequence, TypeAlias

RGB: TypeAlias = tuple[int, int, int]
Cell: TypeAlias = tuple[str, RGB, RGB]

SOLID_BLOCK = "█"
MAGENTA = (255, 0, 255)


@cache
def rgb(color) -> RGB:
    """Convert a CSS-style hex color string into and RGB tuple."""
    assert color[0] == "#"
    assert len(color) == 7
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def clamp_col(color):
    return (
        int(clamp(color[0], 0, 255)),
        int(clamp(color[1], 0, 255)),
        int(clamp(color[2], 0, 255)),
    )


def rand(seed: int) -> float:
    n: int = seed * 374761393
    n = (n ^ (n >> 13)) * 1274126177
    result = ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF
    assert result >= 0 and result <= 1
    return result


def rand_choice(options: Any, seed: int) -> Any:
    choice = rand(seed)
    if choice == 1.0:
        choice = 0.0

    return options[int(choice * len(options))]


def noise_2d(x: float, z: float, seed: int = 0) -> float:
    """Simple value noise for 2D input."""

    def hash_coord(xi: int, zi: int) -> float:
        n = xi + zi * 57 + seed * 374761393
        n = (n ^ (n >> 13)) * 1274126177
        return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF

    x0, z0 = int(math.floor(x)), int(math.floor(z))
    x1, z1 = x0 + 1, z0 + 1
    tx = x - x0
    tz = z - z0
    tx = tx * tx * (3 - 2 * tx)
    tz = tz * tz * (3 - 2 * tz)

    c00 = hash_coord(x0, z0)
    c10 = hash_coord(x1, z0)
    c01 = hash_coord(x0, z1)
    c11 = hash_coord(x1, z1)

    return (c00 * (1 - tx) + c10 * tx) * (1 - tz) + (c01 * (1 - tx) + c11 * tx) * tz


def fractal_noise_2d(
    x: float,
    z: float,
    octaves: int = 4,
    persistence: float = 0.5,
    scale: float = 0.05,
    seed: int = 0,
) -> float:
    """Multi-octave fractal noise (2D)."""
    total = 0.0
    amplitude = 1.0
    frequency = scale
    max_value = 0.0

    for i in range(octaves):
        total += noise_2d(x * frequency, z * frequency, seed + i * 1000) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= 2

    return total / max_value


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between two values."""
    return a + (b - a) * t


def lerp_color(
    c1: tuple[int, int, int], c2: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    """Linear interpolate between two RGB colors."""
    t = clamp(t, 0, 1)
    return (
        int(c1[0] * (1.0 - t) + c2[0] * t),
        int(c1[1] * (1.0 - t) + c2[1] * t),
        int(c1[2] * (1.0 - t) + c2[2] * t),
    )


def contrasting_text_color(bg: RGB) -> RGB:
    """Return black or white text color based on background luminance."""
    # Calculate luminance (standard formula)
    luminance = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    # Threshold of 128 is standard middle gray
    return (0, 0, 0) if luminance > 128 else (255, 255, 255)


@dataclass
class Colormap:
    """A colormap running through a number of linear segments"""

    colors: tuple[RGB, ...] = (MAGENTA,)
    # segments: tuple[float,...] | None = None

    def __post_init__(self):
        assert len(self.colors) > 0

    def val(self, v) -> RGB:
        assert len(self.colors) > 0
        # Only one
        if len(self.colors) == 1:
            return self.colors[0]
        v = clamp(v, 0.0, 1.0)
        w = 1.0 / (len(self.colors) - 1)
        idx = min(int(v / w), len(self.colors) - 2)
        # assert idx <= len(self.colors) - 2, (v, idx)
        remainder = (v - (idx * w)) / w
        # assert remainder >= 0.0
        # assert remainder <= 1.0
        # print(v, remainder)
        result = lerp_color(self.colors[idx], self.colors[idx + 1], remainder)
        # result = clamp_col(result)
        return result


def cmap(*colors) -> Colormap:
    """Factory function for colormaps"""
    return Colormap(colors=tuple([rgb(color) for color in colors]))


def slugify(text: str) -> str:
    return text.lower().replace(" ", "_")


def clear_console():
    "Clear the screen"
    print("\033[0;0H", end="")  # Move cursor
    print("\033[2J", end="")  # Clear screen


def find_shortcode_match(shortcode: str, options: Sequence[str]) -> str:
    """
    Find the best matching among options for the provided shortcode. Shortcodes
    try to approximate human abbreviations that (in reality) relate to
    morphemes.
    """
    sre = re.compile("(^|[ _-])" + "(.*)".join(list(shortcode)), flags=re.IGNORECASE)
    candidates = [option for option in options if sre.search(option)]
    if len(candidates) == 0:
        raise ValueError(f"Could not match '{shortcode}' in: {options}")
    return min((c for c in candidates), key=len)


BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58_encode(num: int, length: int | None = None) -> str:
    """Encode an integer to a Base58 string, optionally padded to a fixed length."""
    encoded = []
    base = len(BASE58_ALPHABET)

    if length is not None:
        for _ in range(length):
            num, rem = divmod(num, base)
            encoded.append(BASE58_ALPHABET[rem])
        if num > 0:
            raise ValueError(f"Number too large to fit in {length} characters")
    else:
        if num == 0:
            return BASE58_ALPHABET[0]
        while num > 0:
            num, rem = divmod(num, base)
            encoded.append(BASE58_ALPHABET[rem])

    return "".join(reversed(encoded))


def base58_decode(s: str) -> int:
    """Decode a Base58 string to an integer."""
    base = len(BASE58_ALPHABET)
    num = 0
    for char in s:
        if char not in BASE58_ALPHABET:
            raise ValueError(f"Invalid Base58 character: {char}")
        num = num * base + BASE58_ALPHABET.index(char)
    return num
