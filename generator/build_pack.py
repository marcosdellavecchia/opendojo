"""Builds the Open Dojo asset pack, build/pack/opendojo.pk3.

    build/venv/bin/python generator/build_pack.py [--qvms <dir>] [--skip-map]

Everything in the pack is either a text file in pack/ or generated
here. --qvms is where MVSDK's cgame.qvm, ui.qvm and jk2mpgame.qvm are
(build.sh builds them).
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

from common import BUILD, ROOT, write_text

import arena
import bots
import effects
import fonts
import items
import model
import sounds
import strings
import textures
import ui

PACK_DIR = os.path.join(BUILD, 'pack')
STAGING = os.path.join(PACK_DIR, 'base')
Q3MAP2 = os.path.join(BUILD, 'third_party', 'netradiant-custom', 'install', 'q3map2')
PK3 = os.path.join(PACK_DIR, 'opendojo.pk3')

# compiler leftovers that don't go in the pack
EXCLUDE_EXT = {'.map', '.prt', '.srf', '.lin', '.bak'}


def copy_assets():
    src = os.path.join(ROOT, 'pack')
    for dirpath, _, files in os.walk(src):
        for name in files:
            if name.startswith('.'):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), src)
            dst = os.path.join(STAGING, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(dirpath, name), dst)


def q3map2(stage, *args):
    # its multithreaded lighting crashes on macOS: one thread
    cmd = [Q3MAP2, *stage, '-game', 'jk2', '-fs_basepath', PACK_DIR, '-threads', '1', *args]
    res = subprocess.run(cmd, capture_output=True, text=True)
    log = os.path.join(PACK_DIR, 'q3map2.log')
    with open(log, 'a') as f:
        f.write(' '.join(cmd) + '\n' + res.stdout + res.stderr)
    if res.returncode != 0 or 'LEAKED' in res.stdout:
        sys.exit('q3map2 failed (%s), see %s' % (' '.join(stage or ['-bsp']), log))


def build_map(name, text):
    path = os.path.join(STAGING, 'maps', name + '.map')
    write_text(STAGING, 'maps/%s.map' % name, text)
    q3map2([], '-meta', '-patchmeta', path)
    q3map2(['-vis'], '-saveprt', path)
    q3map2(['-light'], '-fast', '-samples', '2', '-bounce', '1', '-patchshadows', path)


def zip_pack():
    with zipfile.ZipFile(PK3, 'w', zipfile.ZIP_DEFLATED) as z:
        for dirpath, _, files in os.walk(STAGING):
            for name in sorted(files):
                if os.path.splitext(name)[1].lower() in EXCLUDE_EXT:
                    continue
                full = os.path.join(dirpath, name)
                z.write(full, os.path.relpath(full, STAGING).replace(os.sep, '/'))
    return PK3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--qvms', default=os.path.join(BUILD, 'mvsdk-build', 'code', 'vm'))
    ap.add_argument('--mvsdk', default=os.path.join(BUILD, 'mvsdk'), help='MVSDK source')
    ap.add_argument('--skip-map', action='store_true', help='keep the last compiled map')
    args = ap.parse_args()

    bsp = os.path.join(STAGING, 'maps', 'open_dojo.bsp')
    kept = None
    if args.skip_map and os.path.exists(bsp):
        kept = open(bsp, 'rb').read()
    shutil.rmtree(STAGING, ignore_errors=True)
    if os.path.exists(os.path.join(PACK_DIR, 'q3map2.log')):
        os.remove(os.path.join(PACK_DIR, 'q3map2.log'))
    os.makedirs(STAGING)

    copy_assets()
    textures.generate(STAGING)
    strings.generate(STAGING)
    fonts.generate(STAGING)
    ui.generate(STAGING)
    items.generate(STAGING)
    print('model:', model.generate(STAGING, args.mvsdk))
    effects.generate(STAGING, set())
    print('sounds:', sounds.generate(STAGING))
    bots.generate(STAGING)

    # the menu definitions are part of MVSDK's source (GPLv2)
    menudef = os.path.join(args.mvsdk, 'code', 'ui', 'menudef.h')
    os.makedirs(os.path.join(STAGING, 'ui', 'jk2mp'), exist_ok=True)
    shutil.copyfile(menudef, os.path.join(STAGING, 'ui', 'jk2mp', 'menudef.h'))

    for qvm in ('cgame.qvm', 'ui.qvm', 'jk2mpgame.qvm'):
        src = os.path.join(args.qvms, qvm)
        if not os.path.exists(src):
            sys.exit('%s is missing: build the QVMs first (build.sh)' % src)
        os.makedirs(os.path.join(STAGING, 'vm'), exist_ok=True)
        shutil.copyfile(src, os.path.join(STAGING, 'vm', qvm))

    if kept:
        os.makedirs(os.path.dirname(bsp), exist_ok=True)
        open(bsp, 'wb').write(kept)
    else:
        build_map('open_dojo', arena.generate())

    print('pack:', zip_pack(), '%.1f MB' % (os.path.getsize(PK3) / 1048576))


if __name__ == '__main__':
    main()
