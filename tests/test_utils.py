from landscape.utils import contrasting_text_color, rgb


def test_rgb():
    assert rgb("#ff00ff") == (255, 0, 255)


def test_contrasting_text_color():
    assert contrasting_text_color((255, 255, 255)) == (0, 0, 0)
    assert contrasting_text_color((0, 0, 0)) == (255, 255, 255)
    assert contrasting_text_color((255, 0, 0)) == (255, 255, 255)
    assert contrasting_text_color((0, 255, 0)) == (0, 0, 0)
