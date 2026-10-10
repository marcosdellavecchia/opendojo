"""Sounds, synthesized here (saber hum, swings, clashes, footsteps...), as
16-bit mono WAV at the file names the game code plays."""

import io
import wave

import numpy as np

from common import rng, write_bytes

RATE = 22050


def wav(samples):
    s = np.clip(samples, -1, 1)
    data = (s * 32000).astype('<i2').tobytes()
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)
    return buf.getvalue()


def t(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def lowpass(x, alpha):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * RATE), int(release * RATE)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def hum(seconds=2.0, base=92.0, seed=1):
    x = t(seconds)
    # frequencies that complete whole cycles in the loop, so it loops cleanly
    f = np.round(base * seconds) / seconds
    wobble = 1 + 0.15 * np.sin(2 * np.pi * x / seconds * 2)
    s = (np.sin(2 * np.pi * f * x) * 0.6 + np.sin(2 * np.pi * 2 * f * x) * 0.25
         + np.sin(2 * np.pi * 3 * f * x + 0.5) * 0.12 + np.sin(2 * np.pi * 5 * f * x) * 0.05)
    buzz = rng(seed).normal(0, 1, len(x))
    buzz = lowpass(buzz, 0.08) * 0.15
    return 0.5 * s * wobble + buzz


def sweep(seconds, f0, f1, seed=2, noise=0.3):
    x = t(seconds)
    f = np.linspace(f0, f1, len(x))
    phase = 2 * np.pi * np.cumsum(f) / RATE
    s = np.sin(phase) * 0.6 + np.sin(2 * phase) * 0.25 + np.sin(3 * phase) * 0.1
    n = lowpass(rng(seed).normal(0, 1, len(x)), 0.15) * noise
    return s + n


def swing(seed):
    r = rng(seed)
    dur = 0.35 + 0.15 * r.random()
    x = t(dur)
    shape = np.sin(np.pi * x / dur) ** 2
    f0 = 90 + 30 * r.random()
    f = f0 * (1 + 1.2 * shape)
    phase = 2 * np.pi * np.cumsum(f) / RATE
    tone = np.sin(phase) * 0.5 + np.sin(2 * phase) * 0.3
    whoosh = lowpass(r.normal(0, 1, len(x)), 0.05 + 0.2 * shape.mean()) * 1.6
    return (tone + whoosh) * shape * 0.9


def clash(seed, dur=0.45, bright=1.0):
    r = rng(seed)
    x = t(dur)
    out = np.zeros(len(x))
    for _ in range(7):
        f = (900 + 2600 * r.random()) * bright
        decay = 6 + 14 * r.random()
        out += np.sin(2 * np.pi * f * x + r.random() * 6) * np.exp(-decay * x) * (0.3 + 0.5 * r.random())
    crack = r.normal(0, 1, len(x)) * np.exp(-30 * x)
    sizzle = lowpass(r.normal(0, 1, len(x)), 0.5) * np.exp(-8 * x) * 0.4
    hum_ = hum(dur, 140, seed) * np.exp(-5 * x)
    return (out * 0.35 + crack * 0.6 + sizzle + hum_ * 0.5) * env(len(x), 0.002, 0.05)


def thump(seed, dur=0.15, freq=70.0, noise=0.5):
    r = rng(seed)
    x = t(dur)
    s = np.sin(2 * np.pi * freq * x * (1 - 0.3 * x / dur)) * np.exp(-18 * x)
    n = lowpass(r.normal(0, 1, len(x)), 0.1) * np.exp(-25 * x) * noise
    return (s + n) * 0.9


def sizzle(seed, dur=0.5):
    r = rng(seed)
    x = t(dur)
    n = r.normal(0, 1, len(x))
    return (lowpass(n, 0.6) * 0.5 + hum(dur, 120, seed) * 0.4) * np.exp(-4 * x) * env(len(x), 0.003, 0.05)


def grunt(seed, dur=0.35, f0=180.0):
    r = rng(seed)
    x = t(dur)
    f = f0 * (1 - 0.35 * x / dur)
    phase = 2 * np.pi * np.cumsum(f) / RATE
    s = np.sign(np.sin(phase)) * 0.2 + np.sin(phase) * 0.4
    return lowpass(s + r.normal(0, 0.05, len(x)), 0.12) * env(len(x), 0.02, 0.15) * 1.5


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def generate(staging):
    out = {
        'sound/weapons/saber/saberhum.wav': hum(2.0, 92, 1),
        'sound/weapons/saber/saberhum1.wav': hum(2.0, 96, 2),
        'sound/weapons/saber/saberon.wav': sweep(0.6, 40, 140, 3) * env(int(0.6 * RATE), 0.01, 0.2),
        'sound/weapons/saber/saberoffquick.wav': sweep(0.4, 140, 30, 4) * env(int(0.4 * RATE), 0.005, 0.25),
        'sound/weapons/saber/saberspin.wav': np.tile(swing(5), 2),
        'sound/weapons/saber/saberhit.wav': mix(sizzle(6, 0.5), thump(6, 0.2, 60, 0.3)),
    }
    for i in range(1, 9):
        out['sound/weapons/saber/saberhup%d.wav' % i] = swing(10 + i)
    for i in range(1, 10):
        out['sound/weapons/saber/saberblock%d.wav' % i] = clash(20 + i)
    for i in range(1, 4):
        out['sound/weapons/saber/bounce%d.wav' % i] = clash(40 + i, 0.25, 1.3)
        out['sound/weapons/saber/saberhitwall%d.wav' % i] = sizzle(50 + i, 0.45)
    for i in range(1, 5):
        out['sound/player/footsteps/step%d.wav' % i] = thump(60 + i, 0.12, 90 + 10 * i, 0.4) * 0.6
        out['sound/player/footsteps/boot%d.wav' % i] = thump(70 + i, 0.12, 80 + 10 * i, 0.5) * 0.6
    out['sound/player/land1.wav'] = thump(80, 0.25, 55, 0.6)
    out['sound/player/roll1.wav'] = lowpass(rng(81).normal(0, 1, int(0.4 * RATE)), 0.05) * env(int(0.4 * RATE), 0.05, 0.2) * 2
    out['sound/player/fallsplat.wav'] = thump(82, 0.4, 45, 0.8)
    out['sound/player/talk.wav'] = np.sin(2 * np.pi * 880 * t(0.08)) * env(int(0.08 * RATE), 0.005, 0.04) * 0.3
    # the default model's voice: wordless grunts
    for name, f0, d in (('pain25', 210, 0.25), ('pain50', 200, 0.3), ('pain75', 190, 0.3), ('pain100', 180, 0.35),
                        ('death1', 170, 0.7), ('death2', 160, 0.8), ('death3', 150, 0.9), ('jump1', 230, 0.15),
                        ('falling1', 260, 1.0), ('land1', 180, 0.15), ('gasp', 240, 0.3)):
        out['sound/chars/open/misc/%s.wav' % name] = grunt(sum(map(ord, name)), d, f0)
    for path, s in out.items():
        write_bytes(staging, path, wav(s))
    return len(out)
