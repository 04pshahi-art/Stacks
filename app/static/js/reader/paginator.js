/* Splits a chapter into pages that exactly fill one sheet of paper.
   It measures with a hidden sheet that has the same size and styles as the real
   ones, so every page break is where the browser would really run out of room. */
import { h } from "../lib/dom.js";

function buildBlock(block) {
  if (block.kind === "title") {
    return h("header", { class: "sheet__head" },
      h("p", { class: "sheet__kicker", text: block.kicker }),
      h("h2", { class: "sheet__chapter", text: block.text }));
  }
  if (block.kind === "img") return buildFigure(block);
  return h("p", { class: block.cont ? "is-cont" : "", text: block.text });
}

/* A picture. Its shape is known up front (--ratio), so a page can be measured
   before the image has loaded, and CSS keeps it within the page. */
function buildFigure(block) {
  const figure = h("figure", { class: "sheet__figure" },
    h("img", { src: block.url, alt: block.alt, width: block.width, height: block.height, decoding: "async" }));
  figure.style.setProperty("--ratio", String(block.width / block.height));
  return figure;
}

const toBlock = (item) => item.type === "image"
  ? { kind: "img", url: item.url, alt: item.alt, width: item.width, height: item.height }
  : { kind: "p", text: item.text };

/* What a page says out loud: chapter heading and paragraphs, no pictures. */
export function pageText(page) {
  return page.blocks
    .map((block) => {
      if (block.kind === "title") return `${block.kicker}. ${block.text}.`;
      return block.kind === "p" ? block.text : "";
    })
    .filter(Boolean)
    .join("\n");
}

/* Fill a sheet with a page (or empty it when there is no page). Returns its body. */
export function mountSheet(sheet, page, label = "") {
  if (!page) {
    sheet.replaceChildren();
    return null;
  }
  const body = h("div", { class: "sheet__body" }, page.blocks.map(buildBlock));
  sheet.replaceChildren(body, h("div", { class: "sheet__num", text: label }));
  return body;
}

const fits = (body) => body.scrollHeight <= body.clientHeight + 1;

/* The most words of a paragraph that still fit on the current page, or null. */
function splitToFit(block, body) {
  const words = block.text.split(" ");
  const node = buildBlock(block);
  body.append(node);

  let low = 0;
  let high = words.length - 1;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    node.textContent = words.slice(0, middle).join(" ");
    if (fits(body)) low = middle;
    else high = middle - 1;
  }
  node.remove();

  if (low === 0) return null;
  return {
    head: { ...block, text: words.slice(0, low).join(" ") },
    tail: { kind: "p", cont: true, text: words.slice(low).join(" ") },
  };
}

export function paginate(chapter, measure) {
  const body = mountSheet(measure, { blocks: [] }, "00");
  const pages = [];
  let blocks = [];

  const finishPage = () => {
    if (blocks.length) pages.push({ blocks });
    blocks = [];
    body.replaceChildren();
  };

  const queue = [
    { kind: "title", kicker: `Chapter ${chapter.number}`, text: chapter.title },
    ...chapter.blocks.map(toBlock),
  ];

  while (queue.length) {
    const block = queue.shift();
    const node = buildBlock(block);
    body.append(node);

    if (fits(body)) {
      blocks.push(block);
      continue;
    }
    node.remove();

    const split = block.kind === "p" ? splitToFit(block, body) : null;
    if (split) {
      blocks.push(split.head);
      queue.unshift(split.tail);
    } else if (blocks.length) {
      queue.unshift(block); // does not fit here at all: start the next page with it
    } else {
      blocks.push(block); // taller than a whole page: keep it rather than loop forever
    }
    finishPage();
  }
  finishPage();
  return pages.length ? pages : [{ blocks: [] }];
}
