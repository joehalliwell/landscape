from landscape.utils import rgb


def test_rgb():
    assert rgb("#ff00ff") == (255, 0, 255)
