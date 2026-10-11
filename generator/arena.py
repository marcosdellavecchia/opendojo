"""The open_dojo map: a broad FFA hall with a central prize, upper galleries
over its long sides and a workshop wing behind each short side, written as a
.map file for q3map2 (-game jk2). Every brush is an axis-aligned box."""

X, Y, H, T = 1024, 768, 352, 16
PILLARS = [(px, py) for px in (-448, 448) for py in (-256, 256)]
# The wings: interior from the hall wall to WX, |y| <= WY, WH high, entered
# through two doors in each short wall (|y| between the DOOR values).
WX, WY, WH = 1552, 512, 256
DOOR, DOOR_H = (256, 448), 160
# The galleries: a slab over |y| >= GY, |x| <= GX, its floor GZ high, with
# STEPS stairs (24 deep, 16 high) down to the hall at both ends. Gaps in
# its railing are drop points; columns hold its front edge.
GX, GY, GZ = 768, 608, 128
STEPS = 7
STAIR_X = GX + 24 * STEPS
RAIL_GAPS = [(-432, -336), (336, 432)]
COLUMNS = [(cx, GY + 12) for cx in (-576, -192, 192, 576)]
# Solid cover, (center x, center y, half x, half y), 76 high; bot routes
# use the same footprints. Hall machinery first, then the wing crates.
COVER = [(px, py, 48, 44) for px in (-768, 768) for py in (-384, 384)]
COVER += [(s * 1200, 160, 40, 40) for s in (-1, 1)]
COVER += [(s * 1392, -160, 40, 40) for s in (-1, 1)]
# The hall's supply bays and the posts of their gantries (12 by 16).
BAYS = (-832, 832)
POSTS = [(sx + dx, sy) for sx in BAYS for dx in (-102, 102) for sy in (-132, 132)]

AXES = {
    (1, 0, 0): ((0, 1, 0), (0, 0, 1)),
    (-1, 0, 0): ((0, 0, 1), (0, 1, 0)),
    (0, 1, 0): ((0, 0, 1), (1, 0, 0)),
    (0, -1, 0): ((1, 0, 0), (0, 0, 1)),
    (0, 0, 1): ((1, 0, 0), (0, 1, 0)),
    (0, 0, -1): ((0, 1, 0), (1, 0, 0)),
}

CAULK = 'common/caulk'
UP, DOWN = (0, 0, 1), (0, 0, -1)


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


def xbox(s, mins, maxs, tex, faces=None, scale=0.5):
    """box() for the east side (s=1) or mirrored onto the west side (s=-1)."""
    if s > 0:
        return box(mins, maxs, tex, faces, scale)
    flip = {(-n[0], n[1], n[2]): t for n, t in (faces or {}).items()}
    return box((-maxs[0], mins[1], mins[2]), (-mins[0], maxs[1], maxs[2]), tex, flip, scale)


def entity(fields, brushes=()):
    out = ['{']
    out += ['"%s" "%s"' % kv for kv in fields.items()]
    out += brushes
    out.append('}')
    return '\n'.join(out)


def wall(mins, maxs, faces, make=box):
    """A wall with a protective kickplate; faces: the normals that show."""
    top = (maxs[0], maxs[1], 24)
    bottom = (mins[0], mins[1], 24)
    return [make(mins, top, CAULK, {n: 'open/trim' for n in faces}, 0.25),
            make(bottom, maxs, CAULK, {n: 'open/wall' for n in faces}, 0.5)]


def hall():
    brushes = []
    # floor and ceiling: only their inner face shows
    brushes.append(box((-X - T, -Y - T, -T), (X + T, Y + T, 0), CAULK, {UP: 'open/floor'}, 0.25))
    brushes.append(box((-X - T, -Y - T, H), (X + T, Y + T, H + T), CAULK, {DOWN: 'open/ceiling'}, 0.5))
    # The long walls, then the short walls, cut by the wing doors.
    brushes += wall((-X, -Y - T, 0), (X, -Y, H), [(0, 1, 0)])
    brushes += wall((-X, Y, 0), (X, Y + T, H), [(0, -1, 0)])
    lo, hi = DOOR
    for s in (-1, 1):
        inner, outer = (-s, 0, 0), (s, 0, 0)
        x0, x1 = sorted((s * X, s * (X + T)))
        for y0, y1 in ((-Y, -hi), (-lo, lo), (hi, Y)):
            brushes += wall((x0, y0, 0), (x1, y1, H), [inner, outer])
        for y0, y1 in ((-hi, -lo), (lo, hi)):
            brushes.append(box((x0, y0, DOOR_H), (x1, y1, H), CAULK,
                               {inner: 'open/wall', outer: 'open/wall', DOWN: 'open/trim'}, 0.5))
            # A steel frame through the wall marks each door from both rooms.
            for j0, j1 in ((y0 - 16, y0), (y1, y1 + 16)):
                brushes.append(xbox(s, (X - 16, j0, 0), (X + T + 16, j1, DOOR_H + 16), 'open/pillar'))
            brushes.append(xbox(s, (X - 16, y0, DOOR_H), (X + T + 16, y1, DOOR_H + 16),
                                'open/trim'))
    # Structural ribs along the walls, clear of the routes.
    for x in (-864, -576, -288, 288, 576, 864):
        for y in (-Y, Y - 10):
            brushes.append(box((x - 10, y, 24), (x + 10, y + 10, H - 28), 'open/pillar', {}, 0.5))
    for y in (-576, 576):
        for x in (-X, X - 10):
            brushes.append(box((x, y - 10, 24), (x + 10, y + 10, H - 28), 'open/pillar', {}, 0.5))
    # pillars
    for px, py in PILLARS:
        brushes.append(box((px - 32, py - 32, 0), (px + 32, py + 32, H), 'open/pillar', {}, 0.5))
        brushes.append(box((px - 46, py - 46, 0), (px + 46, py + 46, 10), 'open/trim', {}, 0.25))
    # Waist-high machinery breaks long sight lines without sealing a route;
    # in the hall, each pair also screens a wing door.
    for cx, cy, hx, hy in COVER:
        brushes.append(box((cx - hx, cy - hy, 0), (cx + hx, cy + hy, 76),
                           'open/pillar', {UP: 'open/trim'}, 0.5))
        brushes.append(box((cx - hx - 6, cy - hy - 6, 76),
                           (cx + hx + 6, cy + hy + 6, 82), 'open/trim'))
    # the dais: two low steps
    brushes.append(box((-224, -160, 0), (224, 160, 12), 'open/trim', {UP: 'open/floor'}, 0.25))
    brushes.append(box((-160, -96, 12), (160, 96, 24), 'open/trim', {UP: 'open/floor'}, 0.25))
    # Supply bays on the short walls, between the wing doors. Their low pads
    # can be stepped onto; overhead gantries make them legible at a distance.
    for sx in BAYS:
        brushes.append(box((sx - 108, -128, 0), (sx + 108, 128, 12),
                           'open/trim', {}, 0.25))
        for sy in (-112, 112):
            brushes.append(box((sx - 92, sy - 8, 12), (sx + 92, sy + 8, 18),
                               'open/trim', {}, 0.5))
        brushes.append(box((sx - 108, -140, 130), (sx + 108, 140, 142),
                           'open/trim', {DOWN: 'open/light'}))
    for px, py in POSTS:
        brushes.append(box((px - 6, py - 8, 0), (px + 6, py + 8, 140), 'open/pillar'))
    # Long ceiling beams give the hall a clear visual rhythm.
    for bx in (-704, 0, 704):
        brushes.append(box((bx - 8, -Y, H - 50), (bx + 8, Y, H), 'open/pillar'))
    # light panels on the ceiling
    for lx in (-768, -384, 0, 384, 768):
        for ly in (-576, -288, 0, 288, 576):
            brushes.append(box((lx - 48, ly - 48, H - 4), (lx + 48, ly + 48, H), 'open/light', {}, 0.5))
    return brushes


def galleries():
    brushes = []
    for s in (-1, 1):
        def ybox(mins, maxs, tex, faces=None, scale=0.5):
            """box() for the north gallery (s=1) or mirrored south."""
            if s > 0:
                return box(mins, maxs, tex, faces, scale)
            flip = {(n[0], -n[1], n[2]): t for n, t in (faces or {}).items()}
            return box((mins[0], -maxs[1], mins[2]), (maxs[0], -mins[1], maxs[2]), tex, flip, scale)

        brushes.append(ybox((-GX, GY, GZ - 16), (GX, Y, GZ), 'open/trim',
                            {UP: 'open/floor', DOWN: 'open/ceiling'}, 0.25))
        # The railing, waist high, open at the drop points.
        edges = [-GX] + [x for gap in RAIL_GAPS for x in gap] + [GX]
        for x0, x1 in zip(edges[::2], edges[1::2]):
            brushes.append(ybox((x0, GY, GZ), (x1, GY + 8, GZ + 34), 'open/pillar',
                                {UP: 'open/trim'}))
        for cx, cy in COLUMNS:
            brushes.append(ybox((cx - 12, cy - 12, 0), (cx + 12, cy + 12, GZ - 16), 'open/pillar'))
        # Stairs at both ends, each step a solid block down to the floor.
        for e in (-1, 1):
            for k in range(1, STEPS + 1):
                x0, x1 = sorted((e * (GX + 24 * (k - 1)), e * (GX + 24 * k)))
                brushes.append(ybox((x0, GY, 0), (x1, Y, GZ - 16 * k), 'open/trim',
                                    {UP: 'open/floor'}, 0.25))
        # A supply pad at the middle.
        brushes.append(ybox((-96, GY + 32, GZ), (96, Y, GZ + 6), 'open/trim', {}, 0.25))
        # Lamps under the slab keep the lane beneath it readable.
        for cx in (-576, -192, 192, 576):
            brushes.append(ybox((cx - 40, 676, GZ - 20), (cx + 40, 700, GZ - 16), 'open/light'))
    return brushes


def wings():
    brushes = []
    for s in (-1, 1):
        # floor, ceiling, back and side walls
        brushes.append(xbox(s, (X, -WY - T, -T), (WX + T, WY + T, 0), CAULK, {UP: 'open/floor'}, 0.25))
        brushes.append(xbox(s, (X, -WY - T, WH), (WX + T, WY + T, WH + T), CAULK, {DOWN: 'open/ceiling'}, 0.5))
        for mins, maxs, n in (((WX, -WY, 0), (WX + T, WY, WH), (-1, 0, 0)),
                              ((X + T, WY, 0), (WX, WY + T, WH), (0, -1, 0)),
                              ((X + T, -WY - T, 0), (WX, -WY, WH), (0, 1, 0))):
            brushes += wall(mins, maxs, [n], lambda *a: xbox(s, *a))
        for y in (-288, 288):
            brushes.append(xbox(s, (WX - 10, y - 10, 24), (WX, y + 10, WH - 20), 'open/pillar'))
        brushes.append(xbox(s, (1288, -WY, WH - 24), (1304, WY, WH), 'open/pillar'))
        # The wing's supply bay against the back wall.
        brushes.append(xbox(s, (1440, -112, 0), (WX, 112, 12), 'open/trim', {}, 0.25))
        for sy in (-104, 104):
            brushes.append(xbox(s, (1448, sy - 8, 12), (WX, sy + 8, 18), 'open/trim'))
        brushes.append(xbox(s, (1448, -64, WH - 4), (1544, 64, WH), 'open/light'))
        for ly in (-320, 320):
            brushes.append(xbox(s, (1240, ly - 15, WH - 4), (1352, ly + 15, WH), 'open/light'))
    return brushes


def generate():
    brushes = hall() + galleries() + wings()
    world = entity({
        'classname': 'worldspawn',
        'message': 'Open Dojo',
        '_minlight': '24',
        '_color': '0.9 0.95 1',
    }, brushes)

    ents = [world]
    cool = '0.85 0.92 1'
    # point lights, a grid below the ceiling
    for lx in (-768, -384, 0, 384, 768):
        for ly in (-576, -288, 0, 288, 576):
            ents.append(entity({'classname': 'light', 'origin': '%d %d %d' % (lx, ly, H - 40),
                                'light': '560', '_color': cool}))
    for gy in (-688, 688):
        for lx in (-576, -192, 192, 576):
            ents.append(entity({'classname': 'light', 'origin': '%d %d %d' % (lx, gy, GZ - 36),
                                'light': '220', '_color': cool}))
    for s in (-1, 1):
        for ly in (-320, 320):
            ents.append(entity({'classname': 'light', 'origin': '%d %d %d' % (s * 1296, ly, WH - 40),
                                'light': '420', '_color': cool}))
        ents.append(entity({'classname': 'light', 'origin': '%d 0 %d' % (s * 1480, WH - 50),
                            'light': '300', '_color': cool}))
    # Spawn points in every area, facing into the action.
    spawns = [(-896, -528, 45), (-896, 528, -45), (896, -528, 135), (896, 528, -135),
              (-576, -528, 45), (576, -528, 135), (-576, 528, -45), (576, 528, -135),
              (-896, -192, 0), (-896, 192, 0), (896, -192, 180), (896, 192, 180)]
    spawns += [(s * 1480, y, 90 + 90 * s) for s in (-1, 1) for y in (-300, 300)]
    for sx, sy, angle in spawns:
        ents.append(entity({'classname': 'info_player_deathmatch',
                            'origin': '%d %d 40' % (sx, sy), 'angle': str(angle)}))
    for gx, angle in ((-640, 0), (640, 180)):
        for gy in (-688, 688):
            ents.append(entity({'classname': 'info_player_deathmatch',
                                'origin': '%d %d %d' % (gx, gy, GZ + 40), 'angle': str(angle)}))
    ents.append(entity({'classname': 'info_player_start', 'origin': '-896 0 40', 'angle': '0'}))
    # Center: one contested high-value shield. Six supply bays (hall, both
    # galleries, both wings) sustain longer fights; health rewards the side
    # lanes, the sheltered lane under each gallery and the wing corners.
    pickups = [('item_shield_lrg_instant', 0, 0, 52, 35)]
    pickups += [('item_shield_sm_instant', x, 0, 42, 20) for x in (-832, 832, -1496, 1496)]
    pickups += [('item_shield_sm_instant', 0, y, GZ + 36, 20) for y in (-696, 696)]
    for y in (-1, 1):
        for x in (-736, 736, -384, 384):
            pickups.append(('item_medpak_instant', x, y * (544 if abs(x) > 400 else 688), 32, 25))
        for x in (-1488, 1488):
            pickups.append(('item_medpak_instant', x, y * 448, 32, 25))
    for cls, x, y, z, wait in pickups:
        ents.append(entity({'classname': cls, 'origin': '%d %d %d' % (x, y, z),
                            'wait': str(wait)}))
    return '\n'.join(ents) + '\n'
