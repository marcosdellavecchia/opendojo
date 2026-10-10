#!/bin/sh
# Builds everything into build/:
#
#   1. the engine: browser build and dedicated server (build-engine.sh)
#   2. MVSDK's QVMs (cgame, ui, jk2mpgame) from the src/mvsdk submodule,
#      with patches/mvsdk.patch (the pack's names; players may add bots)
#   3. q3map2, to compile the map (NetRadiant-custom, GPLv2)
#   4. the asset pack, build/pack/opendojo.pk3 (generator/build_pack.py)
#   5. the static site, build/site/ (site/build.mjs)
#
#   ./build.sh [--server host:port --relay wss://… --source <url>]   (site options)
#
# Needs: cmake, emscripten, a C compiler, Python 3, Node, and for q3map2
# glib, libxml2, libpng, jpeg-turbo, assimp, minizip (brew install ...).

set -eu
root=$(cd "$(dirname "$0")" && pwd)
out="$root/build"
mkdir -p "$out"

# 1
"$root/build-engine.sh" web ded

# 2
echo "build: QVMs from MVSDK $(git -C "$root/src/mvsdk" rev-parse --short HEAD)"
rm -rf "$out/mvsdk"
mkdir -p "$out/mvsdk" "$out/mvsdk-build"
git -C "$root/src/mvsdk" archive HEAD | tar -x -C "$out/mvsdk"
(cd "$out/mvsdk" && patch -p1 --quiet < "$root/patches/mvsdk.patch")
(cd "$out/mvsdk-build" && cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
	"$out/mvsdk" > cmake.log && make qvms > make.log 2>&1) || { tail -20 "$out/mvsdk-build/make.log"; exit 1; }

# 3 (the NetRadiant-custom commit it was made with)
netradiant=8216133984031afaa9a857b56ea66dd9c3d54b26
q3map2="$out/third_party/netradiant-custom/install/q3map2"
if [ ! -x "$q3map2" ]; then
	echo "build: q3map2"
	mkdir -p "$out/third_party"
	[ -d "$out/third_party/netradiant-custom" ] ||
		{ git init -q "$out/third_party/netradiant-custom" &&
		git -C "$out/third_party/netradiant-custom" fetch -q --depth 1 https://github.com/Garux/netradiant-custom.git $netradiant &&
		git -C "$out/third_party/netradiant-custom" checkout -q FETCH_HEAD; }
	jpeg=$(brew --prefix jpeg-turbo 2>/dev/null || echo /usr)
	(cd "$out/third_party/netradiant-custom" && make -j8 DEPENDENCIES_CHECK=off BUILD=release \
		CPPFLAGS_JPEG="-I$jpeg/include" LIBS_JPEG="-L$jpeg/lib -ljpeg" binaries-q3map2 > q3map2-build.log 2>&1) ||
		{ grep -m 10 -A 3 'error' "$out/third_party/netradiant-custom/q3map2-build.log"; exit 1; }
fi

# 4
if [ ! -x "$out/venv/bin/python" ]; then
	python3 -m venv "$out/venv"
	"$out/venv/bin/pip" install -q pillow==12.3.0 numpy==2.5.3
fi
"$out/venv/bin/python" "$root/generator/build_pack.py"

# 5
node "$root/site/build.mjs" "$@"
