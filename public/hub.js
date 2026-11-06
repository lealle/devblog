"use strict";

// This public interface MUST NOT fetch or embed content from private repositories.
const $ = id => document.getElementById(id);
const PAGE_SIZE = 24;
const KINDS = new Set(["all", "design", "experience"]);
const state = { items: [], kind: "all", category: "", query: "", matches: [], visible: 0 };

function normalize(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase("ko-KR");
}

function allowedPreviewUrl(raw) {
  try {
    const url = new URL(raw);
    return url.protocol === "https:" &&
      url.hostname === "lealle.github.io" &&
      url.pathname.startsWith("/design-atlas/") ? url.href : "#";
  } catch {
    return "#";
  }
}

function blogSearchUrl() {
  return "./search.html" + (state.query.trim() ? "?q=" + encodeURIComponent(state.query.trim()) : "");
}

function updateLinks() {
  $("blog-search").href = blogSearchUrl();
  $("blog-search-hero").href = blogSearchUrl();
}

function updateAddress() {
  const params = new URLSearchParams();
  if (state.kind !== "all") params.set("type", state.kind);
  if (state.query) params.set("q", state.query);
  history.replaceState(null, "", location.pathname + (params.size ? "?" + params : ""));
}

function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = String(text);
  return el;
}

function updateCategories() {
  const field = $("category"), labels = new Map();
  for (const item of state.items) {
    if (state.kind !== "all" && state.kind !== item.kind) continue;
    labels.set(item.category, item.category_label || item.category);
  }
  const sorted = [...labels].sort((a, b) => a[1].localeCompare(b[1], "ko"));
  field.replaceChildren(new Option("모든 분야", ""));
  for (const [id, label] of sorted) field.add(new Option(label, id));
  if (!labels.has(state.category)) state.category = "";
  field.value = state.category;
}

function matchScore(item, tokens) {
  const title = normalize(item.title);
  const desc = normalize(item.description);
  const category = normalize(item.category_label);
  const searchable = [title, desc, category, item.style || "", item.number || ""].join(" ");
  if (!tokens.every(token => normalize(searchable).includes(token))) return -1;
  return tokens.reduce((sum, token) => sum +
    (title.includes(token) ? 8 : 0) +
    (category.includes(token) ? 4 : 0) +
    (desc.includes(token) ? 2 : 0), 0);
}

function renderCard(item) {
  const card = element("article", "resource");
  const type = item.kind === "design" ? "DESIGN" : "EXPERIENCE";
  card.append(element("span", "type", type + " · " + item.number));
  card.append(element("h3", "", item.title));
  card.append(element("p", "", item.description || item.style || "상세 화면을 확인하세요."));
  const actions = element("div", "actions");
  const link = element("a", "", "실제 화면 열기 ↗");
  link.href = allowedPreviewUrl(item.url);
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  actions.append(link);
  card.append(actions);
  return card;
}

function renderMore() {
  const fragment = document.createDocumentFragment();
  const end = Math.min(state.visible + PAGE_SIZE, state.matches.length);
  for (let i = state.visible; i < end; i++) fragment.append(renderCard(state.matches[i]));
  if (!state.matches.length) {
    fragment.append(element("p", "empty", "일치하는 디자인이 없습니다. 검색어 또는 분야를 바꿔 보세요."));
  }
  $("results").append(fragment);
  state.visible = end;
  $("load-more").hidden = end >= state.matches.length;
  $("status").textContent = state.matches.length + "개 중 " + state.visible + "개 표시 · 기술 문서는 별도 전체 검색";
}

function search() {
  const tokens = normalize(state.query).trim().split(/\s+/).filter(Boolean);
  state.matches = state.items.filter(item =>
    (state.kind === "all" || state.kind === item.kind) &&
    (!state.category || state.category === item.category)
  ).map(item => ({ item, score: matchScore(item, tokens) }))
    .filter(entry => entry.score >= 0)
    .sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title, "ko"))
    .map(entry => entry.item);
  state.visible = 0;
  $("results").replaceChildren();
  renderMore();
  updateLinks();
  updateAddress();
}

function setKind(kind, scroll = false) {
  if (!KINDS.has(kind)) return;
  state.kind = kind;
  for (const button of document.querySelectorAll(".kind-filter [data-kind]")) {
    button.setAttribute("aria-pressed", String(button.dataset.kind === kind));
  }
  updateCategories();
  search();
  if (scroll) $("discovery-title").scrollIntoView({ behavior: "smooth", block: "start" });
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
  for (const button of document.querySelectorAll("[data-kind]")) {
    button.addEventListener("click", () => setKind(button.dataset.kind, !button.closest(".kind-filter")));
  }
  $("category").addEventListener("change", () => {
    state.category = $("category").value;
    search();
  });
  $("load-more").addEventListener("click", renderMore);
  fetch("./hub-data.json", { cache: "no-cache" })
    .then(response => {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(data => {
      if (data.schema !== 2 || !Array.isArray(data.items)) throw new Error("Invalid public catalog");
      state.items = data.items.filter(item =>
        item && ["design", "experience"].includes(item.kind) &&
        typeof item.title === "string" && typeof item.url === "string"
      );
      for (const [id, key] of [["design-count", "designs"], ["experience-count", "experiences"]]) {
        if (Number.isInteger(data.counts?.[key])) $(id).textContent = String(data.counts[key]);
      }
      setKind(state.kind);
    })
    .catch(() => {
      $("status").textContent = "공개 디자인 목록을 불러오지 못했습니다. Design Atlas 원본 페이지에서 확인할 수 있습니다.";
    });
}

initialize();
