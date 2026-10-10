"""JK2 fonts (fonts/<name>.fontdat + .tga) and the console's character grid,
rendered from SIL OFL fonts in pack-src/fonts.

The game code asks for a small, a medium and a large font by name;
patches/mvsdk.patch and the engine name them open_small, open_medium
and open_large. They are sized like the fonts the code was written for. Each gets larger "_sharpN" variants, which
JK2MV picks for crisp text at high resolutions."""

import os
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common import ROOT, out_path, write_bytes

SRC = os.path.join(ROOT, 'pack-src', 'fonts')
MONO = os.path.join(SRC, 'sharetechmono-ShareTechMono-Regular.ttf')
SANS = os.path.join(SRC, 'exo2-Exo2[wght].ttf')

# name -> (ttf, weight for variable fonts, base point size, variant scales)
FONTS = {
    'open_small': (MONO, None, 18, (1.5, 2.25, 3.5)),
    'open_medium': (SANS, 500, 20, (1.5, 2.25, 3.5)),
    'open_large': (SANS, 700, 17, (1.5, 2.25, 3.5)),
}

CHARS = [c for c in range(32, 256) if not 127 <= c < 160]


def load(ttf, weight, size):
    font = ImageFont.truetype(ttf, size)
    if weight is not None:
        try:
            font.set_variation_by_axes([weight])
        except OSError:
            pass
    return font


def render_font(ttf, weight, point):
    font = load(ttf, weight, point)
    ascent, descent = font.getmetrics()
    glyphs = {}
    for c in CHARS:
        ch = bytes([c]).decode('cp1252', errors='replace')
        x0, y0, x1, y1 = font.getbbox(ch)
        glyphs[c] = (ch, x0, y0, max(x1 - x0, 0), max(y1 - y0, 0), int(round(font.getlength(ch))))

    # shelf packing, growing the atlas until it fits
    pad = 2
    for size in (128, 256, 512, 1024, 2048):
        x = y = row = 0
        places = {}
        ok = True
        for c in CHARS:
            _, _, _, w, h, _ = glyphs[c]
            if x + w + pad > size:
                x, y, row = 0, y + row + pad, 0
            if y + h + pad > size:
                ok = False
                break
            places[c] = (x + pad, y + pad)
            x += w + pad
            row = max(row, h)
        if ok:
            break

    atlas = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(atlas)
    for c in CHARS:
        ch, x0, y0, w, h, _ = glyphs[c]
        if w and h:
            px, py = places[c]
            draw.text((px - x0, py - y0), ch, fill=255, font=font)

    data = bytearray()
    for c in range(256):
        if c not in glyphs:
            data += struct.pack('<4hi4f', 0, 0, 0, 0, 0, 0, 0, 0, 0)
            continue
        _, x0, y0, w, h, adv = glyphs[c]
        px, py = places[c]
        baseline = ascent - y0
        data += struct.pack('<4hi4f', w, h, adv, x0, baseline,
                            px / size, py / size, (px + w) / size, (py + h) / size)
    data += struct.pack('<5h', point, ascent + descent, ascent, descent, 0)
    data += b'\0\0'	# sizeof(dfontdat_t) is padded to a multiple of 4
    assert len(data) == 7180
    return atlas, bytes(data)


def save_alpha_tga(staging, rel, alpha):
    a = np.asarray(alpha)
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = a
    Image.fromarray(rgba, 'RGBA').save(out_path(staging, rel), compression=None)


def charset(staging):
    """gfx/2d/charsgrid_med: the console's 16x16 grid of 32x32 cells."""
    cell = 32
    font = load(MONO, None, 30)
    ascent, _ = font.getmetrics()
    img = Image.new('L', (cell * 16, cell * 16), 0)
    draw = ImageDraw.Draw(img)
    for c in range(32, 256):
        if 127 <= c < 160:
            continue
        ch = bytes([c]).decode('cp1252', errors='replace')
        w = font.getlength(ch)
        cx, cy = (c % 16) * cell, (c // 16) * cell
        draw.text((cx + (cell - w) / 2, cy + cell - 6 - ascent), ch, fill=255, font=font)
    save_alpha_tga(staging, 'gfx/2d/charsgrid_med.tga', img)


def generate(staging):
    for name, (ttf, weight, point, scales) in FONTS.items():
        atlas, dat = render_font(ttf, weight, point)
        save_alpha_tga(staging, 'fonts/%s.tga' % name, atlas)
        write_bytes(staging, 'fonts/%s.fontdat' % name, dat)
        for i, s in enumerate(scales):
            atlas, dat = render_font(ttf, weight, int(round(point * s)))
            save_alpha_tga(staging, 'fonts/%s_sharp%d.tga' % (name, i + 1), atlas)
            write_bytes(staging, 'fonts/%s_sharp%d.fontdat' % (name, i + 1), dat)
    charset(staging)
    # the fonts' licenses travel with the pack
    for lic in ('exo2-OFL.txt', 'sharetechmono-OFL.txt'):
        with open(os.path.join(SRC, lic), 'rb') as f:
            write_bytes(staging, 'fonts/licenses/%s' % lic, f.read())
