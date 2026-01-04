import math
from functools import cache
from typing import Any, TypeAlias, overload

RGB: TypeAlias = tuple[int, int, int]
Cell: TypeAlias = tuple[str, RGB, RGB]

SOLID_BLOCK = "█"


@cache
def _rgb(color) -> RGB:
    """Convert a CSS-style hex color string into and RGB tuple."""
    assert color[0] == "#"
    assert len(color) == 7
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


@overload
def rgb(color: str) -> RGB:
    pass


@overload
def rgb(color: str, *tail: str) -> list[RGB]:
    pass


def rgb(color: str, *tail: str) -> RGB | list[RGB]:
    if not tail:
        return _rgb(color)
    return [_rgb(color)] + [_rgb(c) for c in tail]


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def rand(*seeds: Any) -> float:
    n: int = 74761393
    for x in seeds:
        n += hash(x)
        n = (n ^ (n >> 13)) * 1274126177
    result = ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF
    assert result >= 0 and result <= 1
    return result


def rand_choice(options: Any, *seeds: Any) -> Any:
    choice = rand(*seeds)
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

    return (c00 * (1 - tx) + c10 * tx) * (1 - tz) + (
        c01 * (1 - tx) + c11 * tx
    ) * tz


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
        total += (
            noise_2d(x * frequency, z * frequency, seed + i * 1000) * amplitude
        )
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
