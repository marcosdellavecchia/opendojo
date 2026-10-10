// Local server: the page, the engine build, the asset pack and the licenses
// page, with a relay to the test game server.
//
//   node server/dev.mjs [--port 8090] [--public] [--game 127.0.0.1:28170]
//
// Run the test server first (./test-server.sh). The site itself is static
// (site/build.mjs); this serves the same files straight from the build.

import { createHash } from 'node:crypto';
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { attachRelay, resolveGameServer } from './relay.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const build = join(root, 'build');

const { values: args } = parseArgs({
	options: {
		port: { type: 'string', default: process.env.PORT ?? '8090' },
		public: { type: 'boolean', default: false },
		game: { type: 'string', default: '127.0.0.1:28170' },
	},
});

const types = {
	'.html': 'text/html; charset=utf-8',
	'.js': 'text/javascript; charset=utf-8',
	'.wasm': 'application/wasm',
	'.json': 'application/json',
	'.pk3': 'application/octet-stream',
	'.txt': 'text/plain; charset=utf-8',
};

const files = {
	'/': join(root, 'web/index.html'),
	'/main.js': join(root, 'web/main.js'),
	'/jk2mvmp.js': join(build, 'web/out/Release/jk2mvmp.js'),
	'/jk2mvmp.wasm': join(build, 'web/out/Release/jk2mvmp.wasm'),
	'/base/opendojo.pk3': join(build, 'pack/opendojo.pk3'),
};

function manifest() {
	const path = files['/base/opendojo.pk3'];
	if (!existsSync(path)) return [];
	const data = readFileSync(path);
	return [{ name: 'opendojo.pk3', size: data.length, version: createHash('sha256').update(data).digest('hex').slice(0, 16) }];
}

function send(req, res, path) {
	if (!path || !existsSync(path)) {
		res.writeHead(404).end('Not found');
		return;
	}
	res.writeHead(200, {
		'Content-Type': types[extname(path)] ?? 'application/octet-stream',
		'Content-Length': statSync(path).size,
		'Cache-Control': 'no-cache',
	});
	if (req.method === 'HEAD') res.end();
	else createReadStream(path).pipe(res);
}

const server = createServer((req, res) => {
	const url = new URL(req.url, 'http://localhost');
	if (handleStatus(req, res)) return;
	if (url.pathname === '/config.json') {
		const host = req.headers.host ?? `localhost:${args.port}`;
		res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
		res.end(JSON.stringify({ server: args.game, relay: `ws://${host}/relay` }));
	} else if (url.pathname === '/base/manifest.json') {
		res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
		res.end(JSON.stringify(manifest()));
	} else if (url.pathname === '/licenses') {
		res.writeHead(302, { Location: '/licenses/' }).end();
	} else if (url.pathname.startsWith('/licenses/')) {
		// written by site/build.mjs
		const name = url.pathname.slice('/licenses/'.length) || 'index.html';
		send(req, res, /^[\w.-]+$/.test(name) ? join(build, 'site/licenses', name) : null);
	} else {
		send(req, res, files[url.pathname]);
	}
});

const handleStatus = attachRelay(server, { game: await resolveGameServer(args.game) });

const host = args.public ? '0.0.0.0' : '127.0.0.1';
server.listen(Number(args.port), host, () => {
	console.log(`Open Dojo: http://localhost:${args.port}/ -> test server ${args.game}`);
	for (const [path, file] of Object.entries(files)) {
		if (!existsSync(file)) console.warn(`warning: ${path} is missing (${file}): run ./build.sh`);
	}
});
