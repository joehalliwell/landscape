from enum import IntEnum


class Season(IntEnum):
    """Season codes (4 bits)."""

    EARLY_SPRING = 0
    MID_SPRING = 1
    LATE_SPRING = 2
    EARLY_SUMMER = 3
    MID_SUMMER = 4
    LATE_SUMMER = 5
    EARLY_AUTUMN = 6
    MID_AUTUMN = 7
    LATE_AUTUMN = 8
    EARLY_WINTER = 9
    MID_WINTER = 10
    LATE_WINTER = 11
    # 12-15 reserved


# Season adjustments: (brightness_mult, red_shift, green_shift, blue_shift)
# Brightness multiplier applied to post-processing; color shifts tint the scene
SEASON_ADJUSTMENTS: dict[Season, tuple[float, int, int, int]] = {
    Season.EARLY_SPRING: (1.0, 0, 5, 5),  # Cool, fresh
    Season.MID_SPRING: (1.0, 5, 5, 0),  # Neutral-warm
    Season.LATE_SPRING: (1.0, 5, 5, -5),  # Warming
    Season.EARLY_SUMMER: (1.0, 5, 0, -5),  # Warm
    Season.MID_SUMMER: (1.0, 0, 0, 0),  # Neutral (baseline)
    Season.LATE_SUMMER: (0.95, 10, 5, -5),  # Golden, slightly dim
    Season.EARLY_AUTUMN: (0.9, 15, 5, -10),  # Warm, starting to darken
    Season.MID_AUTUMN: (0.8, 20, -5, -15),  # Darker, strong red-orange
    Season.LATE_AUTUMN: (0.3, 10, -15, -20),  # DRAMATIC: very dark, deep reds
    Season.EARLY_WINTER: (0.85, 0, 0, 10),  # Cool blue, shorter days
    Season.MID_WINTER: (0.8, -5, 0, 15),  # Cold blue, dark
    Season.LATE_WINTER: (0.85, -5, 5, 10),  # Cold but brightening
}
