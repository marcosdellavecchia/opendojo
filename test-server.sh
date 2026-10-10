#!/bin/sh
# Runs a test game server: the dedicated server built here, with only the
# Open Dojo pack, on UDP 28170, off the public server lists (dedicated 1).
# Build first: ./build.sh.
#
#   ./test-server.sh [+set name value]...
#
# OPEN_CHEATS=1 starts the map with cheats (devmap), for the automated
# fight test, which places players with setviewpos (test/play.mjs).

set -eu
root=$(cd "$(dirname "$0")" && pwd)
out="$root/build"

mkdir -p "$out/server/base" "$out/server-home"
ln -sf "$out/pack/opendojo.pk3" "$out/server/base/opendojo.pk3"
cp "$root/server/server.cfg" "$out/server/base/server.cfg"

cheats=""
[ "${OPEN_CHEATS:-0}" = 1 ] && cheats="+devmap open_dojo"

exec "$out/native/out/Release/jk2mvded" \
	+set fs_basepath "$out/server" +set fs_homepath "$out/server-home" \
	+set dedicated 1 +set net_port 28170 "$@" +exec server.cfg $cheats
