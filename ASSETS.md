# The open asset pack: what's in it and where it comes from

`build/pack/opendojo.pk3` is built by `generator/build_pack.py`. It
contains **no files from Jedi Knight II: Jedi Outcast**, from JK2MV's
`assetsmv*.pk3`, or from any other game or mod. Each entry below is one of:

- **Generated**: made by a script in `generator/` from code and numbers,
  with no input files. Written for this project; same license as the
  repository (GPLv2).
- **Written**: a text file in `pack/` written for this project
  (GPLv2).
- **Third party**: listed with its source, author and license.

| Files in the pack | Kind | Made by / source | License | Notes |
| --- | --- | --- | --- | --- |
| `vm/cgame.qvm`, `vm/ui.qvm`, `vm/jk2mpgame.qvm` | Third party (code) | Compiled from [MVSDK](https://github.com/mvdevs/mvsdk) at the submodule's commit (`src/mvsdk`, 4c7c463) with MVSDK's bundled lcc/q3asm. cgame and ui are unmodified; jk2mpgame (the server's) has `patches/mvsdk.patch` (players may add bots) | GPLv2 | The JK2 game code released by Raven Software under the GPLv2, maintained by the JK2MV developers. Source: the MVSDK repository at that commit, plus the patch. |
| `ui/jk2mp/menudef.h` | Third party (code) | MVSDK `code/ui/menudef.h`, unmodified | GPLv2 | Menu constants the UI code reads. |
| `maps/open_dojo.bsp` | Generated | `tools/arena.py` writes the map source, compiled with q3map2 from [NetRadiant-custom](https://github.com/Garux/netradiant-custom) | GPLv2 (the map) | q3map2 (GPLv2) is a build tool only; its output carries no license of its own. |
| `textures/open/*.jpg` | Generated | `tools/textures.py` (procedural noise and patterns) | GPLv2 | |
| `shaders/open_map.shader`, `shaders/open_ui.shader` | Written | `pack/shaders/` | GPLv2 | Shader names `white`, `console` and `textures/common/*` are names the engine and compiler expect. |
| `shaders/open_effects.shader`, `gfx/effects/**`, `gfx/2d/crosshair*.tga` | Generated | `tools/effects.py` | GPLv2 | Saber blades, glows, crosshairs. |
| `shaders/open_placeholders.shader` | Generated | `tools/effects.py` from `pack-src/placeholders.txt` | GPLv2 | Invisible stand-ins. The list holds only shader *names* the GPL code registers (from a run of the game), no content. |
| `fonts/{open_small,open_medium,open_large}*.{fontdat,tga}` | Generated from third-party fonts | `tools/fonts.py` renders bitmap fonts from the two fonts below | SIL OFL 1.1 | The game code's font names are changed to these by `patches/mvsdk.patch` and the engine changes (see `git log`). The fonts' licenses are in the pack, `fonts/licenses/`, and on `licenses/`. |
| (font source) `pack-src/fonts/sharetechmono-ShareTechMono-Regular.ttf` | Third party | [Share Tech Mono](https://github.com/google/fonts/tree/main/ofl/sharetechmono), Carrois Type Design, Ralph du Carrois | SIL OFL 1.1, Reserved Font Name "Share" | Not in the pack itself; only the rendered bitmaps are, under other names (allowed for a Modified Version, which must not use the reserved name). |
| (font source) `pack-src/fonts/exo2-Exo2[wght].ttf` | Third party | [Exo 2](https://github.com/google/fonts/tree/main/ofl/exo2), The Exo 2 Project Authors | SIL OFL 1.1 | Not in the pack itself; bitmaps rendered from it are. |
| `gfx/2d/charsgrid_med.tga` | Generated from Share Tech Mono | `tools/fonts.py` | SIL OFL 1.1 | The console's character grid. |
| `gfx/open/console.tga`, `ui/open/cursor.tga` | Generated | `tools/ui.py` | GPLv2 | |
| `ui/jk2mpmenus.txt`, `ui/jk2mpingame.txt`, `ui/open/*.menu` | Written | `pack/ui/` | GPLv2 | A minimal menu set (main, in-game, error). |
| `strip/*.sp` | Generated | `tools/strings.py` | GPLv2 | English text written for this project. Which references exist comes from the GPL code; references without written text get a readable version of their name. |
| `mpdefault.cfg` | Written | `pack/` | GPLv2 | Default keys and settings. |
| `mv.info` | Written | `pack/` | GPLv2 | Tells JK2MV the pack works with every game version. |
| `models/players/_humanoid/_humanoid.gla`, `animation.cfg` | Generated | `tools/skeleton.py`, `tools/model.py` | GPLv2 | Skeleton and 2,848 frames of procedural animation. Bone and animation *names* follow the GPL game code. |
| `models/players/open/model.glm`, `model_{default,red,blue}.skin`, `body_*.jpg`, `icon_default.jpg` | Generated | `tools/model.py` | GPLv2 | A box-built humanoid, the default model (renamed from the code's original default by `patches/mvsdk.patch`). |
| `models/weapons2/saber/saber_w.glm`, `saber_w.jpg` | Generated | `tools/model.py` | GPLv2 | The saber hilt and the tag its blade comes out of. |
| `models/map_objects/mp/{medpac,psd_sm,psd}.md3`, `open_*.jpg`, `gfx/hud/i_icon_medkit.tga`, `gfx/mp/{small_shield,large_shield}.tga` | Generated | `generator/items.py` | GPLv2 | Original health and shield pickup shapes, textures and HUD icons. Legacy paths are required by the game code's item definitions. |
| `botfiles/bots.txt`, `botfiles/open.jkb`, `botroutes/open_dojo.wnt` | Generated | `tools/bots.py` | GPLv2 | Bot names made up for the pack; waypoints computed from the map's layout. |
| `sound/**/*.wav` | Generated | `tools/sounds.py` (synthesized with NumPy) | GPLv2 | Saber hum, swings, clashes, footsteps, wordless grunts, pickup tones. |

Build-time tools, none of them in the pack: Python 3, NumPy (BSD), Pillow
(MIT-CMU), q3map2 (GPLv2), Emscripten (MIT/UIUC), CMake. Test-only:
Playwright (Apache 2.0) driving the installed Google Chrome.

## What the site distributes besides the pack

| File | What it is | License / source |
| --- | --- | --- |
| `jk2mvmp.js`, `jk2mvmp.wasm` | JK2MV built for the browser, from this repository's commit plus the engine changes (see `git log`) | GPLv2. JK2MV (mvdevs) is based on the JK2 source code Raven Software released under the GPLv2; gl4es (MIT), SDL2 (zlib), zlib, libpng, libjpeg, minizip are linked in. |
| `index.html`, `main.js`, `licenses/` | The page | GPLv2, this repository |

## Open questions for review (not legal advice)

- **Names from the original game.** The pack and the code it runs no longer
  use the original default model's or fonts' names, and the game type names
  shown on screen are neutral ("Master Duel", "Relic FFA", "Capture the
  Item"). What remains are internal identifiers that players don't see:
  cvar names (`g_jediVmerc`, `g_maxHolocronCarry`), server info keys
  (`truejedi`), file paths the code asks for (for example
  `gfx/hud/w_icon_lightsaber`, which the pack fills with an invisible
  placeholder), animation and string reference names. See `LEGAL.md`.
- **Words in the game code.** The GPL game code still has its own text in
  places: game type names (for example "Jedi Master"), force power names
  and holocrons. The pack's strings avoid Star Wars terms, and the test
  server overrides the default team names ("Empire", "Rebellion"). An audit
  of every string the code itself prints was not done.
- **The JK2 SDK release.** MVSDK and JK2MV rest on Raven's GPLv2 source
  release. That covers the code, not the game's data, which is why none
  of it is used.
- **"Lightsaber" as a mechanic.** The pack contains no Star Wars logos,
  characters, models, music or sounds. Whether a glowing-blade sword fight
  raises trade dress concerns is a question for counsel, not for this POC.
