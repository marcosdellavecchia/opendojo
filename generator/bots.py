"""Bots for the open pack: the list of bots (botfiles/bots.txt), their
personality (botfiles/open.jkb) and the open_dojo map's waypoints
(botroutes/open_dojo.wnt), all written here."""

import math

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


PILLARS = [(px, py) for px in (-448, 448) for py in (-256, 256)]


def floor_height(x, y):
    if abs(x) <= 160 and abs(y) <= 96:
        return 24
    if abs(x) <= 224 and abs(y) <= 160:
        return 12
    return 0


def clear(a, b):
    """The segment a-b stays away from the pillars."""
    for px, py in PILLARS:
        dx, dy = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / length2)) if length2 else 0.0
        cx, cy = a[0] + t * dx, a[1] + t * dy
        if math.hypot(px - cx, py - cy) < 56:
            return False
    return True


def waypoints():
    """A grid over the hall's floor, each point linked to its neighbours.
    Points are at a standing player's origin (24 above the floor)."""
    points = []
    for x in range(-640, 641, 128):
        for y in range(-384, 385, 128):
            if all(math.hypot(x - px, y - py) > 72 for px, py in PILLARS):
                points.append((x, y, floor_height(x, y) + 25))
    lines = []
    for i, p in enumerate(points):
        near = [j for j, q in enumerate(points)
                if j != i and math.hypot(p[0] - q[0], p[1] - q[1]) < 190 and clear(p, q)]
        nxt = points[i + 1] if i + 1 < len(points) else p
        dist = math.dist(p, nxt)
        lines.append('%d 0 0.000000 (%f %f %f) { %s} %f\n' % (
            i, p[0], p[1], p[2], ''.join('%d ' % j for j in near), dist))
    return ''.join(lines)


def generate(staging):
    write_text(staging, 'botfiles/bots.txt', bots_txt())
    write_text(staging, 'botfiles/open.jkb', personality())
    write_text(staging, 'botroutes/open_dojo.wnt', waypoints())
