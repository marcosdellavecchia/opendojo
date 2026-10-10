// The page: downloads the asset pack, starts the browser build of JK2MV and
// joins the game server, straight into the game.
//
// Adapted from jk2web's page (web/main.js there). Its storage has names of
// its own, so it can share a site with other pages (for example jk2web's, if
// served under its /open): the Cache API cache "opendojo", the IndexedDB of
// the IDBFS mount /opendojo-home, and localStorage keys starting with
// "opendojo.". It uses no OPFS.

import createJK2 from './jk2mvmp.js';

const $ = (id) => document.getElementById(id);
const BASE_PATH = '/jk2';
const HOME_PATH = '/opendojo-home';
const CACHE_NAME = 'opendojo';
const STORAGE_PREFIX = 'opendojo.';

// connstate_t (q_shared.h)
const CA_DISCONNECTED = 1;
const CA_CONNECTED = 5;
const CA_ACTIVE = 8;
const TEAM_SPECTATOR = '3';
const JOIN_TIMEOUT = 20000;

const config = await fetch('config.json', { cache: 'no-store' }).then((res) => res.json()).catch(() => null);

function storageGet(key) {
	try { return localStorage.getItem(STORAGE_PREFIX + key); } catch { return null; }
}

function storageSet(key, value) {
	try { localStorage.setItem(STORAGE_PREFIX + key, value); } catch { /* private mode */ }
}

// ----- the page -----

const ui = {
	setStatus(text, { error = false } = {}) {
		$('status').textContent = text ?? '';
		$('status').className = error ? 'error' : '';
	},
	setProgress(fraction) {
		$('progress').hidden = fraction == null;
		if (fraction != null) $('progress').value = fraction;
	},
	setBusy(busy) {
		$('play').disabled = busy;
	},
	show(visible) {
		$('start').hidden = !visible;
	},
};

const debugLines = [];
const missing = new Set();
function debug(line) {
	debugLines.push(line);
	if (debugLines.length > 400) debugLines.shift();
	$('debug').textContent = debugLines.join('\n');
	// what the engine looked for and didn't find, for the asset inventory
	const m = /(?:couldn't find|can't find|could not find|couldn't load|not found:?|couldn't open|Failed to load)\s+([\w./-]+)/i.exec(line);
	if (m) {
		missing.add(m[1]);
		$('missing').textContent = [...missing].sort().join('\n');
	}
}

function formatMB(bytes) {
	return `${(bytes / 1048576).toFixed(1)} MB`;
}

// ----- game data -----

async function readStream(stream, size, onChunk) {
	const data = new Uint8Array(size);
	const reader = stream.getReader();
	let offset = 0;
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		if (offset + value.length > size) throw new Error('the download is larger than expected');
		data.set(value, offset);
		offset += value.length;
		onChunk(value.length);
	}
	if (offset !== size) throw new Error(`the download stopped at ${formatMB(offset)} of ${formatMB(size)}`);
	return data;
}

// Downloads the files in base/manifest.json, kept in this page's own cache
// so later visits don't download them again. Returns [name, bytes][].
async function loadGameData(onProgress) {
	const manifest = await fetch('base/manifest.json', { cache: 'no-store' }).then((res) => {
		if (!res.ok) throw new Error(`no list of game files (${res.status})`);
		return res.json();
	});
	const total = manifest.reduce((sum, f) => sum + f.size, 0);
	let loaded = 0;
	const count = (bytes) => onProgress((loaded += bytes), total);

	let cache = null;
	try {
		cache = self.caches ? await caches.open(CACHE_NAME) : null;
	} catch (err) {
		console.warn('No cache for the game data:', err);
	}

	const files = [];
	const urls = new Set();
	for (const file of manifest) {
		const url = new URL(`base/${encodeURIComponent(file.name)}?v=${file.version}`, document.baseURI).href;
		urls.add(url);
		const cached = await cache?.match(url).catch(() => null);
		let data = cached ? new Uint8Array(await cached.arrayBuffer()) : null;
		if (data && data.length !== file.size) data = null;	// a broken entry
		if (data) {
			count(data.length);
		} else {
			let res;
			try {
				res = await fetch(url);
			} catch (err) {
				throw new Error(`Couldn't download ${file.name}: ${err.message}. Check the connection and try again.`);
			}
			if (!res.ok) throw new Error(`Couldn't download ${file.name} (HTTP ${res.status}).`);
			try {
				data = await readStream(res.body, file.size, count);
			} catch (err) {
				throw new Error(`Couldn't download ${file.name}: ${err.message}. Try again.`);
			}
			try {
				await cache?.put(url, new Response(data));
			} catch (err) {
				console.warn(`Couldn't cache ${file.name}:`, err);
				cache = null;
			}
		}
		files.push([file.name, data]);
	}

	// drop old versions, only from this page's own cache
	try {
		for (const req of await cache?.keys() ?? []) {
			if (!urls.has(req.url)) await cache.delete(req);
		}
	} catch (err) {
		console.warn('Cache cleanup failed:', err);
	}
	return files;
}

// ----- the game -----

let game = null;
let gameQuit = false;

function connectRelay() {
	const net = {
		queue: [],
		pending: [],
		ws: null,
		send(frame) {
			if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(frame);
			else if (this.pending.length < 64) this.pending.push(frame);
		},
	};
	function open() {
		const ws = new WebSocket(config.relay);
		ws.binaryType = 'arraybuffer';
		ws.onopen = () => {
			for (const frame of net.pending) ws.send(frame);
			net.pending = [];
		};
		ws.onmessage = (event) => net.queue.push(new Uint8Array(event.data));
		ws.onclose = () => setTimeout(open, 2000);
		net.ws = ws;
	}
	open();
	return net;
}

function gameSize() {
	const aspect = screen.width / screen.height;
	const canvas = $('canvas');
	let width = canvas.clientWidth, height = canvas.clientHeight;
	if (width / height > aspect) width = Math.round(height * aspect);
	else height = Math.round(width / aspect);
	return { width, height };
}

function gameArgs(name) {
	const { width, height } = gameSize();
	return [
		'+set', 'fs_basepath', BASE_PATH,
		'+set', 'fs_homepath', HOME_PATH,
		'+set', 'mv_menuOverride', '1',
		'+set', 'cl_motd', '0',
		'+set', 'con_notifytime', '8',
		'+set', 'r_fullscreen', '0',
		'+set', 'r_mode', '-1',
		'+set', 'r_customwidth', String(width),
		'+set', 'r_customheight', String(height),
		'+set', 'name', name,
		// ?dev=1: the engine reports every file it can't find (the Debug panel)
		...(new URLSearchParams(location.search).has('dev') ? ['+set', 'developer', '1'] : []),
		'+connect', config.server,
	];
}

function runMainLoop(module) {
	const channel = new MessageChannel();
	const tick = () => {
		let wait;
		try {
			wait = module._Sys_WebFrame();
		} catch (err) {
			gameStopped(module, err);
			return;
		}
		if (wait > 1) setTimeout(tick, wait - 1);
		else channel.port2.postMessage(0);
	};
	channel.port1.onmessage = tick;
	tick();
}

function command(module, text) {
	module.ccall('Sys_WebCommand', null, ['string'], [text]);
}

function cvar(module, name) {
	return module.ccall('Sys_WebCvar', 'string', ['string'], [name]);
}

function followWindowSize(module) {
	let { width, height } = gameSize();
	let timer;
	addEventListener('resize', () => {
		clearTimeout(timer);
		timer = setTimeout(() => {
			const size = gameSize();
			if (size.width === width && size.height === height) return;
			({ width, height } = size);
			command(module, `r_customwidth ${width}; r_customheight ${height}; vid_restart`);
		}, 500);
	});
}

const connection = { joinStarted: 0, seenConnecting: false, connected: false, inGame: false, lastError: '', timer: 0 };

function joining(module) {
	Object.assign(connection, {
		joinStarted: performance.now(), seenConnecting: false, connected: false, inGame: false,
		lastError: cvar(module, 'com_errorMessage'),
	});
}

function watchConnection(module) {
	connection.timer = setInterval(() => {
		if (!connection.joinStarted) return;
		const state = module._Sys_WebClientState();
		if (state > CA_DISCONNECTED) connection.seenConnecting = true;
		if (state >= CA_CONNECTED) connection.connected = true;
		if (state === CA_ACTIVE && !connection.inGame) {
			connection.inGame = true;
			joinTheGame(module);
		}
		if (connection.seenConnecting && state <= CA_DISCONNECTED) {
			const error = cvar(module, 'com_errorMessage');
			left(error && error !== connection.lastError ? `Disconnected: ${error.replace(/\^./g, '')}` : 'Disconnected.');
		} else if (!connection.connected && performance.now() - connection.joinStarted > JOIN_TIMEOUT) {
			command(module, 'disconnect');
			left("Couldn't join the test server: it didn't answer.");
		}
	}, 250);
}

// The pack has no Force or key menus, so the page sets what they would: a
// Force setup with saber offense 3 (all three stances) and stances on the
// middle mouse button. Configs saved by earlier visits may lack them.
const FORCE_POWERS = '7-1-032330000000001333';

// New players start as spectators with the force powers menu (w_force.c);
// join the game for them.
function joinTheGame(module) {
	command(module, `forcepowers "${FORCE_POWERS}"; model open/default; bind MOUSE3 saberAttackCycle`);
	const started = performance.now();
	let tries = 0;
	const timer = setInterval(() => {
		if (cvar(module, 'ui_myteam') === TEAM_SPECTATOR) {
			if (tries++ % 4 === 0) command(module, 'team free');
		} else if (tries) {
			module._Sys_WebCloseMenu();
			clearInterval(timer);
		}
		if (performance.now() - started > 5000) clearInterval(timer);
	}, 250);
}

function left(message) {
	connection.joinStarted = 0;
	document.exitPointerLock?.();
	ui.setBusy(false);
	ui.setProgress(null);
	ui.show(true);
	ui.setStatus(message);
	$('play').textContent = 'Rejoin';
	refreshServerStatus();
}

function gameStopped(module, err) {
	const quit = err?.name === 'ExitStatus';
	if (!quit) console.error(err);
	clearInterval(connection.timer);
	connection.joinStarted = 0;
	document.exitPointerLock?.();
	ui.show(true);
	if (module.gameError) {
		ui.setBusy(true);
		ui.setStatus(`Error: ${module.gameError}`, { error: true });
	} else if (quit) {
		gameQuit = true;
		ui.setBusy(false);
		ui.setProgress(null);
		ui.setStatus(null);
	} else {
		ui.setBusy(true);
		ui.setStatus(`The game crashed: ${err?.message ?? err}. Reload the page to try again.`, { error: true });
	}
}

function persistHome(FS) {
	let syncing = false;
	const sync = () => {
		if (syncing) return;
		syncing = true;
		FS.syncfs(false, () => { syncing = false; });
	};
	setInterval(sync, 10000);
	addEventListener('pagehide', sync);
}

async function start(name) {
	ui.setBusy(true);
	ui.setStatus('Downloading the free asset pack…');
	ui.setProgress(0);
	const files = await loadGameData((loaded, total) => {
		ui.setProgress(loaded / total);
		ui.setStatus(`Downloading the free asset pack · ${formatMB(loaded)} of ${formatMB(total)}`);
	});

	ui.setStatus('Starting the engine…');
	const module = await createJK2({
		canvas: $('canvas'),
		print: (text) => { console.log(text); debug(text); },
		printErr: (text) => { console.warn(text); debug(text); },
	});
	const { FS } = module;
	window.jk2 = module;

	FS.mkdirTree(`${BASE_PATH}/base`);
	for (const [fileName, data] of files) {
		FS.writeFile(`${BASE_PATH}/base/${fileName}`, data, { canOwn: true });
	}
	FS.mkdirTree(HOME_PATH);
	FS.mount(FS.filesystems.IDBFS, {}, HOME_PATH);
	await new Promise((resolve) => FS.syncfs(true, resolve));
	persistHome(FS);

	module.jk2net = connectRelay();
	game = module;

	ui.show(false);
	$('canvas').focus();
	try {
		module.callMain(gameArgs(name));
	} catch (err) {
		gameStopped(module, err);
		return;
	}
	joining(module);
	watchConnection(module);
	runMainLoop(module);
	followWindowSize(module);
}

function playerName() {
	let name = $('name').value.replace(/[";\\]/g, '').trim().slice(0, 31);
	if (!name) name = `Player${Math.floor(100 + Math.random() * 900)}`;
	$('name').value = name;
	storageSet('name', name);
	return name;
}

function play() {
	if (!config?.server || !config?.relay) {
		ui.setStatus('This page has no test server configured (config.json).', { error: true });
		return;
	}
	if (gameQuit) {
		location.reload();
		return;
	}
	if (game) {
		ui.show(false);
		$('canvas').focus();
		joining(game);
		command(game, `name "${playerName()}"; connect ${config.server}`);
		return;
	}
	start(playerName()).catch((err) => {
		console.error(err);
		ui.setBusy(false);
		ui.setProgress(null);
		ui.setStatus(err.message, { error: true });
	});
}

let statusTimer = 0;
async function refreshServerStatus() {
	clearTimeout(statusTimer);
	if ($('start').hidden || !config?.relay) return;
	const url = new URL('status', config.relay.replace(/^ws/, 'http')).href;
	try {
		const res = await fetch(url, { cache: 'no-store' });
		const s = res.ok ? await res.json() : { online: false };
		$('server').textContent = s.online
			? `Test server: ${s.map ?? '?'}, ${s.players ?? 0} playing`
			: 'Test server: not answering';
	} catch {
		$('server').textContent = 'Test server: not answering';
	}
	statusTimer = setTimeout(refreshServerStatus, 5000);
}

$('name').value = storageGet('name') ?? '';
$('form').addEventListener('submit', (event) => {
	event.preventDefault();
	play();
});
if (!config) ui.setStatus("Couldn't load this page's settings (config.json).", { error: true });
refreshServerStatus();

// for the automated tests: ?autoplay=<name> plays straight away
const autoplay = new URLSearchParams(location.search).get('autoplay');
if (autoplay) {
	$('name').value = autoplay;
	play();
}
