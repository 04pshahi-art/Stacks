/* Entry point for every page. Each feature only starts if its markup exists. */
import { initChat } from "./chat.js";
import { initNotifications } from "./notify.js";
import { initConfirmForms, initLocalTimes } from "./page.js";
import { initTagSuggestions } from "./tags.js";

function mount(selector, start) {
  const node = document.querySelector(selector);
  if (node) start(node);
}

initConfirmForms();
initLocalTimes();
mount("[data-notify]", initNotifications);
mount("[data-chat]", initChat);
mount("[data-tag-form]", initTagSuggestions);
