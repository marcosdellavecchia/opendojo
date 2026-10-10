"""The open pack's player model: models/players/_humanoid/_humanoid.gla (the
skeleton and every animation), animation.cfg, models/players/open/model.glm
(the mesh; the game code's default model, renamed by patches/mvsdk.patch) and its
skins, and the saber, models/weapons2/saber/saber_w.glm.

All of it is generated here. The animations are procedural: every animation
name the game code knows gets frames, and the saber moves are built from
MVSDK's own table of saber moves (bg_saber.c), which says in which quadrant
each move starts and ends, so the blade sweeps where the combat code expects.
"""

import math
import os
import re
import struct

import numpy as np

import skeleton as sk
from common import out_path, save_image, value_noise, write_bytes, write_text
from skeleton import FWD, LEFT, RIGHT, UP, Pose, angles, axis_angle, unit

GLA_NAME = 'models/players/_humanoid/_humanoid'
MODEL_DIR = 'models/players/open'

# ---------------------------------------------------------------------------
# animation names and saber moves, from the game code

def anim_names(mvsdk):
    """The animation names in enum order (anims.h, the 1.04 numbering the
    game code uses internally)."""
    text = open(os.path.join(mvsdk, 'code', 'game', 'anims.h'), encoding='latin-1').read()
    first = text[:text.index('MAX_ANIMATIONS,')]
    return re.findall(r'^\s*((?:BOTH|TORSO|LEGS|FACE)_[A-Z0-9_]+)', first, re.M)


def saber_moves(mvsdk):
    """{anim name: (start quadrant, end quadrant)} from saberMoveData."""
    text = open(os.path.join(mvsdk, 'code', 'game', 'bg_saber.c'), encoding='latin-1').read()
    start = text.index('saberMoveData_t\tsaberMoveData')
    table = text[start:text.index('};', start)]
    moves = {}
    for anim, q1, q2 in re.findall(r'\{\s*"[^"]*",\s*(BOTH_\w+),\s*(Q_\w+),\s*(Q_\w+)', table):
        moves.setdefault(anim, (q1, q2))
    return moves


# angle of each quadrant in the frontal plane: 0 right, 90 up (seen by the player)
QUAD = {'Q_R': 0, 'Q_TR': 45, 'Q_T': 90, 'Q_TL': 135, 'Q_L': 180, 'Q_BL': 225, 'Q_B': 270, 'Q_BR': 315}


def quad_dir(theta):
    t = math.radians(theta)
    return math.cos(t) * RIGHT + math.sin(t) * UP


# ---------------------------------------------------------------------------
# poses

def ease(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def nlerp(a, b, t):
    v = lerp(a, b, t)
    if np.linalg.norm(v) < 1e-3:
        v = lerp(a, b, t + 0.05) + FWD * 0.1
    return unit(v)


STANCE_R = np.array([3.0, -6.0, -21.0])
STANCE_L = np.array([-3.5, 5.5, -21.0])
SWING_CENTER = np.array([1.0, -2.5, 19.0])
READY_HAND = np.array([8.0, -5.0, 12.5])
READY_BLADE = unit(FWD * 0.65 + UP * 0.7 + RIGHT * 0.1)
LEVEL = {
    1: dict(psi=75, twist=18, two=False),
    2: dict(psi=100, twist=25, two=False),
    3: dict(psi=120, twist=34, two=True),
}


class SaberState:
    """Where the saber is: right wrist target, blade direction, torso yaw."""

    def __init__(self, hand, blade, twist=0.0, lean=0.0):
        self.hand = np.asarray(hand, float)
        self.blade = unit(blade)
        self.twist = twist
        self.lean = lean

    def mix(self, other, t):
        return SaberState(lerp(self.hand, other.hand, t), nlerp(self.blade, other.blade, t),
                          self.twist * (1 - t) + other.twist * t, self.lean * (1 - t) + other.lean * t)


def swing_state(psi, w, lvl):
    """A point of a slash: psi = angle of the blade from straight ahead,
    w = the frontal direction it leans to."""
    p = math.radians(psi)
    hand = SWING_CENTER + FWD * (7 + 6 * math.cos(p)) + w * (10 * math.sin(p))
    blade = math.cos(p) * FWD + math.sin(p) * w
    twist = LEVEL[lvl]['twist'] * float(np.dot(w, LEFT)) * math.sin(p) / math.sin(math.radians(LEVEL[lvl]['psi']))
    return SaberState(hand, blade, twist)


def ready_state():
    return SaberState(READY_HAND, READY_BLADE)


def quad_state(q, lvl):
    if q == 'Q_R_READY':
        return ready_state()
    return swing_state(LEVEL[lvl]['psi'], quad_dir(QUAD[q]), lvl)


BLOCKS = {
    'Q_T': ((8, -3, 33), LEFT * 1.0 + FWD * 0.15),
    'Q_TR': ((9, -10, 21), UP + FWD * 0.3),
    'Q_TL': ((9, 6, 21), UP + FWD * 0.3),
    'Q_R': ((9, -11, 16), UP + FWD * 0.4),
    'Q_L': ((9, 7, 16), UP + FWD * 0.4),
    'Q_BR': ((9, -10, 12), -UP + FWD * 0.35),
    'Q_BL': ((9, 6, 12), -UP + FWD * 0.35),
    'Q_B': ((10, -2, 10), -UP + LEFT * 0.6 + FWD * 0.3),
}


def block_state(q):
    hand, blade = BLOCKS[q]
    return SaberState(hand, blade, twist=8 * float(np.dot(unit(np.asarray(hand) - SWING_CENTER), LEFT)))


def saber_pose(s, lvl=2, crouch=0.0, feet=None, **kw):
    """A full-body pose holding the saber as in s."""
    pose = Pose(**kw)
    pose.rhand = s.hand + np.array([0, 0, -crouch * 0.8])
    pose.blade = s.blade
    pose.torso = (s.twist, s.lean, 0.0)
    pose.pelvis = np.array([0.0, 0.0, 10.0 - crouch])
    pose.pelvis_rot = (s.twist * 0.25, 0.0, 0.0)
    pose.rfoot, pose.lfoot = feet or (STANCE_R, STANCE_L)
    if LEVEL.get(lvl, {}).get('two'):
        pose.lhand = pose.rhand - s.blade * 3.2 + np.array([0, 0, -1.0])
        pose.lhand_dir = s.blade
    return pose


def clip(states, n, lvl, **kw):
    """n frames along a list of SaberStates (evenly spaced keys, eased)."""
    out = []
    keys = len(states) - 1
    for f in range(n):
        t = f / (n - 1)
        k = min(int(t * keys), keys - 1)
        local = ease(t * keys - k)
        out.append(saber_pose(states[k].mix(states[k + 1], local), lvl, **kw))
    return out


def attack_clip(q1, q2, lvl, n=12):
    w = quad_dir(QUAD[q1])
    psi0 = LEVEL[lvl]['psi']
    out = []
    for f in range(n):
        t = f / (n - 1)
        # slow wind-up, fast through the front
        u = t * t * (3 - 2 * t)
        psi = psi0 - 2 * psi0 * u
        s = swing_state(psi, w, lvl)
        s.lean = 10 * math.sin(math.pi * u) * (1.5 if lvl == 3 else 1)
        out.append(saber_pose(s, lvl))
    return out


def transition_clip(q1, q2, lvl, n=6):
    a, b = QUAD[q1], QUAD[q2]
    d = (b - a + 180) % 360 - 180
    psi0 = LEVEL[lvl]['psi']
    out = []
    for f in range(n):
        t = ease(f / (n - 1))
        psi = psi0 - 0.35 * psi0 * math.sin(math.pi * t)
        out.append(saber_pose(swing_state(psi, quad_dir(a + d * t), lvl), lvl))
    return out


def bounce_clip(q, lvl, n=8, back=30, settle=0.5):
    w = quad_dir(QUAD[q])
    psi0 = LEVEL[lvl]['psi']
    s0 = swing_state(psi0 * 0.4, w, lvl)
    s1 = swing_state(min(psi0 + back, 170), w, lvl)
    s2 = s0.mix(s1, settle)
    return clip([s0, s1, s2], n, lvl)


# ---------------------------------------------------------------------------
# other motions

def idle_pose(saber=True, breathe=0.0, lvl=2):
    if saber:
        s = ready_state()
        s.hand = s.hand + np.array([0, 0, breathe])
        if lvl == 1:
            s = SaberState(s.hand + np.array([1, 1, 2]), unit(FWD * 0.5 + UP * 0.9 + RIGHT * 0.2))
        elif lvl == 3:
            s = SaberState(np.array([6.0, -4.0, 22.0]), unit(UP * 0.9 + FWD * 0.2 - FWD * 0.3 + RIGHT * 0.1))
        return saber_pose(s, lvl if lvl == 3 else 2)
    pose = Pose()
    pose.pelvis = np.array([0.0, 0.0, 10.5 + breathe * 0.3])
    pose.rfoot = np.array([0.5, -5.5, -21.0])
    pose.lfoot = np.array([-0.5, 5.5, -21.0])
    return pose


def idle_clip(saber=True, n=20, lvl=2):
    return [idle_pose(saber, 0.4 * math.sin(2 * math.pi * f / n), lvl) for f in range(n)]


def gait_clip(n, stride, lift, direction=FWD, saber=True, bob=0.8, crouch=0.0, lean=0.0):
    """A looping walk or run: feet move along direction, n frames per cycle."""
    out = []
    side = np.cross(UP, direction)
    for f in range(n):
        ph = 2 * math.pi * f / n
        if saber:
            pose = saber_pose(ready_state(), 2, crouch=crouch)
        else:
            pose = idle_pose(False)
            pose.pelvis = pose.pelvis - np.array([0, 0, crouch])
        for foot, phase, base in (('rfoot', 0, np.array([0.5, -5.5, -21.0])), ('lfoot', math.pi, np.array([-0.5, 5.5, -21.0]))):
            c = math.cos(ph + phase)
            s = math.sin(ph + phase)
            pos = base + direction * (stride / 2 * c) + UP * (lift * max(0.0, -s))
            setattr(pose, foot, pos)
        pose.pelvis = pose.pelvis + UP * (bob * abs(math.cos(ph))) - UP * bob
        pose.torso = (pose.torso[0], pose.torso[1] + lean, pose.torso[2])
        if not saber:
            swing = 8 * math.cos(ph)
            pose.rhand = np.array([1.0 + swing * float(np.dot(direction, FWD)), -9.5, 10.5])
            pose.lhand = np.array([1.0 - swing * float(np.dot(direction, FWD)), 9.5, 10.5])
        out.append(pose)
    return out


def blend_clip(a, b, n):
    """Moves between two poses: interpolates the pose fields."""
    out = []
    for f in range(n):
        t = ease(f / max(n - 1, 1))
        p = Pose()
        for k in ('pelvis', 'rfoot', 'lfoot'):
            setattr(p, k, lerp(getattr(a, k), getattr(b, k), t))
        for k in ('pelvis_rot', 'torso', 'head'):
            setattr(p, k, tuple(lerp(getattr(a, k), getattr(b, k), t)))
        p.rhand = None if a.rhand is None and b.rhand is None else lerp(
            a.rhand if a.rhand is not None else default_hand('r'), b.rhand if b.rhand is not None else default_hand('r'), t)
        p.lhand = None if a.lhand is None and b.lhand is None else lerp(
            a.lhand if a.lhand is not None else default_hand('l'), b.lhand if b.lhand is not None else default_hand('l'), t)
        p.blade = nlerp(a.blade, b.blade, t)
        p.lhand_dir = nlerp(a.lhand_dir, b.lhand_dir, t)
        if a.body is not None or b.body is not None:
            ra = a.body[0] if a.body is not None else np.eye(3)
            rb = b.body[0] if b.body is not None else np.eye(3)
            pivot = (a.body or b.body)[1]
            p.body = (rot_lerp(ra, rb, t), pivot)
        out.append(p)
    return out


def default_hand(side):
    return np.array([3.0, -10.0 if side == 'r' else 10.0, 10.0])


def rot_lerp(ra, rb, t):
    r = ra.T @ rb
    angle = math.degrees(math.acos(np.clip((np.trace(r) - 1) / 2, -1, 1)))
    if angle < 1e-3:
        return ra
    axis = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]])
    if np.linalg.norm(axis) < 1e-6:
        axis = np.array([0, 1.0, 0])
    return ra @ axis_angle(axis, angle * t)


def crouch_pose(saber=True):
    if saber:
        p = saber_pose(ready_state(), 2, crouch=13)
    else:
        p = idle_pose(False)
        p.pelvis = np.array([0.0, 0.0, -3.0])
    p.torso = (p.torso[0], 22.0, 0.0)
    p.pelvis_rot = (p.pelvis_rot[0], 10.0, 0.0)
    p.rfoot = np.array([3.0, -6.0, -21.0])
    p.lfoot = np.array([-4.0, 6.0, -21.0])
    return p


def fall_clip(n, direction=-1, saber=True, lie_hold=0):
    """Falling over backwards (direction -1) or forwards (+1)."""
    start = idle_pose(saber)
    out = []
    for f in range(n + lie_hold):
        t = ease(min(f / (n - 1), 1.0))
        p = idle_pose(saber)
        p.pelvis = lerp(start.pelvis, start.pelvis + np.array([0, 0, -4]), t)
        p.torso = (0, -20 * direction * math.sin(math.pi * t), 0)
        p.head = (0, -15 * direction * t, 0)
        pitch = 90 * t * direction
        p.body = (axis_angle(LEFT, pitch), np.array([0, 0, -24.0]))
        if saber:
            p.rhand = lerp(p.rhand, np.array([2.0, -14.0, 12.0]), t)
        out.append(p)
    return out


def flip_clip(n, axis, turns=1.0, height=10.0, tuck=True, saber=True):
    out = []
    for f in range(n):
        t = f / (n - 1)
        p = saber_pose(ready_state(), 2) if saber else idle_pose(False)
        k = math.sin(math.pi * t)
        if tuck:
            p.pelvis = p.pelvis + UP * (height * k)
            p.rfoot = p.rfoot + UP * (14 * k + height * k) + FWD * (4 * k)
            p.lfoot = p.lfoot + UP * (14 * k + height * k) + FWD * (4 * k)
            p.torso = (0, 30 * k, 0)
        p.body = (axis_angle(axis, 360 * turns * ease(t)), np.array([0, 0, 4.0 + height * k]))
        out.append(p)
    return out


def roll_clip(n, axis, saber=True):
    out = []
    for f in range(n):
        t = f / (n - 1)
        k = math.sin(math.pi * t)
        p = crouch_pose(saber)
        p.pelvis = p.pelvis - UP * (6 * k)
        p.rfoot = p.rfoot + UP * (10 * k)
        p.lfoot = p.lfoot + UP * (10 * k)
        p.torso = (0, 22 + 30 * k, 0)
        p.body = (axis_angle(axis, 360 * ease(t)), np.array([0, 0, -12.0]))
        out.append(p)
    return out


def jump_clips():
    stand = saber_pose(ready_state(), 2)
    crouch = saber_pose(ready_state(), 2, crouch=6)
    air = saber_pose(ready_state(), 2)
    air.rfoot = np.array([5.0, -5.5, -14.0])
    air.lfoot = np.array([-2.0, 5.5, -17.0])
    air.pelvis = np.array([0.0, 0.0, 9.0])
    return {
        'jump': blend_clip(crouch, air, 6),
        'inair': [air, air],
        'land': blend_clip(crouch, stand, 6),
    }


def force_clip(n, hand_from, hand_to, lhand=True, saber=True, hold=0):
    a = saber_pose(ready_state(), 2) if saber else idle_pose(False)
    b = saber_pose(ready_state(), 2) if saber else idle_pose(False)
    if lhand:
        a.lhand, b.lhand = np.asarray(hand_from, float), np.asarray(hand_to, float)
        a.lhand_dir = b.lhand_dir = UP
    else:
        a.rhand, b.rhand = np.asarray(hand_from, float), np.asarray(hand_to, float)
    frames = blend_clip(a, b, n)
    return frames + [frames[-1]] * hold


def lock_clip(n, lvl=2, circle=False):
    """Saber lock: blades crossed in front, pushing from behind to in front."""
    out = []
    for f in range(n):
        t = f / (n - 1)
        hand = np.array([9.0 + 5 * t, -3.0, 21.0 + (3 * math.sin(2 * math.pi * t) if circle else 0)])
        blade = unit(FWD * 0.6 + UP * 0.8 + LEFT * 0.25)
        s = SaberState(hand, blade, twist=-5 + 10 * t, lean=5 * t)
        out.append(saber_pose(s, 3))
    return out


def special_clips():
    c = {}
    # lunge: crouched, slashing up from bottom to top
    frames = []
    for f in range(14):
        t = f / 13
        u = ease(t)
        s = swing_state(110 - 220 * u, quad_dir(270), 2)
        frames.append(saber_pose(s, 2, crouch=10 * (1 - u)))
    c['lunge'] = frames
    # jump overhead slash
    frames = []
    for f in range(16):
        t = f / 15
        k = math.sin(math.pi * t)
        s = swing_state(130 - 260 * ease(t), quad_dir(90), 3)
        p = saber_pose(s, 3)
        p.rfoot = p.rfoot + UP * (12 * k)
        p.lfoot = p.lfoot + UP * (12 * k)
        frames.append(p)
    c['leap'] = frames
    # flips with a slash or a stab downwards
    c['flipslash'] = flip_clip(16, LEFT, 1.0, 12)
    for i, p in enumerate(c['flipslash']):
        s = swing_state(120 - 240 * i / 15, quad_dir(180), 2)
        p.rhand, p.blade = s.hand, s.blade
    c['flipstab'] = flip_clip(14, LEFT, 1.0, 12)
    for i, p in enumerate(c['flipstab']):
        t = i / 13
        p.rhand = np.array([6.0, -3.0, 20 - 12 * t])
        p.blade = nlerp(UP, -UP + FWD * 0.2, t)
    # behind the back
    frames = []
    for f in range(12):
        t = ease(f / 11)
        s = SaberState(lerp(READY_HAND, np.array([4.0, -9.0, 14.0]), t), nlerp(READY_BLADE, -FWD + RIGHT * 0.2, t), twist=-20 * t)
        frames.append(saber_pose(s, 2))
    c['backstab'] = frames
    frames = []
    for f in range(14):
        t = ease(f / 13)
        s = swing_state(80 - 160 * t, quad_dir(0), 2)
        p = saber_pose(s, 2)
        p.pelvis_rot = (-200 * t, 0, 0)
        p.torso = (-80 * t, 5, 0)
        frames.append(p)
    c['backspin'] = frames
    frames = []
    for f in range(12):
        t = ease(f / 11)
        s = SaberState(lerp(READY_HAND, np.array([2.0, -8.0, 4.0]), t), nlerp(READY_BLADE, -FWD - UP * 0.2, t), twist=-15 * t)
        frames.append(saber_pose(s, 2, crouch=12))
    c['crouchback'] = frames
    return c


# ---------------------------------------------------------------------------
# which animation gets what

class Library:
    def __init__(self):
        self.clips = {}	# key -> list of poses

    def get(self, key, make):
        if key not in self.clips:
            self.clips[key] = make()
        return key


def build_anims(names, moves):
    """Returns (library, {name: (clip key, fps, loopFrames)})."""
    lib = Library()
    table = {}
    specials = special_clips()
    jumps = jump_clips()

    saber_re = re.compile(r'^BOTH_([ATSRBDVHKP])([1-5])_(.+)$')
    geo_level = {1: 1, 2: 2, 3: 3, 4: 3, 5: 2}
    speed = {  # fps per saber level
        'A': {1: 28, 2: 20, 3: 14}, 'T': {1: 30, 2: 25, 3: 20}, 'S': {1: 30, 2: 24, 3: 18},
        'R': {1: 30, 2: 24, 3: 18}, 'B': {1: 26, 2: 24, 3: 20}, 'D': {1: 26, 2: 24, 3: 20},
    }

    def set_(name, key, fps, loop=-1):
        table[name] = (key, fps, loop)

    for name in names:
        m = saber_re.match(name)
        if m:
            kind, level = m.group(1), int(m.group(2))
            base = 'BOTH_%s1_%s' % (kind, m.group(3))
            if kind in 'ATSRBD':
                quads = moves.get(base)
                if quads is None and kind == 'D':
                    quads = moves.get('BOTH_B1_%s' % m.group(3))
                if quads is None:
                    continue
                q1, q2 = quads
                g = geo_level[level]
                fps = speed[kind][g]
                if kind == 'A':
                    key = lib.get(('A', q1, q2, g), lambda: attack_clip(q1, q2, g))
                elif kind == 'T':
                    key = lib.get(('T', q1, q2, g), lambda: transition_clip(q1, q2, g))
                elif kind == 'S':
                    key = lib.get(('S', q2, g), lambda: clip([ready_state(), quad_state(q2, g)], 6, g))
                elif kind == 'R':
                    key = lib.get(('R', q1, g), lambda: clip([quad_state(q1, g), ready_state()], 8, g))
                else:
                    key = lib.get((kind, q1, g), lambda: bounce_clip(q1, g, back=35 if kind == 'B' else 20))
                set_(name, key, fps)
                continue
            quads = moves.get(name)
            if quads is None:
                continue
            q1, q2 = quads
            if kind == 'P':
                key = lib.get(('P', q2), lambda: clip([ready_state(), block_state(q2), block_state(q2)], 8, 2))
                set_(name, key, 22)
            elif kind == 'K':
                key = lib.get(('K', q2), lambda: clip([ready_state(), block_state(q2), quad_state(q2, 2)], 8, 2))
                set_(name, key, 22)
            elif kind == 'V':
                key = lib.get(('V', q1), lambda: bounce_clip(q1, 2, n=10, back=60, settle=0.3))
                set_(name, key, 20)
            elif kind == 'H':
                opp = {'Q_T': 'Q_B', 'Q_TR': 'Q_BL', 'Q_TL': 'Q_BR', 'Q_BL': 'Q_TR', 'Q_B': 'Q_T', 'Q_BR': 'Q_TL'}[q1]
                key = lib.get(('H', q1), lambda: clip([block_state(q1), quad_state(opp, 2), ready_state()], 12, 2))
                set_(name, key, 18)
            continue

    def add(name, key, make, fps, loop=-1):
        if name in names and name not in table:
            set_(name, lib.get(key, make), fps, loop)

    # saber specials and locks
    add('BOTH_LUNGE2_B__T_', 'lunge', lambda: specials['lunge'], 18)
    add('BOTH_FORCELEAP2_T__B_', 'leap', lambda: specials['leap'], 14)
    add('BOTH_JUMPFLIPSLASHDOWN1', 'flipslash', lambda: specials['flipslash'], 12)
    add('BOTH_JUMPFLIPSTABDOWN', 'flipstab', lambda: specials['flipstab'], 12)
    add('BOTH_A2_STABBACK1', 'backstab', lambda: specials['backstab'], 18)
    add('BOTH_ATTACK_BACK', 'backspin', lambda: specials['backspin'], 16)
    add('BOTH_CROUCHATTACKBACK1', 'crouchback', lambda: specials['crouchback'], 18)
    for n_ in ('BOTH_BF2LOCK', 'BOTH_BF1LOCK'):
        add(n_, 'lock', lambda: lock_clip(20), 10)
    for n_ in ('BOTH_CWCIRCLELOCK', 'BOTH_CCWCIRCLELOCK'):
        add(n_, 'lockcircle', lambda: lock_clip(20, circle=True), 10)
    for n_ in ('BOTH_BF2RETURN', 'BOTH_BF1RETURN', 'BOTH_CWCIRCLE_R2__R_S1', 'BOTH_CCWCIRCLE_R2__L_S1'):
        add(n_, 'lockreturn', lambda: clip([SaberState((12, -3, 21), FWD * 0.6 + UP * 0.8), ready_state()], 8, 2), 20)
    for n_ in ('BOTH_BF2BREAK', 'BOTH_BF1BREAK', 'BOTH_CWCIRCLEBREAK', 'BOTH_CCWCIRCLEBREAK',
               'BOTH_CWCIRCLE_A2__L__R', 'BOTH_CCWCIRCLE_A2__R__L'):
        add(n_, 'lockbreak', lambda: attack_clip('Q_TL', 'Q_BR', 2), 20)
    # not in the move table, but cgame wants every animation of the saber block
    add('BOTH_K1_S1_B_', ('K', 'Q_B'), lambda: clip([ready_state(), block_state('Q_B'), quad_state('Q_B', 2)], 8, 2), 22)
    add('BOTH_SABERFAST_STANCE', 'stance1', lambda: idle_clip(True, 20, 1), 10, 0)
    add('BOTH_SABERSLOW_STANCE', 'stance3', lambda: idle_clip(True, 20, 3), 10, 0)
    add('BOTH_ENGAGETAUNT', 'taunt', lambda: transition_clip('Q_R', 'Q_T', 2, 8) + transition_clip('Q_T', 'Q_R', 2, 8), 10)

    # standing, moving
    add('BOTH_STAND2', 'idle2', lambda: idle_clip(True), 10, 0)
    add('BOTH_STAND1', 'idle1', lambda: idle_clip(False), 10, 0)
    add('BOTH_STAND1TO2', 'draw', lambda: blend_clip(idle_pose(False), idle_pose(True), 8), 20)
    add('BOTH_STAND2TO1', 'putaway', lambda: blend_clip(idle_pose(True), idle_pose(False), 8), 20)
    add('BOTH_WALK2', 'walk2', lambda: gait_clip(24, 16, 3, saber=True, bob=0.5), 24, 0)
    add('BOTH_WALK1', 'walk1', lambda: gait_clip(24, 16, 3, saber=False, bob=0.5), 24, 0)
    add('BOTH_RUN2', 'run2', lambda: gait_clip(16, 30, 6, saber=True, bob=1.5, lean=8), 24, 0)
    add('BOTH_RUN1', 'run1', lambda: gait_clip(16, 30, 6, saber=False, bob=1.5, lean=8), 24, 0)
    add('BOTH_WALKBACK2', 'walkback2', lambda: gait_clip(24, 14, 3, -FWD, True, 0.5), 24, 0)
    add('BOTH_WALKBACK1', 'walkback1', lambda: gait_clip(24, 14, 3, -FWD, False, 0.5), 24, 0)
    add('BOTH_RUNBACK2', 'runback2', lambda: gait_clip(16, 24, 5, -FWD, True, 1.2), 24, 0)
    add('BOTH_RUNBACK1', 'runback1', lambda: gait_clip(16, 24, 5, -FWD, False, 1.2), 24, 0)
    add('BOTH_STRAFE_LEFT1', 'strafel', lambda: gait_clip(20, 14, 3, LEFT, True, 0.6), 24, 0)
    add('BOTH_STRAFE_RIGHT1', 'strafer', lambda: gait_clip(20, 14, 3, RIGHT, True, 0.6), 24, 0)
    add('BOTH_RUNSTRAFE_LEFT1', 'runstrafel', lambda: gait_clip(16, 24, 5, LEFT, True, 1.2), 24, 0)
    add('BOTH_RUNSTRAFE_RIGHT1', 'runstrafer', lambda: gait_clip(16, 24, 5, RIGHT, True, 1.2), 24, 0)
    add('BOTH_CROUCH1', 'crouch', lambda: blend_clip(idle_pose(True), crouch_pose(True), 6), 24)
    add('BOTH_UNCROUCH1', 'uncrouch', lambda: blend_clip(crouch_pose(True), idle_pose(True), 6), 24)
    add('BOTH_CROUCH1IDLE', 'crouchidle', lambda: [crouch_pose(True)] * 2, 10, 0)
    add('BOTH_CROUCH1WALK', 'crouchwalk', lambda: crouch_walk(FWD), 20, 0)
    add('BOTH_CROUCH1WALKBACK', 'crouchwalkback', lambda: crouch_walk(-FWD), 20, 0)
    add('BOTH_JUMP1', 'jump', lambda: jumps['jump'], 20)
    add('BOTH_INAIR1', 'inair', lambda: jumps['inair'], 10, 0)
    add('BOTH_LAND1', 'land', lambda: jumps['land'], 20)
    add('BOTH_LAND2', 'land', lambda: jumps['land'], 20)
    for d in ('BACK', 'LEFT', 'RIGHT'):
        add('BOTH_JUMP%s1' % d, 'jump', None, 20)
        add('BOTH_INAIR%s1' % d, 'inair', None, 10, 0)
        add('BOTH_LAND%s1' % d, 'land', None, 20)
        add('BOTH_FORCEJUMP%s1' % d, 'jump', None, 20)
        add('BOTH_FORCEINAIR%s1' % d, 'inair', None, 10, 0)
        add('BOTH_FORCELAND%s1' % d, 'land', None, 20)
    add('BOTH_FORCEJUMP1', 'jump', None, 20)
    add('BOTH_FORCEINAIR1', 'inair', None, 10, 0)
    add('BOTH_FORCELAND1', 'land', None, 20)

    # acrobatics
    add('BOTH_FLIP_F', 'flipf', lambda: flip_clip(16, LEFT, 1, 12), 20)
    add('BOTH_FLIP_B', 'flipb', lambda: flip_clip(16, LEFT, -1, 12), 20)
    add('BOTH_FLIP_L', 'flipl', lambda: flip_clip(16, FWD, -1, 10), 20)
    add('BOTH_FLIP_R', 'flipr', lambda: flip_clip(16, FWD, 1, 10), 20)
    add('BOTH_ROLL_F', 'rollf', lambda: roll_clip(14, LEFT), 22)
    add('BOTH_ROLL_B', 'rollb', lambda: roll_clip(14, -LEFT), 22)
    add('BOTH_ROLL_L', 'rolll', lambda: roll_clip(14, -FWD), 22)
    add('BOTH_ROLL_R', 'rollr', lambda: roll_clip(14, FWD), 22)
    for n_, k in (('BOTH_ROLL_FR', 'rollf'), ('BOTH_ROLL_FL', 'rollf'), ('BOTH_ROLL_BR', 'rollb'), ('BOTH_ROLL_BL', 'rollb')):
        add(n_, k, None, 22)
    for n_ in ('BOTH_ARIAL_LEFT', 'BOTH_CARTWHEEL_LEFT', 'BOTH_BUTTERFLY_LEFT', 'BOTH_WALL_FLIP_LEFT', 'BOTH_WALL_RUN_LEFT_FLIP'):
        add(n_, 'flipl', None, 18)
    for n_ in ('BOTH_ARIAL_RIGHT', 'BOTH_CARTWHEEL_RIGHT', 'BOTH_BUTTERFLY_RIGHT', 'BOTH_WALL_FLIP_RIGHT', 'BOTH_WALL_RUN_RIGHT_FLIP',
               'BOTH_ARIAL_F1', 'BOTH_BUTTERFLY_FR1', 'BOTH_BUTTERFLY_FL1', 'BOTH_FJSS_TR_BL', 'BOTH_FJSS_TL_BR'):
        add(n_, 'flipr', None, 18)
    for n_ in ('BOTH_FLIP_BACK1', 'BOTH_FLIP_BACK2', 'BOTH_FLIP_BACK3', 'BOTH_WALL_FLIP_BACK1', 'BOTH_WALL_FLIP_BACK2', 'BOTH_FLIP_LEFT'):
        add(n_, 'flipb', None, 18)
    add('BOTH_WALL_FLIP_FWD', 'flipf', None, 18)
    for n_ in ('BOTH_WALL_RUN_RIGHT', 'BOTH_WALL_RUN_LEFT'):
        add(n_, 'run2', None, 24, 0)
    for n_ in ('BOTH_WALL_RUN_RIGHT_STOP', 'BOTH_WALL_RUN_LEFT_STOP'):
        add(n_, 'land', None, 20)
    for d, v in (('F', FWD), ('B', -FWD), ('L', LEFT), ('R', RIGHT)):
        add('BOTH_HOP_' + d, 'hop' + d, lambda v=v: hop_clip(v), 20)
    for d, v in (('L', LEFT), ('R', RIGHT), ('FL', FWD + LEFT), ('FR', FWD + RIGHT), ('BL', LEFT - FWD), ('BR', RIGHT - FWD)):
        add('BOTH_DODGE_' + d, 'dodge' + d, lambda v=v: dodge_clip(unit(v)), 20)

    # getting hurt, falling, dying
    add('BOTH_PAIN1', 'pain', lambda: pain_clip(), 20)
    for i in range(2, 21):
        add('BOTH_PAIN%d' % i, 'pain', None, 20)
    add('BOTH_DEATH1', 'deathback', lambda: fall_clip(14, -1), 16)
    add('BOTH_DEATH2', 'deathfwd', lambda: fall_clip(14, 1), 16)
    for i in range(3, 26):
        add('BOTH_DEATH%d' % i, 'deathback' if i % 2 else 'deathfwd', None, 16)
    add('BOTH_DEAD1', 'deadback', lambda: fall_clip(14, -1)[-1:] * 2, 10, 0)
    add('BOTH_DEAD2', 'deadfwd', lambda: fall_clip(14, 1)[-1:] * 2, 10, 0)
    for i in range(3, 26):
        add('BOTH_DEAD%d' % i, 'deadback' if i % 2 else 'deadfwd', None, 10, 0)
    for n_ in names:
        if n_.startswith(('BOTH_DEATH', 'BOTH_DISMEMBER', 'BOTH_FALLDEATH', 'BOTH_STUMBLEDEATH', 'BOTH_LYINGDEATH')):
            add(n_, 'deathback', None, 16)
        elif n_.startswith(('BOTH_DEAD', 'BOTH_LYINGDEAD', 'BOTH_STUMBLEDEAD', 'BOTH_FALLDEAD')):
            add(n_, 'deadback', None, 10, 0)
    for i in range(1, 6):
        add('BOTH_KNOCKDOWN%d' % i, 'knockdown', lambda: fall_clip(10, -1, lie_hold=10), 16)
        add('BOTH_GETUP%d' % i, 'getup', lambda: list(reversed(fall_clip(16, -1))), 16)
    for n_ in names:
        if 'GETUP' in n_ or n_ in ('BOTH_GET_UP1', 'BOTH_GET_UP2'):
            add(n_, 'getup', None, 16)

    # the Force
    add('BOTH_FORCEPUSH', 'push', lambda: force_clip(8, (6, 6, 18), (16, 4, 24), hold=4), 20)
    add('BOTH_FORCEPULL', 'pull', lambda: force_clip(8, (16, 4, 24), (6, 6, 20), hold=4), 20)
    add('BOTH_MINDTRICK1', 'mindtrick', lambda: force_clip(8, (6, 6, 20), (10, 3, 32), hold=4), 20)
    add('BOTH_MINDTRICK2', 'mindtrick', None, 20)
    add('BOTH_FORCEGRIP1', 'grip', lambda: force_clip(8, (6, 6, 18), (15, 5, 28), hold=8), 20)
    add('BOTH_FORCEGRIP_HOLD', 'griphold', lambda: force_clip(2, (15, 5, 28), (15, 5, 28)), 10, 0)
    add('BOTH_FORCEGRIP3', 'grip', None, 20)
    add('BOTH_FORCEGRIP3THROW', 'push', None, 20)
    add('BOTH_FORCEGRIP_RELEASE', 'pull', None, 20)
    add('BOTH_FORCELIGHTNING', 'lightning', lambda: force_clip(6, (6, 6, 18), (16, 5, 22), hold=6), 20)
    add('BOTH_FORCELIGHTNING_START', 'lightning', None, 20)
    add('BOTH_FORCELIGHTNING_HOLD', 'lightninghold', lambda: force_clip(2, (16, 5, 22), (16, 6, 22)), 10, 0)
    add('BOTH_FORCELIGHTNING_RELEASE', 'pull', None, 20)
    add('BOTH_FORCEHEAL_START', 'heal', lambda: force_clip(10, (6, 6, 18), (4, 3, 24), hold=6), 16)
    add('BOTH_FORCEHEAL_STOP', 'pull', None, 20)
    add('BOTH_FORCEHEAL_QUICK', 'heal', None, 24)
    add('BOTH_SABERPULL', 'pull', None, 20)
    add('BOTH_RESISTPUSH', 'push', None, 20)
    add('BOTH_SABERTHROW1START', 'throw', lambda: clip([ready_state(), SaberState((4, -10, 30), UP - FWD * 0.5), SaberState((16, -4, 24), FWD)], 10, 2), 20)
    add('BOTH_SABERTHROW1STOP', 'catch', lambda: clip([SaberState((16, -4, 24), FWD), ready_state()], 8, 2), 20)
    add('BOTH_SABERTHROW2START', 'throw', None, 20)
    add('BOTH_SABERTHROW2STOP', 'catch', None, 20)

    # everything else: the ready pose, or without the saber the idle
    for n_ in names:
        if n_ in table or n_.startswith('FACE_'):
            continue
        if n_.startswith(('TORSO_', 'LEGS_')):
            add(n_, 'idle2', None, 10, 0)
        elif n_ in NEEDED_EXTRA:
            add(n_, 'idle2', None, 10, 0)
    return lib, table


NEEDED_EXTRA = set()	# filled by generate(): every animation the game code names


def referenced_anims(mvsdk):
    found = set()
    for d in ('game', 'cgame'):
        folder = os.path.join(mvsdk, 'code', d)
        for name in os.listdir(folder):
            if name.endswith('.c') and name not in ('animMappingTable.c', 'bg_multiversion.c'):
                text = open(os.path.join(folder, name), encoding='latin-1').read()
                found.update(re.findall(r'\b((?:BOTH|TORSO|LEGS)_[A-Z0-9_]+)\b', text))
    return found


def crouch_walk(direction):
    base = gait_clip(20, 12, 2, direction, True, 0.3, crouch=13)
    for p in base:
        p.torso = (p.torso[0], 22.0, 0.0)
        p.pelvis_rot = (p.pelvis_rot[0], 10.0, 0.0)
    return base


def hop_clip(direction):
    out = []
    for f in range(10):
        t = f / 9
        k = math.sin(math.pi * t)
        p = saber_pose(ready_state(), 2)
        p.rfoot = p.rfoot + UP * (6 * k) + direction * (4 * (t - 0.5))
        p.lfoot = p.lfoot + UP * (6 * k) + direction * (4 * (t - 0.5))
        out.append(p)
    return out


def dodge_clip(direction):
    a = saber_pose(ready_state(), 2)
    b = saber_pose(ready_state(), 2, crouch=4)
    lean = float(np.dot(direction, LEFT))
    b.torso = (0, -10 * float(np.dot(direction, FWD)), -25 * lean)
    b.pelvis = b.pelvis + direction * 4
    return blend_clip(a, b, 5) + blend_clip(b, a, 5)


def pain_clip():
    a = saber_pose(ready_state(), 2)
    b = saber_pose(ready_state(), 2, crouch=2)
    b.torso = (8, -18, 0)
    b.head = (0, -15, 0)
    return blend_clip(a, b, 4) + blend_clip(b, a, 6)


# ---------------------------------------------------------------------------
# the GLA

def comp_quat_bone(m):
    """14 bytes: a quaternion (w, x, y, z) and a translation, as JK2MV's
    MC_UnCompressQuat reads them."""
    r = m[:, :3]
    t = m[:, 3]
    tr = r[0, 0] + r[1, 1] + r[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w, x, y, z = 0.25 * s, (r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = math.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
        w, x, y, z = (r[2, 1] - r[1, 2]) / s, 0.25 * s, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s
    elif r[1, 1] > r[2, 2]:
        s = math.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
        w, x, y, z = (r[0, 2] - r[2, 0]) / s, (r[0, 1] + r[1, 0]) / s, 0.25 * s, (r[1, 2] + r[2, 1]) / s
    else:
        s = math.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
        w, x, y, z = (r[1, 0] - r[0, 1]) / s, (r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, 0.25 * s
    q = np.array([w, x, y, z])
    q /= np.linalg.norm(q)
    qs = [int(round((v + 2.0) * 16383)) for v in q]
    ts = [int(round((v + 512.0) * 64)) for v in t]
    if not all(0 <= v <= 65535 for v in ts):
        raise ValueError('bone translation out of range: %s' % t)
    return struct.pack('<7H', *qs, *ts)


def mat34(m):
    return struct.pack('<12f', *m.reshape(-1))


def write_gla(frames):
    """frames: list of relative bone matrices (n, 3, 4). Returns bytes."""
    n = len(sk.BONES)
    header_size = 100
    skel = bytearray()
    offsets = []
    children = {i: [j for j in range(n) if sk.PARENT[j] == i] for i in range(n)}
    for i, name in enumerate(sk.NAMES):
        offsets.append(4 * n + len(skel))
        base = np.zeros((3, 4))
        rot = sk.FILE_ROT @ sk.BASE_ROT[i]
        pos = sk.FILE_ROT @ sk.BASE_POS[i]
        base[:, :3] = rot
        base[:, 3] = pos
        inv = np.zeros((3, 4))
        inv[:, :3] = rot.T
        inv[:, 3] = -rot.T @ pos
        skel += struct.pack('<64sIi', name.encode(), 0, sk.PARENT[i])
        skel += mat34(base) + mat34(inv)
        skel += struct.pack('<i', len(children[i])) + struct.pack('<%di' % len(children[i]), *children[i])
    ofs_skel = header_size
    skel_block = struct.pack('<%di' % n, *offsets) + bytes(skel)

    pool = {}
    pool_list = []
    index = bytearray()
    for rel in frames:
        for i in range(n):
            c = comp_quat_bone(rel[i])
            k = pool.get(c)
            if k is None:
                k = pool[c] = len(pool_list)
                pool_list.append(c)
            index += struct.pack('<I', k)[:3]
    while len(index) % 4:
        index += b'\0'
    ofs_frames = ofs_skel + len(skel_block)
    ofs_pool = ofs_frames + len(index)
    pool_bytes = b''.join(pool_list)
    end = ofs_pool + len(pool_bytes)
    header = struct.pack('<4si64sfiiiiii', b'2LGA', 6, GLA_NAME.encode(), 1.0, len(frames), ofs_frames,
                         n, ofs_pool, ofs_skel, end)
    assert len(header) == header_size
    return header + skel_block + bytes(index) + pool_bytes


# ---------------------------------------------------------------------------
# meshes

class Mesh:
    def __init__(self):
        self.surfaces = []	# dicts: name, shader, parent, verts [(pos, normal, uv, bone)], tris, flags

    def surface(self, name, parent=-1, shader='[nomaterial]', flags=0):
        self.surfaces.append(dict(name=name, shader=shader, parent=parent, verts=[], tris=[], flags=flags))
        return len(self.surfaces) - 1

    def box(self, s, bone, lo, hi, uv, top_scale=(1.0, 1.0)):
        """A box (optionally tapered towards +z) on one bone; uv is the
        (u0, v0, u1, v1) region of the texture for every face."""
        surf = self.surfaces[s]
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        c = (lo + hi) / 2
        half = (hi - lo) / 2
        corners = []
        for z in (-1, 1):
            sx, sy = (1, 1) if z < 0 else top_scale
            for y in (-1, 1):
                for x in (-1, 1):
                    corners.append(c + half * np.array([x * sx, y * sy, z]))
        faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        u0, v0, u1, v1 = uv
        for f in faces:
            pts = [corners[i] for i in f]
            normal = unit(np.cross(pts[1] - pts[0], pts[2] - pts[0]))
            base = len(surf['verts'])
            for k, p in enumerate(pts):
                tu = (u0, u1, u1, u0)[k]
                tv = (v1, v1, v0, v0)[k]
                surf['verts'].append((p, normal, (tu, tv), bone))
            surf['tris'] += [(base, base + 2, base + 1), (base, base + 3, base + 2)]

    def tag(self, name, parent, bone, origin, x_axis=FWD, y_axis=LEFT, mirrored=False):
        """A bolt: one triangle whose frame (as JK2MV computes it) has the
        given axes at origin. mirrored: the frame's X axis is -x_axis (the
        saber's *flash, whose blade runs along -X of its frame)."""
        s = self.surface(name, parent, '[nomaterial]', 1)	# G2SURFACEFLAG_ISBOLT
        o = np.asarray(origin, float)
        x = unit(x_axis)
        y = unit(y_axis)
        v2 = o
        v0 = o - x * 0.5 if mirrored else o + x * 0.5
        v1 = v0 + y * 1.0
        surf = self.surfaces[s]
        for p in (v0, v1, v2):
            surf['verts'].append((p, UP, (0, 0), bone))
        surf['tris'].append((0, 1, 2))
        return s


def write_glm(mesh, name, anim_name, num_bones, rot=None):
    """rot: turns the mesh (the player's, into the file's space)."""
    rot = np.eye(3) if rot is None else rot
    surfs = mesh.surfaces
    ns = len(surfs)
    children = {i: [j for j in range(ns) if surfs[j]['parent'] == i] for i in range(ns)}
    header_size = 164

    hier = bytearray()
    hier_offsets = []
    for i, s in enumerate(surfs):
        hier_offsets.append(4 * ns + len(hier))
        hier += struct.pack('<64sI64sii', s['name'].encode(), s['flags'], s['shader'].encode(), 0, s['parent'])
        hier += struct.pack('<i', len(children[i])) + struct.pack('<%di' % len(children[i]), *children[i])
    hier_block = struct.pack('<%di' % ns, *hier_offsets) + bytes(hier)
    # the offsets table follows the header; ofsSurfHierarchy is the first
    # entry, which the engine also walks through in order
    ofs_hier = header_size + 4 * ns
    ofs_lods = header_size + len(hier_block)

    surf_blobs = []
    for i, s in enumerate(surfs):
        bones = sorted({v[3] for v in s['verts']})
        local = {b: k for k, b in enumerate(bones)}
        refs = struct.pack('<%di' % len(bones), *bones)
        tris = b''.join(struct.pack('<3i', *t) for t in s['tris'])
        verts = b''.join(struct.pack('<6fI4B', *(rot @ v[1]), *(rot @ v[0]), local[v[3]], 0, 0, 0, 0) for v in s['verts'])
        uvs = b''.join(struct.pack('<2f', *v[2]) for v in s['verts'])
        surf_blobs.append((i, refs, tris, verts + uvs, len(bones), len(s['tris']), len(s['verts'])))

    # LOD: ofsEnd, surface offsets, surfaces
    lod_surfs = bytearray()
    lod_offsets = []
    surf_start = ofs_lods + 4 + 4 * ns
    for i, refs, tris, vdata, nb, nt, nv in surf_blobs:
        here = surf_start + len(lod_surfs)
        lod_offsets.append(4 * ns + len(lod_surfs))
        hsize = 40
        ofs_refs = hsize
        ofs_tris = ofs_refs + len(refs)
        ofs_verts = ofs_tris + len(tris)
        ofs_end = ofs_verts + len(vdata)
        lod_surfs += struct.pack('<10i', 0, i, -here, nv, ofs_verts, nt, ofs_tris, nb, ofs_refs, ofs_end)
        lod_surfs += refs + tris + vdata
    lod = struct.pack('<i', 4 + 4 * ns + len(lod_surfs)) + struct.pack('<%di' % ns, *lod_offsets) + bytes(lod_surfs)
    end = ofs_lods + len(lod)
    header = struct.pack('<4si64s64siiiiiii', b'2LGM', 6, name.encode(), anim_name.encode(), 0, num_bones, 1,
                         ofs_lods, ns, ofs_hier, end)
    assert len(header) == header_size
    return header + hier_block + lod


# texture regions (u0, v0, u1, v1)
CLOTH = (0.0, 0.0, 0.5, 0.5)
ARMOR = (0.5, 0.0, 1.0, 0.5)
SKIN = (0.0, 0.5, 0.5, 1.0)
DARK = (0.5, 0.5, 1.0, 1.0)


def player_mesh():
    m = Mesh()
    B = sk.INDEX
    hips = m.surface('hips', -1, MODEL_DIR + '/body_default')
    torso = m.surface('torso', hips, MODEL_DIR + '/body_default')
    head = m.surface('head', torso, MODEL_DIR + '/body_default')
    # lower body
    m.box(hips, B['pelvis'], (-4.0, -6.2, 7.5), (4.2, 6.2, 15.2), DARK)
    for side, s in (('r', -1), ('l', 1)):
        m.box(hips, B[side + 'femur'], (-2.6, s * 4 - 2.6, -5.5), (2.6, s * 4 + 2.6, 11.5), CLOTH, (1.0, 1.0))
        m.box(hips, B[side + 'tibia'], (-2.1, s * 4 - 2.0, -21.0), (2.3, s * 4 + 2.0, -4.5), DARK, (1.1, 1.1))
        m.box(hips, B[side + 'talus'], (-2.6, s * 4 - 1.9, -24.0), (6.0, s * 4 + 1.9, -20.0), DARK)
    # upper body
    m.box(torso, B['lower_lumbar'], (-3.6, -5.6, 15.0), (4.0, 5.6, 19.5), CLOTH)
    m.box(torso, B['upper_lumbar'], (-3.9, -6.0, 19.0), (4.4, 6.0, 24.5), CLOTH)
    m.box(torso, B['thoracic'], (-4.2, -6.4, 24.0), (4.8, 6.4, 31.0), ARMOR, (1.0, 1.18))
    m.box(torso, B['cervical'], (-1.6, -1.8, 30.5), (2.0, 1.8, 35.0), SKIN)
    for side, s in (('r', -1), ('l', 1)):
        m.box(torso, B[side + 'clavical'], (-2.4, s * 5.5 - 2.4, 27.0), (2.6, s * 5.5 + 2.4, 31.5), ARMOR)
        m.box(torso, B[side + 'humerus'], (-1.9, s * 7.6 - 1.9, 18.5), (1.9, s * 7.6 + 1.9, 29.0), CLOTH, (1.1, 1.1))
        m.box(torso, B[side + 'radius'], (-1.6, s * 8.2 - 1.6, 9.0), (1.6, s * 8.2 + 1.6, 19.5), CLOTH, (1.15, 1.15))
        m.box(torso, B[side + 'hand'], (-1.4, s * 8.5 - 1.7, 5.5), (1.6, s * 8.5 + 1.7, 9.5), DARK)
    # head: a helmet-like box with a visor band
    m.box(head, B['cranium'], (-3.6, -3.4, 34.5), (4.4, 3.4, 42.5), SKIN, (0.9, 0.92))
    m.box(head, B['cranium'], (3.6, -3.0, 37.5), (4.9, 3.0, 39.5), DARK)
    # a hidden triangle inside the hips on Motion: Ghoul2 only computes bones
    # that some surface uses, and the game reads Motion's orientation
    surf = m.surfaces[hips]
    base = len(surf['verts'])
    for p in ((0.0, -1.0, 11.0), (1.0, 0.0, 11.0), (0.0, 1.0, 11.0)):
        surf['verts'].append((np.array(p), UP, (0.0, 0.0), B['Motion']))
    surf['tris'].append((base, base + 1, base + 2))
    # bolts
    rh, lh = sk.BASE_POS[B['rhand']] + sk.PALM, sk.BASE_POS[B['lhand']] + sk.PALM
    m.tag('*r_hand', torso, B['rhand'], rh)
    m.tag('*l_hand', torso, B['lhand'], lh)
    m.tag('*head_top', head, B['cranium'], (0.5, 0, 42.5))
    return m


HILT = 7.5


def saber_mesh():
    """The saber hilt along +X from the grip; the blade comes out of *flash."""
    m = Mesh()
    s = m.surface('saber', -1, 'models/weapons2/saber/saber_w')
    m.box(s, 0, (-2.5, -0.75, -0.75), (HILT, 0.75, 0.75), (0.0, 0.0, 1.0, 0.5))
    m.box(s, 0, (HILT - 1.5, -1.0, -1.0), (HILT, 1.0, 1.0), (0.0, 0.5, 1.0, 1.0))
    m.box(s, 0, (1.0, -1.0, -1.0), (2.0, 1.0, 1.0), (0.0, 0.5, 1.0, 1.0))
    m.tag('*flash', s, 0, (HILT, 0, 0), FWD, LEFT, mirrored=True)
    return m


def body_texture(tint):
    size = 256
    h = size // 2
    img = np.zeros((size, size, 3))
    n = value_noise(size, 16, 71)
    # cloth: woven
    y, x = np.mgrid[0:h, 0:h]
    weave = 0.5 + 0.5 * np.sin(x * 1.3) * np.sin(y * 1.3)
    cloth = (0.42 + 0.06 * weave + 0.08 * n[:h, :h])[..., None] * np.array([0.78, 0.74, 0.66])
    img[:h, :h] = cloth
    # armor: panels in the team colour
    panel = 0.55 + 0.15 * n[:h, h:]
    edge = (np.minimum.reduce([x, y, h - 1 - x, h - 1 - y]) < 6)
    armor = panel[..., None] * np.asarray(tint)
    armor[edge] *= 0.55
    img[:h, h:] = armor
    # skin
    img[h:, :h] = (0.62 + 0.05 * n[h:, :h])[..., None] * np.array([0.92, 0.75, 0.62])
    # dark leather
    img[h:, h:] = (0.18 + 0.06 * n[h:, h:])[..., None] * np.array([0.9, 0.85, 0.8])
    return img


def saber_texture():
    size = 64
    img = np.zeros((size, size, 3))
    y = np.linspace(0, 1, size)
    ridges = 0.45 + 0.25 * (np.sin(y * 40) > 0)
    img[: size // 2] = ridges[None, :, None] * np.array([0.75, 0.76, 0.8])
    img[size // 2:] = 0.15
    return img


# ---------------------------------------------------------------------------

def generate(staging, mvsdk):
    names = anim_names(mvsdk)
    moves = saber_moves(mvsdk)
    NEEDED_EXTRA.update(referenced_anims(mvsdk))
    lib, table = build_anims(names, moves)

    # frames, in clip order
    frames = []
    first = {}
    for key, poses in lib.clips.items():
        first[key] = len(frames)
        for pose in poses:
            G, P = sk.solve(pose)
            frames.append(sk.relative(sk.to_file(sk.finals(G, P))))
    write_bytes(staging, GLA_NAME + '.gla', write_gla(frames))

    lines = []
    for name in names:
        if name not in table:
            continue
        key, fps, loop = table[name]
        lines.append('%s %d %d %d %g' % (name, first[key], len(lib.clips[key]), loop, fps))
    # cgame refuses the model if any of these has no frames (CG_NeedAnimSequence)
    required = names[names.index('BOTH_A1_T__B_'):names.index('BOTH_H1_S1_BR') + 1]
    required += names[names.index('BOTH_DEATH1'):names.index('BOTH_DEATH19') + 1]
    required += [n for n in names if n.startswith('BOTH_DISMEMBER')]
    lacking = [n for n in required if n not in table]
    if lacking:
        raise SystemExit('animations the game requires have no frames: %s' % ' '.join(lacking))
    cfg = '\n'.join(lines) + '\n'
    if len(cfg) >= 40000:
        raise SystemExit('animation.cfg is %d bytes: the game reads at most 39999' % len(cfg))
    write_text(staging, 'models/players/_humanoid/animation.cfg', cfg)

    mesh = player_mesh()
    write_bytes(staging, MODEL_DIR + '/model.glm',
                write_glm(mesh, MODEL_DIR + '/model.glm', GLA_NAME, len(sk.BONES), sk.FILE_ROT))
    for skin, tint in (('default', (0.35, 0.5, 0.75)), ('red', (0.8, 0.3, 0.25)), ('blue', (0.3, 0.45, 0.85))):
        save_image(staging, '%s/body_%s.jpg' % (MODEL_DIR, skin), body_texture(tint))
        write_text(staging, '%s/model_%s.skin' % (MODEL_DIR, skin),
                   ''.join('%s,%s/body_%s\n' % (s['name'], MODEL_DIR, skin)
                           for s in mesh.surfaces if not s['name'].startswith('*')))
    save_image(staging, MODEL_DIR + '/icon_default.jpg', body_texture((0.35, 0.5, 0.75))[:128, 128:])

    saber = saber_mesh()
    write_bytes(staging, 'models/weapons2/saber/saber_w.glm',
                write_glm(saber, 'models/weapons2/saber/saber_w.glm', '*default', 1))
    save_image(staging, 'models/weapons2/saber/saber_w.jpg', saber_texture())

    missing = [n for n in names if n not in table and not n.startswith('FACE_')]
    return dict(frames=len(frames), clips=len(lib.clips), anims=len(lines), cfg_bytes=len(cfg),
                gla_bytes=os.path.getsize(out_path(staging, GLA_NAME + '.gla')), unmapped=len(missing))
