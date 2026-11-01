/* Buttons, keyboard and swipes all end up as named actions. */
const KEYS = {
  ArrowRight: "next", PageDown: "next", " ": "next",
  ArrowLeft: "prev", PageUp: "prev",
  f: "full", F: "full", l: "speak", L: "speak", c: "toc", C: "toc",
  Escape: "close",
};
const SWIPE_MIN_PX = 50;

export function bindControls(root, actions) {
  root.addEventListener("click", (event) => {
    const control = event.target.closest("[data-action]");
    if (control && !control.disabled) actions[control.dataset.action]?.();
  });

  document.addEventListener("keydown", (event) => {
    const name = KEYS[event.key];
    if (!name || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === " " && event.target.closest("button, a, input")) return;
    event.preventDefault();
    actions[name]();
  });

  const stage = root.querySelector(".reader__stage");
  let start = null;
  stage.addEventListener("pointerdown", (event) => {
    start = { x: event.clientX, y: event.clientY };
  });
  stage.addEventListener("pointerup", (event) => {
    if (!start) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    start = null;
    if (Math.abs(dx) >= SWIPE_MIN_PX && Math.abs(dx) > Math.abs(dy) * 1.5) {
      actions[dx < 0 ? "next" : "prev"]();
    }
  });
  stage.addEventListener("pointercancel", () => { start = null; });
}
