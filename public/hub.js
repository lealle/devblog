"use strict";

const $ = (id) => document.getElementById(id);
const PAGE_SIZE = 24;
const ALLOWED_KINDS = new Set(["all", "prompt", "design", "experience"]);
const ALLOWED_HOSTS = new Set(["github.com", "lealle.github.io"]);
const state = { items: [], kind: "all", category: "", query: "", matches: [], visible: 0, selected: null };
let lastTrigger = null;

function normalize(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase("ko-KR");
}

function safeUrl(raw) {
  try {
    const url = new URL(raw);
    return url.protocol === "https:" && ALLOWED_HOSTS.has(url.hostname) ? url.href : "#";
  } catch {
    return "#";
  }
}

function blogSearchUrl() {
  const query = state.query.trim();
  return "./search.html" + (query ? "?q=" + encodeURIComponent(query) : "");
}

function updateLinks() {
  $("blog-search").href = blogSearchUrl();
  $("blog-search-hero").href = blogSearchUrl();
}

function updateAddress() {
  const params = new URLSearchParams();
  if (state.kind !== "all") params.set("type", state.kind);
  if (state.query) params.set("q", state.query);
  const url = location.pathname + (params.toString() ? "?" + params.toString() : "");
  history.replaceState(null, "", url);
}

function makeElement(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = String(text);
  return el;
}

function updateCategoryOptions() {
  const field = $("category");
  const current = state.category;
  const labels = new Map();
  for (const item of state.items) {
    if (state.kind !== "all" && item.kind !== state.kind) continue;
    labels.set(item.category, item.category_label || item.category);
  }
  const sorted = [...labels].sort((a, b) => a[1].localeCompare(b[1], "ko"));
  field.replaceChildren(new Option("모든 분야", ""));
  for (const [id, label] of sorted) field.add(new Option(label, id));
  if (!labels.has(current)) state.category = "";
  field.value = state.category;
}

function rank(item, tokens) {
  const title = normalize(item.title);
  const desc = normalize(item.description);
  const category = normalize(item.category_label);
  const content = normalize(item.content);
  const haystack = [title, desc, category, content, item.number || ""].join(" ");
  if (!tokens.every(token => haystack.includes(token))) return -1;
  return tokens.reduce((score, token) => score
    + (title.includes(token) ? 8 : 0)
    + (category.includes(token) ? 4 : 0)
    + (desc.includes(token) ? 2 : 0)
    + (content.includes(token) ? 1 : 0), 0);
}

function search() {
  const tokens = normalize(state.query).trim().split(/\s+/).filter(Boolean);
  state.matches = state.items.filter(item =>
    (state.kind === "all" || item.kind === state.kind) &&
    (!state.category || item.category === state.category)
  ).map(item => ({ item, score: rank(item, tokens) }))
    .filter(entry => entry.score >= 0)
    .sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title, "ko"))
    .map(entry => entry.item);
  state.visible = 0;
  $("results").replaceChildren();
  renderMore();
  updateLinks();
  updateAddress();
}

function renderCard(item) {
  const card = makeElement("article", "resource");
  card.append(makeElement("span", "type",
    item.kind === "prompt" ? "PROMPT · " + item.category_label :
    item.kind === "design" ? "DESIGN · " + item.number :
    "EXPERIENCE · " + item.number));
  card.append(makeElement("h3", "", item.title));
  card.append(makeElement("p", "", item.description || item.style || "상세 자료를 확인하세요."));
  const actions = makeElement("div", "actions");
  if (item.kind === "prompt") {
    const preview = makeElement("button", "", "내용 확인 · 복사");
    preview.type = "button";
    preview.addEventListener("click", () => openPrompt(item, preview));
    actions.append(preview);
  }
  const source = makeElement("a", "", item.kind === "prompt" ? "GitHub 원문 ↗" : "실제 화면 보기 ↗");
  source.href = safeUrl(item.url);
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  actions.append(source);
  card.append(actions);
  return card;
}

function renderMore() {
  const frag = document.createDocumentFragment();
  const end = Math.min(state.visible + PAGE_SIZE, state.matches.length);
  for (let i = state.visible; i < end; i++) frag.append(renderCard(state.matches[i]));
  if (!state.matches.length) {
    frag.append(makeElement("p", "empty", "일치하는 자료가 없습니다. 검색어 또는 분야를 바꿔 보세요."));
  }
  $("results").append(frag);
  state.visible = end;
  $("load-more").hidden = end >= state.matches.length;
  $("status").textContent = state.matches.length + "개 자료 중 " + state.visible + "개 표시 · 기술 블로그는 별도 전체 검색에서 확인";
}

function setKind(kind, scroll = false) {
  if (!ALLOWED_KINDS.has(kind)) return;
  state.kind = kind;
  for (const button of document.querySelectorAll("[data-kind]")) {
    if (button.matches(".kind-filter button")) {
      button.setAttribute("aria-pressed", String(button.dataset.kind === kind));
    }
  }
  updateCategoryOptions();
  search();
  if (scroll) $("discovery-title").scrollIntoView({ behavior: "smooth", block: "start" });
}

function openPrompt(item, trigger) {
  state.selected = item;
  lastTrigger = trigger;
  $("detail-title").textContent = item.title;
  $("detail-description").textContent = item.description || item.category_label;
  $("detail-content").textContent = item.content || "본문이 없습니다. 원문을 확인하세요.";
  $("detail-source").href = safeUrl(item.url);
  $("copy-status").textContent = "";
  $("detail").hidden = false;
  $("detail").setAttribute("tabindex", "-1");
  $("detail").scrollIntoView({ behavior: "smooth", block: "start" });
  $("detail").focus({ preventScroll: true });
}

function closePrompt() {
  $("detail").hidden = true;
  state.selected = null;
  if (lastTrigger && lastTrigger.isConnected) lastTrigger.focus();
}

async function copyPrompt() {
  if (!state.selected) return;
  const content = state.selected.content;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(content);
    } else {
      const helper = document.createElement("textarea");
      helper.value = content;
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.append(helper);
      helper.select();
      const success = document.execCommand("copy");
      helper.remove();
      if (!success) throw new Error("copy not supported");
    }
    $("copy-status").textContent = "프롬프트가 복사되었습니다. [입력] 부분을 바꿔 사용하세요.";
  } catch {
    $("copy-status").textContent = "자동 복사가 불가능합니다. 위 텍스트를 직접 선택해 복사해 주세요.";
  }
}

function initialize() {
  const params = new URLSearchParams(location.search);
  const initialKind = params.get("type") || "all";
  state.kind = ALLOWED_KINDS.has(initialKind) ? initialKind : "all";
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
    button.addEventListener("click", () => setKind(button.dataset.kind, !button.matches(".kind-filter button")));
  }
  $("category").addEventListener("change", () => {
    state.category = $("category").value;
    search();
  });
  $("load-more").addEventListener("click", renderMore);
  $("detail-close").addEventListener("click", closePrompt);
  $("copy-prompt").addEventListener("click", copyPrompt);
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !$("detail").hidden) closePrompt();
  });

  fetch("./hub-data.json", { cache: "no-cache" })
    .then(response => {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(data => {
      if (data.schema !== 1 || !Array.isArray(data.items)) throw new Error("Invalid catalog");
      state.items = data.items.filter(item =>
        item && ALLOWED_KINDS.has(item.kind) && item.kind !== "all" &&
        typeof item.title === "string" && typeof item.url === "string"
      );
      for (const [id, key] of [
        ["prompt-count", "prompts"],
        ["design-count", "designs"],
        ["experience-count", "experiences"],
      ]) {
        if (Number.isInteger(data.counts?.[key])) $(id).textContent = String(data.counts[key]);
      }
      setKind(state.kind);
    })
    .catch(() => {
      $("status").textContent = "자료 색인을 불러오지 못했습니다. 각 원본 저장소 링크에서 자료를 열 수 있습니다.";
    });
}

initialize();
