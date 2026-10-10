"""Checks the generated player model the way JK2MV reads it, and draws
animations to PNG contact sheets.

    build/venv/bin/python generator/preview.py ANIM_NAME... [--out dir]

It parses the .gla/.glm from the staging folder (not the generator's data),
decompresses bones like MC_UnCompressQuat, chains them like G2_TransformBone,
skins the mesh, and computes the *r_hand and the saber's *flash bolts like
G2_ProcessSurfaceBolt, then the blade direction like the game's saber code
(the negative Y axis of GetBoltMatrix, which turns the bolt by 270 degrees).
"""

import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import BUILD  # noqa: E402

STAGING = os.path.join(BUILD, 'pack', 'base')


def read_gla(path):
    d = open(path, 'rb').read()
    ident, ver, name, scale, nframes, ofs_frames, nbones, ofs_pool, ofs_skel, end = struct.unpack_from('<4si64sfiiiiii', d)
    assert ident == b'2LGA' and ver == 6 and end == len(d), (ident, ver, end, len(d))
    bones = []
    for i in range(nbones):
        off = struct.unpack_from('<i', d, 100 + 4 * i)[0]
        p = 100 + off
        bname, flags, parent = struct.unpack_from('<64sIi', d, p)
        base = np.array(struct.unpack_from('<12f', d, p + 72)).reshape(3, 4)
        bones.append((bname.rstrip(b'\0').decode(), parent, base))

    def bone(frame, i):
        o = ofs_frames + (frame * nbones + i) * 3
        idx = d[o] | (d[o + 1] << 8) | (d[o + 2] << 16)
        w, x, y, z, tx, ty, tz = struct.unpack_from('<7H', d, ofs_pool + idx * 14)
        w, x, y, z = (np.array([w, x, y, z]) / 16383.0) - 2.0
        m = np.zeros((3, 4))
        m[0] = [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y), tx / 64 - 512]
        m[1] = [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x), ty / 64 - 512]
        m[2] = [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y), tz / 64 - 512]
        return m
    return dict(bones=bones, nframes=nframes, bone=bone)


def read_glm(path):
    d = open(path, 'rb').read()
    ident, ver, name, anim, _, nbones, nlods, ofs_lods, nsurf, ofs_hier, end = struct.unpack_from('<4si64s64siiiiiii', d)
    assert ident == b'2LGM' and ver == 6 and end == len(d)
    assert ofs_hier == 164 + 4 * nsurf, 'ofsSurfHierarchy must point at the first entry'
    surfs = []
    for i in range(nsurf):
        off = struct.unpack_from('<i', d, 164 + 4 * i)[0]
        p = 164 + off
        sname, flags, shader, _, parent = struct.unpack_from('<64sI64sii', d, p)
        surfs.append(dict(name=sname.rstrip(b'\0').decode(), flags=flags, parent=parent))
    lod_start = ofs_lods
    for i in range(nsurf):
        off = struct.unpack_from('<i', d, lod_start + 4 + 4 * i)[0]
        p = lod_start + 4 + off
        _, idx, ofs_hdr, nv, ofs_v, nt, ofs_t, nb, ofs_b, ofs_end = struct.unpack_from('<10i', d, p)
        assert idx == i and p + ofs_hdr == 0
        refs = struct.unpack_from('<%di' % nb, d, p + ofs_b)
        tris = [struct.unpack_from('<3i', d, p + ofs_t + 12 * k) for k in range(nt)]
        verts = []
        for k in range(nv):
            vals = struct.unpack_from('<6fI', d, p + ofs_v + 32 * k)
            verts.append((np.array(vals[3:6]), refs[vals[6] & 31]))
        surfs[i].update(tris=tris, verts=verts)
    return surfs


# Ghoul2's root matrix for a model bolted to nothing: +90 degrees about Z
ROOT = np.array([[0.0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0]])


def finals(gla, frame):
    out = []
    for i, (name, parent, base) in enumerate(gla['bones']):
        m = gla['bone'](frame, i)
        p = out[parent] if parent >= 0 else ROOT
        if True:
            r = p[:, :3] @ m[:, :3]
            t = p[:, :3] @ m[:, 3] + p[:, 3]
            m = np.column_stack([r, t])
        out.append(m)
    return out


def xform(m, v):
    return m[:, :3] @ v + m[:, 3]


def tag_frame(pts):
    """G2_ProcessSurfaceBolt for a mesh tag."""
    sides = [pts[(j + 1) % 3] - pts[j] for j in range(3)]
    ax1 = sides[2] / np.linalg.norm(sides[2])
    ax0 = sides[0] / np.linalg.norm(sides[0])
    ax0 = ax0 - np.dot(ax0, ax1) * ax1
    ax0 /= np.linalg.norm(ax0)
    ax2 = np.cross(sides[0], sides[2])
    ax2 /= np.linalg.norm(ax2)
    return np.column_stack([ax1, ax0, -ax2, pts[2]])


def pose_geometry(gla, glm, saber, frame):
    F = finals(gla, frame)
    polys = []
    hand = None
    for s in glm:
        pts = [xform(F[b], v) for v, b in s['verts']]
        if s['flags'] & 1:
            if s['name'] == '*r_hand':
                hand = tag_frame(pts)
            continue
        for t in s['tris']:
            polys.append([pts[k] for k in t])
    blade = None
    if hand is not None:
        for s in saber:
            pts = [xform(hand, v) for v, b in s['verts']]
            if s['flags'] & 1:
                fl = tag_frame(pts)
                blade = (fl[:, 3], -fl[:, 0])	# origin, -X: GetBoltMatrix's -Y after its 270 turn
                continue
            for t in s['tris']:
                polys.append([pts[k] for k in t])
    return polys, blade


def project(p, yaw):
    """Camera on the horizon at angle yaw from the model's front (+X)."""
    cam = np.array([np.cos(yaw), np.sin(yaw), 0.0])
    right = np.array([-np.sin(yaw), np.cos(yaw), 0.0])
    return float(np.dot(p, right)), -p[2], -float(np.dot(p, cam))


def draw(gla, glm, saber, frames, title, out, yaw=np.radians(35)):
    cell = 220
    cols = min(len(frames), 6)
    rows = (len(frames) + cols - 1) // cols
    img = Image.new('RGB', (cell * cols, cell * rows + 20), (24, 26, 32))
    dr = ImageDraw.Draw(img)
    dr.text((4, 4), title, fill=(220, 220, 220))
    light = np.array([0.4, 0.3, 0.85])
    for k, f in enumerate(frames):
        ox, oy = (k % cols) * cell + cell // 2, (k // cols) * cell + 20 + int(cell * 0.62)
        sc = cell / 120
        polys, blade = pose_geometry(gla, glm, saber, f)
        items = []
        for poly in polys:
            n = np.cross(poly[1] - poly[0], poly[2] - poly[0])
            if np.linalg.norm(n) < 1e-9:
                continue
            n /= np.linalg.norm(n)
            pr = [project(p, yaw) for p in poly]
            depth = sum(p[2] for p in pr) / 3
            shade = 0.35 + 0.65 * max(0.0, float(np.dot(n, light)))
            items.append((depth, [(ox + sc * a, oy + sc * b) for a, b, _ in pr], shade))
        # floor line
        dr.line([(ox - 50, oy + 24 * sc), (ox + 50, oy + 24 * sc)], fill=(70, 70, 80))
        for depth, pts, shade in sorted(items, key=lambda i: -i[0]):
            g = int(200 * shade)
            dr.polygon(pts, fill=(g, g, int(g * 1.05)))
        if blade is not None:
            o, d = blade
            a = project(o, yaw)
            b = project(o + d * 40, yaw)
            dr.line([(ox + sc * a[0], oy + sc * a[1]), (ox + sc * b[0], oy + sc * b[1])], fill=(90, 170, 255), width=3)
        dr.text((ox - cell // 2 + 4, oy - int(cell * 0.62) + 2), str(f), fill=(150, 150, 150))
    img.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('anims', nargs='*', default=['BOTH_STAND2', 'BOTH_A2_T__B_', 'BOTH_A2__L__R', 'BOTH_RUN2'])
    ap.add_argument('--out', default=os.path.join(BUILD, 'preview'))
    ap.add_argument('--yaw', type=float, default=35)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    gla = read_gla(os.path.join(STAGING, 'models/players/_humanoid/_humanoid.gla'))
    glm = read_glm(os.path.join(STAGING, 'models/players/open/model.glm'))
    saber = read_glm(os.path.join(STAGING, 'models/weapons2/saber/saber_w.glm'))
    cfg = {}
    for line in open(os.path.join(STAGING, 'models/players/_humanoid/animation.cfg')):
        name, first, num, loop, fps = line.split()
        cfg[name] = (int(first), int(num), float(fps))
    for name in args.anims:
        first, num, fps = cfg[name]
        frames = list(range(first, first + num))
        if len(frames) > 12:
            frames = frames[::max(1, len(frames) // 12)][:12]
        out = os.path.join(args.out, '%s.png' % name)
        draw(gla, glm, saber, frames, '%s  frames %d-%d @ %g fps' % (name, first, first + num - 1, fps), out,
             np.radians(args.yaw))
        print(out)


if __name__ == '__main__':
    main()
