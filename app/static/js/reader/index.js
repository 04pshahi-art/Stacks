/* The reader. Shows one page (phones) or a two-page spread (desktop), turns pages
   with a real flip, remembers your place, and has a full-screen mode. */
import { h } from "../lib/dom.js";
import { getJSON } from "../lib/http.js";
import { bindControls } from "./controls.js";
import { PLANS, pagesNeeded, playTurn } from "./flip.js";
import { bindListenPanel } from "./listen-panel.js";
import { Narrator } from "./narrator.js";
import { mountSheet, pageText } from "./paginator.js";
import { Pager } from "./pager.js";
import { createProgressSaver } from "./progress.js";
import { loadSettings, PAPERS, saveSettings, SIZES } from "./settings.js";

const SPREAD_QUERY = "(min-width: 900px)";
const RESIZE_DELAY_MS = 220;
const FONT_WAIT_MS = 1500;

class Reader {
  constructor(root) {
    const find = (selector) => root.querySelector(selector);
    this.root = root;
    this.total = Number(root.dataset.total);
    this.settings = loadSettings();

    this.sheets = [...root.querySelectorAll("[data-sheet]")];
    this.leaf = find("[data-leaf]");
    this.leafFront = find("[data-leaf-front]");
    this.leafBack = find("[data-leaf-back]");
    this.book = find("[data-book]");
    this.status = find("[data-status]");
    this.progressBar = find("[data-progress]");
    this.chapterLabel = find("[data-chapter-label]");
    this.pageLabel = find("[data-page-label]");
    this.toc = find("[data-toc]");
    this.prevButton = find('[data-action="prev"]');
    this.nextButton = find('[data-action="next"]');

    this.wide = matchMedia(SPREAD_QUERY);
    this.pager = new Pager({ api: root.dataset.api, total: this.total, measure: find("[data-measure]") });
    this.saver = createProgressSaver(`${root.dataset.api}/progress`);
    this.cursor = null;
    this.busy = false;
    this.lastSize = "";
    this.pageSerial = 0; // changes every time the visible pages change
    this.visible = [];
    this.setupListening();
  }

  setupListening() {
    const { speechStatus, speechSynthesize } = this.root.dataset;
    const persist = () => saveSettings(this.settings);
    this.narrator = new Narrator({
      reader: this,
      statusUrl: speechStatus,
      synthesizeUrl: speechSynthesize,
      settings: this.settings,
      onChange: (state) => this.listenPanel.setState(state),
      onNotice: (message) => this.listenPanel.say(message),
    });
    this.listenPanel = bindListenPanel(this.root, this.narrator, this.settings, persist);
  }

  /* What the narrator reads: the text of the page(s) on screen. */
  visibleText() {
    return this.visible.map((entry) => pageText(entry.page)).join("\n");
  }

  get columns() {
    return this.wide.matches ? 2 : 1;
  }

  // ---- start up -------------------------------------------------------
  async start() {
    this.applySettings();
    this.root.dataset.mode = this.columns === 2 ? "spread" : "single";
    bindControls(this.root, this.actions());
    this.watchLayout();
    addEventListener("pagehide", () => this.saver.flush());
    document.addEventListener("visibilitychange", () => document.hidden && this.saver.flush());

    try {
      await this.waitForFonts();
      const { startChapter, startRatio } = this.root.dataset;
      await this.show(await this.pager.cursorFor(Number(startChapter), Number(startRatio)));
      this.setStatus(null);
    } catch (error) {
      this.setStatus(error.message);
    }
  }

  async waitForFonts() {
    const loaded = document.fonts?.load("1rem Literata") ?? Promise.resolve();
    await Promise.race([loaded, new Promise((resolve) => setTimeout(resolve, FONT_WAIT_MS))]);
  }

  setStatus(message) {
    this.status.hidden = !message;
    this.status.textContent = message ?? "";
  }

  // ---- painting -------------------------------------------------------
  async entriesFrom(cursor, offsets) {
    const entries = await Promise.all(offsets.map((offset) => this.pager.entryAt(cursor, offset)));
    return new Map(offsets.map((offset, index) => [offset, entries[index]]));
  }

  paint(sheet, entry) {
    mountSheet(sheet, entry?.page, entry ? String(entry.index + 1) : "");
  }

  async show(cursor) {
    const offsets = [...Array(this.columns).keys()];
    const entries = await this.entriesFrom(cursor, offsets);
    this.cursor = cursor;
    this.pageSerial += 1;
    this.visible = [...entries.values()].filter(Boolean);
    this.sheets.forEach((sheet, index) => this.paint(sheet, entries.get(index)));
    await this.updateChrome(entries);
    this.narrator.interrupt();
  }

  async updateChrome(entries) {
    const visible = [...entries.values()].filter(Boolean);
    const first = visible[0];
    const last = visible[visible.length - 1];

    this.chapterLabel.textContent = `Chapter ${first.chapter} of ${this.total} · ${first.title}`;
    const pages = visible.map((entry) => entry.index + 1);
    this.pageLabel.textContent =
      `${pages.length > 1 ? "Pages" : "Page"} ${pages.join("–")} of ${first.count}`;
    this.progressBar.value = Math.min(1, (last.chapter - 1 + (last.index + 1) / last.count) / this.total);

    const atEnd = last.chapter === this.total && last.index === last.count - 1;
    this.prevButton.disabled = first.chapter === 1 && first.index === 0;
    this.nextButton.disabled = atEnd;

    this.saver.queue({
      chapter_number: first.chapter,
      ratio: first.index / first.count,
      finished: atEnd,
    });
  }

  // ---- turning pages --------------------------------------------------
  async turn(direction) {
    if (this.busy || !this.cursor) return false;
    const columns = this.columns;
    const plan = PLANS[columns][direction];

    this.busy = true;
    try {
      const reachable = await this.pager.entryAt(this.cursor, direction > 0 ? columns : -1);
      if (!reachable) return false;

      const entries = await this.entriesFrom(this.cursor, pagesNeeded(plan));
      plan.under.forEach((offset, index) => this.paint(this.sheets[index], entries.get(offset)));
      this.paint(this.leafFront, entries.get(plan.front));
      this.paint(this.leafBack, entries.get(plan.back));

      await playTurn(this.leaf, plan, columns);
      const { cursor } = await this.pager.walk(this.cursor, plan.step);
      await this.show(cursor);
      return true;
    } catch (error) {
      this.setStatus(error.message);
      return false;
    } finally {
      this.busy = false;
    }
  }

  // ---- layout changes: repaginate and stay on the same spot -----------
  watchLayout() {
    let timer = null;
    const soon = () => {
      clearTimeout(timer);
      timer = setTimeout(() => this.relayout(), RESIZE_DELAY_MS);
    };
    this.wide.addEventListener("change", soon);
    new ResizeObserver(soon).observe(this.book);
  }

  async relayout() {
    const size = `${this.columns}:${Math.round(this.book.clientWidth)}x${Math.round(this.book.clientHeight)}:${this.settings.size}`;
    if (!this.cursor || this.busy || size === this.lastSize) return;
    this.lastSize = size;

    this.busy = true;
    try {
      const { chapter } = this.cursor;
      const ratio = await this.pager.ratioOf(this.cursor);
      this.root.dataset.mode = this.columns === 2 ? "spread" : "single";
      this.pager.reset();
      await this.show(await this.pager.cursorFor(chapter, ratio));
    } catch (error) {
      this.setStatus(error.message);
    } finally {
      this.busy = false;
    }
  }

  // ---- settings and modes ---------------------------------------------
  applySettings() {
    this.root.style.setProperty("--read-size", `${SIZES[this.settings.size]}rem`);
    this.root.dataset.paper = PAPERS[this.settings.paper];
    saveSettings(this.settings);
  }

  changeSize(step) {
    const size = Math.max(0, Math.min(SIZES.length - 1, this.settings.size + step));
    if (size === this.settings.size) return;
    this.settings.size = size;
    this.applySettings();
    this.lastSize = "";
    this.relayout();
  }

  setImmersive(on) {
    this.root.classList.toggle("is-immersive", on);
    this.root.querySelector(".reader__exit").hidden = !on;
    if (on && document.fullscreenEnabled && !document.fullscreenElement) {
      this.root.requestFullscreen().catch(() => {});
    } else if (!on && document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
  }

  async toggleToc() {
    if (!this.toc.hidden) {
      this.toc.hidden = true;
      return;
    }
    const list = this.toc.querySelector("[data-toc-list]");
    if (!list.children.length) {
      const { chapters } = await getJSON(`${this.root.dataset.api}/toc`);
      list.append(...chapters.map((chapter) =>
        h("li", {}, h("button", { type: "button", "data-chapter": chapter.number, text: `${chapter.number}. ${chapter.title}` }))));
      list.addEventListener("click", (event) => this.openChapter(event.target.closest("[data-chapter]")));
    }
    for (const button of list.querySelectorAll("button")) {
      button.setAttribute("aria-current", String(Number(button.dataset.chapter) === this.cursor?.chapter));
    }
    this.toc.hidden = false;
  }

  async openChapter(button) {
    if (!button) return;
    this.toc.hidden = true;
    try {
      await this.show(await this.pager.cursorFor(Number(button.dataset.chapter), 0));
    } catch (error) {
      this.setStatus(error.message);
    }
  }

  actions() {
    return {
      next: () => this.turn(1),
      prev: () => this.turn(-1),
      toc: () => this.toggleToc(),
      smaller: () => this.changeSize(-1),
      larger: () => this.changeSize(1),
      paper: () => {
        this.settings.paper = (this.settings.paper + 1) % PAPERS.length;
        this.applySettings();
      },
      full: () => this.setImmersive(!this.root.classList.contains("is-immersive")),
      listen: () => this.listenPanel.toggle(),
      speak: () => this.narrator.toggle(),
      silence: () => this.narrator.stop(),
      close: () => {
        if (this.listenPanel.isOpen) this.listenPanel.close();
        else if (!this.toc.hidden) this.toc.hidden = true;
        else if (this.root.classList.contains("is-immersive")) this.setImmersive(false);
      },
    };
  }
}

const root = document.querySelector("[data-reader]");
if (root) {
  const reader = new Reader(root);
  reader.start();
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement && root.classList.contains("is-immersive")) reader.setImmersive(false);
  });
}
