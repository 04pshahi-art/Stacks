/* New-chapter alerts: a bell with a count, a dropdown, and a toast for fresh ones. */
import { clear, h, timeAgo, when } from "./lib/dom.js";
import { getJSON, postJSON } from "./lib/http.js";

const POLL_MS = 60_000;
const TOAST_MS = 6000;

function showToast(message) {
  const toast = h("div", { class: "toast", role: "status", text: message });
  document.body.append(toast);
  setTimeout(() => toast.remove(), TOAST_MS);
}

export function initNotifications(root) {
  const toggle = root.querySelector("[data-notify-toggle]");
  const badge = root.querySelector("[data-notify-badge]");
  const panel = root.querySelector("[data-notify-panel]");
  const list = root.querySelector("[data-notify-list]");
  let unread = Number(badge.textContent) || 0;

  function setBadge(count) {
    unread = count;
    badge.textContent = count > 99 ? "99+" : String(count);
    badge.hidden = count === 0;
  }

  function draw(items) {
    clear(list);
    if (!items.length) {
      list.append(h("li", { class: "notify__empty", text: "No new chapters yet." }));
      return;
    }
    for (const item of items) {
      list.append(
        h("li", { class: `notify__item${item.read ? "" : " is-unread"}` },
          h("a", { href: item.url },
            h("span", { text: item.message }),
            h("span", { class: "notify__time", text: timeAgo(when(item.created)) }))));
    }
  }

  async function refresh({ announce }) {
    try {
      const data = await getJSON(root.dataset.summaryUrl);
      if (announce && data.unread > unread) {
        const newest = data.items.find((item) => !item.read);
        showToast(newest ? newest.message : "A book you follow has a new chapter.");
      }
      setBadge(data.unread);
      draw(data.items);
    } catch {
      /* offline or signed out: keep what we have */
    }
  }

  async function open() {
    await refresh({ announce: false });
    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    if (unread > 0) {
      postJSON(root.dataset.readUrl).then(() => setBadge(0)).catch(() => {});
    }
  }

  function close() {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  }

  toggle.addEventListener("click", () => (panel.hidden ? open() : close()));
  document.addEventListener("click", (event) => {
    if (!panel.hidden && !root.contains(event.target)) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) close();
  });

  setInterval(() => !document.hidden && refresh({ announce: true }), POLL_MS);
}
