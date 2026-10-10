// Opens Open Dojo in fresh browser profiles and plays: each client loads
// the page, joins the test server, and runs a script of game commands. Writes
// console logs, screenshots and a summary to --out.
//
//   node test/play.mjs [--url http://localhost:8090/] [--clients 2]
//                 [--seconds 40] [--script idle|fight|bots|combo] [--out dir] [--headed]
//                 [--dev] [--server-log build/test-server.log]
//
// Uses the installed Google Chrome (channel "chrome"), each client in a new
// browser with an empty profile, as a first-time visitor would be.

import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';

const { values: args } = parseArgs({
	options: {
		url: { type: 'string', default: 'http://localhost:8090/' },
		clients: { type: 'string', default: '2' },
		seconds: { type: 'string', default: '40' },
		script: { type: 'string', default: 'idle' },
		out: { type: 'string', default: resolve(import.meta.dirname, '../build/test-results') },
		headed: { type: 'boolean', default: false },
		dev: { type: 'boolean', default: false },
		'server-log': { type: 'string' },
		width: { type: 'string', default: '960' },
		height: { type: 'string', default: '600' },
	},
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// a page stuck in the engine never answers evaluate(): give up on the whole run
const deadline = setTimeout(() => {
	console.error('play: timed out');
	process.exit(2);
}, (Number(args.seconds) + 150) * 1000);
deadline.unref();
mkdirSync(args.out, { recursive: true });

async function launchClient(i) {
	const name = `Tester${i + 1}`;
	const browser = await chromium.launch({
		channel: 'chrome',
		headless: !args.headed,
		args: ['--autoplay-policy=no-user-gesture-required', '--mute-audio'],
	});
	const context = await browser.newContext({ viewport: { width: Number(args.width), height: Number(args.height) } });
	const page = await context.newPage();
	const log = [];
	const requests = [];
	const logFile = join(args.out, `${name}.log`);
	writeFileSync(logFile, '');
	const record = (line) => { log.push(line); appendFileSync(logFile, line + '\n'); };
	page.on('console', (msg) => record(msg.text()));
	page.on('pageerror', (err) => record(`PAGE ERROR: ${err.message}`));
	page.on('crash', () => record('PAGE CRASHED'));
	page.on('request', (req) => requests.push(req.url()));
	await page.goto(`${args.url}?autoplay=${name}${args.dev ? '&dev=1' : ''}`);
	return { i, name, browser, page, log, requests };
}

async function state(c) {
	return within(c.page.evaluate(() => ({
		client: window.jk2?._Sys_WebClientState?.() ?? 0,
		status: document.getElementById('status').textContent,
		startVisible: !document.getElementById('start').hidden,
	})), 5000, { error: 'no answer' });
}

// a page busy rendering can leave evaluate() waiting: give up after a while
const within = (promise, ms, fallback = null) =>
	Promise.race([promise.catch(() => fallback), sleep(ms).then(() => fallback)]);

async function cmd(c, text) {
	await within(c.page.evaluate((t) => window.jk2.ccall('Sys_WebCommand', null, ['string'], [t]), text), 5000);
}

async function cvar(c, name) {
	return c.page.evaluate((n) => window.jk2.ccall('Sys_WebCvar', 'string', ['string'], [n]), name);
}

async function waitInGame(c, timeoutMs = 60000) {
	const end = Date.now() + timeoutMs;
	while (Date.now() < end) {
		const s = await state(c);
		if (s.client === 8) return true;
		if (s.startVisible && /error|crash|couldn't/i.test(s.status)) return false;
		await sleep(500);
	}
	return false;
}

const scripts = {
	// one player cycles the saber stances, then adds two bots from the
	// menu's command and lets them fight
	async bots(clients) {
		const [a] = clients;
		for (const stance of ['fast', 'medium', 'strong']) {
			await sleep(1500);
			await within(a.page.screenshot({ path: join(args.out, `${a.name}-stance-${stance}.png`) }), 10000);
			await cmd(a, 'saberAttackCycle');
		}
		await cmd(a, 'addbot');
		await sleep(1500);
		await cmd(a, 'addbot');
		const end = Date.now() + Number(args.seconds) * 1000;
		let n = 0;
		while (Date.now() < end) {
			await sleep(5000);
			await within(a.page.screenshot({ path: join(args.out, `${a.name}-bots-${n++}.png`) }), 10000);
		}
	},
	// strong stance, holding attack with each direction in turn: the server's
	// log shows whether attacks chain (attack, transition, attack) or return
	async combo(clients) {
		const [a] = clients;
		await cmd(a, 'saberAttackCycle');
		await sleep(400);
		await cmd(a, 'saberAttackCycle');
		await sleep(1500);
		for (const move of ['+moveright', '+moveleft', '+forward', '+back']) {
			await cmd(a, `${move}; +attack`);
			await sleep(3000);
			await cmd(a, `-attack; -${move.slice(1)}`);
			await sleep(1500);
		}
	},
	async idle(clients) {
		await sleep(Number(args.seconds) * 1000);
	},
	// two players face to face (needs the server started with cheats:
	// OPEN_CHEATS=1 ./test-server.sh), swinging in turns
	async fight(clients) {
		const [a, b] = clients;
		// through spots apart from each other, so nobody lands on the other (a telefrag)
		const place = async () => {
			await cmd(a, 'setviewpos -300 -200 40 90');
			await cmd(b, 'setviewpos 300 200 40 -90');
			await sleep(300);
			await cmd(a, 'setviewpos 0 -34 40 90');
			await cmd(b, 'setviewpos 0 34 40 -90');
		};
		// two browsers rendering at once: a lower frame rate keeps the pages responsive
		for (const c of clients) await cmd(c, 'com_maxfps 60');
		await place();
		await sleep(1000);
		const moves = ['', '+moveleft', '+moveright', '+back', '+forward'];
		const end = Date.now() + Number(args.seconds) * 1000;
		let n = 0;
		while (Date.now() < end) {
			const attacker = n % 2 ? b : a;
			const move = moves[n % moves.length];
			await cmd(attacker, `${move ? move + '; ' : ''}+attack`);
			await sleep(450);
			await cmd(attacker, `-attack${move ? '; -' + move.slice(1) : ''}`);
			await sleep(250);
			if (n % 8 === 7) await place();
			if (n % 6 === 0) {
				for (const c of clients) await c.page.screenshot({ path: join(args.out, `${c.name}-fight-${n}.png`) });
			}
			n++;
		}
	},
};

const clients = [];
for (let i = 0; i < Number(args.clients); i++) {
	clients.push(await launchClient(i));
	await sleep(1500);
}

const summary = { url: args.url, started: new Date().toISOString(), clients: [] };
for (const c of clients) {
	const ok = await waitInGame(c);
	await sleep(1500);
	await c.page.screenshot({ path: join(args.out, `${c.name}-joined.png`) });
	summary.clients.push({ name: c.name, inGame: ok, state: await state(c) });
	console.log(`${c.name}: ${ok ? 'in game' : 'NOT in game'}`, await state(c));
}

if (summary.clients.every((c) => c.inGame)) {
	await scripts[args.script](clients);
}

for (const c of clients) {
	await within(c.page.screenshot({ path: join(args.out, `${c.name}-end.png`) }), 10000);
	summary.clients[c.i].endState = await within(state(c), 5000);
	// what reached the network: anything but the site's own files would show here
	summary.clients[c.i].requests = [...new Set(c.requests.map((u) => new URL(u).pathname))];
	writeFileSync(join(args.out, `${c.name}-requests.txt`), c.requests.join('\n'));
}
await Promise.all(clients.map((c) => within(c.browser.close(), 10000)));

// the test server's view, when its log is given: kills by saber
if (args['server-log']) {
	const log = readFileSync(args['server-log'], 'latin1').replace(/\x1b\[[0-9]*m/g, '').split('\n');
	const since = log.findIndex((l) => l.includes(`${clients[0].name} @@@PLCONNECT`));
	const tail = log.slice(Math.max(since, 0));
	summary.saberKills = tail.filter((l) => /Kill: .* by MOD_SABER/.test(l)).map((l) => l.replace(/^.*Kill: [0-9 ]+: /, ''));
	summary.botsJoined = tail.filter((l) => /ClientBegin/.test(l) && /bot/i.test(l)).length;
	summary.serverLines = tail.filter((l) => /broadcast|Kill:|bot|forcepowers/i.test(l)).map((l) => l.replace(/^[0-9-]+ [0-9:]+ /, '')).slice(0, 60);
}
writeFileSync(join(args.out, 'summary.json'), JSON.stringify(summary, null, '\t'));
console.log(JSON.stringify(summary, null, 2));
process.exit(0);
