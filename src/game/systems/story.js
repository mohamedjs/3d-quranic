// Runs one data-driven encounter: say / choice / question / verses / reward steps.
// Multi-speaker: a step's `speaker` is a character id from enc.characters, or "player" for
// the child's own lines; it defaults to enc.host. The name tag follows the speaker, the
// speaking character plays its talk clip, and hooks.speaker(id) lets the camera follow.
// A choice option may carry `reply` (one line or a list, each with an optional speaker).
// Never gated on speech synthesis — every line waits for a tap, so a missing voice is harmless.
import { sceneSVG } from '../ui/scenes.js';
import { Voice } from './audio.js';
import { portrait } from '../ui/ui.js';

const box = () => document.getElementById('dialogue');
const $ = s => box().querySelector(s);

const YOU = { name: { ar: 'أنا', en: 'Me' }, role: { ar: '', en: '' } };

export class Story {
  constructor({ lang, hooks }) { this.lang = lang; this.hooks = hooks; }
  t(o) { return o?.[this.lang()] ?? o?.ar ?? ''; }

  // group: { setTalking(id|null) } — the encounter's cast plus the player
  async run(enc, group) {
    const d = box(); d.hidden = false; d.dir = this.lang() === 'ar' ? 'rtl' : 'ltr';
    $('.name').innerHTML = `<span class="portrait"></span><span class="nm"><small></small><b></b></span>`;
    delete d.dataset.lesson;
    this.enc = enc; this.group = group; this.speaker = undefined;
    requestAnimationFrame(() => d.classList.add('show'));
    try {
      for (const step of enc.steps) {
        if (step.type !== 'verses' && step.type !== 'reward') this.setSpeaker(step.speaker ?? enc.host);
        await this[step.type](step, enc);
      }
    } finally {
      Voice.cancel(); this.talk(false); this.scene(null);
      d.classList.remove('show'); setTimeout(() => { d.hidden = true; }, 400);
      this.enc = this.group = null;
    }
  }

  who(id) {
    if (id === 'player') return { ...YOU, ...this.enc.player };
    return this.enc.characters?.find(c => c.id === id) ?? this.enc.character;
  }
  setSpeaker(id) {
    if (id === this.speaker) return;
    this.talk(false); this.speaker = id;
    const w = this.who(id), tag = $('.name');
    $('.name small').textContent = this.t(w.role); $('.name b').textContent = this.t(w.name);
    box().dataset.speaker = id === 'player' ? 'player' : 'npc'; box().dataset.who = id;
    $('.name .portrait').innerHTML = portrait(id, w);
    tag.classList.remove('swap'); void tag.offsetWidth; tag.classList.add('swap');
    this.hooks.speaker?.(id);
  }
  talk(on) { this.group?.setTalking(on ? this.speaker : null); }

  scene(name) {
    const el = document.getElementById('scene');
    if (!name) { el.classList.remove('show'); el.dataset.name = ''; return; }
    if (el.dataset.name === name) return;
    const html = sceneSVG(name, this.lang());
    if (!html) { el.classList.remove('show'); el.dataset.name = ''; return; }   // no painting/SVG for this scene (yet)
    el.dataset.name = name; el.hidden = false;
    el.innerHTML = html;
    el.classList.remove('show'); void el.offsetWidth; el.classList.add('show');
  }

  // Types a line out; first tap finishes it, second tap continues.
  line(text, { wait = true } = {}) {
    const el = $('.text'), next = $('.next');
    this.stopLine?.();  // a hint may still be typing when the next line starts
    this.talk(true);
    const t0 = performance.now(), spoken = Voice.speak(text, this.lang()); this.lastSpoken = spoken;
    el.textContent = ''; next.hidden = true;
    let n = 0, full = false, finished = false, autoTimer = 0;
    return new Promise(resolve => {
      const timer = setInterval(() => { n += 2; el.textContent = text.slice(0, n); if (n >= text.length) complete(); }, 28);
      this.stopLine = () => { clearInterval(timer); clearTimeout(autoTimer); off(); };
      const complete = () => { clearInterval(timer); el.textContent = text; full = true; next.hidden = !wait; if (!wait) done(); };
      const done = () => { if (finished) return; finished = true; clearTimeout(autoTimer); off(); resolve(); };
      // Auto-advance: when the voice finishes (or, with no voice, after a comfortable reading
      // time) the dialogue moves on by itself. A tap still skips ahead at any moment.
      if (wait && this.autoAdvance !== false) {
        const readMs = Math.max(2200, 900 + text.length * 70);
        spoken.then(voiced => {
          if (finished) return;
          const left = voiced ? 650 : Math.max(0, readMs - (performance.now() - t0));
          autoTimer = setTimeout(() => { if (finished) return; if (!full) complete(); this.talk(false); done(); }, left);
        });
      }
      const advance = e => {
        if (e.type === 'keydown' && !['Space', 'Enter', 'KeyE'].includes(e.code)) return;
        if (e.type === 'keydown') e.preventDefault();
        if (!full) complete(); else if (wait) { this.talk(false); done(); }
      };
      const off = () => { $('.box').removeEventListener('click', advance); removeEventListener('keydown', advance); };
      $('.box').addEventListener('click', advance); addEventListener('keydown', advance);
    });
  }

  options(opts, onPick, auto = null) {
    const c = $('.choices'); c.innerHTML = '';
    return new Promise(resolve => {
      let settled = false; const finish = o => { settled = true; resolve(o); };
      const buttons = opts.map((o, k) => {
        const b = document.createElement('button');
        b.innerHTML = `<i>${k + 1}</i><span></span>`; b.querySelector('span').textContent = this.t(o);
        b.onclick = async () => { if (b.disabled) return; if (settled) return; if (await onPick(o, b)) { off(); c.classList.remove('show'); setTimeout(() => { c.innerHTML = ''; }, 250); finish(o); } };
        c.append(b); return b;
      });
      const key = e => { const k = +e.key - 1; if (buttons[k]) buttons[k].click(); };
      const off = () => removeEventListener('keydown', key);
      addEventListener('keydown', key);
      requestAnimationFrame(() => c.classList.add('show'));
      auto?.then(() => { if (!settled && buttons[0]) { buttons[0].classList.add('picked'); buttons[0].click(); } });
    });
  }

  // Wait until the current line's voice has finished (or a reading time when nothing is voiced).
  async spokenEnd(text) {
    const t0 = performance.now(), voiced = await this.lastSpoken;
    const readMs = Math.max(1200, 500 + text.length * 60);
    await new Promise(r => setTimeout(r, voiced ? 450 : Math.max(0, readMs - (performance.now() - t0))));
  }

  async say(step) { this.scene(step.scene); await this.line(this.t(step)); }

  // The prompt (optional) is spoken by the step's speaker; the options are the child's answers.
  // With speaker "player" the child is the one asking: the prompt ("Ask:") is shown quietly,
  // and the picked question is then said aloud as the child's line before the replies.
  async choice(step, enc) {
    this.scene(step.scene);
    const asking = step.speaker === 'player', prompt = this.t(step);
    if (prompt && !asking) await this.line(prompt, { wait: false });
    else { this.stopLine?.(); $('.text').textContent = prompt; $('.next').hidden = true; }
    // Auto-advance: after the prompt has been said, the child picks the first option himself,
    // so the conversation flows like a dialogue (quiz questions stay interactive).
    const auto = this.autoAdvance !== false
      ? (async () => { if (prompt && !asking) await this.lastSpoken; await new Promise(r => setTimeout(r, asking ? 600 : 900)); })()
      : null;
    const picked = await this.options(step.options, async () => true, auto);
    this.talk(false);
    // The child says what he picked — his question, or his answer to the elder — and the
    // replies only start once his voice has finished (never cut him off mid-sentence).
    const said = this.t(picked);
    if (said) {
      this.setSpeaker('player');
      await this.line(said, { wait: false });
      await this.spokenEnd(said);
      this.talk(false);
    }
    for (const r of [].concat(picked.reply ?? [])) {
      this.setSpeaker(r.speaker ?? (asking ? enc.host : step.speaker ?? enc.host));
      this.scene(r.scene ?? step.scene);
      await this.line(this.t(r));
    }
  }

  async question(step) {
    this.scene(step.scene);
    // the "what do we learn?" question gets the lightbulb lesson chip
    const lesson = step.lesson ?? /نتعلّم|نتعلم|\blearn/i.test(`${step.ar ?? ''} ${step.en ?? ''}`);
    if (lesson) box().dataset.lesson = ''; else delete box().dataset.lesson;
    try { await this.askQuestion(step); } finally { delete box().dataset.lesson; }
  }
  async askQuestion(step) {
    await this.line(this.t(step), { wait: false });
    await this.options(step.options, async (o, b) => {
      if (o.correct) { b.classList.add('right'); await new Promise(r => setTimeout(r, 450)); return true; }
      b.classList.add('wrong'); b.disabled = true;
      this.line(this.t(step.hint), { wait: false });
      return false;
    });
    await this.line(this.t(step.praise));
  }

  async verses(step, enc) {
    Voice.cancel(); this.talk(false); this.scene(null);
    box().classList.remove('show');
    await this.hooks.verses(step, enc);
    box().classList.add('show');
  }

  async reward(step, enc) {
    Voice.cancel(); this.talk(false); this.scene(null);
    box().classList.remove('show');
    await this.hooks.reward(enc);
  }
}
