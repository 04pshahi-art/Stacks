/* Text size, paper colour and voice choices, remembered in this browser. */
const KEY = "folio.reader";
export const SIZES = [0.92, 1, 1.08, 1.2, 1.35, 1.5];
export const PAPERS = ["ivory", "sepia", "night"];
export const RATES = [0.75, 0.9, 1, 1.1, 1.25, 1.5, 1.75];
const DEFAULTS = { size: 2, paper: 0, rate: 1, voice: "", aiVoice: "" };

const index = (value, list, fallback) => (Number.isInteger(value) && list[value] ? value : fallback);

export function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY));
    return {
      size: index(saved?.size, SIZES, DEFAULTS.size),
      paper: index(saved?.paper, PAPERS, DEFAULTS.paper),
      rate: RATES.includes(saved?.rate) ? saved.rate : DEFAULTS.rate,
      voice: typeof saved?.voice === "string" ? saved.voice.slice(0, 200) : DEFAULTS.voice,
      aiVoice: typeof saved?.aiVoice === "string" ? saved.aiVoice.slice(0, 60) : DEFAULTS.aiVoice,
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveSettings(settings) {
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    /* private mode: the choice just won't be remembered */
  }
}
