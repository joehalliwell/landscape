import pytest

from landscape.utils import (
    base58_decode,
    base58_encode,
    contrasting_text_color,
    find_shortcode_match,
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


@pytest.mark.parametrize(
    "result,shortcodes",
    [
        ("winter-day", ["w-d", "wd", "w", "W", "winter"]),
        ("summer-day", ["summer", "sd"]),
        ("clear-day", ["c", "cl", "cd"]),
        ("open-day", ["on", "o", "od", "day"]),
        ("afternoon", ["an", "after", "a", "anoon"]),
        ("noon", ["noon", "nn"]),
    ],
)
def test_find_shortcode(result, shortcodes):
    """Ensure that the shortcodes produce the result versus the below list of options"""
    options = ["winter-day", "summer-day", "clear-day", "open-day", "afternoon", "noon"]
    assert result in options
    for code in shortcodes:
        assert find_shortcode_match(code, options) == result, code


@pytest.mark.parametrize(
    "query,options,result",
    [
        ("foo", ["bar", "baz"], None),
    ],
)
def test_find_shortcode_no_match(query, options, result):
    with pytest.raises(ValueError):
        find_shortcode_match(query, options)
