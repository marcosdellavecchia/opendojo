// The relay between the browser build and its game server.
//
//   node relay.mjs [--port 8080] [--public] [--game 127.0.0.1:28070]
//
// Browsers can't send UDP, so the game sends each packet over a WebSocket
// (/relay) and the relay forwards it from a UDP socket of its own, one per
// browser: the game server sees an ordinary client per player. Message
// format: see src/web/net_web.cpp.
//
// The relay only talks to one game server, --game, whatever address the game
// sends to, so it can't be used to send UDP anywhere else. Replies come back
// as from the address the game sent to, so the game sees the server it
// connected to (by name or IP). Run it on the game server's machine, where
// --game is 127.0.0.1; server/dev.mjs runs it next to the page for local play.
//
// From jk2web's relay (web/relay.mjs there), without its Discord notices.
//
// GET /status answers the server's name, map, and player and bot counts, for
// the start screen. The relay asks the game server at most every few seconds
// however many pages ask it: the server only answers 10 queries a second per
// address, and every player comes from the relay's.


import { createServer } from 'node:http';
import { lookup } from 'node:dns/promises';
import { createSocket } from 'node:dgram';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { WebSocketServer } from 'ws';

const PACKET = 0;
const HEADER = 7;
const MAX_PACKETS_PER_SECOND = 1000;
const STATUS_MAX_AGE = 3000;
const STATUS_TIMEOUT = 1500;

const OOB = Buffer.from([0xff, 0xff, 0xff, 0xff]);

// "host:port" -> { address, port }, the port defaulting to the game's
export async function resolveGameServer(text) {
	const [host, port = '28070'] = text.split(':');
	const { address } = await lookup(host, { family: 4 });
	return { address, port: Number(port) };
}

// Asks the game server for its info (getinfo) once per STATUS_MAX_AGE at most.
function statusPoller(game) {
	let cached = null, cachedAt = 0, pending = null;

	function query() {
		return new Promise((done) => {
			const udp = createSocket('udp4');
			const finish = (status) => {
				clearTimeout(timer);
				udp.close();
				done(status);
			};
			const timer = setTimeout(() => finish({ online: false }), STATUS_TIMEOUT);
			udp.on('message', (msg, rinfo) => {
				if (rinfo.address !== game.address || rinfo.port !== game.port) return;
				const text = msg.toString('latin1');
				if (!text.startsWith('\xff\xff\xff\xffinfoResponse')) return;
				const fields = text.slice(text.indexOf('\n') + 1).split('\\').slice(1);
				const info = {};
				for (let i = 0; i + 1 < fields.length; i += 2) info[fields[i].toLowerCase()] = fields[i + 1];
				// clients counts the bots too; g_humanplayers doesn't
				const clients = Number(info.clients ?? 0);
				const players = Number(info.g_humanplayers ?? clients);
				finish({
					online: true,
					name: (info.hostname ?? '').replace(/\^./g, ''),
					map: info.mapname ?? '',
					players,
					bots: clients - players,
					maxPlayers: Number(info.sv_maxclients ?? 0),
				});
			});
			udp.on('error', () => finish({ online: false }));
			udp.send(Buffer.concat([OOB, Buffer.from('getinfo opendojo')]), game.port, game.address);
		});
	}

	return function status() {
		if (cached && Date.now() - cachedAt < STATUS_MAX_AGE) return Promise.resolve(cached);
		pending ??= query().then((result) => {
			cached = result;
			cachedAt = Date.now();
			pending = null;
			return result;
		});
		return pending;
	};
}

export function attachRelay(httpServer, { game, maxClients = 64 }) {
	const wss = new WebSocketServer({ server: httpServer, path: '/relay', maxPayload: 64 * 1024 });
	const status = statusPoller(game);

	wss.on('connection', (ws, req) => {
		const client = req.headers['x-forwarded-for']?.split(',')[0] ?? req.socket.remoteAddress;
		if (wss.clients.size > maxClients) {
			console.log(`relay: ${client} turned away, ${maxClients} players already`);
			ws.close(1013, 'Too many players');
			return;
		}

		const udp = createSocket('udp4');
		let replyFrom = null;	// ip and port (6 bytes) the game last sent to
		let budget = MAX_PACKETS_PER_SECOND;
		const refill = setInterval(() => { budget = MAX_PACKETS_PER_SECOND; }, 1000);

		console.log(`relay: ${client} connected`);

		udp.on('message', (msg, rinfo) => {
			if (rinfo.address !== game.address || rinfo.port !== game.port) return;
			if (!replyFrom || ws.readyState !== ws.OPEN) return;
			const frame = Buffer.allocUnsafe(HEADER + msg.length);
			frame[0] = PACKET;
			replyFrom.copy(frame, 1);
			msg.copy(frame, HEADER);
			ws.send(frame);
		});
		udp.on('error', (err) => console.error('relay: udp error:', err.message));
		udp.bind();

		// Host names (alias frames) need no resolving: they all mean the game
		// server.
		ws.on('message', (data, isBinary) => {
			if (!isBinary || data.length <= HEADER || data[0] !== PACKET || budget-- <= 0) return;
			replyFrom = Buffer.from(data.subarray(1, HEADER));
			udp.send(data.subarray(HEADER), game.port, game.address);
		});

		ws.on('close', () => {
			clearInterval(refill);
			udp.close();
			console.log(`relay: ${client} disconnected`);
		});
	});

	return function handleStatus(req, res) {
		if (new URL(req.url, 'http://localhost').pathname !== '/status') return false;
		status().then((result) => {
			res.writeHead(200, {
				'Content-Type': 'application/json',
				'Cache-Control': 'no-store',
				// the page is on another site (e.g. Vercel)
				'Access-Control-Allow-Origin': '*',
			});
			res.end(JSON.stringify(result));
		});
		return true;
	};
}

// Run on its own, on the game server's machine
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	const { values: args } = parseArgs({
		options: {
			port: { type: 'string', default: process.env.PORT ?? '8080' },
			public: { type: 'boolean', default: false },
			game: { type: 'string', default: '127.0.0.1:28070' },
		},
	});

	const game = await resolveGameServer(args.game);
	let handleStatus;
	const server = createServer((req, res) => {
		if (handleStatus(req, res)) return;
		res.writeHead(200, { 'Content-Type': 'text/plain' }).end('Open Dojo relay\n');
	});
	handleStatus = attachRelay(server, { game });

	const host = args.public ? '0.0.0.0' : '127.0.0.1';
	server.listen(Number(args.port), host, () => {
		console.log(`relay: ws://${host}:${args.port}/relay -> ${game.address}:${game.port}`);
	});
}
