from landscape.textures import Detail, Texture
from landscape.utils import cmap


class TestTexture:
    def test_get_height_mod_returns_zero_without_details(self):
        texture = Texture()
        assert texture.get_height_mod(0.5, 0.5, seed=0) == 0.0

    def test_get_height_mod_returns_detail_height(self):
        # Create a detail that covers everything (density=1.0, low freq)
        detail = Detail(
            name="Test", chars="X", frequency=0.001, density=1.0, height=0.5
        )
        texture = Texture(details=[detail])

        # Should return 0.5 because detail covers this point
        assert texture.get_height_mod(0.5, 0.5, seed=0) == 0.5

    def test_get_height_mod_respects_density(self):
        # Create a detail that covers nothing (density=-1.0)
        detail = Detail(name="Test", chars="X", density=-1.0, height=0.5)
        texture = Texture(details=[detail])

        # Should return 0.0 because detail doesn't cover
        assert texture.get_height_mod(0.5, 0.5, seed=0) == 0.0

    def test_texture_applies_detail_char(self):
        detail = Detail(
            name="Test",
            chars="X",
            frequency=0.001,
            density=1.0,
            color_map=cmap("#ff0000"),
            blend=0.0,
        )
        texture = Texture(details=[detail])

        char, fg, bg = texture.texture(0.5, 0.5, 0.0, seed=0)
        assert char == "X"
        assert fg == (255, 0, 0)

    def test_texture_and_height_mod_consistency(self):
        """Ensure visual and physical representations stay in sync."""
        detail = Detail(
            name="Test",
            chars="X",
            frequency=0.001,
            density=0.5,
            height=0.5,
            color_map=cmap("#ff0000"),
            blend=0.0,
        )
        texture = Texture(details=[detail])

        # Test a coordinate guaranteed to trigger the detail (low freq, high density)
        # using a seed/coord combo that we know hits
        # At (0,0) noise is often predictable or we can just assert they match

        # We'll check a few points to be sure
        for i in range(10):
            h = texture.get_height_mod(i * 1.0, i * 1.0, seed=0)
            char, _, _ = texture.texture(i * 1.0, i * 1.0, 0.0, seed=0)

            if h > 0:
                assert h == 0.5
                assert char == "X"
            else:
                assert h == 0.0
                assert char == " "
