// Render layers. The main camera sees both; the water's mirror camera sees only layer 0,
// so dense grass and particles don't pay for a second render.
export const LAYER_NO_REFLECT = 2;
export function noReflect(obj) { obj.layers.set(LAYER_NO_REFLECT); return obj; }
