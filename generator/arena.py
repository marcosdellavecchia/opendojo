"""The open_dojo map: a closed hall with pillars and a low dais, written as a
.map file for q3map2 (-game jk2). Every brush is an axis-aligned box."""

AXES = {
    (1, 0, 0): ((0, 1, 0), (0, 0, 1)),
    (-1, 0, 0): ((0, 0, 1), (0, 1, 0)),
    (0, 1, 0): ((0, 0, 1), (1, 0, 0)),
    (0, -1, 0): ((1, 0, 0), (0, 0, 1)),
    (0, 0, 1): ((1, 0, 0), (0, 1, 0)),
    (0, 0, -1): ((0, 1, 0), (1, 0, 0)),
}

CAULK = 'common/caulk'


def add(a, b, s=1):
    return tuple(x + s * y for x, y in zip(a, b))


def box(mins, maxs, tex, faces=None, scale=0.5):
    """A brush. tex: texture for every face, faces: {normal: texture} overrides."""
    faces = faces or {}
    lines = ['{']
    for n, (u, v) in AXES.items():
        p1 = tuple(maxs[i] if n[i] > 0 else mins[i] if n[i] < 0 else mins[i] for i in range(3))
        p0 = add(p1, u, 64)
        p2 = add(p1, v, 64)
        t = faces.get(n, tex)
        pts = ' '.join('( %d %d %d )' % p for p in (p0, p1, p2))
        lines.append('%s %s 0 0 0 %g %g 0 0 0' % (pts, t, scale, scale))
    lines.append('}')
    return '\n'.join(lines)


def entity(fields, brushes=()):
    out = ['{']
    out += ['"%s" "%s"' % kv for kv in fields.items()]
    out += brushes
    out.append('}')
    return '\n'.join(out)


def generate():
    # the hall's inside: x -768..768, y -512..512, z 0..320
    X, Y, H, T = 768, 512, 320, 16
    brushes = []
    up, down = (0, 0, 1), (0, 0, -1)
    # floor and ceiling: only their inner face shows
    brushes.append(box((-X - T, -Y - T, -T), (X + T, Y + T, 0), CAULK, {up: 'open/floor'}, 0.25))
    brushes.append(box((-X - T, -Y - T, H), (X + T, Y + T, H + T), CAULK, {down: 'open/ceiling'}, 0.5))
    # walls, a trim band near the floor
    walls = [
        ((-X - T, -Y, 0), (-X, Y, H), (1, 0, 0)),
        ((X, -Y, 0), (X + T, Y, H), (-1, 0, 0)),
        ((-X, -Y - T, 0), (X, -Y, H), (0, 1, 0)),
        ((-X, Y, 0), (X, Y + T, H), (0, -1, 0)),
    ]
    for mins, maxs, n in walls:
        lo, hi = list(mins), list(maxs)
        top = list(hi)
        top[2] = 24
        brushes.append(box(tuple(lo), tuple(top), CAULK, {n: 'open/trim'}, 0.25))
        lo[2] = 24
        brushes.append(box(tuple(lo), tuple(hi), CAULK, {n: 'open/wall'}, 0.5))
    # pillars
    for px in (-448, 448):
        for py in (-256, 256):
            brushes.append(box((px - 32, py - 32, 0), (px + 32, py + 32, H), 'open/pillar', {}, 0.5))
    # the dais: two low steps
    brushes.append(box((-224, -160, 0), (224, 160, 12), 'open/trim', {up: 'open/floor'}, 0.25))
    brushes.append(box((-160, -96, 12), (160, 96, 24), 'open/trim', {up: 'open/floor'}, 0.25))
    # light panels on the ceiling
    for lx in (-512, -256, 0, 256, 512):
        for ly in (-256, 0, 256):
            brushes.append(box((lx - 48, ly - 48, H - 4), (lx + 48, ly + 48, H), 'open/light', {}, 0.5))

    world = entity({
        'classname': 'worldspawn',
        'message': 'Open Dojo',
        '_minlight': '24',
        '_color': '0.9 0.95 1',
    }, brushes)

    ents = [world]
    # point lights, a grid below the ceiling
    for lx in (-512, -256, 0, 256, 512):
        for ly in (-256, 0, 256):
            ents.append(entity({'classname': 'light', 'origin': '%d %d %d' % (lx, ly, H - 40),
                                'light': '420', '_color': '0.85 0.92 1'}))
    # spawn points around the hall, facing the middle
    spawns = [(-640, -384, 45), (-640, 384, -45), (640, -384, 135), (640, 384, -135),
              (0, -416, 90), (0, 416, -90), (-640, 0, 0), (640, 0, 180)]
    for sx, sy, angle in spawns:
        for cls in ('info_player_deathmatch',):
            ents.append(entity({'classname': cls, 'origin': '%d %d 40' % (sx, sy), 'angle': str(angle)}))
    ents.append(entity({'classname': 'info_player_start', 'origin': '-640 0 40', 'angle': '0'}))
    return '\n'.join(ents) + '\n'
