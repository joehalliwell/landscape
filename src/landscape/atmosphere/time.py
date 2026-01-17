from enum import IntEnum

from landscape.utils import Colormap, cmap


class TimeOfDay(IntEnum):
    """Time of day codes (3 bits)."""

    DAWN = 0
    MORNING = 1
    NOON = 2
    AFTERNOON = 3
    DUSK = 4
    EVENING = 5
    NIGHT = 6
    LATE_NIGHT = 7


# Sky color palettes by time of day
TIME_SKY_PALETTES: dict[TimeOfDay, Colormap] = {
    TimeOfDay.DAWN: cmap("#ecb8ec", "#F6FF8F", "#99CCDA", "#77AEBD"),
    TimeOfDay.MORNING: cmap("#87CEEB", "#4A90D9", "#2E6BA6"),
    TimeOfDay.NOON: cmap("#aabbff", "#006aff", "#0069fc"),
    TimeOfDay.AFTERNOON: cmap("#87CEEB", "#5A9BD4", "#3A7BC0"),
    TimeOfDay.DUSK: cmap("#FFD500", "#ff0800", "#480000"),
    TimeOfDay.EVENING: cmap("#2E1A47", "#1A0A2E", "#0A0515"),
    TimeOfDay.NIGHT: cmap("#06063A", "#000000"),
    TimeOfDay.LATE_NIGHT: cmap("#020220", "#000000"),
}

# Brightness/tone adjustments by time: (brightness_mult, warmth_shift, blue_shift)
TIME_ADJUSTMENTS: dict[TimeOfDay, tuple[float, int, int]] = {
    TimeOfDay.DAWN: (0.9, 20, -10),
    TimeOfDay.MORNING: (1.0, 5, 0),
    TimeOfDay.NOON: (1.1, 0, 0),
    TimeOfDay.AFTERNOON: (1.05, 5, -5),
    TimeOfDay.DUSK: (0.5, 15, -15),
    TimeOfDay.EVENING: (0.5, -10, 10),
    TimeOfDay.NIGHT: (0.4, -20, 20),
    TimeOfDay.LATE_NIGHT: (0.35, -10, 10),
}

# Star visibility by time (0 = fully visible, 1 = invisible)
STAR_VISIBILITY: dict[TimeOfDay, float] = {
    TimeOfDay.DAWN: 0.7,
    TimeOfDay.MORNING: 1.0,
    TimeOfDay.NOON: 1.0,
    TimeOfDay.AFTERNOON: 1.0,
    TimeOfDay.DUSK: 0.5,
    TimeOfDay.EVENING: 0.2,
    TimeOfDay.NIGHT: 0.1,
    TimeOfDay.LATE_NIGHT: 0.1,
}
