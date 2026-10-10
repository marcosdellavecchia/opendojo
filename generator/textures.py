"""Procedural textures for the arena: all generated here, no source images."""

import numpy as np

from common import save_image, value_noise


def grid_lines(size, step, width):
    a = np.arange(size) % step
    line = (a < width) | (a >= step - width)
    return line[:, None] | line[None, :]


def tint(gray, color):
    return gray[..., None] * np.asarray(color)[None, None, :]


def floor(size=512):
    n = value_noise(size, 4, 11) * 0.5 + value_noise(size, 32, 12, 2) * 0.5
    base = 0.30 + 0.12 * n
    tiles = grid_lines(size, size // 4, 3)
    bevel = grid_lines(size, size // 4, 6) & ~tiles
    g = np.where(tiles, 0.12, np.where(bevel, base + 0.10, base))
    return tint(g, (0.78, 0.82, 0.90))


def wall(size=512):
    n = value_noise(size, 8, 21)
    g = 0.38 + 0.10 * n
    panel = size // 2
    a = np.arange(size) % panel
    seam_y = (a < 4) | (a >= panel - 4)
    seam_x = ((np.arange(size) % (size // 4)) < 3)
    g = np.where(seam_y[:, None], 0.16, g)
    g = np.where(seam_x[None, :] & ~seam_y[:, None], g - 0.10, g)
    # a darker band in the lower half of each panel
    band = (a > panel * 0.62) & (a < panel * 0.80)
    g = np.where(band[:, None] & ~seam_x[None, :], g - 0.06, g)
    return tint(g, (0.86, 0.84, 0.80))


def trim(size=256):
    n = value_noise(size, 16, 31, 2)
    y = np.linspace(0, 1, size)
    ridge = 0.5 + 0.35 * np.cos(y * np.pi * 8) ** 2
    g = (0.35 + 0.15 * n) * ridge[:, None]
    return tint(g, (0.70, 0.74, 0.80))


def ceiling(size=256):
    n = value_noise(size, 8, 41)
    g = 0.22 + 0.06 * n
    g = np.where(grid_lines(size, size // 2, 2), 0.10, g)
    return tint(g, (0.80, 0.82, 0.88))


def light_panel(size=128):
    y, x = np.mgrid[0:size, 0:size] / (size - 1)
    edge = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    g = np.clip(edge * 10, 0, 1) * 0.9 + 0.1
    return tint(g, (0.85, 0.92, 1.0))


def pillar(size=256):
    n = value_noise(size, 4, 51)
    x = np.linspace(0, 1, size)
    flutes = 0.75 + 0.25 * np.abs(np.sin(x * np.pi * 4))
    g = (0.36 + 0.10 * n) * flutes[None, :]
    return tint(g, (0.82, 0.78, 0.72))


def generate(staging):
    save_image(staging, 'textures/open/floor.jpg', floor())
    save_image(staging, 'textures/open/wall.jpg', wall())
    save_image(staging, 'textures/open/trim.jpg', trim())
    save_image(staging, 'textures/open/ceiling.jpg', ceiling())
    save_image(staging, 'textures/open/light.jpg', light_panel())
    save_image(staging, 'textures/open/pillar.jpg', pillar())
