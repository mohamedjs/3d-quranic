// Runs one data-driven encounter: say / choice / question / verses / reward steps.
// Never gated on speech synthesis — every line waits for a tap, so a missing voice is harmless.
import { sceneSVG } from './scenes.js';
import { Voice } from './audio.js';

const box = () => document.getElementById('dialogue');
const $ = s => box().querySelector(s);

export class Story {
  constructor({ lang, hooks }) { this.lang = lang; this.hooks = hooks; }
  t(o) { return o?.[this.lang()] ?? o?.ar ?? ''; }

  async run(enc, npc) {
    const d = box(); d.hidden = false; d.dir = this.lang() === 'ar' ? 'rtl' : 'ltr';
    $('.name').innerHTML = `<small></small><b></b>`;
    $('.name small').textContent = this.t(enc.character.role); $('.name b').textContent = this.t(enc.character.name);
    requestAnimationFrame(() => d.classList.add('show'));
    try {
      for (const step of enc.steps) await this[step.type](step, enc, npc);
    } finally {
      Voice.cancel(); npc.talking = false; this.scene(null);
      d.classList.remove('show'); setTimeout(() => { d.hidden = true; }, 400);
    }
  }

  scene(name) {
    const el = document.getElementById('scene');
    if (!name) { el.classList.remove('show'); el.dataset.name = ''; return; }
    if (el.dataset.name === name) return;
    el.dataset.name = name; el.hidden = false;
    el.innerHTML = sceneSVG(name, this.lang());
    el.classList.remove('show'); void el.offsetWidth; el.classList.add('show');
  }

  // Types a line out; first tap finishes it, second tap continues.
  line(text, npc, { wait = true } = {}) {
    const el = $('.text'), next = $('.next');
    this.stopLine?.();  // a hint may still be typing when the next line starts
    npc.talking = true; Voice.speak(text, this.lang());
    el.textContent = ''; next.hidden = true;
    let n = 0, full = false;
    return new Promise(resolve => {
      const timer = setInterval(() => { n += 2; el.textContent = text.slice(0, n); if (n >= text.length) complete(); }, 28);
      this.stopLine = () => { clearInterval(timer); off(); };
      const complete = () => { clearInterval(timer); el.textContent = text; full = true; next.hidden = !wait; if (!wait) done(); };
      const done = () => { off(); resolve(); };
      const advance = e => {
        if (e.type === 'keydown' && !['Space', 'Enter', 'KeyE'].includes(e.code)) return;
        if (e.type === 'keydown') e.preventDefault();
        if (!full) complete(); else if (wait) { npc.talking = false; done(); }
      };
      const off = () => { $('.box').removeEventListener('click', advance); removeEventListener('keydown', advance); };
      $('.box').addEventListener('click', advance); addEventListener('keydown', advance);
    });
  }

  options(opts, onPick) {
    const c = $('.choices'); c.innerHTML = '';
    return new Promise(resolve => {
      const buttons = opts.map((o, k) => {
        const b = document.createElement('button');
        b.innerHTML = `<i>${k + 1}</i><span></span>`; b.querySelector('span').textContent = this.t(o);
        b.onclick = async () => { if (b.disabled) return; if (await onPick(o, b)) { off(); c.classList.remove('show'); setTimeout(() => { c.innerHTML = ''; }, 250); resolve(o); } };
        c.append(b); return b;
      });
      const key = e => { const k = +e.key - 1; if (buttons[k]) buttons[k].click(); };
      const off = () => removeEventListener('keydown', key);
      addEventListener('keydown', key);
      requestAnimationFrame(() => c.classList.add('show'));
    });
  }

  async say(step, enc, npc) { this.scene(step.scene); await this.line(this.t(step), npc); }

  async choice(step, enc, npc) {
    this.scene(step.scene);
    await this.line(this.t(step), npc, { wait: false });
    await this.options(step.options, async () => true);
    npc.talking = false;
  }

  async question(step, enc, npc) {
    this.scene(step.scene);
    await this.line(this.t(step), npc, { wait: false });
    await this.options(step.options, async (o, b) => {
      if (o.correct) { b.classList.add('right'); await new Promise(r => setTimeout(r, 450)); return true; }
      b.classList.add('wrong'); b.disabled = true;
      this.line(this.t(step.hint), npc, { wait: false });
      return false;
    });
    await this.line(this.t(step.praise), npc);
  }

  async verses(step, enc, npc) {
    Voice.cancel(); npc.talking = false; this.scene(null);
    box().classList.remove('show');
    await this.hooks.verses(step, enc, npc);
    box().classList.add('show');
  }

  async reward(step, enc, npc) {
    Voice.cancel(); npc.talking = false; this.scene(null);
    box().classList.remove('show');
    await this.hooks.reward(enc);
  }
}
