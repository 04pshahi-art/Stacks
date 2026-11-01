/* "Suggest genres and moods" on the upload form. */
import { postJSON } from "./lib/http.js";

const SAMPLE_CHARS = 5000;

function readFileStart(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => resolve("");
    reader.readAsText(file.slice(0, SAMPLE_CHARS * 2));
  });
}

async function sampleText(form) {
  const file = form.elements.file?.files[0];
  const readable = file && /\.(txt|md)$/i.test(file.name);
  const typed = ["title", "description"].map((name) => form.elements[name].value).join(". ");
  return readable ? `${typed}\n${await readFileStart(file)}` : typed;
}

function tick(form, name, values) {
  for (const box of form.querySelectorAll(`input[name="${name}"]`)) {
    box.checked = values.includes(box.value);
  }
}

export function initTagSuggestions(form) {
  const note = form.querySelector("[data-suggest-note]");
  form.querySelector("[data-suggest]").addEventListener("click", async () => {
    const text = (await sampleText(form)).trim();
    if (text.length < 20) {
      note.textContent = "Add a description or choose a text file first.";
      return;
    }
    note.textContent = "Reading…";
    try {
      const { genres, moods } = await postJSON(form.dataset.suggestUrl, { text });
      tick(form, "genres", genres);
      tick(form, "moods", moods);
      note.textContent = "Suggestions applied. Change anything you like.";
    } catch (error) {
      note.textContent = error.message;
    }
  });
}
