"""Bots for the open pack: the list of bots (botfiles/bots.txt), their
personality (botfiles/open.jkb) and the open_dojo map's waypoints
(botroutes/open_dojo.wnt), all written here."""

import math

import arena
from common import write_text

NAMES = ['Rook', 'Ember', 'Quill', 'Vale', 'Sable', 'Tamsin', 'Orrin', 'Juno']

# the Force setup the game falls back on (w_force.c): saber offense,
# defense and throw at 3, so bots use every stance
FORCE = '7-1-032330000000001333'


def bots_txt():
    out = ['// Bots of the open pack: names made up for it, all on the pack\'s model.\n']
    for name in NAMES:
        out.append('{\nname\t"%s"\nmodel\t"open/default"\npersonality\t"botfiles/open.jkb"\n}\n' % name)
    return ''.join(out)


def personality():
    # the parser wants a line break before the group name and "\r\n{" after it
    lines = [
        '// The open pack\'s bot personality: a saber fighter.',
        'GeneralBotInfo',
        '{',
        '\treflex\t100',
        '\taccuracy\t0.8',
        '\tturnspeed\t15',
        '\tturnspeed_combat\t25',
        '\tmaxturn\t90',
        '\tperfectaim\t0',
        '\tchatability\t0',
        '\tchatfrequency\t0',
        '\thatelevel\t1',
        '\tcamper\t0',
        '\tsaberspecialist\t1',
        '\tforceinfo\t%s' % FORCE,
        '}',
        '',
        'BotWeaponWeights',
        '{',
        '\tWP_SABER\t20',
        '}',
        '',
    ]
    return '\r\n'.join(lines)


def floor_height(x, y):
    if abs(x) <= 160 and abs(y) <= 96:
        return 24
    if abs(x) <= 224 and abs(y) <= 160:
        return 12
    if any(abs(x - sx) <= 108 for sx in arena.BAYS) and abs(y) <= 128:
        return 12
    if 1440 <= abs(x) <= arena.WX and abs(y) <= 112:
        return 12
    return 0


def inside(x, y, m=20):
    """On the floor of the hall, a wing or a doorway, m from the walls."""
    ax, ay = abs(x), abs(y)
    lo, hi = arena.DOOR
    return ((ax <= arena.X - m and ay <= arena.Y - m) or
            (arena.X + arena.T + m <= ax <= arena.WX - m and ay <= arena.WY - m) or
            (arena.X - 24 <= ax <= arena.X + arena.T + 24 and lo + m <= ay <= hi - m))


def walkable(x, y):
    """A standing spot on the ground floor (under the galleries too)."""
    if not inside(x, y):
        return False
    if any(math.hypot(x - px, y - py) < 62 for px, py in arena.PILLARS):
        return False
    if any(abs(x - cx) < hx + 26 and abs(y - cy) < hy + 26
           for cx, cy, hx, hy in arena.COVER):
        return False
    if any(abs(x - px) < 26 and abs(y - py) < 28 for px, py in arena.POSTS):
        return False
    if any(abs(x - cx) < 38 and abs(abs(y) - cy) < 38 for cx, cy in arena.COLUMNS):
        return False
    # the stairs' solid steps
    return not (arena.GX - 20 <= abs(x) <= arena.STAIR_X + 20 and abs(y) >= arena.GY - 20)


def clear(a, b):
    """Keep route edges at player width from the walls, machinery and pillars."""
    steps = max(1, int(math.dist(a[:2], b[:2]) / 12))
    return all(walkable(a[0] + (b[0] - a[0]) * i / steps,
                        a[1] + (b[1] - a[1]) * i / steps)
               for i in range(steps + 1))


def graph():
    """The route points (a standing player's origin, 25 above the floor) and
    their links: two-way along the ground floor, each gallery and its
    stairs, one-way from the railing gaps down to the hall."""
    ground = [(x, y) for x in range(-1408, 1409, 128) for y in range(-640, 641, 128)]
    ground += [(sx * 976, sy * y) for sx in (-1, 1) for sy in (-1, 1) for y in (560, 688)]
    points = [(x, y, floor_height(x, y) + 25) for x, y in ground if walkable(x, y)]
    two, one = set(), set()
    for i, p in enumerate(points):
        for j, q in enumerate(points):
            if i < j and math.dist(p[:2], q[:2]) < 190 and clear(p, q):
                two.add((i, j))
    gz = arena.GZ + 25
    for sy in (-1, 1):
        y = sy * 688
        row = [-736] + list(range(-640, 641, 128)) + [736]
        first = len(points)
        points += [(x, y, gz + (6 if abs(x) <= 96 else 0)) for x in row]
        two.update((first + k, first + k + 1) for k in range(len(row) - 1))
        for e in (-1, 1):
            # down the steps to the corner of the hall
            top = first + (len(row) - 1 if e > 0 else 0)
            chain = [top]
            for k in (2, 4, 6):
                points.append((e * (arena.GX + 24 * k - 12), y, arena.GZ - 16 * k + 25))
                chain.append(len(points) - 1)
            chain.append(points.index((e * 976, y, 25)))
            two.update(zip(chain, chain[1:]))
        for x0, x1 in arena.RAIL_GAPS:
            x = (x0 + x1) // 2
            one.add((first + row.index(x), points.index((x, sy * 512, 25))))
    return points, two, one


def trail(n, two):
    """The order bots walk the points in (they step to the next or previous
    point, and take a link when it shortens the walk): every point at least
    once, each step along a two-way link. Where it runs out of new points
    the walk goes back the shortest way, so some points repeat."""
    near = {i: set() for i in range(n)}
    for a, b in two:
        near[a].add(b)
        near[b].add(a)
    order, seen = [0], {0}
    while len(seen) < n:
        here = order[-1]
        fresh = sorted(near[here] - seen,
                       key=lambda j: (len(near[j] - seen), j))
        if fresh:
            order.append(fresh[0])
            seen.add(fresh[0])
            continue
        back, queue = {here: None}, [here]
        while queue:
            k = queue.pop(0)
            if k not in seen:
                break
            for j in sorted(near[k]):
                if j not in back:
                    back[j] = k
                    queue.append(j)
        else:
            raise SystemExit('bot routes: %d points out of reach' % (n - len(seen)))
        path = []
        while k != here:
            path.append(k)
            k = back[k]
        order += path[::-1]
        seen.add(order[-1])
    return order


def waypoints():
    points, two, one = graph()
    order = trail(len(points), two)
    links = {i: set() for i in range(len(points))}
    for a, b in two:
        links[a].add(b)
        links[b].add(a)
    for a, b in one:
        links[a].add(b)
    copies = {}
    for w, p in enumerate(order):
        copies.setdefault(p, []).append(w)
    lines = []
    for w, p in enumerate(order):
        # each linked point, and this point's other visits, by its visits
        # closest along the trail; the game reads at most 32
        near = [c for q in sorted(links[p] | {p})
                for c in sorted(copies[q], key=lambda c: abs(c - w))[:2] if c != w]
        if len(near) > 32:
            raise SystemExit('bot routes: waypoint %d has %d links' % (w, len(near)))
        pos = points[p]
        nxt = points[order[w + 1]] if w + 1 < len(order) else pos
        lines.append('%d 0 0.000000 (%f %f %f) { %s} %f\n' % (
            w, pos[0], pos[1], pos[2], ''.join('%d ' % c for c in near), math.dist(pos, nxt)))
    return ''.join(lines)


def generate(staging):
    write_text(staging, 'botfiles/bots.txt', bots_txt())
    write_text(staging, 'botfiles/open.jkb', personality())
    write_text(staging, 'botroutes/open_dojo.wnt', waypoints())
