// For serving Open Dojo under another site's /open (jk2web's, say): checks
// that both share the origin without touching each other's storage, that
// /open survives a reload, and that the other site's page still loads.
// Needs test/site-server.mjs (with --main, the other site's static build)
// and a game server.
//
//   node test/isolation.mjs [--url http://127.0.0.1:8091]
//
// 1. Fresh profile: open the other site's page and leave markers where
//    jk2web's page keeps its things (localStorage "name", Cache "jk2web-base",
//    OPFS "jk2-base", IndexedDB "/home").
// 2. Open /open, join the game, reload, join again.
// 3. The markers must be unchanged, Open Dojo's storage must be its own
//    (localStorage "opendojo.*", Cache "opendojo", IndexedDB "/opendojo-home").
// 4. The other site's page loads again as before.
// 5. A failed download of the pack says so.

import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';

const { values: args } = parseArgs({ options: { url: { type: 'string', default: 'http://127.0.0.1:8091' } } });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const check = (name, ok, detail = '') => {
	results.push({ name, ok, detail });
	console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ` (${detail})` : ''}`);
};

const profile = mkdtempSync(join(tmpdir(), 'opendojo-isolation-'));
const context = await chromium.launchPersistentContext(profile, {
	channel: 'chrome', headless: true, viewport: { width: 960, height: 600 }, args: ['--mute-audio'],
});
const page = context.pages()[0] ?? await context.newPage();
const errors = [];
// headless Chrome refuses pointer lock without a click: not an error of the page
page.on('pageerror', (e) => { if (!/pointer lock/i.test(e.message)) errors.push(e.message); });

// 1
await page.goto(`${args.url}/`);
await page.waitForSelector('#start', { timeout: 15000 });
const mainTitle = await page.title();
check('main page loads', mainTitle.length > 0 && !/Open Dojo/.test(mainTitle), mainTitle);
await page.evaluate(async () => {
	localStorage.setItem('name', 'MainMarker');
	const cache = await caches.open('jk2web-base');
	await cache.put('/base/marker.txt', new Response('main-cache-marker'));
	const root = await navigator.storage.getDirectory();
	const dir = await root.getDirectoryHandle('jk2-base', { create: true });
	const file = await dir.getFileHandle('marker.txt', { create: true });
	const w = await file.createWritable();
	await w.write('main-opfs-marker');
	await w.close();
	await new Promise((resolve, reject) => {
		const req = indexedDB.open('/home', 21);
		req.onupgradeneeded = () => req.result.createObjectStore('FILE_DATA');
		req.onsuccess = () => {
			const tx = req.result.transaction('FILE_DATA', 'readwrite');
			tx.objectStore('FILE_DATA').put('main-idb-marker', '/home/marker');
			tx.oncomplete = () => { req.result.close(); resolve(); };
		};
		req.onerror = () => reject(req.error);
	});
});

// 2
async function joinOpen(label) {
	await page.goto(`${args.url}/open/?autoplay=Isolation`);
	const end = Date.now() + 60000;
	let state = 0;
	while (Date.now() < end) {
		state = await page.evaluate(() => window.jk2?._Sys_WebClientState?.() ?? 0).catch(() => 0);
		if (state === 8) break;
		await sleep(500);
	}
	check(`/open joins the game (${label})`, state === 8, `client state ${state}`);
	await sleep(3000);
}
await joinOpen('first visit');
await page.evaluate(() => window.jk2.FS.syncfs(false, () => {}));
await sleep(1000);
await joinOpen('after a reload');

// 3
const storage = await page.evaluate(async () => {
	const out = {};
	out.localStorage = Object.fromEntries(Object.keys(localStorage).map((k) => [k, localStorage.getItem(k)]));
	out.caches = await caches.keys();
	const mainCache = await caches.open('jk2web-base');
	const m = await mainCache.match('/base/marker.txt');
	out.mainCacheMarker = m ? await m.text() : null;
	out.mainCacheKeys = (await mainCache.keys()).map((r) => new URL(r.url).pathname);
	const root = await navigator.storage.getDirectory();
	const names = [];
	for await (const name of root.keys()) names.push(name);
	out.opfs = names;
	const dir = await root.getDirectoryHandle('jk2-base');
	const files = [];
	for await (const name of dir.keys()) files.push(name);
	out.mainOpfsFiles = files;
	out.mainOpfsMarker = await (await (await dir.getFileHandle('marker.txt')).getFile()).text();
	out.idb = (await indexedDB.databases()).map((d) => d.name);
	out.mainIdbMarker = await new Promise((resolve) => {
		const req = indexedDB.open('/home');
		req.onsuccess = () => {
			const get = req.result.transaction('FILE_DATA').objectStore('FILE_DATA').get('/home/marker');
			get.onsuccess = () => { resolve(get.result); req.result.close(); };
			get.onerror = () => resolve(null);
		};
		req.onerror = () => resolve(null);
	});
	return out;
});
console.log(JSON.stringify(storage, null, 2));
check('main localStorage untouched', storage.localStorage.name === 'MainMarker');
check('Open Dojo localStorage is namespaced', Object.keys(storage.localStorage).every((k) => k === 'name' || k.startsWith('opendojo.')),
	Object.keys(storage.localStorage).join(', '));
check('main cache untouched', storage.mainCacheMarker === 'main-cache-marker' && storage.mainCacheKeys.length === 1);
check('Open Dojo has its own cache', storage.caches.includes('opendojo'), storage.caches.join(', '));
check('main OPFS untouched', storage.mainOpfsMarker === 'main-opfs-marker' && storage.mainOpfsFiles.length === 1);
check('Open Dojo writes nothing to OPFS', storage.opfs.length === 1 && storage.opfs[0] === 'jk2-base', storage.opfs.join(', '));
check('main IndexedDB untouched', storage.mainIdbMarker === 'main-idb-marker');
check('Open Dojo has its own IndexedDB', storage.idb.includes('/opendojo-home'), storage.idb.join(', '));

// 4
await page.goto(`${args.url}/`);
await page.waitForSelector('#start', { timeout: 15000 });
check('main page loads afterwards', !/Open Dojo/.test(await page.title()));
check('no page errors', errors.length === 0, errors.join(' | '));

await context.close();
rmSync(profile, { recursive: true, force: true });

// 5. a failed download says so
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const ctx = await browser.newContext();
const p2 = await ctx.newPage();
await p2.route('**/opendojo.pk3*', (route) => route.fulfill({ status: 503, body: 'unavailable' }));
await p2.goto(`${args.url}/open/?autoplay=Broken`);
await p2.waitForFunction(() => /couldn't/i.test(document.getElementById('status').textContent), null, { timeout: 15000 }).catch(() => {});
const status = await p2.evaluate(() => [document.getElementById('status').textContent, document.getElementById('play').disabled]);
check('a failed download shows an error and Play can be pressed again', /Couldn't download opendojo\.pk3 \(HTTP 503\)/.test(status[0]) && !status[1], status[0]);
await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(failed.length ? `${failed.length} check(s) failed` : 'all checks passed');
process.exit(failed.length ? 1 : 0);
