# 003 — Four new stories, two new villagers, host changes
Status: Ready     Builds on: docs/new-stories-review.md, docs/asbab-stories.md, docs/001-characters-v3.md, docs/002-coins-and-world-cleanup.md

Executor: Gemini 4 Neon (High). Reviewer: Claude Opus 5.5 (also reviews the religious content).

## 1. Goal
Grow the game from 18 to 22 stories and bring in the two new villagers built in 001:
**Sheikh Younis** (`sheikh`, the village teacher) and **Aunt Salma** (`aunt`, keeps the orchards).
Also hand two existing stories to them so the new faces appear early. Children (6–11) are the
audience; Arabic is Modern Standard Arabic, simple and warm, with English and Russian.

## 2. Stack
Data only (JSON) plus the reviewer sheet. No code changes except the ones listed in §3.

## 3. Structure — files you may change
```
public/data/encounters.json        4 new encounters, 2 host changes
docs/new-stories-review.md         NOT yours — do not edit (the reviewer updates it)
```
Nothing else. (`ui.js` SURAHS already covers all 114 surahs after 002.)

## 4. The two new characters (copy these blocks exactly into each story's `characters`)
```json
{ "id": "sheikh", "name": {"ar":"الشيخ يونس","en":"Sheikh Younis","ru":"Шейх Юнус"},
  "role": {"ar":"معلّم القرية","en":"The Village Teacher","ru":"Учитель деревни"},
  "look": {"robe": 9409080, "inner": 15724527, "skin": 10251080, "beard": 12632256, "headwear": "turban", "cloth": 16777215, "staff": false, "height": 1.76},
  "model": "models/sheikh.glb", "position": [X, Z], "facing": F, "pose": "stand", "yOffset": 0 }
{ "id": "aunt", "name": {"ar":"الخالة سلمى","en":"Aunt Salma","ru":"Тётя Сальма"},
  "role": {"ar":"صاحبة البستان","en":"The Orchard Keeper","ru":"Хозяйка сада"},
  "look": {"robe": 13148000, "inner": 15329767, "skin": 11036482, "beard": null, "headwear": "hijab", "cloth": 12609136, "staff": false, "height": 1.58},
  "model": "models/aunt.glb", "position": [X, Z], "facing": F, "pose": "stand", "yOffset": 0 }
```
Speaker ids in steps are `sheikh` and `aunt`.

## 5. Rules for the content (non-negotiable)
- Never depict, voice or quote-as-dialogue any prophet, companion, or Maryam. Villagers narrate
  ABOUT them; Quranic words appear only as short quotes inside «» that match the Mushaf exactly,
  and as `verses` steps (text/audio come from Quran.com at runtime).
- Only what the Qur'an and sahih hadith state. No invented details (names of the whale, number of
  sleepers' dog details beyond the Qur'an, etc.). When the Qur'an mentions a disputed detail
  (e.g. the number of the sleepers, 18:22), say Allah knows best, as the Qur'an itself does.
- Honorifics: «عليه السلام» after prophets' names; «ﷺ» for the Prophet Muhammad.
- Each story has a `_note` (English) listing what was left out for children and why, and
  `sources` (Qur'an refs with ranges, tafsir Ibn Kathir / al-Muyassar, sunnah.com links for any
  hadith).
- Arabic: fusha, short sentences, harakat only where needed for correct reading of a key word.

## 6. Shape of each new story (follow the existing encounters exactly)
Same keys and order as `nuh-and-the-ark`: id, category, order, area, requires, title{ar,en,ru},
host, characters[], stage{distance,talkRadius}, player, objective{ar[],en[],ru[]}, greeting,
after, sources, _note, steps[], reward{points:50,ar,en,ru}, narration{ar,en,ru}.
Steps: 10–16 total, mixing `say`, `choice` (player asks; options with `reply` arrays),
exactly one `verses` step, 2 `question` steps (3 options, one `correct: true`, with `hint`),
ending with a lesson `question` then `{"type":"reward"}`. Every text has ar, en and ru.
`scene` keys on steps: use only scene names that already exist in `src/game/ui/scenes.js` or
`public/illustrations/*.webp`; if none fits, omit `scene`.

## 7. The four stories
| id | category / order | requires | area | hosts | verses step | core of the story |
|---|---|---|---|---|---|---|
| `yunus-and-the-whale` | prophets / 6 | `muhammad-the-trustworthy` | fields (riverbank) | sheikh + farmer | 21:87–21:88 | Yunus leaves his people, the ship, the whale, his du'a «لا إله إلا أنت سبحانك إني كنت من الظالمين», Allah saves him; 37:139–148 (the plant, his people believed). Lesson: turn to Allah in every hardship. |
| `sulayman-and-the-ant` | prophets / 7 | `yunus-and-the-whale` | oasis orchards | aunt + amina | 27:18–27:19 | Sulayman's army, the ant warns the ants, Sulayman smiles and thanks Allah. Lesson: care for small creatures; thank Allah for blessings. |
| `companions-of-the-cave` | quran / 10 | `the-guest-and-the-lamp` | mountains (hills) | sheikh | 18:10–18:10 | Young believers flee to the cave, Allah makes them sleep for years, they wake; 18:9–26. Number/years: as the Qur'an states (309 years, 18:25) and that Allah knows best their number (18:22). Lesson: hold to faith, Allah protects. |
| `luqman-wisdom` | quran / 11 | `companions-of-the-cave` | village | aunt + grandma (Zainab, id `grandma`, model `models/grandma_zainab.glb`, pose `sit` only if placed on a bench — otherwise use `amina`) | 31:17–31:18 | Luqman's advice to his son (31:13–19): no shirk, gratitude to parents, prayer, enjoin good, patience, no arrogance, walk modestly, lower the voice. Lesson: good manners. |

Positions: pick spots inside the listed area that are open walkable ground (not water, not
inside a house, ≥ 15 m from any other story's host, ≥ 2.5 m between a story's own characters),
characters facing the approach path. Verify each spot in the running game (see §10).

## 8. Host changes to existing stories
- `best-dates` (orchard, oasis): replace `hamdan` with `aunt` — swap the character block and
  change every `"speaker": "hamdan"` in that story to `"aunt"`. Re-read every line she now says:
  fix grammatical gender in Arabic (the speaker is now a woman: e.g. «كنتُ» stays, but
  adjectives/participles about herself must be feminine) and in Russian.
- `the-new-qibla` (ruins): replace `farmer` with `sheikh` the same way (male → male, only
  names/roles change; fix any line that says «جدّك» / grandpa about the speaker).
- Keep positions of these characters as they are.

## 9. Tasks
1. Read `public/data/encounters.json` fully for two stories (`nuh-and-the-ark`, `best-dates`) and
   `docs/new-stories-review.md` §intro to absorb tone and structure.
2. Write the 4 stories (one at a time), then the 2 host changes.
3. Validate JSON (`python3 -m json.tool public/data/encounters.json > /dev/null`).
4. Run the acceptance checks.

## 10. Acceptance checks
- JSON valid; every step text has `ar`, `en`, `ru`; every `speaker` in a story is in that
  story's `characters` or is `player`; orders inside each category are 1..N without gaps.
- `npm run build` exits 0.
- In headless Chromium (as in docs/002 §10): `__game.begin()`, then for each new id
  `__game.chooseStory(id)` and `__game.coins.ensure(id); __game.balance().find(r => r.id === id)`
  → `reached: true`, `coins >= 20`, `notWalkable: 0`. Screenshot each new host location once
  (teleport: `__game.player.pos.set(x, y, z)` near the host) and look at it: hosts stand on
  ground, not in walls/water.

## 11. Out of scope
No code, no audio, no illustrations, no edits to existing story texts other than §8.
Do not commit or push.

## 12. Decisions
