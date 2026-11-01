/* Small page-wide behaviours that need no page of their own. */
export function initConfirmForms() {
  document.addEventListener("submit", (event) => {
    const message = event.target.dataset?.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
  });
}

export function initLocalTimes() {
  const format = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
  for (const node of document.querySelectorAll("time[data-local-time]")) {
    const date = new Date(node.dateTime);
    if (!Number.isNaN(date.getTime())) node.textContent = format.format(date);
  }
}
