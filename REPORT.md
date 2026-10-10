# Open Dojo: proof of concept report

Open Dojo began as a proof of concept inside jk2web (served at its `/open`
path) answering one question: can JK2 Web's multiplayer run with **no Jedi
Outcast files at all**, on the same engine and game code with an asset pack
made for it? This is that report, with paths changed to this repository's
layout. The engine changes listed as the engine changes (see `git log`) back then are now
commits on the engine source here (see `git log`), and the bot and naming
changes to the game code are `patches/mvsdk.patch`.

**Result: it works.** Two fresh browser profiles open the page, download
the free pack automatically, join a test server, see each other and fight
with JK2's own saber combat: hits, kills, parries, chained attacks, bots.

## Validation

Run on macOS (Apple Silicon), Chrome, against the POC's test server on the
same machine, with the static site build served at `/open` next to an
unmodified build of the main site (`test/site-server.mjs`, the
production layout: one origin).

**POC** (`test/play.mjs --clients 2 --script fight --server-log …`,
server started with `OPEN_CHEATS=1` so the test can place the players face
to face):

- Two browsers with new, empty profiles each load `/open`, download the pack
  and reach the game (client state `CA_ACTIVE`): **pass**.
- Requests made by each browser: `/open/`, `/open/main.js`,
  `/open/jk2mvmp.js`, `/open/jk2mvmp.wasm`, `/open/config.json`,
  `/open/base/manifest.json`, `/open/base/opendojo.pk3`, and the relay's
  `/status`. Nothing else, no game files: **pass**.
- Both players spawn and see each other (screenshots), move, and fight. The
  server logs `Tester1 killed Tester2 by MOD_SABER` and the reverse: saber
  damage is computed by the server's game code from the new skeleton.
  **pass**.
- With a temporarily instrumented game module (not shipped), one 40 second
  fight logged 29 parries (top, upper and lower, both sides), bounces,
  deflections and 20+ different saber moves: blocking works too.
- Combos: the test server hosts 1.04, like the main one. Holding attack
  with a direction in red stance chains attacks (attack, transition,
  attack, then return), per the server's log of saber moves; on 1.02 the
  same input returned after every attack.
- Stances: `saberAttackCycle` (middle mouse button) goes fast, medium,
  strong (HUD screenshots). The page gives players the game's own fallback
  Force setup, with saber offense 3: there is no Force menu in the pack.
- Bots (`play.mjs --script bots`): a player adds two bots with the menu's
  command, they spawn, walk the generated waypoints and fight: the server
  logged bot kills on each other and on the player.
- From PLAY to in-game: about 2 s with the pack cached, locally.
  Frame rate: about 118 fps (the display's) in headed Chrome, one client.

**Isolation and the main application** (`test/isolation.mjs`, all
pass):

- The main page loads, before and after using `/open`, in the same profile.
- Markers left in the main page's storage (localStorage `name`, Cache
  `jk2web-base`, OPFS `jk2-base`, IndexedDB `/home`) are unchanged after
  playing on `/open`.
- `/open` keeps to its own storage: localStorage `opendojo.*`, Cache
  `opendojo`, IndexedDB `/opendojo-home`, nothing in OPFS.
- `/open` joins again after a reload (storage not corrupted).
- A failed pack download says so ("Couldn't download opendojo.pk3 (HTTP
  503).") and PLAY works again.
- While it lived inside jk2web: jk2web's own site build still succeeded,
  its engine builds were not touched, and `git status` there showed only
  the POC's folder. Now it is this separate repository, and jk2web is back
  to how it was.

**Not tested:**

- Importing real game files on the main page. No Jedi Outcast files exist
  on this machine. The main page's code is unchanged, and the storage it
  uses is untouched (above).
- Real players over the internet, other browsers than Chrome, sound
  (headless runs are muted), saber locks, force powers.

**Separation:** Open Dojo now lives in its own repository, with its own
copy of the engine; jk2web doesn't refer to it.

## Feasibility report

### Technical results

- **Does JK2MV run without proprietary JK2 assets?** Yes. With two small
  engine changes, the engine, renderer, UI, cgame and server all run on the
  free pack:
  - don't require a file named `assets5.pk3` to start;
  - host the version `mv_serverversion` asks for (1.04 by default) even
    without the game's `assets2.pk3`/`assets5.pk3`.

  Without the second change, JK2MV falls back to 1.02, whose rules differ
  from the main server's 1.04: red stance barely chains attacks there, so
  combos like right-right-diagonal didn't work.
- **Minimum replacement assets** (see [the inventory](#phase-3-asset-inventory)):
  a default config, 8 string packages, 3 QVMs (GPL), fonts under 3 fixed
  names, a menu set, a map, the player skeleton with every animation the
  code checks for, a player mesh with 3 tags, a saber model with its tag,
  saber blade shaders. Everything else is optional.
- **Engine modifications:** only the engine changes (see `git log`) (the two changes
  above), in the POC's own build. Game code: cgame and ui are MVSDK's own, unmodified. The server's
  game module has one small addition (`patches/mvsdk.patch`), so players can
  add bots from the menu: on a dedicated server, `addbot` is a server
  console command only. Combat code is untouched.
- **Does the original combat system work?** Yes, the code is the original:
  attacks, chains, parries, bounces, damage, all computed by MVSDK from the
  generated animations. How it *feels* depends on those animations, which
  are procedural and simple. Hit areas, swing timing and block poses are
  approximations of JK2's, not copies. Tuning them is the main remaining
  work.
- **Main technical lessons:** the skeleton is part of the combat rules,
  because the server animates every player to trace the blade. Several
  undocumented Ghoul2 conventions had to be matched:
  - models face -Y (the engine's "identity" root matrix turns them +90°);
  - the saber blade runs along -X of the `*flash` tag's frame;
  - a `Motion` bone with -Y forward is read by the 1.02 spine code, and it
    must be used by some surface, or Ghoul2 leaves it uncomputed and the
    torso turns 180° on the server;
  - `ofsSurfHierarchy` must point at the first entry, not the table;
  - `.fontdat` files must be 7180 bytes, not 7178.
- **Remaining limitations:**
  - The character and animations are placeholders (box-built, procedural).
  - The HUD is the code's text HUD. There are no force power effects, no
    blood or sparks beyond the saber glow, and no menu art.
  - One map (with generated bot routes; bots play, simply).
  - The page has no player customization.
- **Standard JK2 servers:** no. The free client can connect to them, but
  has none of their maps or models, and pure servers would refuse it.
- **Original players on the free server:** possible in principle (same
  protocol, same animation numbers, `sv_pure 0`, the pack as a download),
  not tried. Their own Kyle model's animations would not match the hit
  areas the server computes from the free skeleton, which would make hits
  look wrong to them.
- **Download size:** the pack is 2.4 MB, plus the engine (3.2 MB wasm,
  0.4 MB JS, both compressible). About 6 MB on the first visit, cached
  afterwards. The main page needs about 620 MB of the player's game files.
- **Performance:** like the main page. The QVM interpreter costs the same.
  The scene is simpler than JK2's maps.

### Legal and licensing considerations

Not legal advice. The open questions for counsel, and what was done so far,
are in [`LEGAL.md`](LEGAL.md). In short:

- **Included assets:** everything in `ASSETS.md`. All of it is either
  generated by this project's scripts, written for it, GPL code (MVSDK
  QVMs, `menudef.h`), or bitmaps rendered from two SIL OFL fonts (Exo 2,
  Share Tech Mono).
- **Original JK2 resources:** none are used, fetched or bundled.
- **Names and text:** the original default model's and fonts' names are
  replaced in the POC's builds, and the text players see is neutral
  (no Star Wars terms). The free mode has a neutral working name, "Open
  Dojo". Internal identifiers from the game code remain.
- **GPLv2:** `licenses/` carries the license texts of the engine,
  the libraries built into it, the game code and the fonts. The page links
  to the source code (`node site/build.mjs --source <url>`), which must be
  published, at the deployed commit, before the site goes live.
- **For counsel:** the look and sound of the blades, serving the free mode
  from a JK2-named domain, the original's gameplay mechanics, identifiers
  left in the code, and an unused header with a third-party copyright line
  in the engine's MP3 decoder (the decoder itself is GPLv2).

### Recommendation: Partially viable

The technical question is answered: free-assets multiplayer with JK2's own
engine, netcode and combat works in the browser today, at a fraction of the
download. What keeps this from "viable" are not blockers but real work:

1. **A real character and animation set** (the largest item). Combat feel
   in JK2 lives in the animations: swing arcs, timing, block poses, saber
   locks, acrobatics. The procedural set proves the pipeline. A proper set
   needs an animator (Blender with a GLA exporter, or keep generating with
   much more care), probably several weeks.
2. **Polish for players:** HUD art, force power effects, hit effects,
   menus (a Force setup menu, key bindings), a second map. About 1 to 2
   weeks.
3. **Legal review** of the points above, and a decision on the fixed
   names (keep them for compatibility, or patch the game code and accept
   a free-only client).
4. **Deployment** (below), about 1 day once approved.

Estimated remaining effort: about 4 to 8 weeks of focused work, mostly
animation and art, plus legal review.

## Phase 3: asset inventory

What the engine and game code ask for, from running the POC's server and
client on an empty file system (`?dev=1` lists the misses) and from the
code. Formats are JK2's.

| Resource | Format | Status |
| --- | --- | --- |
| A file named `assets5.pk3` | — | Required by the engine to start, and to host 1.04 (`assets2.pk3` for 1.03); **engine patch** removes both checks |
| `mpdefault.cfg` | text | Required (fatal without it) |
| `strip/con_text.sp`, `mp_ingame.sp`, `mp_svgame.sp`, `sp_ingame.sp`, `str_server.sp` | StripEd text, fixed package IDs for `con_text` (3) and `str_server` (1) | Required (fatal without them); others optional |
| `vm/cgame.qvm`, `vm/ui.qvm`, `vm/jk2mpgame.qvm` | QVM bytecode | Required; built from MVSDK (GPL); the pak needs `mv.info` saying `compatible all` or 1.02 servers won't load them |
| `ui/jk2mpmenus.txt`, `ui/jk2mpingame.txt` + menus | menu script | Required by ui (ERR_DROP without them) |
| `fonts/{ocr_a,ergoec,anewhope}.fontdat` + images (renamed `open_small`, `open_medium`, `open_large` in the POC's builds) | 7180-byte glyph table + TGA | Required for any text; replaceable |
| `gfx/2d/charsgrid_med` | 16x16 glyph grid image | Console text; replaceable |
| `maps/*.bsp` | Raven BSP v1 (q3map2 `-game jk2`) | Required |
| `models/players/_humanoid/_humanoid.gla` | Ghoul2 skeleton v6 | Required by client and **server**; bone names fixed by code |
| `models/players/_humanoid/animation.cfg` | text, under 40,000 bytes | Required; every animation from `BOTH_A1_T__B_` to `BOTH_H1_S1_BR`, `BOTH_DEATH1-19` and `BOTH_DISMEMBER_*` must have frames or cgame rejects the model |
| `models/players/kyle/model.glm` + `model_default.skin` (`models/players/open/` in the POC's builds) | Ghoul2 mesh v6 | Required (path set by the game code); tags `*r_hand`, `*l_hand`, `*head_top`; bones `Motion`, `lower_lumbar` |
| `models/weapons2/saber/saber_w.glm` | Ghoul2 mesh with tag `*flash` | Required for the blade's position (server) |
| `gfx/effects/sabers/*_glow`, `*_line`, `saberBlur` | shaders | Optional, but the blade is invisible without them |
| `sound/weapons/saber/*`, footsteps, voices | WAV | Optional |
| ~270 HUD, effect and menu images | images/shaders | Optional (checkerboard without them); invisible placeholders |
| `botfiles/bots.txt`, `botfiles/*.jkb`, `botroutes/<map>.wnt` | text | Optional; needed for bots (generated) |
| `forcepowers` (a cvar, not a file) | `rank-side-18 levels` | The code's default has saber offense 0, which locks players in the fast stance; the pack sets the game's fallback setup |

## Phase 1: technical assessment (inside jk2web)

(Written before the implementation; the findings held. Later discoveries are
in the feasibility report.)

### How the current app works (relevant parts)

- **Engine**: JK2MV compiled with Emscripten (`src/`, browser code in
  `src/web/`), producing `jk2mvmp.js`/`.wasm`. Built by the top-level
  CMake (`emcmake cmake`, `BuildMVSDK=OFF`), rendering through gl4es to
  WebGL 2.
- **Game logic**: the cgame, ui and game modules are *not* built by the
  site. They are the QVMs inside the player's own `assets0.pk3`/`assets2.pk3`/
  `assets5.pk3`, run in the engine's QVM interpreter.
- **Files**: `web/main.js` writes the player's pk3s (from OPFS,
  `web/gamefiles.js`) and JK2MV's `assetsmv*.pk3` (Cache API,
  `jk2web-base`) into Emscripten's MEMFS at `/jk2/base`, and mounts IDBFS
  at `/home` for configs. localStorage keys: `name`, `fullscreen`,
  `gameFolder`; sessionStorage: `autoplay`.
- **Versions**: there's no picker. The game server decides: JK2MV hosts
  1.04 if `assets5.pk3` exists, 1.03 with `assets2.pk3`, otherwise 1.02
  (`sv_init.cpp`). The client takes the server's protocol (15 = 1.02,
  16 = 1.03/1.04).
- **Multiplayer**: `src/web/net_web.cpp` sends UDP packets over a
  WebSocket to `web/relay.mjs`, which forwards them to one game server
  (`jk2mvded`). The page joins with `+connect` and skips the menus.

### What the engine and game code need from the game's files

Found by reading the code and by running the POC's own dedicated server
on an empty file system:

- **Engine (hard requirements)**: a file named `assets5.pk3` must exist,
  or `FS_Startup` exits (`files.cpp`). Then `mpdefault.cfg`, and the
  string packages `strip/con_text.sp`, `mp_ingame.sp`, `mp_svgame.sp`,
  `sp_ingame.sp` (fatal if missing). With those, a stub `keynames.sp` and
  the QVMs, the dedicated server initialises completely.
- **Game code (QVMs)**: open source. MVSDK (GPLv2, the JK2 SDK code
  maintained by the JK2MV developers) builds `cgame.qvm`, `ui.qvm` and
  `jk2mpgame.qvm` with its own bundled lcc/q3asm, with no game files
  needed. So the game logic, movement and saber combat are available
  under the GPL.
- **UI**: `ui.qvm` needs a menu set (`ui/jk2mpmenus.txt` and the menus in
  it) or fails with "default menu file not found". cgame needs a HUD menu
  file and fonts (`fonts/*.fontdat` with an image per font).
- **Player model: the big dependency.** Players are Ghoul2 models
  (`.glm` mesh on a `.gla` skeleton). The *server's* game code loads
  `models/players/kyle/model.glm`, its skeleton
  (`models/players/_humanoid/_humanoid.gla`) and `animation.cfg`, and
  runs every player's animations on the server to find where the saber
  is: the blade starts at the `*flash` tag of `saber_w.glm`, bolted to the
  `*r_hand` tag of the player model (`w_saber.c`, `g_client.c`). Saber
  hits and blocks are traces along that blade. So the skeleton's
  animations *are* the combat hitboxes. The code also refers to bones by
  name (`model_root`, `pelvis`, `lower_lumbar`, `upper_lumbar`,
  `thoracic`, `cervical`, `cranium`, `rhumerus`, `rradius`, `rtibia`,
  `Motion`, …) and to animations by number, with frame ranges and speeds
  from `animation.cfg`. Attack timing comes from those animation lengths.
- **Maps**: Raven BSP (`RBSP` version 1). q3map2 (GPLv2, from
  NetRadiant-custom) compiles it with `-game jk2`.
- **Everything else** (sounds, effects, icons, most shaders and images)
  is looked up by name, and missing files fall back to defaults with a
  warning: optional.

### 1. What can be reused safely

- The engine source and its browser changes, *as a separate build*
  (a snapshot of the committed tree, built into `build/`).
- The relay protocol and `src/web/net_web.cpp` as they are.
- MVSDK's game code, built into QVMs from the pinned submodule commit,
  without this repository's patch for Claude's bot.
- The page's main loop, relay connection and join logic, *copied* into
  `web/` rather than imported, so the main page can change freely.

### 2. What must be replaced or modified

- **Engine**: one change for now, in a patch applied only to the POC's
  build (the engine changes (see `git log`)): don't require `assets5.pk3`.
- **All game content**: default config, string packages, fonts and a
  console font, a minimal menu set and HUD, shaders, a map, a player
  model with skeleton and animations, a saber model, saber shaders and
  sounds. All made for this project (generated by scripts in
  `generator/`), or under clear open licenses (fonts: SIL OFL).

### 3. Expected minimum resource dependencies

`mpdefault.cfg`; `strip/*.sp` (5 packages); 3 QVMs; fonts (`ocr_a`,
`ergoec`, `anewhope` names, used by the code) and `gfx/2d/charsgrey`;
`ui/jk2mpmenus.txt` and a few menus, HUD menu; one map
(`maps/<name>.bsp`); `models/players/kyle/model.glm`,
`models/players/_humanoid/_humanoid.gla` and `animation.cfg`, a skin;
`models/weapons2/saber/saber_w.glm` (and `.md3` view model); saber blade
shaders; a few sounds. Paths are fixed by the game code.

### 4. Architectural blockers

- None that stop the engine. The engine's only hard-coded file checks are
  cheap to patch.
- **The skeleton and animations are the main risk.** The combat code
  expects JK2's ~1,100 animation numbers with sensible lengths, and saber
  attacks moving along the 8 attack directions (top to bottom, left to
  right, …). A procedurally animated skeleton can map every animation
  number to a smaller set of generated motions, but hits, blocks and
  saber locks will only be as good as those motions.
- Bone *orientations* matter too: the code turns the torso and head with
  `SetBoneAngles` using axis conventions of the original skeleton.
- Path names like `models/players/kyle/` are hard-coded in the game code.
  They are file paths, not content, but they are kept here only because
  renaming them would mean changing the game code.

### 5. Isolation strategy

- POC code and asset sources: `open/` only. Build output: `build/open/`
  (git-ignored) only.
- Engine: `build-engine.sh` builds from `git archive HEAD` of this
  repository and its submodules into `build/src`, applies
  the engine changes (see `git log`) there, and builds into `build/web` and
  `build/native`. The working tree, `build/web`, `build/native` and
  `dist/` are not touched.
- Browser storage, separate from the main page on the same origin: its
  own Cache API cache (`opendojo`), its own IndexedDB (IDBFS mounted at
  `/opendojo-home`, so a different database name) and `opendojo.`-prefixed
  localStorage keys. It never reads OPFS, where the main page keeps the
  player's game files.
- Test server: a separate `jk2mvded` (the POC's build) on its own port,
  with its own base folder holding only the free pack.
- Removal: delete `open/` and `build/open/` (done: it moved to this repository).
