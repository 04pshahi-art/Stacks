/* The "Listen" panel: play/pause, stop, speed, and which voice to use. */
import { RATES } from "./settings.js";
import { h } from "../lib/dom.js";

/* Prefer natural sounding voices in the visitor's own language. */
function voiceScore(voice) {
  const language = navigator.language.split("-")[0];
  let score = voice.lang.toLowerCase().startsWith(language) ? 5 : 0;
  if (/natural/i.test(voice.name)) score += 3;
  if (/online/i.test(voice.name)) score += 2;
  if (/google/i.test(voice.name)) score += 1;
  return score;
}

export function bindListenPanel(root, narrator, settings, persist) {
  const panel = root.querySelector("[data-listen]");
  const toolButton = root.querySelector('[data-action="listen"]');
  const engineName = panel.querySelector("[data-listen-engine]");
  const notice = panel.querySelector("[data-listen-notice]");
  const rateSelect = panel.querySelector("[data-listen-rate]");
  const voiceRow = panel.querySelector("[data-listen-voice-row]");
  const voiceSelect = panel.querySelector("[data-listen-voice]");
  let aiMode = false;

  rateSelect.append(...RATES.map((rate) =>
    h("option", { value: rate, selected: rate === settings.rate, text: `${rate}×` })));
  rateSelect.addEventListener("change", () => {
    settings.rate = Number(rateSelect.value);
    persist();
  });
  voiceSelect.addEventListener("change", () => {
    settings[aiMode ? "aiVoice" : "voice"] = voiceSelect.value;
    persist();
  });

  const choose = (select, wanted, fallback) => {
    select.value = wanted;
    return select.value || fallback;
  };

  function fillAiVoices() {
    const voices = narrator.aiVoices;
    voiceSelect.replaceChildren(...voices.map((voice) => h("option", { value: voice.id, text: voice.label })));
    settings.aiVoice = choose(voiceSelect, settings.aiVoice, voices[0].id);
    voiceSelect.value = settings.aiVoice;
  }

  function fillVoices() {
    if (aiMode) return;
    const voices = [...narrator.browser?.voices() ?? []].sort((a, b) => voiceScore(b) - voiceScore(a));
    voiceSelect.replaceChildren(...voices.map((voice) =>
      h("option", { value: voice.name, text: `${voice.name} (${voice.lang})` })));
    if (!voices.length) return;
    const wanted = voices.some((voice) => voice.name === settings.voice) ? settings.voice : voices[0].name;
    voiceSelect.value = wanted;
    settings.voice = wanted;
  }

  async function open() {
    const engine = await narrator.prepare();
    engineName.textContent = engine ? engine.label : "Not supported in this browser";
    aiMode = engine !== narrator.browser;
    voiceRow.hidden = aiMode && !narrator.aiVoices.length;
    if (!aiMode) fillVoices();
    else if (narrator.aiVoices.length) fillAiVoices();
    panel.hidden = false;
  }

  if (narrator.browser) speechSynthesis.addEventListener("voiceschanged", fillVoices);

  return {
    toggle: () => (panel.hidden ? open() : (panel.hidden = true)),
    close: () => { panel.hidden = true; },
    get isOpen() { return !panel.hidden; },
    setState(state) {
      panel.dataset.state = state;
      toolButton.setAttribute("aria-pressed", String(state !== "idle"));
    },
    say(message) {
      notice.textContent = message;
      notice.hidden = !message;
    },
  };
}
