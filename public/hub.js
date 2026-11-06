"use strict";

// Only the publicly published Design Atlas URLs may be embedded.
// Prompt Library and DevKit are private and must not be fetched here.
const $ = id => document.getElementById(id);
const PAGE_SIZE = 12;
const KINDS = new Set(["all", "design", "experience"]);
const MODES = new Set(["blog", "home", "prompts"]);
const state = {
  items: [], kind: "all", category: "", query: "", matches: [], visible: 0,
  selected: null, mode: "blog", trigger: null, observed: null
};
const observer = "IntersectionObserver" in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const frame = entry.target;
        observer.unobserve(frame);
        const url = frame.dataset.src;
        if (url) frame.src = url;
      }
    }, { rootMargin: "260px 0px" })
  : null;

function normalize(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase("ko-KR");
}

function previewUrl(item, mode = "blog") {
  if (!item || !["design", "experience"].includes(item.kind)) return null;
  try {
    const url = new URL(item.url);
    if (url.protocol !== "https:" ||
        url.hostname !== "lealle.github.io" ||
        !url.pathname.startsWith("/design-atlas/")) return null;
    if (item.kind === "design") {
      if (!/^\/design-atlas\/designs\/\d{3}\.html$/.test(url.pathname)) return null;
      url.searchParams.set("embed", "1");
      url.searchParams.set("mode", MODES.has(mode) ? mode : "blog");
    } else if (url.pathname !== "/design-atlas/experiences/index.html" ||
        !/^\d{1,2}$/.test(url.searchParams.get("scene") || "")) return null;
    return url.href;
  } catch {
    return null;
  }
}

function sourceUrl(item) {
  try {
    const url = new URL(item.url);
    if (url.protocol !== "https:" || url.hostname !== "lealle.github.io" ||
        !url.pathname.startsWith("/design-atlas/")) return "#";
    return url.href;
  } catch {
    return "#";
  }
}

function blogSearchUrl() {
  return "./search.html" +
    (state.query.trim() ? "?q=" + encodeURIComponent(state.query.trim()) : "");
}

function updateLinks() {
  $("blog-search").href = blogSearchUrl();
  $("blog-search-hero").href = blogSearchUrl();
}

function updateAddress() {
  const params = new URLSearchParams();
  if (state.kind !== "all") params.set("type", state.kind);
  if (state.query) params.set("q", state.query);
  history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params : ""));
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function updateCategories() {
  const field = $("category");
  const labels = new Map();
  for (const item of state.items) {
    if (state.kind !== "all" && item.kind !== state.kind) continue;
    labels.set(item.category, item.category_label || item.category);
  }
  const sorted = [...labels].sort((a, b) => a[1].localeCompare(b[1], "ko"));
  field.replaceChildren(new Option("모든 분야", ""));
  for (const [id, label] of sorted) field.add(new Option(label, id));
  if (!labels.has(state.category)) state.category = "";
  field.value = state.category;
}

function rank(item, words) {
  const title = normalize(item.title), category = normalize(item.category_label);
  const desc = normalize(item.description), style = normalize(item.style);
  const searchable = [title, desc, category, style, item.number || ""].join(" ");
  if (!words.every(word => searchable.includes(word))) return -1;
  return words.reduce((sum, word) => sum +
    (title.includes(word) ? 8 : 0) + (category.includes(word) ? 4 : 0) +
    (desc.includes(word) ? 2 : 0) + (style.includes(word) ? 1 : 0), 0);
}

function makeFrame(item, thumbnail = false) {
  const frame = document.createElement("iframe");
  frame.title = thumbnail ? item.title + " 화면 축소 미리보기" : item.title + " 실시간 미리보기";
  frame.referrerPolicy = "no-referrer";
  frame.loading = thumbnail ? "lazy" : "eager";
  if (thumbnail) {
    frame.className = "preview-thumbnail";
    frame.tabIndex = -1;
    frame.setAttribute("aria-hidden", "true");
    // Card previews are noninteractive; the full preview is accessible by button.
    frame.setAttribute("sandbox", "allow-scripts allow-same-origin");
    frame.dataset.src = previewUrl(item, "blog") || "";
    if (observer) observer.observe(frame);
    else frame.src = frame.dataset.src;
  } else {
    frame.className = "preview-full";
    frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms");
    frame.src = previewUrl(item, state.mode) || "about:blank";
  }
  return frame;
}

function renderCard(item) {
  const card = el("article", "resource");
  const visual = el("div", "resource-visual");
  const fallback = el("div", "resource-visual-fallback", "LIVE PREVIEW · " + item.number);
  visual.append(fallback);
  if (previewUrl(item)) visual.append(makeFrame(item, true));
  card.append(visual);
  const body = el("div", "resource-body");
  body.append(el("span", "type", (item.kind === "design" ? "DESIGN" : "EXPERIENCE") + " / " + item.number));
  body.append(el("h3", "", item.title));
  body.append(el("p", "", item.description || item.style || "디자인 실제 화면을 확인하세요."));
  const actions = el("div", "actions");
  const preview = el("button", "preview-action", "이 화면에서 미리보기");
  preview.type = "button";
  preview.addEventListener("click", () => showPreview(item, preview));
  const link = el("a", "", "원본 열기 ↗");
  link.href = sourceUrl(item);
  // Same-tab navigation also works in in-app browsers that block popups.
  link.rel = "noopener noreferrer";
  actions.append(preview, link);
  body.append(actions);
  card.append(body);
  return card;
}

function renderMore() {
  const fragment = document.createDocumentFragment();
  const end = Math.min(state.visible + PAGE_SIZE, state.matches.length);
  for (let i = state.visible; i < end; i++) fragment.append(renderCard(state.matches[i]));
  if (!state.matches.length) {
    fragment.append(el("p", "empty", "일치하는 디자인이 없습니다. 필터를 해제하거나 다른 단어로 검색해 보세요."));
  }
  $("results").append(fragment);
  state.visible = end;
  $("load-more").hidden = end >= state.matches.length;
  $("status").textContent = "디자인 " + state.matches.length + "개 중 " + end + "개 표시";
}

function search() {
  const words = normalize(state.query).trim().split(/\s+/).filter(Boolean);
  state.matches = state.items.filter(item =>
    (state.kind === "all" || state.kind === item.kind) &&
    (!state.category || state.category === item.category)
  ).map(item => ({ item, score: rank(item, words) }))
    .filter(entry => entry.score >= 0)
    .sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title, "ko"))
    .map(entry => entry.item);
  // Disconnect previews before removing the old cards, avoiding stale observers.
  if (observer) document.querySelectorAll(".preview-thumbnail").forEach(frame => observer.unobserve(frame));
  state.visible = 0;
  $("results").replaceChildren();
  renderMore();
  updateLinks();
  updateAddress();
}

function setKind(kind, scroll = false) {
  if (!KINDS.has(kind)) return;
  state.kind = kind;
  document.querySelectorAll(".kind-filter [data-kind]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.kind === kind));
  });
  updateCategories();
  search();
  if (scroll) $("discovery-title").scrollIntoView({ behavior: "smooth", block: "start" });
}

function showPreview(item, trigger) {
  const url = previewUrl(item);
  if (!url) return;
  state.selected = item;
  state.trigger = trigger;
  state.mode = "blog";
  $("preview-title").textContent = item.title;
  $("preview-context").textContent = item.kind === "design" ?
    "실제 Design Atlas 시안 · 화면 전환 가능" : "체험형 디자인 · 실제 조작 가능";
  $("preview-original").href = sourceUrl(item);
  $("preview-modes").hidden = item.kind !== "design";
  updateModeButtons();
  const host = $("preview-viewport");
  host.replaceChildren(makeFrame(item));
  $("preview-dialog").showModal();
}

function updateModeButtons() {
  $("preview-modes").querySelectorAll("[data-mode]").forEach(button => {
    button.setAttribute("aria-pressed", String(state.mode === button.dataset.mode));
  });
}

function switchMode(mode) {
  if (!MODES.has(mode) || !state.selected || state.selected.kind !== "design") return;
  state.mode = mode;
  updateModeButtons();
  $("preview-viewport").replaceChildren(makeFrame(state.selected));
}

function closePreview() {
  $("preview-dialog").close();
}

function restoreFocus() {
  $("preview-viewport").replaceChildren();
  if (state.trigger && state.trigger.isConnected) state.trigger.focus();
  state.selected = null;
  state.trigger = null;
}

function initialize() {
  const params = new URLSearchParams(location.search);
  const initialKind = params.get("type") || "all";
  state.kind = KINDS.has(initialKind) ? initialKind : "all";
  state.query = (params.get("q") || "").slice(0, 200);
  $("search-input").value = state.query;
  updateLinks();
  $("search-form").addEventListener("submit", event => {
    event.preventDefault();
    state.query = $("search-input").value.trim();
    search();
  });
  $("search-input").addEventListener("input", () => {
    state.query = $("search-input").value.trim();
    search();
  });
  document.querySelectorAll("[data-kind]").forEach(button => {
    button.addEventListener("click", () => setKind(button.dataset.kind, !button.closest(".kind-filter")));
  });
  $("category").addEventListener("change", () => {
    state.category = $("category").value;
    search();
  });
  $("load-more").addEventListener("click", renderMore);
  $("preview-close").addEventListener("click", closePreview);
  $("preview-dialog").addEventListener("close", restoreFocus);
  $("preview-modes").querySelectorAll("[data-mode]").forEach(button => {
    button.addEventListener("click", () => switchMode(button.dataset.mode));
  });
  fetch("./hub-data.json", { cache: "no-cache" })
    .then(response => {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(data => {
      if (data.schema !== 2 || !Array.isArray(data.items)) throw new Error("Unexpected catalog");
      state.items = data.items.filter(item =>
        item && ["design", "experience"].includes(item.kind) &&
        typeof item.title === "string" && previewUrl(item)
      );
      for (const [id, key] of [["design-count", "designs"], ["experience-count", "experiences"]]) {
        if (Number.isInteger(data.counts?.[key])) $(id).textContent = String(data.counts[key]);
      }
      setKind(state.kind);
    })
    .catch(() => {
      $("status").textContent = "디자인 목록을 불러오지 못했습니다. Design Atlas 원본 저장소 링크를 이용해 주세요.";
    });
}

initialize();
