"""Original MD3 health/shield pickups and matching HUD icons."""

import math
import struct

import numpy as np

from common import save_image, write_bytes

BASE = 'models/map_objects/mp'


def field(value, width=64):
    return value.encode()[:width - 1].ljust(width, b'\0')


def surface(name, shader, rings, sides=10):
    vertices, normals, uvs, tris = [], [], [], []
    for z, radius in rings:
        for i in range(sides + 1):
            angle = 2 * math.pi * i / sides
            c, s = math.cos(angle), math.sin(angle)
            vertices.append((radius * c, radius * s, z))
            normals.append((c, s, 0.3))
            uvs.append((i / sides, 1 - z / 28))
    row = sides + 1
    for j in range(len(rings) - 1):
        for i in range(sides):
            a = j * row + i
            tris.extend(((a, a + 1, a + row), (a + 1, a + row + 1, a + row)))
    # A top face avoids the hollow-cylinder silhouette from above.
    top = len(vertices)
    vertices.append((0, 0, rings[-1][0]))
    normals.append((0, 0, 1))
    uvs.append((0.5, 0.5))
    last = (len(rings) - 1) * row
    tris.extend((top, last + i, last + i + 1) for i in range(sides))

    triangles = b''.join(struct.pack('<3i', *tri) for tri in tris)
    shader_data = struct.pack('<64si', field(shader), 0)
    st = b''.join(struct.pack('<2f', *uv) for uv in uvs)
    xyz = b''
    for point, normal in zip(vertices, normals):
        nx, ny, nz = normal
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        lat = int(math.atan2(ny, nx) * 255 / (2 * math.pi)) & 255
        lng = int(math.acos(nz / length) * 255 / (2 * math.pi)) & 255
        xyz += struct.pack('<3hH', *(int(round(c * 64)) for c in point), (lat << 8) | lng)
    header_size = 108
    ofs_tri = header_size
    ofs_shader = ofs_tri + len(triangles)
    ofs_st = ofs_shader + len(shader_data)
    ofs_xyz = ofs_st + len(st)
    end = ofs_xyz + len(xyz)
    header = struct.pack('<4s64s10i', b'IDP3', field(name), 0, 1, 1,
                         len(vertices), len(tris), ofs_tri, ofs_shader,
                         ofs_st, ofs_xyz, end)
    return header + triangles + shader_data + st + xyz


def md3(name, color):
    shell = surface('shell', BASE + '/open_shell', [(0, 12), (3, 14), (5, 13)])
    body = surface('core', BASE + '/open_' + color,
                   [(5, 10), (8, 12), (20, 12), (24, 9), (26, 6)])
    frame_size = 56
    ofs_frames = 108
    ofs_tags = ofs_frames + frame_size
    ofs_surfs = ofs_tags
    end = ofs_surfs + len(shell) + len(body)
    header = struct.pack('<4si64s9i', b'IDP3', 15, field(name), 0, 1, 0, 2,
                         0, ofs_frames, ofs_tags, ofs_surfs, end)
    frame = struct.pack('<3f3f3ff16s', -14, -14, 0, 14, 14, 26,
                        0, 0, 13, 25, field('idle', 16))
    return header + frame + shell + body


def texture(color, emblem=False):
    size = 128
    y, x = np.mgrid[:size, :size]
    base = np.asarray(color)
    stripe = (x % 32 < 4) | (y % 37 < 3)
    img = np.ones((size, size, 3)) * base * (0.75 + 0.13 * np.sin(x / 10))[..., None]
    img[stripe] *= 0.58
    if emblem:
        plus = ((abs(x - 64) < 9) & (abs(y - 64) < 30)) | ((abs(y - 64) < 9) & (abs(x - 64) < 30))
        img[plus] = (0.91, 0.95, 0.77)
    else:
        ring = (np.hypot(x - 64, y - 64) > 24) & (np.hypot(x - 64, y - 64) < 35)
        img[ring] = (0.85, 0.94, 0.89)
    return np.clip(img, 0, 1)


def icon(color, health=False, size=64):
    y, x = np.mgrid[:size, :size]
    x = x - (size - 1) / 2
    y = y - (size - 1) / 2
    shape = (abs(x) + abs(y) * 0.52) < size * 0.38
    border = (abs(x) + abs(y) * 0.52) > size * 0.32
    rgba = np.zeros((size, size, 4))
    rgba[shape, :3] = color
    rgba[shape & border, :3] = (0.88, 0.90, 0.74)
    rgba[shape, 3] = 1
    if health:
        mark = ((abs(x) < 4) & (abs(y) < 17)) | ((abs(y) < 4) & (abs(x) < 17))
    else:
        mark = (np.abs(np.hypot(x, y) - 12) < 2) | ((abs(x) < 3) & (abs(y) < 20))
    rgba[shape & mark, :3] = (0.98, 0.98, 0.90)
    return rgba


def generate(staging):
    save_image(staging, BASE + '/open_shell.jpg', texture((0.22, 0.31, 0.32)))
    save_image(staging, BASE + '/open_health.jpg', texture((0.30, 0.66, 0.42), True))
    save_image(staging, BASE + '/open_shield.jpg', texture((0.28, 0.61, 0.73)))
    for path, color in (('medpac.md3', 'health'), ('psd_sm.md3', 'shield'), ('psd.md3', 'shield')):
        write_bytes(staging, BASE + '/' + path, md3(path, color))
    save_image(staging, 'gfx/hud/i_icon_medkit.tga', icon((0.26, 0.65, 0.39), True))
    save_image(staging, 'gfx/mp/small_shield.tga', icon((0.25, 0.58, 0.70)))
    save_image(staging, 'gfx/mp/large_shield.tga', icon((0.33, 0.68, 0.81)))
