// Builds the static site: build/site/, which any static host serves, at the
// root of a domain or under a path (the page loads everything relatively).
//
//   node site/build.mjs [--server host:port] [--relay wss://…/relay] [--out dir]
//                       [--source <url of the published source code>]
//
// --server is the game server the page joins, --relay the relay in front of
// it (server/relay.mjs, next to the game server). Without them, config.json
// is left out and the page says it has no server. --source is where the page
// and its licenses page point for the source code the GPL requires: it must
// be published there, at the deployed commit.

import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { writeLicenses } from './licenses.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const build = resolve(here, '../build');

const { values: args } = parseArgs({
	options: {
		server: { type: 'string' },
		relay: { type: 'string' },
		out: { type: 'string', default: join(build, 'site') },
		source: { type: 'string' },
	},
});

const site = args.out;
const files = [
	[join(here, '../web/index.html'), 'index.html'],
	[join(here, '../web/main.js'), 'main.js'],
	[join(build, 'web/out/Release/jk2mvmp.js'), 'jk2mvmp.js'],
	[join(build, 'web/out/Release/jk2mvmp.wasm'), 'jk2mvmp.wasm'],
	[join(build, 'pack/opendojo.pk3'), 'base/opendojo.pk3'],
];
for (const [from] of files) {
	if (!existsSync(from)) {
		console.error(`site/build: ${from} is missing: run ./build.sh`);
		process.exit(1);
	}
}

// it empties the output folder: only ever one inside build/
if (!resolve(site).startsWith(build + '/')) {
	console.error(`site/build: --out must be inside ${build}`);
	process.exit(1);
}
rmSync(site, { recursive: true, force: true });
for (const [from, to] of files) {
	mkdirSync(dirname(join(site, to)), { recursive: true });
	copyFileSync(from, join(site, to));
}

// the source code's address, on the page and its licenses page
const source = args.source ?? 'SOURCE-NOT-PUBLISHED-YET';
if (!args.source) console.warn('site/build: no --source: publish the source code and build again with its address before deploying');
writeFileSync(join(site, 'index.html'), readFileSync(join(site, 'index.html'), 'utf8')
	.replace(/(<a id="source" href=")[^"]*/, `$1${source}`));
const licenses = writeLicenses(join(site, 'licenses'), { source });

const pk3 = readFileSync(join(site, 'base/opendojo.pk3'));
writeFileSync(join(site, 'base/manifest.json'), JSON.stringify([
	{ name: 'opendojo.pk3', size: pk3.length, version: createHash('sha256').update(pk3).digest('hex').slice(0, 16) },
]));
if (args.server) {
	const relay = args.relay ?? `wss://${args.server.split(':')[0]}/relay`;
	writeFileSync(join(site, 'config.json'), JSON.stringify({ server: args.server, relay }));
}

console.log(`site/build: ${site}${args.server ? `, joining ${args.server}` : ', no server configured'}, ${licenses} licenses`);
