let animate = null;
let createScope = null;
try {
  ({ animate, createScope } = await import("/vendor/anime.esm.min.js"));
} catch {
  // Review remains fully usable if the optional motion layer cannot load.
}

const tokenFromUrl = new URLSearchParams(location.search).get("session");
if (tokenFromUrl) {
  sessionStorage.setItem("review-session", tokenFromUrl);
  history.replaceState({}, "", location.pathname);
}
const token = sessionStorage.getItem("review-session") || "";
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const dashboard = document.querySelector("#dashboard");
const flow = document.querySelector("#review-flow");
const loading = document.querySelector("#loading");
const errorState = document.querySelector("#error-state");
const toast = document.querySelector("#toast");
let cards = [];
let initialTotal = 0;
let currentIndex = 0;
let activeCategory = "";
let saveTimer = null;
let scope = null;

const label = value => String(value || "").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET") headers["X-Review-Token"] = token;
  const response = await fetch(path, { ...options, headers });
  const value = await response.json().catch(() => ({ error: "The server returned an unreadable response." }));
  if (!response.ok) {
    const error = new Error(value.error || `Request failed with status ${response.status}`);
    error.payload = value;
    error.status = response.status;
    throw error;
  }
  return value;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== undefined && value !== null) node.setAttribute(key, value);
  });
  for (const child of Array.isArray(children) ? children : [children]) {
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 4500);
}

function animateIn(target) {
  scope?.revert();
  if (reduceMotion || !animate || !createScope) return;
  scope = createScope({ root: target }).add(() => {
    animate(target, { opacity: [0, 1], y: [18, 0], duration: 340, ease: "outQuad" });
  });
}

function groupedCards() {
  return cards.reduce((groups, card) => {
    (groups[card.category] ||= []).push(card);
    return groups;
  }, {});
}

function renderDashboard() {
  flow.hidden = true;
  dashboard.hidden = false;
  dashboard.replaceChildren();
  const count = cards.length;
  const reviewButton = el("button", { class: "primary", type: "button", onclick: () => openFlow(0) },
    count ? `Review ${count} ${count === 1 ? "item" : "items"}` : "Review complete");
  reviewButton.disabled = count === 0;
  const hero = el("div", { class: "hero" }, [
    el("div", { class: "hero-grid" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, count ? "Ready for review" : "Inbox clear"),
        el("h1", {}, count ? "Turn evidence into governed decisions." : "You are all caught up."),
        el("p", {}, count
          ? "Review each evidence-backed proposal, refine its fields, and decide what reaches the canonical trackers."
          : "There are no pending proposals. New validated ingestion proposals will appear here."),
        reviewButton,
      ]),
      el("div", { class: "count-lockup", "aria-label": `${count} items ready for review` }, [
        el("span", { class: "count-number" }, count),
        el("span", { class: "count-label" }, "Items ready for review"),
      ]),
    ]),
  ]);
  dashboard.append(hero);
  if (count) {
    const section = el("section", { class: "category-section", "aria-labelledby": "category-heading" }, [
      el("h2", { id: "category-heading" }, "Review by category"),
    ]);
    const grid = el("div", { class: "category-grid" });
    Object.entries(groupedCards()).forEach(([category, items]) => {
      grid.append(el("button", {
        class: `category-card category-${category}`, type: "button",
        onclick: () => openFlow(cards.findIndex(card => card.category === category)),
        "aria-label": `Review ${items.length} ${label(category)} items`,
      }, [el("span", {}, label(category)), el("strong", {}, items.length)]));
    });
    section.append(grid);
    dashboard.append(section);
  }
  animateIn(dashboard);
}

function progress() {
  const remaining = cards.length;
  const completed = Math.max(0, initialTotal - remaining);
  const total = Math.max(initialTotal, remaining);
  const percent = total ? Math.round((completed / total) * 100) : 100;
  return el("div", { class: "progress-shell" }, [
    el("div", { class: "progress-copy" }, [
      el("span", {}, `${completed} completed`),
      el("span", {}, `${remaining} left`),
    ]),
    el("div", { class: "progress-track", role: "progressbar", "aria-label": "Review progress",
      "aria-valuemin": "0", "aria-valuemax": String(total), "aria-valuenow": String(completed) },
      el("div", { class: "progress-value", style: `width:${percent}%` })),
  ]);
}

function currentRows(row) {
  if (!row) return el("p", {}, "The tracker row is no longer available.");
  const list = el("dl");
  Object.entries(row).filter(([, value]) => value !== "").forEach(([key, value]) => {
    list.append(el("dt", {}, key), el("dd", {}, value));
  });
  return list;
}

function comparison(card) {
  if (card.action !== "update") return document.createDocumentFragment();
  return el("details", { class: "comparison" }, [
    el("summary", {}, `Compare with current tracker row ${card.tracker_id || ""}`),
    el("div", { class: "comparison-grid" }, [
      el("div", {}, [el("h3", {}, "Current tracker row"), currentRows(card.current_row)]),
      el("div", {}, [el("h3", {}, "Proposed change"), currentRows(card.fields)]),
    ]),
  ]);
}

function normalizeDate(value) {
  const match = String(value || "").match(/^\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : "";
}

function fieldControl(card, definition) {
  const name = definition.name;
  const id = `field-${card.proposal_id}-${name.replace(/[^a-z0-9]/gi, "-")}`;
  const value = card.fields[name] ?? "";
  let input;
  if (definition.enum) {
    input = el("select", { id, name });
    input.append(el("option", { value: "" }, "Select an option"));
    definition.enum.forEach(option => input.append(el("option", { value: option }, label(option))));
    input.value = value;
  } else if (definition.computed) {
    input = el("input", { id, name, value, readonly: "", "aria-describedby": `${id}-hint` });
  } else if (definition.type === "date") {
    input = el("input", { id, name, type: "date", value: normalizeDate(value) });
  } else if (definition.type === "number") {
    input = el("input", { id, name, type: "number", value, step: "0.1",
      min: definition.minimum, max: definition.maximum, inputmode: "decimal" });
  } else if (/description|statement|mitigation|rationale|notes|actions|resolution|impact if|contingency|plan/i.test(name)) {
    input = el("textarea", { id, name }, value);
  } else {
    input = el("input", { id, name, type: "text", value });
  }
  if (definition.required) input.required = true;
  if (!definition.computed) input.addEventListener("input", () => scheduleSave(card));
  const labelChildren = [name];
  if (definition.required) {
    labelChildren.push(
      el("span", { class: "required-marker", "aria-hidden": "true" }, " *"),
      el("span", { class: "sr-only" }, " required"),
    );
  }
  const wrapper = el("div", { class: `field ${input.tagName === "TEXTAREA" ? "field-wide" : ""}` }, [
    el("label", { for: id }, labelChildren), input,
  ]);
  if (definition.computed) wrapper.append(el("small", { id: `${id}-hint` }, "Calculated from the proposal inputs."));
  return wrapper;
}

function orderedFieldSchema(card) {
  const fields = [...card.field_schema];
  const titleIndex = fields.findIndex(definition => definition.name.endsWith(" Title"));
  if (titleIndex < 0) return fields;
  const [title] = fields.splice(titleIndex, 1);
  const statementIndex = fields.findIndex(definition => definition.name === "Statement");
  if (statementIndex < 0) return [title, ...fields];
  const [statement] = fields.splice(statementIndex, 1);
  return [title, statement, ...fields];
}

function collectFields(card) {
  const form = document.querySelector("#proposal-form");
  const fields = {};
  for (const definition of card.field_schema) {
    const input = form.elements.namedItem(definition.name);
    if (!input) continue;
    if (input.value !== "" || Object.hasOwn(card.fields, definition.name)) {
      fields[definition.name] = definition.type === "number" && input.value !== "" ? Number(input.value) : input.value;
    }
  }
  return fields;
}

function riskDerived(card, fields) {
  if (card.category !== "risk") return;
  const weights = { very_low: .05, low: .1, moderate: .2, medium: .2, high: .4, very_high: .8, critical: .8 };
  const score = Number(fields.Probability) * weights[fields.Impact];
  if (!Number.isFinite(score)) return;
  fields["Risk Score"] = Number(score.toFixed(3));
  fields["Calculated Severity"] = score >= .5 ? "Sev 1" : score >= .2 ? "Sev 2" : "Sev 3";
  const form = document.querySelector("#proposal-form");
  for (const name of ["Risk Score", "Calculated Severity"]) {
    const input = form.elements.namedItem(name);
    if (input) input.value = fields[name];
  }
}

function renderValidation(problems = []) {
  const target = document.querySelector("#validation");
  if (!target) return;
  target.replaceChildren();
  target.hidden = problems.length === 0;
  if (!problems.length) return;
  target.append(el("h3", {}, "Resolve before accepting"));
  const list = el("ul");
  problems.forEach(problem => list.append(el("li", {}, problem)));
  target.append(list);
}

async function save(card) {
  clearTimeout(saveTimer);
  const state = document.querySelector("#save-state");
  const fields = collectFields(card);
  riskDerived(card, fields);
  state.textContent = "Saving changes";
  try {
    const result = await api("/api/autosave", { method: "POST", body: JSON.stringify({
      proposal_id: card.proposal_id, revision: card.revision, fields,
    }) });
    card.fields = fields;
    card.revision = result.revision;
    state.textContent = result.validation.length ? "Saved with validation needs" : "All changes saved";
    renderValidation(result.validation);
  } catch (error) {
    state.textContent = "Changes not saved";
    renderValidation([error.message]);
    if (error.status === 409) showToast("This proposal changed elsewhere. Reload the inbox before continuing.");
    throw error;
  }
}

function scheduleSave(card) {
  const state = document.querySelector("#save-state");
  state.textContent = "Unsaved changes";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => save(card).catch(() => {}), 350);
}

function evidence(card) {
  const section = el("section", { class: "evidence", "aria-labelledby": "evidence-title" }, [
    el("h3", { id: "evidence-title" }, "Source evidence"),
  ]);
  const list = el("div", { class: "evidence-list" });
  const entries = card.evidence.length ? card.evidence : card.source_refs.map(source_ref => ({ source_ref, excerpt: "" }));
  entries.forEach(entry => {
    const lines = entry.line_start ? `, lines ${entry.line_start}${entry.line_end ? `–${entry.line_end}` : ""}` : "";
    list.append(el("article", { class: "evidence-item" }, [
      el("div", { class: "source-ref" }, `${entry.source_ref || "Unknown source"}${lines}`),
      el("p", { class: "excerpt" }, entry.excerpt || "No excerpt was captured for this older proposal."),
    ]));
  });
  section.append(list);
  return section;
}

async function ensureSaved(card) {
  clearTimeout(saveTimer);
  const fields = collectFields(card);
  if (JSON.stringify(fields) !== JSON.stringify(card.fields)) await save(card);
}

async function decide(card, decision) {
  const note = document.querySelector("#reviewer-note").value.trim();
  const buttons = [...document.querySelectorAll(".actions button")];
  buttons.forEach(button => { button.disabled = true; });
  try {
    await ensureSaved(card);
    const body = { proposal_id: card.proposal_id, revision: card.revision };
    let result;
    if (decision === "accept") {
      result = await api("/api/accept", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(body) });
      showToast(`Accepted and written as ${result.tracker_id}.`);
    } else if (decision === "reject") {
      result = await api("/api/reject", { method: "POST", body: JSON.stringify({ ...body, reason: note }) });
      showToast("Rejected. No tracker row was written.");
    } else {
      result = await api("/api/flag", { method: "POST", body: JSON.stringify({ ...body, note }) });
      card.revision = result.revision;
      card.review = { state: "flagged", clarification_note: note };
      showToast("Flagged for AI review and kept in the pending inbox.");
      renderCard();
      return;
    }
    cards.splice(currentIndex, 1);
    if (!cards.length) {
      renderDashboard();
      return;
    }
    currentIndex = Math.min(currentIndex, cards.length - 1);
    renderCard();
  } catch (error) {
    renderValidation(error.payload?.validation || [error.message]);
    buttons.forEach(button => { button.disabled = false; });
  }
}

function categoryNavigation() {
  const nav = el("nav", { class: "category-nav", "aria-label": "Proposal categories" });
  Object.entries(groupedCards()).forEach(([category, items]) => {
    nav.append(el("button", { class: `quiet category-${category}`, type: "button",
      "aria-current": category === activeCategory ? "true" : "false",
      onclick: () => { currentIndex = cards.findIndex(card => card.category === category); renderCard(); },
    }, `${label(category)} (${items.length})`));
  });
  return nav;
}

function renderCard() {
  if (!cards.length) { renderDashboard(); return; }
  clearTimeout(saveTimer);
  const card = cards[currentIndex];
  activeCategory = card.category;
  flow.replaceChildren(progress());
  const article = el("article", { class: `review-card category-${card.category}`, "aria-label": `${card.category_label} review` });
  const form = el("form", { id: "proposal-form", novalidate: "" });
  const grid = el("div", { class: "field-grid" });
  orderedFieldSchema(card).forEach(definition => grid.append(fieldControl(card, definition)));
  form.append(grid);
  article.append(
    form,
    el("span", { class: "save-state form-status", id: "save-state", role: "status" }, "All changes saved"),
    el("div", { id: "validation", class: "validation", hidden: "", role: "alert" }),
    comparison(card),
    evidence(card),
  );
  if (card.review?.state === "flagged") {
    article.append(el("div", { class: "flagged-state" }, [
      el("strong", {}, "Flagged for AI review"),
      el("p", {}, card.review.clarification_note || "No clarification note was supplied."),
    ]));
  }
  article.append(el("div", { class: "reviewer-note field" }, [
    el("label", { for: "reviewer-note" }, "Optional reviewer note"),
    el("textarea", { id: "reviewer-note", placeholder: "Add a reject reason or clarify what AI should review." },
      card.review?.clarification_note || ""),
  ]));
  article.append(el("div", { class: "actions", "aria-label": "Review decision" }, [
    el("button", { class: "primary", type: "button", onclick: () => decide(card, "accept") }, "Accept and write tracker"),
    el("button", { class: "danger", type: "button", onclick: () => decide(card, "reject") }, "Reject"),
    el("button", { class: "secondary", type: "button", onclick: () => decide(card, "flag") }, "Flag for AI review"),
  ]));
  article.append(el("div", { class: "navigation" }, [
    el("button", { class: "quiet", type: "button", disabled: currentIndex === 0 ? "" : undefined,
      onclick: () => { currentIndex -= 1; renderCard(); } }, "Previous"),
    el("button", { class: "quiet", type: "button", onclick: renderDashboard }, "Back to inbox"),
    el("button", { class: "quiet", type: "button", disabled: currentIndex >= cards.length - 1 ? "" : undefined,
      onclick: () => { currentIndex += 1; renderCard(); } }, "Next"),
  ]));
  flow.append(el("div", { class: "flow-layout" }, [categoryNavigation(), article]));
  riskDerived(card, card.fields);
  animateIn(article);
  article.querySelector("input, select, textarea")?.focus({ preventScroll: true });
}

function openFlow(index) {
  if (!cards.length) return;
  currentIndex = Math.max(0, index);
  dashboard.hidden = true;
  flow.hidden = false;
  renderCard();
}

async function loadInbox() {
  try {
    const result = await api("/api/inbox");
    cards = result.cards;
    initialTotal = cards.length;
    loading.hidden = true;
    renderDashboard();
  } catch (error) {
    loading.hidden = true;
    errorState.hidden = false;
    errorState.append(el("p", { class: "eyebrow" }, "Unable to load"),
      el("h1", {}, "The review inbox is unavailable."), el("p", {}, error.message));
  }
}

window.addEventListener("beforeunload", () => scope?.revert());
loadInbox();
