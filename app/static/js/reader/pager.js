/* Chapters are fetched one at a time and cut into pages on demand.
   A "cursor" is {chapter, index}: the first page currently showing. */
import { getJSON } from "../lib/http.js";
import { paginate } from "./paginator.js";

export class Pager {
  constructor({ api, total, measure }) {
    this.api = api;
    this.total = total;
    this.measure = measure;
    this.cache = new Map();
    this.pending = new Map();
  }

  /* Forget every page cut so far (the page size or text size changed). */
  reset() {
    this.cache.clear();
  }

  load(number) {
    if (number < 1 || number > this.total) return Promise.resolve(null);
    if (this.cache.has(number)) return Promise.resolve(this.cache.get(number));
    if (!this.pending.has(number)) {
      const request = getJSON(`${this.api}/chapters/${number}`)
        .then((chapter) => {
          const record = { title: chapter.title, pages: paginate(chapter, this.measure) };
          this.cache.set(number, record);
          return record;
        })
        .finally(() => this.pending.delete(number));
      this.pending.set(number, request);
    }
    return this.pending.get(number);
  }

  async cursorFor(chapter, ratio) {
    const { pages } = await this.load(chapter);
    const index = Math.min(pages.length - 1, Math.floor(Math.max(0, ratio) * pages.length));
    return { chapter, index };
  }

  async ratioOf(cursor) {
    const { pages } = await this.load(cursor.chapter);
    return cursor.index / pages.length;
  }

  /* Move up to |delta| pages, stopping at the ends of the book. */
  async walk(cursor, delta) {
    const step = Math.sign(delta);
    let current = cursor;
    let taken = 0;

    for (let count = Math.abs(delta); count > 0; count--) {
      const here = await this.load(current.chapter);
      const index = current.index + step;
      if (index >= 0 && index < here.pages.length) {
        current = { chapter: current.chapter, index };
      } else {
        const next = await this.load(current.chapter + step);
        if (!next) break;
        current = { chapter: current.chapter + step, index: step > 0 ? 0 : next.pages.length - 1 };
      }
      taken += 1;
    }
    return { cursor: current, taken };
  }

  /* The page `offset` pages from the cursor, or null past either end of the book. */
  async entryAt(cursor, offset) {
    const { cursor: target, taken } = await this.walk(cursor, offset);
    if (taken !== Math.abs(offset)) return null;
    const record = await this.load(target.chapter);
    return { ...target, page: record.pages[target.index], count: record.pages.length, title: record.title };
  }
}
