#!/bin/sh
# Builds the engine: the browser build (jk2mvmp.js and .wasm) into
# build/web and the native dedicated server (jk2mvded) into build/native.
#
#   ./build-engine.sh [web] [ded]     (both by default)
#
# Needs cmake, emscripten (emcmake) and a C/C++ compiler. The gl4es patches
# in patches/gl4es/ go into the libs/gl4es submodule as CMake builds it.

set -eu
root=$(cd "$(dirname "$0")" && pwd)
targets=${*:-web ded}
cmake_flags="-DUseInternalLibs=ON -DBuildPortableVersion=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBuildMVSDK=OFF"

for target in $targets; do
	case $target in
	web)
		mkdir -p "$root/build/web"
		(cd "$root/build/web" && emcmake cmake $cmake_flags -DBuildMVDED=OFF "$root" > cmake.log &&
			emmake make -j8 > make.log 2>&1) || { tail -30 "$root/build/web/make.log"; exit 1; }
		echo "engine: build/web/out/Release/jk2mvmp.{js,wasm}"
		;;
	ded)
		mkdir -p "$root/build/native"
		(cd "$root/build/native" && cmake -G "Unix Makefiles" $cmake_flags -DBuildMVMP=OFF "$root" > cmake.log &&
			make -j8 > make.log 2>&1) || { tail -30 "$root/build/native/make.log"; exit 1; }
		echo "engine: build/native/out/Release/jk2mvded"
		;;
	*)
		echo "build-engine: unknown target $target" >&2
		exit 1
		;;
	esac
done
