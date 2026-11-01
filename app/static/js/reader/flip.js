/* The page turn. The leaf is a sheet with a front and a back that swings around
   the spine. Which pages sit under it, and which faces it carries, is a plan. */

/* Offsets are in pages from the first visible page. `under` is what the two (or one)
   static sheets show while the leaf is in the air. */
export const PLANS = {
  2: {
    1: { under: [0, 3], front: 1, back: 2, from: 0, to: -180, step: 2 },
    "-1": { under: [-2, 1], front: -1, back: 0, from: -180, to: 0, step: -2 },
  },
  1: {
    1: { under: [1], front: 0, back: null, from: 0, to: -180, step: 1 },
    "-1": { under: [0], front: -1, back: null, from: -180, to: 0, step: -1 },
  },
};

const DURATION_MS = 760;
const EASING = "cubic-bezier(0.55, 0.06, 0.25, 1)";
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function pagesNeeded(plan) {
  return [...plan.under, plan.front, plan.back].filter((offset) => offset !== null);
}

export async function playTurn(leaf, plan, columns) {
  if (calm()) return;
  const timing = { duration: DURATION_MS, easing: EASING, fill: "both" };
  leaf.hidden = false;

  const animations = [
    leaf.animate(
      [{ transform: `rotateY(${plan.from}deg)` }, { transform: `rotateY(${plan.to}deg)` }],
      timing),
    leaf.querySelector(".leaf__shade").animate(
      [{ opacity: 0 }, { opacity: 0.9, offset: 0.5 }, { opacity: 0 }],
      { ...timing, easing: "linear" }),
  ];
  if (columns === 1) {
    // One page wide: the leaf swings off to the left, so fade it as it goes.
    const fade = plan.step > 0 ? [1, 1, 0] : [0, 1, 1];
    animations.push(leaf.animate(fade.map((opacity) => ({ opacity })), { ...timing, easing: "linear" }));
  }

  try {
    await Promise.all(animations.map((animation) => animation.finished));
  } finally {
    leaf.hidden = true;
    animations.forEach((animation) => animation.cancel());
  }
}
