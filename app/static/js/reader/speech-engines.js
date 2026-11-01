/* Two ways to speak. Both have the same shape:
     speak(text, {rate, voice, aiVoice, tone}) -> Promise that settles when the text has been read
     pause(), resume(), cancel()
   so the narrator doesn't care which one it is using. */
import { postForBlob } from "../lib/http.js";

const MAX_CHUNK_CHARS = 240;
const SENTENCE_RE = /[^.!?…]+[.!?…]*["')\]”’]*\s*/g;

function wrapLong(sentence, max) {
  const pieces = [];
  let line = "";
  for (const word of sentence.split(" ")) {
    if (line && line.length + word.length + 1 > max) {
      pieces.push(line);
      line = word;
    } else {
      line = line ? `${line} ${word}` : word;
    }
  }
  return line ? [...pieces, line] : pieces;
}

/* Short pieces at sentence ends: engines cope better and the first words start sooner.
   Each piece says whether it ends a paragraph, so the narrator can pause there. */
export function splitSentences(text, max = MAX_CHUNK_CHARS) {
  return text.split("\n").flatMap((line) => {
    const sentences = (line.match(SENTENCE_RE) ?? [])
      .map((sentence) => sentence.trim())
      .filter(Boolean)
      .flatMap((sentence) => wrapLong(sentence, max));

    const chunks = [];
    let current = "";
    for (const sentence of sentences) {
      if (current && current.length + sentence.length + 1 > max) {
        chunks.push(current);
        current = sentence;
      } else {
        current = current ? `${current} ${sentence}` : sentence;
      }
    }
    if (current) chunks.push(current);
    return chunks.map((chunk, index) => ({ text: chunk, paragraphEnd: index === chunks.length - 1 }));
  });
}

/* ---- the voices built into the browser or operating system ----------------- */
export class BrowserVoice {
  label = "Browser voice";

  static supported() {
    return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  }

  voices() {
    return speechSynthesis.getVoices();
  }

  speak(text, { rate, voice }) {
    return new Promise((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = rate;
      utterance.voice = this.voices().find((candidate) => candidate.name === voice) ?? null;
      utterance.onend = resolve;
      utterance.onerror = resolve; // a cancelled utterance reports an "error"; that is fine
      speechSynthesis.speak(utterance);
    });
  }

  pause() { speechSynthesis.pause(); }
  resume() { speechSynthesis.resume(); }

  cancel() {
    speechSynthesis.cancel();
    speechSynthesis.resume(); // some browsers stay paused after a cancel
  }
}

/* ---- the AI voice running on the server (Kokoro or Piper) ------------------- */
const TONE_SPEED = { narration: 0.95, dialogue: 1.05 };

export class AiVoice {
  constructor(synthesizeUrl, { engine, voices }) {
    this.url = synthesizeUrl;
    this.voices = voices;
    this.label = engine === "kokoro" ? "AI voice: Kokoro (runs on this computer)" : "AI voice: Piper (runs on this computer)";
    this.audioByKey = new Map(); // request -> Promise of a playable address
    this.playing = null;
    this.epoch = 0; // bumped on cancel so audio that arrives late is not played
  }

  /* Only Kokoro has several voices and a speed setting; the server ignores them for Piper. */
  request(text, { aiVoice, tone }) {
    const voice = this.voices.some((choice) => choice.id === aiVoice) ? aiVoice : this.voices[0]?.id;
    return { text, voice, speed: TONE_SPEED[tone] ?? 1 };
  }

  audioFor(request) {
    const key = JSON.stringify(request);
    if (!this.audioByKey.has(key)) {
      const audio = postForBlob(this.url, request).then((blob) => URL.createObjectURL(blob));
      audio.catch(() => this.audioByKey.delete(key));
      this.audioByKey.set(key, audio);
    }
    return this.audioByKey.get(key);
  }

  /* Start making the next piece while the current one is still playing. */
  prefetch(text, options) {
    if (text) this.audioFor(this.request(text, options)).catch(() => {});
  }

  async speak(text, { rate, ...options }) {
    const request = this.request(text, options);
    const epoch = this.epoch;
    const address = await this.audioFor(request);
    if (epoch !== this.epoch) return;
    return new Promise((resolve, reject) => {
      const audio = new Audio(address);
      audio.playbackRate = rate;
      const done = () => {
        this.playing = null;
        this.forget(request);
        resolve();
      };
      audio.onended = done;
      audio.onerror = () => {
        this.playing = null;
        reject(new Error("The AI voice's audio couldn't be played."));
      };
      this.playing = { audio, done };
      audio.play().catch(reject);
    });
  }

  forget(request) {
    const key = JSON.stringify(request);
    this.audioByKey.get(key)?.then((address) => URL.revokeObjectURL(address));
    this.audioByKey.delete(key);
  }

  pause() { this.playing?.audio.pause(); }
  resume() { this.playing?.audio.play(); }

  cancel() {
    this.epoch += 1;
    this.playing?.audio.pause();
    this.playing?.done();
    for (const key of [...this.audioByKey.keys()]) this.forget(JSON.parse(key));
  }
}
