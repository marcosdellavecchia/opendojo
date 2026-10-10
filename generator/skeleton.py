"""The humanoid skeleton of the open pack and the pose solver.

Model space: X forward, Y left, Z up, origin at the player's origin (the
middle of its bounding box), feet at z = -24. Bone names are the ones the
game code asks for. Bone orientations follow what the code's SetBoneAngles
calls expect (see REPORT.md): the spine bones have X up, Y left and Z
back, so the view's pitch bends them forward; the cranium has X forward, Y
left, Z up; every other bone has the model's axes.

A pose gives, per bone, a world rotation G (relative to the bone's base
orientation) and a position. The GLA stores, per frame and bone, the
transform from the parent's "final" matrix, where final = [G | p - G p0].
"""

import numpy as np

SPINE_BASIS = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)	# columns: X=up, Y=left, Z=back
# Motion: its -Y axis points forward (the game's spine code reads it that way)
MOTION_BASIS = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], float)	# columns: X=left, Y=back, Z=up

# name, parent, base position, base orientation
BONES = [
    ('model_root', None, (0, 0, 0), None),
    ('pelvis', 'model_root', (0, 0, 12), None),
    ('Motion', 'model_root', (0, 0, 0), MOTION_BASIS),
    ('lower_lumbar', 'pelvis', (0, 0, 15), SPINE_BASIS),
    ('upper_lumbar', 'lower_lumbar', (0, 0, 19), SPINE_BASIS),
    ('thoracic', 'upper_lumbar', (0, 0, 24), SPINE_BASIS),
    ('cervical', 'thoracic', (0, 0, 32), SPINE_BASIS),
    ('cranium', 'cervical', (0, 0, 34.5), None),
    ('rclavical', 'thoracic', (0, -2, 29.5), None),
    ('rhumerus', 'rclavical', (0, -7.5, 29.5), None),
    ('rradius', 'rhumerus', (0, -8, 19), None),
    ('rhand', 'rradius', (0, -8.5, 9), None),
    ('lclavical', 'thoracic', (0, 2, 29.5), None),
    ('lhumerus', 'lclavical', (0, 7.5, 29.5), None),
    ('lradius', 'lhumerus', (0, 8, 19), None),
    ('lhand', 'lradius', (0, 8.5, 9), None),
    ('rfemur', 'pelvis', (0, -4, 11), None),
    ('rtibia', 'rfemur', (0, -4, -5), None),
    ('rtalus', 'rtibia', (0, -4, -21), None),
    ('lfemur', 'pelvis', (0, 4, 11), None),
    ('ltibia', 'lfemur', (0, 4, -5), None),
    ('ltalus', 'ltibia', (0, 4, -21), None),
]

NAMES = [b[0] for b in BONES]
INDEX = {n: i for i, n in enumerate(NAMES)}
PARENT = [INDEX[b[1]] if b[1] else -1 for b in BONES]
BASE_POS = np.array([b[2] for b in BONES], float)
BASE_ROT = np.array([b[3] if b[3] is not None else np.eye(3) for b in BONES], float)

L_UPPER = np.linalg.norm(BASE_POS[INDEX['rradius']] - BASE_POS[INDEX['rhumerus']])
L_FORE = np.linalg.norm(BASE_POS[INDEX['rhand']] - BASE_POS[INDEX['rradius']])
L_THIGH = np.linalg.norm(BASE_POS[INDEX['rtibia']] - BASE_POS[INDEX['rfemur']])
L_SHIN = np.linalg.norm(BASE_POS[INDEX['rtalus']] - BASE_POS[INDEX['rtibia']])
PALM = np.array([0, 0, -2.5])	# the hand's grip point, from the wrist, in the hand's frame

FWD = np.array([1.0, 0, 0])
LEFT = np.array([0, 1.0, 0])
RIGHT = -LEFT
UP = np.array([0, 0, 1.0])


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def angles(yaw=0.0, pitch=0.0, roll=0.0):
    """Rotation matrix whose columns are Quake's forward, left, up for these
    angles in degrees (pitch > 0 looks down, yaw > 0 turns left)."""
    y, p, r = np.radians([yaw, pitch, roll])
    sy, cy, sp, cp, sr, cr = np.sin(y), np.cos(y), np.sin(p), np.cos(p), np.sin(r), np.cos(r)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp])
    up = np.array([cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp])
    return np.column_stack([fwd, -right, up])


def axis_angle(axis, deg):
    a = unit(axis)
    t = np.radians(deg)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * k + (1 - np.cos(t)) * (k @ k)


def frame_from(primary, secondary, base_primary, base_secondary):
    """Rotation taking (base_primary, base_secondary) to (primary, secondary),
    secondary orthogonalized against primary."""
    def basis(p, s):
        p = unit(p)
        s = np.asarray(s, float) - np.dot(s, p) * p
        if np.linalg.norm(s) < 1e-6:
            s = np.cross(p, UP) if abs(p[2]) < 0.9 else np.cross(p, FWD)
        s = unit(s)
        return np.column_stack([p, s, np.cross(p, s)])
    return basis(primary, secondary) @ basis(base_primary, base_secondary).T


def two_bone(root, target, l1, l2, pole):
    d = np.asarray(target, float) - root
    dist = np.clip(np.linalg.norm(d), 1e-3, (l1 + l2) * 0.999)
    direction = unit(d)
    a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist)
    h = np.sqrt(max(l1 * l1 - a * a, 0.0))
    perp = np.asarray(pole, float) - np.dot(pole, direction) * direction
    perp = unit(perp) if np.linalg.norm(perp) > 1e-6 else unit(np.cross(direction, LEFT))
    mid = root + direction * a + perp * h
    return mid, root + direction * dist


class Pose:
    """What a frame looks like. Positions are in model space; the body's
    facing is +X unless pelvis yaw says otherwise."""

    def __init__(self, **kw):
        self.pelvis = np.array([0.0, 0.0, 10.0])
        self.pelvis_rot = (0.0, 0.0, 0.0)	# yaw, pitch, roll
        self.torso = (0.0, 0.0, 0.0)	# spread over the three spine bones
        self.head = (0.0, 0.0, 0.0)
        self.rhand = None	# wrist target
        self.blade = FWD	# where the right hand's X axis (the saber) points
        self.lhand = None
        self.lhand_dir = FWD
        self.rfoot = np.array([2.0, -5.5, -21.0])
        self.lfoot = np.array([-2.0, 5.5, -21.0])
        self.body = None	# (rotation, pivot): turns the whole pose, for flips and falls
        for k, v in kw.items():
            setattr(self, k, v)


def solve(pose):
    """Returns (G, P): world rotations (n, 3, 3) and positions (n, 3)."""
    n = len(BONES)
    G = np.zeros((n, 3, 3))
    P = np.zeros((n, 3))

    def place(name, rot, pos=None):
        i = INDEX[name]
        G[i] = rot
        if pos is None:
            p = PARENT[i]
            pos = P[p] + G[p] @ (BASE_POS[i] - BASE_POS[p])
        P[i] = pos

    place('model_root', np.eye(3), np.zeros(3))
    place('Motion', np.eye(3), np.zeros(3))
    rp = angles(*pose.pelvis_rot)
    place('pelvis', rp, np.asarray(pose.pelvis, float))
    ty, tp, tr = pose.torso
    g = rp
    for name, share in (('lower_lumbar', 0.3), ('upper_lumbar', 0.3), ('thoracic', 0.4)):
        g = g @ angles(ty * share, tp * share, tr * share)
        place(name, g)
    hy, hp, hr = pose.head
    gc = g @ angles(hy * 0.5, hp * 0.5, hr * 0.5)
    place('cervical', gc)
    place('cranium', gc @ angles(hy * 0.5, hp * 0.5, hr * 0.5))
    place('rclavical', g)
    place('lclavical', g)

    # arms
    for side, hand, hdir, sign in (('r', pose.rhand, pose.blade, -1), ('l', pose.lhand, pose.lhand_dir, 1)):
        clav = INDEX[side + 'clavical']
        shoulder = P[clav] + G[clav] @ (BASE_POS[INDEX[side + 'humerus']] - BASE_POS[clav])
        if hand is None:
            # hanging, a little forward and out
            hand = shoulder + g @ np.array([3.0, sign * 2.5, -19.5])
            hdir = g @ FWD
        # the elbow points back and out
        pole = g @ np.array([-1.0, sign * 0.6, -0.3])
        elbow, wrist = two_bone(shoulder, hand, L_UPPER, L_FORE, pole)
        upper_dir = unit(elbow - shoulder)
        fore_dir = unit(wrist - elbow)
        bend = fore_dir - np.dot(fore_dir, upper_dir) * upper_dir
        if np.linalg.norm(bend) < 1e-3:
            bend = g @ FWD
        place(side + 'humerus', frame_from(upper_dir, bend, -UP, FWD), shoulder)
        hdir = unit(hdir)
        place(side + 'radius', frame_from(fore_dir, hdir, -UP, FWD), elbow)
        # the hand: X along hdir, -Z continuing the forearm
        z = -(fore_dir - np.dot(fore_dir, hdir) * hdir)
        if np.linalg.norm(z) < 1e-3:
            z = np.cross(hdir, g @ LEFT)
        z = unit(z)
        place(side + 'hand', np.column_stack([hdir, np.cross(z, hdir), z]), wrist)

    # legs: knees point where the pelvis faces
    for side, foot in (('r', pose.rfoot), ('l', pose.lfoot)):
        hip = P[INDEX['pelvis']] + rp @ (BASE_POS[INDEX[side + 'femur']] - BASE_POS[INDEX['pelvis']])
        knee, ankle = two_bone(hip, np.asarray(foot, float), L_THIGH, L_SHIN, rp @ FWD)
        thigh = unit(knee - hip)
        shin = unit(ankle - knee)
        fwd = rp @ FWD
        place(side + 'femur', frame_from(thigh, fwd, -UP, FWD), hip)
        place(side + 'tibia', frame_from(shin, fwd, -UP, FWD), knee)
        yaw_only = angles(pose.pelvis_rot[0])
        place(side + 'talus', yaw_only, ankle)

    if pose.body is not None:
        rot, pivot = pose.body
        pivot = np.asarray(pivot, float)
        for i in range(n):
            if NAMES[i] in ('model_root', 'Motion'):
                continue
            G[i] = rot @ G[i]
            P[i] = pivot + rot @ (P[i] - pivot)
    return G, P


# Ghoul2 turns every model by +90 degrees about Z (the "identityMatrix" root in
# tr_ghoul2.cpp), so files face -Y: they store the pose turned by -90.
FILE_ROT = np.array([[0.0, 1, 0], [-1, 0, 0], [0, 0, 1]])


def to_file(F):
    """finals in the generator's space -> the file's: Q F Q^T."""
    out = np.zeros_like(F)
    for i in range(len(F)):
        out[i, :, :3] = FILE_ROT @ F[i, :, :3] @ FILE_ROT.T
        out[i, :, 3] = FILE_ROT @ F[i, :, 3]
    return out


def finals(G, P):
    """final matrices (n, 3, 4): [G | p - G p0]."""
    out = np.zeros((len(BONES), 3, 4))
    for i in range(len(BONES)):
        out[i, :, :3] = G[i]
        out[i, :, 3] = P[i] - G[i] @ BASE_POS[i]
    return out


def relative(F):
    """Per-bone frame matrices: parent_final^-1 * final."""
    out = np.zeros_like(F)
    for i in range(len(BONES)):
        p = PARENT[i]
        if p < 0:
            out[i] = F[i]
            continue
        rp, tp = F[p][:, :3], F[p][:, 3]
        r, t = F[i][:, :3], F[i][:, 3]
        out[i, :, :3] = rp.T @ r
        out[i, :, 3] = rp.T @ (t - tp)
    return out


def hand_grip(G, P, side='r'):
    i = INDEX[side + 'hand']
    return P[i] + G[i] @ PALM
