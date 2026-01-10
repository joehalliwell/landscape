import pytest

from landscape.utils import (
    base58_decode,
    base58_encode,
    contrasting_text_color,
    rgb,
)


def test_rgb():
    assert rgb("#ff00ff") == (255, 0, 255)


def test_contrasting_text_color():
    assert contrasting_text_color((255, 255, 255)) == (0, 0, 0)
    assert contrasting_text_color((0, 0, 0)) == (255, 255, 255)
    assert contrasting_text_color((255, 0, 0)) == (255, 255, 255)
    assert contrasting_text_color((0, 255, 0)) == (0, 0, 0)


@pytest.mark.parametrize(
    "val, length, expected_str",
    [
        (0, 1, "1"),
        (0, 3, "111"),
        (57, 1, "z"),
        (57, 2, "1z"),
        (123456789, 5, "BukQL"),
        (123456789, 9, "1111BukQL"),
    ],
)
def test_base58_encode_decode(val, length, expected_str):
    assert base58_encode(val, length=length) == expected_str
    assert base58_decode(expected_str) == val


@pytest.mark.parametrize("invalid_char", ["0", "O", "I", "l", "+", "/"])
def test_base58_decode_invalid(invalid_char):
    with pytest.raises(ValueError, match="Invalid Base58 character"):
        base58_decode(invalid_char)
