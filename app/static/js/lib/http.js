/* Requests to our own server. Adds the CSRF token Flask-WTF expects. */
const csrfToken = () => document.querySelector('meta[name="csrf-token"]')?.content ?? "";

async function send(url, { method = "GET", body, keepalive = false, accept = "application/json" } = {}) {
  const response = await fetch(url, {
    method,
    keepalive,
    credentials: "same-origin",
    headers: {
      Accept: accept,
      ...(body !== undefined && { "Content-Type": "application/json" }),
      ...(method !== "GET" && { "X-CSRFToken": csrfToken() }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Something went wrong.");
  }
  return response;
}

export async function request(url, options) {
  const response = await send(url, options);
  return response.json().catch(() => ({}));
}

export const getJSON = (url) => request(url);
export const postJSON = (url, body = {}, options = {}) => request(url, { ...options, method: "POST", body });

/* POST JSON, get a file back (used for the AI voice's audio). */
export async function postForBlob(url, body) {
  const response = await send(url, { method: "POST", body, accept: "audio/*" });
  return response.blob();
}
