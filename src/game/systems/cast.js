// Encounter cast. An encounter may list several `characters` (a multi-speaker scene) or,
// as older data does, a single `character`. Both are normalised here, once, at load:
//   enc.characters  [{ id, name, role, look, model, position:[x,z], facing, pose:'stand'|'sit', seat, yOffset }]
//   enc.host        id of the character who greets, carries the marker and speaks by default
//   enc.character   the host's definition (kept for code that shows "who told this story")
export function normalizeEncounters(data) {
  for (const e of data.encounters) {
    if (!Array.isArray(e.characters) || !e.characters.length) e.characters = [{ id: 'main', ...e.character }];
    e.characters.forEach((c, i) => { c.id ??= i ? `npc${i}` : 'main'; c.pose ??= 'stand'; });
    if (!e.characters.some(c => c.id === e.host)) e.host = e.characters[0].id;
    e.character = e.characters.find(c => c.id === e.host);
  }
  return data;
}
export const PLAYER_ID = 'player';
