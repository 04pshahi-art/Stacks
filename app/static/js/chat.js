/* The reading assistant. The server asks the locally running AI; links to books
   always come from the database, and everything is inserted as text. */
import { h } from "./lib/dom.js";
import { getJSON, postJSON } from "./lib/http.js";

const GREETING = "Hi! Tell me a genre, a mood, or a feeling and I'll find something to read.";
const MAX_TURNS = 6;

export function initChat(root) {
  const panel = root.querySelector("[data-chat-panel]");
  const toggle = root.querySelector("[data-chat-toggle]");
  const log = root.querySelector("[data-chat-log]");
  const form = root.querySelector("[data-chat-form]");
  const status = root.querySelector("[data-chat-status]");
  const input = form.elements.message;
  const history = [];
  let opened = false;

  function say(role, text, books = []) {
    const bubble = h("div", { class: `chat__msg${role === "user" ? " chat__msg--user" : ""}`, text });
    if (books.length) {
      bubble.append(h("div", { class: "chat__books" },
        books.map((book) => h("a", { class: `chip mood-${book.mood}`, href: book.url, text: `${book.title}, ${book.author}` }))));
    }
    log.append(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  }

  function setStatus(online) {
    status.dataset.online = String(online);
    status.textContent = online ? "Local AI online" : "AI offline, search only";
  }

  async function firstOpen() {
    say("assistant", GREETING);
    try {
      setStatus((await getJSON(root.dataset.statusUrl)).online);
    } catch {
      setStatus(false);
    }
  }

  function setOpen(open) {
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open && !opened) {
      opened = true;
      firstOpen();
    }
    if (open) input.focus();
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    say("user", message);
    const thinking = say("assistant", "Thinking…");
    try {
      const data = await postJSON(root.dataset.chatUrl, { message, history });
      thinking.remove();
      say("assistant", data.reply, data.books);
      setStatus(data.online);
      history.push({ role: "user", content: message }, { role: "assistant", content: data.reply });
      history.splice(0, Math.max(0, history.length - MAX_TURNS));
    } catch (error) {
      thinking.textContent = error.message;
    }
  });

  toggle.addEventListener("click", () => setOpen(panel.hidden));
  root.querySelector("[data-chat-close]").addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) setOpen(false);
  });
}
