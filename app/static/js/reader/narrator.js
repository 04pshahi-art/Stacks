/* Reads the book aloud: speaks the page on screen, turns the page, and carries on.
   If the reader turns pages themselves, it simply carries on from the new page. */
import { getJSON } from "../lib/http.js";
import { AiVoice, BrowserVoice, splitSentences } from "./speech-engines.js";

const PARAGRAPH_PAUSE_MS = 600;
const OPENING_QUOTE = /^["“'‘«]/;

/* Words inside quotation marks are spoken a little livelier than the narration. */
const toneOf = (text) => (OPENING_QUOTE.test(text) ? "dialogue" : "narration");

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export class Narrator {
  /* reader needs: visibleText(), turn(direction) -> Promise<boolean>, pageSerial */
  constructor({ reader, statusUrl, synthesizeUrl, settings, onChange, onNotice }) {
    this.reader = reader;
    this.statusUrl = statusUrl;
    this.synthesizeUrl = synthesizeUrl;
    this.settings = settings;
    this.onChange = onChange;
    this.onNotice = onNotice;

    this.state = "idle"; // idle, playing or paused
    this.engine = null;
    this.browser = BrowserVoice.supported() ? new BrowserVoice() : null;
    this.runId = 0;
  }

  /* Pick the AI voice if the server has one, otherwise the browser's voice. */
  async prepare() {
    if (this.engine) return this.engine;
    const status = await getJSON(this.statusUrl).catch(() => ({ engine: null, voices: [] }));
    this.aiVoices = status.voices ?? [];
    this.engine = status.engine ? new AiVoice(this.synthesizeUrl, status) : this.browser;
    return this.engine;
  }

  setState(state) {
    this.state = state;
    this.onChange(state);
  }

  toggle() {
    if (this.state === "idle") return this.start();
    if (this.state === "playing") return this.pause();
    return this.resume();
  }

  async start() {
    if (!(await this.prepare())) {
      this.onNotice("This browser can't read aloud.");
      return;
    }
    this.run();
  }

  pause() {
    this.engine.pause();
    this.setState("paused");
  }

  resume() {
    this.engine.resume();
    this.setState("playing");
  }

  stop() {
    this.runId += 1; // ends the running loop
    this.engine?.cancel();
    this.setState("idle");
  }

  /* The page changed under us. While reading, the loop picks up the new page.
     While paused there is nothing to carry on, so end the session. */
  interrupt() {
    if (this.state === "playing") this.engine.cancel();
    else if (this.state === "paused") this.stop();
  }

  isCurrent(runId, serial) {
    return this.runId === runId && this.reader.pageSerial === serial;
  }

  async run() {
    const runId = ++this.runId;
    this.setState("playing");
    try {
      while (this.runId === runId) {
        const serial = this.reader.pageSerial;
        const finished = await this.speakAll(splitSentences(this.reader.visibleText()), runId, serial);
        if (this.runId !== runId) return;
        if (finished && !(await this.reader.turn(1))) break; // end of the book
      }
    } catch (error) {
      this.onNotice(error.message);
    }
    if (this.runId === runId) this.setState("idle");
  }

  voiceOptions(text) {
    const { rate, voice, aiVoice } = this.settings;
    return { rate, voice, aiVoice, tone: toneOf(text) };
  }

  /* True if every piece was read, false if the page changed or we were stopped. */
  async speakAll(chunks, runId, serial) {
    for (let index = 0; index < chunks.length; index += 1) {
      if (!this.isCurrent(runId, serial)) return false;
      const { text, paragraphEnd } = chunks[index];
      const next = chunks[index + 1]?.text;
      if (next) this.engine.prefetch?.(next, this.voiceOptions(next));
      try {
        await this.engine.speak(text, this.voiceOptions(text));
      } catch (error) {
        if (!this.switchToBrowserVoice()) throw error;
        index -= 1; // read the same piece again with the other voice
        continue;
      }
      if (paragraphEnd && this.isCurrent(runId, serial)) await wait(PARAGRAPH_PAUSE_MS);
    }
    return this.isCurrent(runId, serial);
  }

  switchToBrowserVoice() {
    if (!this.browser || this.engine === this.browser) return false;
    this.engine.cancel();
    this.engine = this.browser;
    this.onNotice("The AI voice isn't working, so Folio switched to the browser voice.");
    return true;
  }
}
