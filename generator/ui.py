"""Images for the menus and the console, generated here."""

import numpy as np

from common import save_image, value_noise


def cursor(size=32):
    y, x = np.mgrid[0:size, 0:size].astype(float)
    # an arrow: inside the triangle (0,0) (0,24) (17,17)
    inside = (x >= 0) & (y >= x) & (y - 24 <= -x * 7 / 17 + 0) | ((x <= 1.5) & (y <= 24))
    inside &= (y <= 24 + 0 * x) & (x <= 17)
    edge = inside & ~np.roll(np.roll(inside, 1, 0), 1, 1)
    rgba = np.zeros((size, size, 4))
    rgba[inside] = (0.85, 0.92, 1.0, 1.0)
    rgba[edge] = (0.1, 0.2, 0.35, 1.0)
    return rgba


def console(size=256):
    n = value_noise(size, 8, 61)
    rgba = np.zeros((size, size, 4))
    rgba[..., 0] = 0.03 + 0.03 * n
    rgba[..., 1] = 0.05 + 0.03 * n
    rgba[..., 2] = 0.09 + 0.04 * n
    rgba[..., 3] = 0.88
    return rgba


def generate(staging):
    save_image(staging, 'ui/open/cursor.tga', cursor())
    save_image(staging, 'gfx/open/console.tga', console())
