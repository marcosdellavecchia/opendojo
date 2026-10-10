// Test-only: serves another site's static build at / (jk2web's, say) and
// Open Dojo's site at /open,
// on one origin as a static host would in production, with a relay to the
// test game server. For isolation.mjs.
//
//   node test/site-server.mjs --main <dir> [--open build/site] [--port 8091] [--game 127.0.0.1:28170]

import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve } from 'node:path';
import { parseArgs } from 'node:util';
import { attachRelay, resolveGameServer } from '../server/relay.mjs';

const { values: args } = parseArgs({
	options: {
		main: { type: 'string' },
		open: { type: 'string', default: resolve(import.meta.dirname, '../build/site') },
		port: { type: 'string', default: '8091' },
		game: { type: 'string', default: '127.0.0.1:28170' },
	},
});

const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json' };

function serve(res, root, path) {
	let file = normalize(join(root, path));
	if (!file.startsWith(root)) return res.writeHead(403).end();
	if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
	if (!existsSync(file)) return res.writeHead(404).end('Not found');
	res.writeHead(200, { 'Content-Type': types[extname(file)] ?? 'application/octet-stream', 'Cache-Control': 'no-cache' });
	createReadStream(file).pipe(res);
}

const server = createServer((req, res) => {
	const { pathname } = new URL(req.url, 'http://localhost');
	if (handleStatus(req, res)) return;
	if (pathname === '/open') return res.writeHead(302, { Location: '/open/' }).end();
	if (pathname.startsWith('/open/')) {
		if (pathname === '/open/config.json') {
			res.writeHead(200, { 'Content-Type': 'application/json' });
			return res.end(JSON.stringify({ server: args.game, relay: `ws://${req.headers.host}/relay` }));
		}
		return serve(res, resolve(args.open), pathname.slice('/open'.length));
	}
	return serve(res, resolve(args.main), pathname);
});
const handleStatus = attachRelay(server, { game: await resolveGameServer(args.game) });
server.listen(Number(args.port), '127.0.0.1', () => console.log(`site-server: http://127.0.0.1:${args.port}/ and /open/`));
