# Open Dojo

Free multiplayer sword fighting in the browser. Open the page, type a name,
PLAY: no install, no account, no game to buy.

Open Dojo runs [JK2MV](https://github.com/mvdevs/jk2mv), the open source
engine for Jedi Knight II multiplayer, compiled to WebAssembly, with its GPL
game code ([MVSDK](https://github.com/mvdevs/mvsdk)): the same movement,
saber combat and netcode. Everything the game shows and plays is made for
this project: the map, the character and its animations, textures, sounds,
menus and text, in a 2.4 MB asset pack. **No files from the commercial game
are used.** See [ASSETS.md](ASSETS.md) for where every file comes from.

It started as a proof of concept inside [jk2web](https://www.jk2web.com),
which plays the original game with files the player owns:
[REPORT.md](REPORT.md) has the findings. Open questions for legal review
are in [LEGAL.md](LEGAL.md).

## Quick start (macOS)

```sh
brew install cmake emscripten node python glib libxml2 jpeg-turbo libpng assimp minizip
git clone --recursive <this repository> opendojo
cd opendojo
npm install

./build.sh                    # the engine, the game code, the asset pack, the site
./test-server.sh              # a game server on UDP 28170 (in its own terminal)
npm start                     # http://localhost:8090/
```

Open http://localhost:8090/ in Chrome and PLAY. Click the game for the
mouse; Esc opens the in-game menu (join, watch, add or remove a bot, leave).
WASD moves, the left button attacks, the middle button (or L) changes saber
stance, space jumps, Shift+` opens the console. Two tabs or browsers are two
players. `?dev=1` makes the engine report every file it doesn't find (Debug
panel).

## Building

`./build.sh` builds everything into `build/` (git-ignored):

1. **The engine** (`./build-engine.sh`): the browser build,
   `build/web/out/Release/jk2mvmp.{js,wasm}`, and the native dedicated
   server, `build/native/out/Release/jk2mvded`, with CMake and Emscripten.
2. **The game code**: MVSDK's QVMs (cgame, ui, jk2mpgame) from the
   `src/mvsdk` submodule with `patches/mvsdk.patch`, compiled with MVSDK's
   own lcc/q3asm.
3. **q3map2**, from NetRadiant-custom, to compile the map (once).
4. **The asset pack**, `build/pack/opendojo.pk3`, by `generator/build_pack.py`
   (Python, NumPy, Pillow, in `build/venv`).
5. **The static site**, `build/site/`: the page, the engine, the pack and the
   license texts (`site/build.mjs`).

Later runs reuse what's built. `generator/preview.py BOTH_A2_T__B_ ...` draws
animations from the built pack to PNG contact sheets, the way the engine
reads them.

## Testing

With the test server started with cheats, so the test can place the players
face to face, and `npm start` running:

```sh
OPEN_CHEATS=1 ./test-server.sh
node test/play.mjs --clients 2 --script fight --server-log build/test-server.log   # two players fight
node test/play.mjs --clients 1 --script bots --server-log build/test-server.log    # bots, stances
node test/play.mjs --clients 1 --script combo                                      # red stance chains
```

Each client is a new Chrome profile (Playwright with the installed Chrome).
Screenshots, console logs, the requests each page made and a summary go to
`build/test-results/`. The summary lists the saber kills from the server's
log.

`test/isolation.mjs` is for serving Open Dojo under another site's `/open`,
such as jk2web's. `test/site-server.mjs --main <that site's build>` serves both
on one origin; the test checks that neither touches the other's storage.

## Layout

| Path | What it is |
| --- | --- |
| `src/`, `libs/`, `CMakeLists.txt`, `tools/`, `patches/gl4es/`, `res/` | The engine: JK2MV with jk2web's browser support (`src/web/`), and the changes for Open Dojo (see `git log`) |
| `src/mvsdk/` | The game code (submodule, MVSDK) |
| `libs/gl4es/` | OpenGL 1.x on WebGL (submodule) |
| `patches/mvsdk.patch` | Open Dojo's changes to the game code: the pack's names, and players may add bots |
| `generator/` | The asset pack's generators: map, textures, fonts, strings, skeleton and animations, meshes, effects, sounds, bots |
| `pack/` | Hand-written pack files: default config, shaders, menus |
| `pack-src/` | Generator inputs: the two OFL fonts (with their licenses), placeholder shader names |
| `web/` | The page |
| `site/` | The static site build and its licenses page |
| `server/` | `dev.mjs` (local server), `relay.mjs` (WebSocket to UDP relay), `server.cfg` (the game server's settings) |
| `test/` | Browser tests |

## How it works

```
static site ─────────────────────── page, jk2mvmp.wasm, opendojo.pk3, config.json, licenses/
browser (jk2mvmp.wasm) ──wss──▶ relay.mjs ──UDP 127.0.0.1──▶ jk2mvded (opendojo.pk3)
```

- **Engine**: JK2MV for `wasm32`, rendering through gl4es to WebGL 2.
  Browsers can't send UDP, so `src/web/net_web.cpp` sends each packet over
  a WebSocket to `server/relay.mjs`, which forwards it to the game server
  next to it. The engine changes for Open Dojo: start without the game's
  files, host JK2 1.04 rules (whose red stance chains attacks), and use the
  pack's model and font names.
- **Game code**: MVSDK's cgame, ui and game modules, run as QVMs from the
  pack. The server's game module also lets players add bots
  (`addbot`/`removebot`, up to `g_openBots`).
- **The pack**: everything is generated or written here (see ASSETS.md).
  The player model is a Ghoul2 skeleton with procedural animations for
  every animation the game code knows. Saber moves follow MVSDK's own table
  of saber moves, because the server animates every player to trace the
  blade: the skeleton is part of the combat rules. REPORT.md lists the
  Ghoul2 conventions this depends on.
- **The page** (`web/`) downloads the pack (kept in the Cache API cache
  `opendojo`), starts the engine and joins the server in `config.json`,
  straight into the game. It sets the game's fallback Force setup (all three
  saber stances) and the middle mouse button for stances, since the pack
  has no Force or key menus.

## Deploying

Not deployed yet. Two parts:

1. **The game server**, on any small Linux machine:
   - `build/native/out/Release/jk2mvded` with a base folder holding only
     `opendojo.pk3` and `server/server.cfg`, as `test-server.sh` does, on
     UDP 28170, `dedicated 1`, without cheats.
   - `node server/relay.mjs --port <port> --game 127.0.0.1:28170` next to
     it, behind https (Caddy, for example) at `/relay` (and `/status`).
2. **The site**: publish this repository's source first, then
   `node site/build.mjs --server <host>:28170 --relay wss://<host>/relay --source <source url>`
   and serve `build/site/` from any static host, at a domain's root or
   under a path.

   `.github/workflows/deploy.yml` does this on every push to main: it runs
   `./build.sh` on GitHub and deploys `build/site/` to Vercel, with the
   source link at the pushed commit (`vercel.json` turns off Vercel's own
   builds, which can't build this). It needs, in the repository's settings:
   - the secrets `VERCEL_TOKEN` (an account token), `VERCEL_ORG_ID` and
     `VERCEL_PROJECT_ID` (from `.vercel/project.json` after `vercel link`);
     without them it builds but doesn't deploy
   - the variable `OPENDOJO_SERVER` (`<host>:28170`), and `OPENDOJO_RELAY`
     if the relay isn't at `wss://<host>/relay`; without it the page says it
     has no server

Before publishing, read [LEGAL.md](LEGAL.md).

## License and credits

Open Dojo is licensed under the GNU GPL v2, like JK2MV (see `LICENSE`). The
site carries the license texts of everything it distributes at `licenses/`.

- [JK2MV](https://github.com/mvdevs/jk2mv) and
  [MVSDK](https://github.com/mvdevs/mvsdk) by the JK2MV developers, based on
  the Jedi Knight II source code released by Raven Software under the GPLv2.
- [jk2web](https://www.jk2web.com): the browser port of JK2MV this builds on.
- [gl4es](https://github.com/ptitSeb/gl4es) by ptitSeb (MIT), SDL 2 (zlib),
  zlib, libpng, libjpeg, minizip, Emscripten.
- [q3map2](https://github.com/Garux/netradiant-custom) (GPLv2), to compile the
  map.
- Fonts: [Exo 2](https://github.com/googlefonts/Exo-2.0) and
  [Share Tech Mono](https://fonts.google.com/specimen/Share+Tech+Mono)
  (SIL Open Font License).

Not affiliated with or endorsed by any game publisher or film studio.
