"""Saber blades, crosshairs and other effect images, generated here, and
invisible placeholders for the optional images the game code asks for that
the pack doesn't make (otherwise the engine draws its default checkerboard).

The placeholder names are the shader names the GPL game code registers that
were reported missing in a run of the game (pack-src/placeholders.txt).
"""

import os

import numpy as np

from common import ROOT, save_image, write_text

SABER_COLORS = {
    'red': (1.0, 0.2, 0.15), 'orange': (1.0, 0.55, 0.1), 'yellow': (1.0, 0.9, 0.2),
    'green': (0.25, 1.0, 0.3), 'blue': (0.25, 0.55, 1.0), 'purple': (0.75, 0.3, 1.0),
}


def radial(size, falloff=2.0):
    y, x = np.mgrid[0:size, 0:size]
    r = np.hypot(x - (size - 1) / 2, y - (size - 1) / 2) / (size / 2)
    return np.clip(1 - r, 0, 1) ** falloff


def across(size, core=0.18, falloff=2.5):
    """A beam's cross-section along u, the same along v."""
    u = np.abs(np.linspace(-1, 1, size))
    g = np.where(u < core, 1.0, np.clip(1 - (u - core) / (1 - core), 0, 1) ** falloff)
    return np.tile(g[None, :], (size, 1))


def colored(g, color, white_core=0.0):
    rgb = g[..., None] * np.asarray(color)[None, None, :]
    if white_core:
        w = np.clip((g - (1 - white_core)) / white_core, 0, 1)[..., None]
        rgb = rgb * (1 - w) + w
    return rgb


def crosshair(size, kind):
    y, x = np.mgrid[0:size, 0:size] - (size - 1) / 2
    r = np.hypot(x, y)
    if kind % 3 == 0:
        a = (np.abs(r - size * 0.3) < 1.2)
    elif kind % 3 == 1:
        a = ((np.abs(x) < 1.2) | (np.abs(y) < 1.2)) & (r > size * 0.12) & (r < size * 0.42)
    else:
        a = r < 2.0
    rgba = np.ones((size, size, 4))
    rgba[..., 3] = a.astype(float)
    return rgba


SHADERS = """// Saber blades and effects, written for the open pack.
"""


def generate(staging, provided):
    shaders = [SHADERS]
    for name, color in SABER_COLORS.items():
        save_image(staging, 'gfx/effects/sabers/%s_glow2.jpg' % name, colored(radial(64, 1.6), color))
        save_image(staging, 'gfx/effects/sabers/%s_line2.jpg' % name, colored(across(64), color, white_core=0.45))
        for part in ('glow', 'line'):
            shaders.append('gfx/effects/sabers/%s_%s\n{\n\tcull twosided\n\tnopicmip\n\t{\n'
                           '\t\tmap gfx/effects/sabers/%s_%s2.jpg\n\t\tblendfunc GL_ONE GL_ONE\n'
                           '\t\trgbgen vertex\n\t}\n}\n' % (name, part, name, part))
    save_image(staging, 'gfx/effects/sabers/blur.jpg', colored(across(64, 0.0, 1.5), (0.6, 0.6, 0.6)))
    shaders.append('gfx/effects/sabers/saberBlur\n{\n\tcull twosided\n\tnopicmip\n\t{\n'
                   '\t\tmap gfx/effects/sabers/blur.jpg\n\t\tblendfunc GL_ONE GL_ONE\n\t\trgbgen vertex\n\t}\n}\n')
    save_image(staging, 'gfx/effects/flare.jpg', colored(radial(64, 3), (1, 1, 1)))
    for n in ('gfx/effects/saberFlare', 'gfx/effects/yellow_glow', 'gfx/effects/saberDamageGlow'):
        shaders.append('%s\n{\n\tcull twosided\n\t{\n\t\tmap gfx/effects/flare.jpg\n'
                       '\t\tblendfunc GL_ONE GL_ONE\n\t\trgbgen vertex\n\t}\n}\n' % n)
    for i in range(10):
        save_image(staging, 'gfx/2d/crosshair%s.tga' % 'abcdefghij'[i], crosshair(32, i))
    write_text(staging, 'shaders/open_effects.shader', ''.join(shaders))

    made = {'gfx/effects/sabers/%s_%s' % (c, p) for c in SABER_COLORS for p in ('glow', 'line')}
    made |= {'gfx/effects/sabers/saberBlur', 'gfx/effects/saberFlare', 'gfx/effects/yellow_glow',
             'gfx/effects/saberDamageGlow'}
    made |= {'gfx/2d/crosshair%s' % c for c in 'abcdefghij'}
    placeholders(staging, made | provided)


def placeholders(staging, made):
    names = []
    for line in open(os.path.join(ROOT, 'pack-src', 'placeholders.txt')):
        name = line.split('//')[0].strip()
        if name:
            name = os.path.splitext(name)[0] if name.endswith(('.tga', '.jpg')) else name
            if name not in made:
                names.append(name)
    out = ['// Invisible stand-ins for optional images the game code asks for.\n']
    for n in names:
        out.append('%s\n{\n\tnopicmip\n\t{\n\t\tmap $whiteimage\n\t\tblendfunc GL_ZERO GL_ONE\n\t}\n}\n' % n)
    write_text(staging, 'shaders/open_placeholders.shader', ''.join(out))
