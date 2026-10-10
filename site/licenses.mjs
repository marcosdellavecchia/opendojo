// The licenses of everything Open Dojo's site distributes: the engine
// (GPLv2) and the libraries built into it, the game code, and the fonts the
// pack's bitmap fonts come from. writeLicenses() copies their texts into a
// folder with an index page; site/build.mjs puts it at licenses/.

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, readdirSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '..');	// the engine's source: LICENSE, libs/

// the first /* ... */ comment of a source file: where these libraries keep their license
function headerComment(path) {
	const text = readFileSync(path, 'latin1');
	const start = text.indexOf('/*');
	return text.slice(start, text.indexOf('*/', start) + 2);
}

function section(path, from, to) {
	const text = readFileSync(path, 'latin1');
	const start = text.indexOf(from);
	const end = text.indexOf(to, start + from.length);
	return text.slice(start, end > 0 ? end : undefined);
}

function emscriptenRoot() {
	try {
		const emcc = realpathSync(execFileSync('which', ['emcc'], { encoding: 'utf8' }).trim());
		for (let dir = dirname(emcc); dir !== '/'; dir = dirname(dir)) {
			if (existsSync(join(dir, 'LICENSE')) && existsSync(join(dir, 'libexec'))) return { root: dir, libexec: join(dir, 'libexec') };
			if (existsSync(join(dir, 'LICENSE')) && existsSync(join(dir, 'system'))) return { root: dir, libexec: dir };
		}
	} catch { /* not installed */ }
	return null;
}

function sdl2License(libexec) {
	const ports = join(libexec, 'cache/ports/sdl2');
	if (!existsSync(ports)) return null;
	for (const name of readdirSync(ports)) {
		const path = join(ports, name, 'LICENSE.txt');
		if (existsSync(path)) return readFileSync(path, 'latin1');
	}
	return null;
}

export function writeLicenses(out, { source }) {
	mkdirSync(out, { recursive: true });
	const em = emscriptenRoot();
	const items = [
		['JK2MV, the engine (jk2mvmp.wasm), and its game code MVSDK (the QVMs in the pack)', 'GNU GPL v2',
			'GPL-2.0.txt', () => readFileSync(join(src, 'LICENSE'), 'latin1'),
			'Based on the Jedi Knight II source code released by Raven Software under the GPLv2.'],
		['gl4es (OpenGL on WebGL), built into the engine', 'MIT', 'gl4es.txt', () => readFileSync(join(src, 'libs/gl4es/LICENSE'), 'latin1')],
		['SDL 2, built into the engine', 'zlib', 'SDL2.txt', () => em && sdl2License(em.libexec)],
		['zlib, built into the engine', 'zlib', 'zlib.txt', () => headerComment(join(src, 'libs/zlib/include/zlib.h'))],
		['minizip, built into the engine', 'zlib', 'minizip.txt', () => headerComment(join(src, 'libs/minizip/include/minizip/unzip.h'))],
		['libpng, built into the engine', 'libpng', 'libpng.txt', () => headerComment(join(src, 'libs/libpng/include/png.h'))],
		['libjpeg (Independent JPEG Group), built into the engine', 'IJG', 'libjpeg.txt',
			() => section(join(src, 'libs/jpeg-9a/README'), 'LEGAL ISSUES', 'REFERENCES')],
		['Emscripten runtime and OpenAL implementation', 'MIT / University of Illinois', 'emscripten.txt',
			() => em && readFileSync(join(em.root, 'LICENSE'), 'latin1')],
		['musl libc, built into the engine by Emscripten', 'MIT', 'musl.txt',
			() => em && readFileSync(join(em.libexec, 'system/lib/libc/musl/COPYRIGHT'), 'latin1')],
		['libc++, built into the engine by Emscripten', 'Apache 2.0 with LLVM exception', 'libcxx.txt',
			() => em && readFileSync(join(em.libexec, 'system/lib/libcxx/LICENSE.TXT'), 'latin1')],
		['Exo 2 (the medium and large bitmap fonts in the pack are rendered from it)', 'SIL Open Font License 1.1', 'OFL-Exo2.txt',
			() => readFileSync(join(src, 'pack-src/fonts/exo2-OFL.txt'), 'utf8')],
		['Share Tech Mono (the small bitmap font and the console font are rendered from it)', 'SIL Open Font License 1.1', 'OFL-ShareTechMono.txt',
			() => readFileSync(join(src, 'pack-src/fonts/sharetechmono-OFL.txt'), 'utf8')],
	];

	const rows = [];
	for (const [what, license, file, read, note] of items) {
		let text = null;
		try { text = read(); } catch { /* missing */ }
		if (!text) {
			console.warn(`site/licenses: no license text found for ${what}`);
			continue;
		}
		writeFileSync(join(out, file), text);
		rows.push(`<tr><td>${what}${note ? `<br><small>${note}</small>` : ''}</td><td><a href="${file}">${license}</a></td></tr>`);
	}

	writeFileSync(join(out, 'index.html'), `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="data:,">
<title>Open Dojo licenses</title>
<style>
	:root { color-scheme: dark; }
	body { margin: 0; padding: 32px 16px; background: #0b0d12; color: #e8ecf4; font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }
	main { max-width: 760px; margin: 0 auto; }
	a { color: #5aa9ff; }
	table { width: 100%; border-collapse: collapse; }
	td { padding: 8px 6px; border-bottom: 1px solid #222837; vertical-align: top; }
	small { color: #9aa3b5; }
</style>
</head>
<body>
<main>
<h1>Licenses</h1>
<p>This page's game runs the JK2MV engine and its game code, both free software under the GNU General Public License v2.
The complete source code, including this site's changes to the engine and game code and the scripts that make every
asset in the game's pack, is at <a href="${source}">${source}</a>.</p>
<p>The game's assets (map, character, animations, textures, sounds, menus, text) were made for this project and are
distributed under the GPLv2 with the rest of the source. Its bitmap fonts are rendered from the two fonts below,
under the SIL Open Font License.</p>
<table>
${rows.join('\n')}
</table>
<p><a href="../">Back</a></p>
</main>
</body>
</html>
`);
	return rows.length;
}
