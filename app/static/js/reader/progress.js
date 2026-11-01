/* Tells the server where the reader is, a moment after they stop turning pages. */
import { postJSON } from "../lib/http.js";

const DELAY_MS = 800;

export function createProgressSaver(url) {
  let timer = null;
  let latest = null;

  function send(keepalive) {
    clearTimeout(timer);
    if (!latest) return;
    const body = latest;
    latest = null;
    postJSON(url, body, { keepalive }).catch(() => {});
  }

  return {
    queue(body) {
      latest = body;
      clearTimeout(timer);
      timer = setTimeout(() => send(false), DELAY_MS);
    },
    flush() {
      send(true);
    },
  };
}
