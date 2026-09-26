// Floating virtual joystick (touch): a translucent teal-glass base with a thin gold ring and a
// gold knob, spawned under the thumb in the left half of the screen. Pure DOM, pointer-events
// none — PlayerController feeds it; it never takes a touch itself.
export const STICK_R = 60;                 // knob travel (px)
const BASE_R = STICK_R + 14;               // drawn base radius
const HUD_SEL = '#dock, #zoom, #talk:not([hidden]), #objective, #minimap, #points';

// Is this a touch-first device? (touch laptops count too: keyboard keeps working alongside)
export const isTouchDevice = () => typeof window !== 'undefined' && (
  (typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches) || navigator.maxTouchPoints > 0 || 'ontouchstart' in window);

export function createJoystick() {
  const el = document.createElement('div');
  el.id = 'stick'; el.setAttribute('aria-hidden', 'true');
  el.innerHTML = '<i class="base"></i><i class="knob"></i>';
  document.body.append(el);
  const knob = el.querySelector('.knob');
  let cx = 0, cy = 0;
  return {
    // centre the base near (x, y), nudged clear of the HUD and the screen edges → the centre used
    show(x, y) {
      const hud = document.getElementById('hud');
      const rects = hud && !hud.hidden ? [...document.querySelectorAll(HUD_SEL)].map(e => e.getBoundingClientRect()).filter(r => r.width && r.height) : [];
      const m = BASE_R + 8;
      for (let it = 0; it < 4; it++) {
        for (const r of rects) {
          const x0 = r.left - m, x1 = r.right + m, y0 = r.top - m, y1 = r.bottom + m;
          if (x <= x0 || x >= x1 || y <= y0 || y >= y1) continue;
          const opts = [[x - x0, x0, y], [x1 - x, x1, y], [y - y0, x, y0], [y1 - y, x, y1]].sort((a, b) => a[0] - b[0]);
          // prefer a push that keeps the base inside the screen
          const ok = opts.find(o => o[1] >= m && o[1] <= innerWidth - m && o[2] >= m && o[2] <= innerHeight - m) ?? opts[0];
          x = ok[1]; y = ok[2];
        }
        x = Math.min(Math.max(x, m), innerWidth - m); y = Math.min(Math.max(y, m), innerHeight - m);
      }
      cx = x; cy = y;
      el.style.transform = `translate(${x}px, ${y}px)`;
      knob.style.transform = 'translate(-50%, -50%)';
      el.classList.add('on');
      return { x, y };
    },
    // knob offset in px (already clamped to STICK_R)
    move(dx, dy) { knob.style.transform = `translate(calc(-50% + ${dx.toFixed(1)}px), calc(-50% + ${dy.toFixed(1)}px))`; el.classList.toggle('far', Math.hypot(dx, dy) > STICK_R * 0.86); },
    hide() { el.classList.remove('on', 'far'); knob.style.transform = 'translate(-50%, -50%)'; },
    get center() { return { x: cx, y: cy }; },
  };
}
