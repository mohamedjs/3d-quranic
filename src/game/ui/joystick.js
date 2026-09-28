// Fixed virtual joystick (touch devices): always shown at the bottom-left corner of the HUD
// (inside the safe area), a translucent teal-glass base with a thin gold ring and a gold knob,
// dimmed until touched. Pure DOM with pointer-events none — PlayerController hit-tests it
// (`hit`) and feeds the knob; only a touch that STARTS on it moves the child.
export const STICK_R = 50;                 // knob travel (px) — the base is 128 px across (CSS)
const GRAB = 18;                           // extra px round the base that still count as "on it"

// Is this a touch-first device? (touch laptops count too: keyboard keeps working alongside)
export const isTouchDevice = () => typeof window !== 'undefined' && (
  (typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches) || navigator.maxTouchPoints > 0 || 'ontouchstart' in window);

export function createJoystick() {
  const el = document.createElement('div');
  el.id = 'stick'; el.setAttribute('aria-hidden', 'true');
  el.innerHTML = '<i class="base"></i><i class="knob"></i>';
  (document.getElementById('hud') ?? document.body).append(el);   // hidden with the HUD (title, dialogue)
  const knob = el.querySelector('.knob');
  const rect = () => el.getBoundingClientRect();
  return {
    el,
    // centre + radius of the base on screen, or null while it isn't shown
    get circle() { const r = rect(); return r.width ? { x: r.left + r.width / 2, y: r.top + r.height / 2, r: r.width / 2 } : null; },
    hit(x, y) { const c = this.circle; return !!c && Math.hypot(x - c.x, y - c.y) <= c.r + GRAB; },
    press() { el.classList.add('on'); },
    // knob offset in px (already clamped to STICK_R)
    move(dx, dy) { knob.style.transform = `translate(calc(-50% + ${dx.toFixed(1)}px), calc(-50% + ${dy.toFixed(1)}px))`; el.classList.toggle('far', Math.hypot(dx, dy) > STICK_R * 0.86); },
    hide() { el.classList.remove('on', 'far'); knob.style.transform = 'translate(-50%, -50%)'; },
  };
}
