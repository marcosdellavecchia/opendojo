"""Shared helpers for the open asset pack generators."""

import os
import struct

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, 'build')


def out_path(staging, rel):
    path = os.path.join(staging, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def rng(seed):
    return np.random.default_rng(seed)


def value_noise(size, cells, seed, octaves=4):
    """Tileable fractal value noise in [0, 1], shape (size, size)."""
    r = rng(seed)
    out = np.zeros((size, size))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = cells * (2 ** o)
        grid = r.random((n, n))
        # bilinear, wrapping, with smoothstep
        coords = np.arange(size) * n / size
        i0 = np.floor(coords).astype(int) % n
        i1 = (i0 + 1) % n
        f = coords - np.floor(coords)
        f = f * f * (3 - 2 * f)
        a = grid[np.ix_(i0, i0)]
        b = grid[np.ix_(i0, i1)]
        c = grid[np.ix_(i1, i0)]
        d = grid[np.ix_(i1, i1)]
        fy = f[:, None]
        fx = f[None, :]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
        total += amp
        amp *= 0.5
    return out / total


def save_image(staging, rel, rgb):
    """rgb: float array (h, w, 3 or 4) in [0, 1]. Saves .tga, .jpg or .png."""
    data = np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8)
    mode = 'RGBA' if data.shape[2] == 4 else 'RGB'
    img = Image.fromarray(data, mode)
    path = out_path(staging, rel)
    if rel.endswith('.jpg'):
        img.save(path, quality=90)
    elif rel.endswith('.tga'):
        img.save(path, compression=None)
    else:
        img.save(path)
    return path


def write_bytes(staging, rel, data):
    with open(out_path(staging, rel), 'wb') as f:
        f.write(data)


def write_text(staging, rel, text):
    with open(out_path(staging, rel), 'w', newline='\n') as f:
        f.write(text)


def pack_floats(*values):
    return struct.pack('<%df' % len(values), *values)
