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
const userSubmittedSource = "User Submitted";
const flow = document.querySelector("#review-flow");
const loading = document.querySelector("#loading");
const errorState = document.querySelector("#error-state");
const toast = document.querySelector("#toast");
const acceptedButton = document.querySelector("#view-accepted");
const headerTitle = document.querySelector("#header-title");
const acceptedPage = location.pathname === "/accepted";
let cards = [];
let categories = [];
let progressSummary = { pending: 0, accepted: 0, rejected: 0, flagged: 0, completed: 0, total: 0, categories: {} };
let currentIndex = 0;
let activeCategory = "";
let searchQuery = "";
let reviewFilter = "all";
let completenessFilter = "all";
let sortMode = "queue";
let fieldView = "all";
let saveTimer = null;
let filterTimer = null;
let scope = null;

const label = value => String(value || "").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
const longTextField = name => /description|statement|question|why it matters|answer|mitigation|rationale|notes|actions|resolution|impact if|contingency|plan/i.test(name);

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (token) headers["X-Review-Token"] = token;
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

function acceptedItemTitle(item) {
  const fields = item.fields || {};
  const title = item.field_schema?.find(definition => definition.name.endsWith(" Title"));
  const candidates = [fields[title?.name], fields.Name, fields.Question, fields.Statement,
    fields[item.category_label], fields.Description, item.title];
  return candidates.map(value => String(value || "").trim()).find(Boolean) || "Untitled";
}

function renderAcceptedPage(items) {
  const content = el("div", { class: "accepted-values-content" });
  let activeCategory = items[0]?.category || "";
  let selected = items[0] || null;
  const render = () => {
    content.replaceChildren();
    if (!selected) { content.append(el("p", {}, "No tracker values have been accepted yet.")); return; }
    const groups = items.reduce((result, item) => { (result[item.category] ||= []).push(item); return result; }, {});
    if (!groups[activeCategory]) {
      activeCategory = Object.keys(groups)[0];
      selected = groups[activeCategory][0];
    }
    const tabs = el("nav", { class: "category-tabs", "aria-label": "Accepted categories" });
    Object.entries(groups).forEach(([category, group]) => tabs.append(el("button", { class: `quiet category-${category}`, type: "button", "aria-current": category === activeCategory ? "true" : undefined, onclick: () => { activeCategory = category; selected = group[0]; render(); } }, `${label(category)} (${group.length})`)));
    const list = el("aside", { class: "proposal-list", "aria-label": "Accepted values" });
    groups[activeCategory].forEach(item => {
      const row = el("article", { class: `proposal-list-item category-${item.category}${item === selected ? " is-selected" : ""}` });
      row.append(el("button", { class: "proposal-list-title", type: "button", onclick: () => { selected = item; render(); } }, acceptedItemTitle(item)));
      list.append(row);
    });
    const form = el("form", { class: `accepted-editor expanded-card-content category-${selected.category}` });
    const schema = selected.field_schema || Object.keys(selected.fields)
      .filter(name => !/(^.* ID$|Source Refs|Notes|Created At|Updated At)/.test(name))
      .map(name => ({ name: name, type: /date/i.test(name) ? "date" : "text" }));
    const orderedSchema = [...schema];
    const titleIndex = orderedSchema.findIndex(definition => definition.name.endsWith(" Title"));
    if (titleIndex >= 0) orderedSchema.unshift(orderedSchema.splice(titleIndex, 1)[0]);
    const statementIndex = orderedSchema.findIndex(definition => definition.name === "Statement");
    if (statementIndex >= 0) orderedSchema.splice(1, 0, orderedSchema.splice(statementIndex, 1)[0]);
    orderedSchema.forEach(definition => {
      if (definition.computed) return;
      const value = selected.fields[definition.name] ?? "";
      const input = longTextField(definition.name) ? el("textarea", { name: definition.name }, value) : definition.enum ? el("select", { name: definition.name }) : el("input", { name: definition.name, type: definition.type === "date" ? "date" : definition.type === "number" ? "number" : "text", value });
      if (definition.enum) { input.append(el("option", { value: "" }, "Select an option")); definition.enum.forEach(option => input.append(el("option", { value: option }, label(option)))); input.value = value; }
      form.append(el("div", { class: `field${longTextField(definition.name) ? " field-wide" : ""}` }, [el("label", { for: definition.name }, definition.name), input]));
    });
    const status = el("span", { class: "save-state", role: "status" }, "");
    form.append(el("div", { class: "modal-actions" }, [el("button", { class: "primary", type: "submit" }, "Save"), status]));
    form.addEventListener("submit", async event => {
      event.preventDefault(); status.textContent = "Saving";
      const fields = Object.fromEntries(new FormData(form).entries());
      try { await api("/api/accepted/update", { method: "POST", body: JSON.stringify({ category: selected.category, tracker_id: selected.tracker_id, fields }) }); Object.assign(selected.fields, fields); selected.title = fields[`${selected.category_label} Title`] || fields.Statement || selected.title; status.textContent = "Saved"; }
      catch (error) { status.textContent = error.message || "Could not save"; }
    });
    content.append(tabs, el("div", { class: "review-layout accepted-layout" }, [list, form]));
  };
  render();
  flow.hidden = false;
  flow.replaceChildren(content);
  content.querySelector("button")?.focus();
}

function openAcceptedValues() {
  location.assign("/accepted");
}

function animateIn(target) {
  scope?.revert();
  if (reduceMotion || !animate || !createScope) return;
  scope = createScope({ root: target }).add(() => {
    animate(target, { opacity: [0, 1], y: [18, 0], duration: 340, ease: "outQuad" });
  });
}

function groupedCards() {
  const groups = Object.fromEntries(categories.map(category => [category.id, []]));
  return cards.reduce((groups, card) => {
    (groups[card.category] ||= []).push(card);
    return groups;
  }, groups);
}

function progress() {
  const { completed = 0, total = 0, pending = cards.length, accepted = 0, rejected = 0, flagged = 0 } = progressSummary;
  const percent = total ? Math.round((completed / total) * 100) : 100;
  return el("div", { class: "progress-shell" }, [
    el("div", { class: "progress-copy" }, [
      el("strong", {}, `${completed} of ${total} reviewed`),
      el("span", {}, `${pending} pending`),
    ]),
    el("div", { class: "progress-track", role: "progressbar", "aria-label": "Review progress",
      "aria-valuemin": "0", "aria-valuemax": String(total), "aria-valuenow": String(completed) },
      el("div", { class: "progress-value", style: `width:${percent}%` })),
    el("div", { class: "progress-details", "aria-label": "Review totals" }, [
      el("span", {}, `${accepted} accepted`),
      el("span", {}, `${rejected} rejected`),
      el("span", {}, `${flagged} flagged`),
    ]),
  ]);
}

function missingRequired(card) {
  return card.field_schema.filter(definition => definition.required
    && String(card.fields[definition.name] ?? "").trim() === "").length;
}

function cardSearchText(card) {
  return [cardTitle(card), card.category_label, card.review?.state,
    ...Object.values(card.fields || {}),
    ...(card.source_refs || []),
    ...(card.evidence || []).flatMap(entry => [entry.source_ref, entry.excerpt]),
  ].join(" ").toLowerCase();
}

function visibleCards() {
  const query = searchQuery.trim().toLowerCase();
  const filtered = cards.filter(card => {
    const state = card.review?.state === "flagged" ? "flagged" : "pending";
    if (query && !cardSearchText(card).includes(query)) return false;
    if (reviewFilter !== "all" && state !== reviewFilter) return false;
    const incomplete = missingRequired(card) > 0;
    if (completenessFilter === "incomplete" && !incomplete) return false;
    if (completenessFilter === "complete" && incomplete) return false;
    return true;
  });
  if (sortMode === "title") filtered.sort((a, b) => cardTitle(a).localeCompare(cardTitle(b)));
  if (sortMode === "attention") filtered.sort((a, b) => missingRequired(b) - missingRequired(a));
  return filtered;
}

function selectOption(value, text, selected) {
  return el("option", { value, selected: selected ? "" : undefined }, text);
}

function scheduleFilterRender(options = {}) {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(() => renderCategory(options), 140);
}

function triageControls(matchCount) {
  const search = el("input", { class: "triage-search", type: "search", value: searchQuery,
    placeholder: "Search titles, fields, sources, or evidence", "aria-label": "Search pending proposals" });
  search.addEventListener("input", () => {
    searchQuery = search.value;
    scheduleFilterRender({ focusSearch: true });
  });
  const review = el("select", { "aria-label": "Filter by review state" }, [
    selectOption("all", "All review states", reviewFilter === "all"),
    selectOption("pending", "Pending only", reviewFilter === "pending"),
    selectOption("flagged", "Flagged only", reviewFilter === "flagged"),
  ]);
  review.addEventListener("change", () => { reviewFilter = review.value; scheduleFilterRender(); });
  const completeness = el("select", { "aria-label": "Filter by completeness" }, [
    selectOption("all", "Any completeness", completenessFilter === "all"),
    selectOption("incomplete", "Needs required fields", completenessFilter === "incomplete"),
    selectOption("complete", "Required fields complete", completenessFilter === "complete"),
  ]);
  completeness.addEventListener("change", () => { completenessFilter = completeness.value; scheduleFilterRender(); });
  const sort = el("select", { "aria-label": "Sort proposals" }, [
    selectOption("queue", "Queue order", sortMode === "queue"),
    selectOption("attention", "Needs attention first", sortMode === "attention"),
    selectOption("title", "Title A to Z", sortMode === "title"),
  ]);
  sort.addEventListener("change", () => { sortMode = sort.value; scheduleFilterRender(); });
  const reset = el("button", { class: "quiet filter-reset", type: "button", onclick: () => {
    searchQuery = "";
    reviewFilter = "all";
    completenessFilter = "all";
    sortMode = "queue";
    renderCategory({ focusSearch: true });
  } }, "Reset");
  const controls = el("section", { class: "triage-controls", "aria-label": "Find and organize proposals" }, [
    search,
    el("div", { class: "triage-selects" }, [review, completeness, sort, reset]),
    el("p", { class: "filter-count", role: "status" }, `${matchCount} of ${cards.length} pending proposals match`),
  ]);
  return controls;
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
  } else if (longTextField(name)) {
    input = el("textarea", { id, name }, value);
  } else {
    input = el("input", { id, name, type: "text", value });
  }
  if (definition.required) input.required = true;
  if (!definition.computed) input.addEventListener("input", () => {
    scheduleSave(card);
    updateAdvancedFieldPresentation();
  });
  const labelChildren = [name];
  if (definition.required) {
    labelChildren.push(
      el("span", { class: "required-marker", "aria-hidden": "true" }, " *"),
      el("span", { class: "sr-only" }, " required"),
    );
  }
  const fieldName = name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const quickClass = name.endsWith(" Title") ? "field-quick-title" : name === "Status" ? "field-quick-status" : name === "Statement" ? "field-quick-statement" : "";
  const wrapper = el("div", { class: `field field-${fieldName} ${quickClass} ${input.tagName === "TEXTAREA" ? "field-wide" : ""}`,
    "data-required": definition.required ? "true" : "false" }, [
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

function fieldSection(definition) {
  const name = definition.name.toLowerCase();
  if (definition.type === "date" || /date/.test(name)) return "Dates";
  if (/owner|raised by|responsible|accountable/.test(name)) return "Ownership";
  if (/linked|relationship|dependency/.test(name)) return "Relationships";
  if (/probability|likelihood|severity|score|priority/.test(name)) return "Assessment";
  if (/mitigation|response|contingency|validation|action|plan|resolution|impact if/.test(name)) return "Response planning";
  return "Details";
}

function updateAdvancedFieldPresentation() {
  const selector = document.querySelector("#field-visibility");
  const mode = selector?.value || fieldView;
  document.querySelectorAll(".field-group").forEach(group => {
    let visible = 0;
    let completed = 0;
    const fields = [...group.querySelectorAll(".field")];
    fields.forEach(field => {
      const input = field.querySelector("input, select, textarea");
      const populated = String(input?.value || "").trim() !== "";
      const required = field.dataset.required === "true";
      const show = mode === "all" || (mode === "required" && required) || (mode === "populated" && populated);
      field.hidden = !show;
      if (show) visible += 1;
      if (populated) completed += 1;
    });
    group.hidden = visible === 0;
    const status = group.querySelector(".field-group-status");
    if (status) status.textContent = `${completed} of ${fields.length} completed`;
  });
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

async function revealSource(sourceRef) {
  try {
    await api(`/api/reveal-source?path=${encodeURIComponent(sourceRef)}`);
    showToast("Revealed the source file in Finder.");
  } catch (error) {
    showToast(error.message || "The source file could not be revealed in Finder.");
  }
}

function evidence(card) {
  const entries = card.evidence.length ? card.evidence : card.source_refs.map(source_ref => ({ source_ref, excerpt: "" }));
  const section = el("aside", { class: "evidence", "aria-label": "Sources" }, [
    el("div", { class: "evidence-heading" }, [
      el("p", { class: "eyebrow" }, `${entries.length} ${entries.length === 1 ? "source" : "sources"}`),
    ]),
  ]);
  const list = el("div", { class: "evidence-list" });
  entries.forEach(entry => {
    const lines = entry.line_start ? `, lines ${entry.line_start}${entry.line_end ? `–${entry.line_end}` : ""}` : "";
    const source = entry.source_ref === userSubmittedSource
      ? el("strong", { class: "source-ref" }, userSubmittedSource)
      : el("button", { class: "source-ref", type: "button", title: "Reveal source in Finder",
        "aria-label": `Reveal ${entry.source_ref || "source"} in Finder`, onclick: () => revealSource(entry.source_ref || "") },
        `${entry.source_ref || "Unknown source"}${lines}`);
    list.append(el("article", { class: "evidence-item" }, [
      source,
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

async function decide(card, decision, note = "") {
  const buttons = [...document.querySelectorAll(".category-actions button")];
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
      showToast("Flagged for AI review and kept in the pending inbox.");
      await refreshInbox();
      currentIndex = cards.findIndex(item => item.proposal_id === card.proposal_id);
      renderCategory();
      return;
    }
    await refreshInbox();
    if (!cards.length) {
      renderEmptyReview();
      return;
    }
    const nextInCategory = cards.findIndex(item => item.category === activeCategory);
    currentIndex = nextInCategory >= 0 ? nextInCategory : Math.min(currentIndex, cards.length - 1);
    renderCategory();
  } catch (error) {
    renderValidation(error.payload?.validation || [error.message]);
    buttons.forEach(button => { button.disabled = false; });
  }
}

function categoryNavigation(matches) {
  const nav = el("nav", { class: "category-tabs", "aria-label": "Proposal categories" });
  const matchingCounts = matches.reduce((counts, card) => {
    counts[card.category] = (counts[card.category] || 0) + 1;
    return counts;
  }, {});
  Object.entries(groupedCards()).forEach(([category, items]) => {
    const summary = progressSummary.categories?.[category] || { completed: 0, total: items.length, pending: items.length };
    const matching = matchingCounts[category] || 0;
    nav.append(el("button", { class: `quiet category-${category}`, type: "button",
      "aria-current": category === activeCategory ? "true" : "false",
      "aria-label": `${label(category)}, ${summary.completed} of ${summary.total} reviewed, ${matching} matching pending`,
      onclick: () => openFlow(category),
    }, [
      el("span", { class: "category-tab-label" }, label(category)),
      el("span", { class: "category-tab-meta" }, `${summary.completed}/${summary.total} reviewed · ${matching === items.length ? `${items.length} pending` : `${matching} match`}`),
    ]));
  });
  return nav;
}

function titleDefinition(card) {
  return card.field_schema.find(definition => definition.name.endsWith(" Title"));
}

function quickDefinitions(card) {
  const preferred = [titleDefinition(card), card.field_schema.find(definition => definition.name === "Status"),
    card.field_schema.find(definition => definition.name === "Statement"),
    card.field_schema.find(definition => definition.name === "Priority")];
  return preferred.filter((definition, index) => definition && preferred.indexOf(definition) === index);
}

function cardTitle(card) {
  if (["stakeholder", "system"].includes(card.category)) {
    return String(card.fields.Name || "").trim() || "No name found";
  }
  const title = titleDefinition(card);
  return card.fields[title?.name] || card.fields.Statement || `${card.category_label} proposal`;
}

function animateStack(target) {
  scope?.revert();
  if (reduceMotion || !animate || !createScope) return;
  scope = createScope({ root: flow }).add(() => {
    animate(target, { opacity: [0.35, 1], y: [30, 0], scale: [0.97, 1], duration: 420, ease: "outExpo" });
  });
}

function renderProposalListItem(card, selected) {
  const article = el("article", { class: `proposal-list-item category-${card.category}${selected ? " is-selected" : ""}`,
    "aria-label": `${card.category_label} proposal: ${cardTitle(card)}` });
  const selectCard = () => {
    currentIndex = cards.indexOf(card);
    renderCategory();
  };
  const missing = missingRequired(card);
  const sources = (card.evidence?.length || card.source_refs?.length || 0);
  article.append(el("button", { class: "proposal-list-title", type: "button", "aria-current": selected ? "true" : undefined, onclick: selectCard }, [
    el("span", { class: "proposal-title-copy" }, cardTitle(card)),
    el("span", { class: "proposal-list-meta" }, [
      ...(card.review?.state === "flagged" ? [el("span", { class: "proposal-badge flagged" }, "Flagged")] : []),
      ...(missing ? [el("span", { class: "proposal-badge needs-attention" }, `${missing} required`)] : [el("span", { class: "proposal-badge complete" }, "Required complete")]),
      el("span", {}, `${sources} ${sources === 1 ? "source" : "sources"}`),
    ]),
  ]));
  return article;
}

function reviewActions(card) {
  return el("div", { class: "category-actions", "aria-label": "Review decision" }, [
    el("button", { class: "primary", type: "button", onclick: () => decide(card, "accept") }, "Accept"),
    el("button", { class: "danger", type: "button", onclick: event => openDecisionModal(card, "reject", event.currentTarget) }, "Reject"),
    el("button", { class: "secondary", type: "button", onclick: event => openDecisionModal(card, "flag", event.currentTarget) }, "Flag for AI review"),
    el("button", { class: "quiet create-proposal", type: "button", title: `Create ${label(activeCategory)} proposal`,
      "aria-label": `Create ${label(activeCategory)} proposal`, onclick: event => openCreateProposalModal(activeCategory, event.currentTarget) }, "+"),
  ]);
}

function expandedCardContent(card, position, categoryTotal) {
  const content = el("section", { class: `expanded-card-content category-${card.category}`, "aria-label": `${card.category_label} details` });
  const stickyHeader = el("header", { class: "review-sticky-header" }, [
    el("div", { class: "review-heading" }, [
      el("p", { class: "eyebrow" }, `${card.category_label} ${position} of ${categoryTotal}`),
      el("h2", {}, cardTitle(card)),
    ]),
    el("div", { class: "review-sticky-actions" }, [
      el("span", { class: "save-state", id: "save-state", role: "status" }, "All changes saved"),
      reviewActions(card),
    ]),
  ]);
  const form = el("form", { id: "proposal-form", novalidate: "" });
  const quickGrid = el("div", { class: "quick-field-grid" });
  const quick = quickDefinitions(card);
  quick.forEach(definition => quickGrid.append(fieldControl(card, definition)));
  form.append(quickGrid);

  const quickNames = new Set(quick.map(definition => definition.name));
  const advanced = orderedFieldSchema(card).filter(definition => !quickNames.has(definition.name));
  if (advanced.length) {
    const visibility = el("select", { id: "field-visibility", "aria-label": "Choose which additional fields to show" }, [
      selectOption("all", "All fields", fieldView === "all"),
      selectOption("required", "Required only", fieldView === "required"),
      selectOption("populated", "Populated only", fieldView === "populated"),
    ]);
    visibility.addEventListener("change", () => {
      fieldView = visibility.value;
      updateAdvancedFieldPresentation();
    });
    const groups = new Map();
    advanced.forEach(definition => {
      const section = fieldSection(definition);
      if (!groups.has(section)) groups.set(section, []);
      groups.get(section).push(definition);
    });
    const groupContainer = el("div", { class: "field-groups" });
    groups.forEach((definitions, section) => {
      const fields = el("div", { class: "field-grid" });
      definitions.forEach(definition => fields.append(fieldControl(card, definition)));
      groupContainer.append(el("details", { class: "field-group", open: "" }, [
        el("summary", {}, [
          el("span", {}, section),
          el("span", { class: "field-group-status" }, ""),
        ]),
        fields,
      ]));
    });
    form.append(el("section", { class: "advanced-section", "aria-labelledby": "additional-fields-title" }, [
      el("div", { class: "advanced-heading" }, [
        el("div", {}, [
          el("h3", { id: "additional-fields-title" }, `Additional fields (${advanced.length})`),
          el("p", {}, "Fields are grouped for faster review and remain open by default."),
        ]),
        el("label", { class: "field-visibility-label", for: "field-visibility" }, ["Show", visibility]),
      ]),
      groupContainer,
    ]));
  }

  const formPane = el("div", { class: "form-pane" }, [
    form,
    el("div", { id: "validation", class: "validation", hidden: "", role: "alert" }),
    comparison(card),
  ]);
  content.append(stickyHeader, el("div", { class: "review-body" }, [formPane, evidence(card)]));
  if (card.review?.state === "flagged") {
    formPane.prepend(el("div", { class: "flagged-state" }, [
      el("strong", {}, "Flagged for AI review"),
      el("p", {}, card.review.clarification_note || "No clarification note was supplied."),
    ]));
  }
  return content;
}

function closeModal(modal, trigger, restoreFocus = true) {
  modal.remove();
  document.querySelector(".site-header")?.removeAttribute("inert");
  document.querySelector("main")?.removeAttribute("inert");
  if (restoreFocus) trigger?.focus();
}

function showModal(modal, initialFocus, trigger) {
  document.querySelector(".site-header")?.setAttribute("inert", "");
  document.querySelector("main")?.setAttribute("inert", "");
  document.body.append(modal);
  modal.addEventListener("click", event => {
    if (event.target === modal) closeModal(modal, trigger);
  });
  modal.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeModal(modal, trigger);
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...modal.querySelectorAll("button, input, select, textarea, [href], [tabindex]:not([tabindex='-1'])")]
      .filter(node => !node.disabled && !node.hidden);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  initialFocus.focus();
}

function openDecisionModal(card, decision, trigger) {
  const isReject = decision === "reject";
  const modal = el("div", { class: "review-note-modal", role: "dialog", "aria-modal": "true",
    "aria-labelledby": "review-note-title", "aria-describedby": "review-note-description" });
  const form = el("form", {});
  const note = el("textarea", { id: "decision-note", placeholder: isReject
    ? "Optionally explain why this proposal is being rejected."
    : "Optionally describe what should be reviewed." });
  form.append(
    el("p", { class: "eyebrow" }, isReject ? "Reject proposal" : "Flag for AI review"),
    el("h2", { id: "review-note-title" }, isReject ? "Add a rejection note" : "Add a review note"),
    el("p", { id: "review-note-description" }, isReject ? "The proposal will be archived without writing to a tracker." : "The proposal will remain pending for clarification."),
    el("label", { for: "decision-note" }, "Optional reviewer note"),
    note,
    el("div", { class: "modal-actions" }, [
      el("button", { class: "quiet", type: "button", onclick: () => closeModal(modal, trigger) }, "Cancel"),
      el("button", { class: isReject ? "danger" : "secondary", type: "submit" }, isReject ? "Reject proposal" : "Flag for AI review"),
    ]),
  );
  form.addEventListener("submit", event => {
    event.preventDefault();
    const value = note.value.trim();
    closeModal(modal, trigger, false);
    decide(card, decision, value);
  });
  modal.append(form);
  showModal(modal, note, trigger);
}

function categoryToolbar(card) {
  return el("section", { class: "category-toolbar", "aria-label": `${label(activeCategory)} review actions` }, [
    el("div", { class: "toolbar-actions" }, [
      el("div", { class: "category-actions", "aria-label": "Review decision" }, [
        ...(card ? [] : [el("button", { class: "quiet create-proposal", type: "button", title: `Create ${label(activeCategory)} proposal`,
          "aria-label": `Create ${label(activeCategory)} proposal`, onclick: event => openCreateProposalModal(activeCategory, event.currentTarget) }, "+")]),
      ]),
    ]),
  ]);
}

function renderCategory(options = {}) {
  clearTimeout(saveTimer);
  if (!activeCategory) activeCategory = categories[0]?.id || "";
  const matches = visibleCards();
  const categoryCards = matches.filter(item => item.category === activeCategory);
  const card = categoryCards.includes(cards[currentIndex]) ? cards[currentIndex] : categoryCards[0] || null;
  if (card) activeCategory = card.category;
  flow.replaceChildren(progress(), triageControls(matches.length), categoryNavigation(matches));
  const list = el("aside", { class: "proposal-list", "aria-label": `${label(activeCategory)} proposals` });
  categoryCards.forEach(item => list.append(renderProposalListItem(item, item === card)));
  const review = el("div", { class: `category-review${card ? "" : " empty-category-review"}` }, card ? [] : [categoryToolbar(card)]);
  if (card) review.append(expandedCardContent(card, categoryCards.indexOf(card) + 1, categoryCards.length));
  else review.append(el("section", { class: "state-panel empty-category-state" }, [
    el("p", { class: "eyebrow" }, `${label(activeCategory)} results`),
    el("h2", {}, `No ${label(activeCategory).toLowerCase()} proposals match.`),
    el("p", {}, cards.some(item => item.category === activeCategory)
      ? "Adjust the search or filters to see more proposals."
      : "No proposals in this category are pending."),
  ]));
  flow.append(el("div", { class: "review-layout" }, card ? [list, review] : [review]));
  if (options.focusSearch) {
    const search = flow.querySelector(".triage-search");
    search?.focus();
    search?.setSelectionRange(search.value.length, search.value.length);
  }
  if (!card) return;
  riskDerived(card, card.fields);
  updateAdvancedFieldPresentation();
  animateStack(flow.querySelector(".expanded-card-content"));
  if (!options.focusSearch) flow.querySelector("#proposal-form .quick-field-grid input, #proposal-form .quick-field-grid select, #proposal-form .quick-field-grid textarea, #proposal-form .field-group input, #proposal-form .field-group select, #proposal-form .field-group textarea")?.focus({ preventScroll: true });
}

function renderEmptyReview() {
  renderCategory();
}

function openFlow(category) {
  activeCategory = category;
  const categoryIndex = cards.findIndex(card => card.category === category);
  if (categoryIndex >= 0) currentIndex = categoryIndex;
  flow.hidden = false;
  renderCategory();
}

function openCreateProposalModal(category, trigger) {
  const modal = el("div", { class: "review-note-modal", role: "dialog", "aria-modal": "true",
    "aria-labelledby": "create-proposal-title", "aria-describedby": "create-proposal-description" });
  const form = el("form", {});
  const sourceRef = el("input", { id: "proposal-source-ref", type: "text", required: "", value: userSubmittedSource, placeholder: "workspace/meetings/2026-09-04 - Workshop.md" });
  const status = el("p", { class: "save-state", role: "status" }, "");
  form.append(
    el("p", { class: "eyebrow" }, `New ${label(category)} proposal`),
    el("h2", { id: "create-proposal-title" }, "Create a pending proposal"),
    el("p", { id: "create-proposal-description" }, "This defaults to reviewer-provided evidence. Replace it with a workspace source when one is available, then complete the fields before accepting it."),
    el("label", { for: "proposal-source-ref" }, "Workspace source reference"),
    sourceRef,
    status,
    el("div", { class: "modal-actions" }, [
      el("button", { class: "quiet", type: "button", onclick: () => closeModal(modal, trigger) }, "Cancel"),
      el("button", { class: "primary", type: "submit" }, "Create proposal"),
    ]),
  );
  form.addEventListener("submit", async event => {
    event.preventDefault();
    status.textContent = "Creating";
    try {
      await api("/api/create", { method: "POST", body: JSON.stringify({ category, source_ref: sourceRef.value.trim() }) });
      await refreshInbox();
      activeCategory = category;
      currentIndex = cards.findIndex(card => card.category === category);
      closeModal(modal, trigger, false);
      renderCategory();
      showToast("Pending proposal created.");
    } catch (error) {
      status.textContent = error.message || "Could not create the proposal";
    }
  });
  modal.append(form);
  showModal(modal, sourceRef, trigger);
}

function applyInboxResult(result) {
  cards = result.cards || [];
  categories = result.categories || [];
  progressSummary = result.progress || {
    pending: cards.length,
    accepted: 0,
    rejected: 0,
    flagged: cards.filter(card => card.review?.state === "flagged").length,
    completed: 0,
    total: cards.length,
    categories: {},
  };
}

async function refreshInbox() {
  applyInboxResult(await api("/api/inbox"));
}

async function loadInbox() {
  try {
    if (acceptedPage) {
      const result = await api("/api/accepted");
      loading.hidden = true;
      renderAcceptedPage(result.items || []);
      return;
    }
    applyInboxResult(await api("/api/inbox"));
    loading.hidden = true;
    flow.hidden = false;
    renderCategory();
  } catch (error) {
    loading.hidden = true;
    errorState.hidden = false;
    errorState.append(el("p", { class: "eyebrow" }, "Unable to load"),
      el("h1", {}, "The review inbox is unavailable."), el("p", {}, error.message));
  }
}

window.addEventListener("beforeunload", () => scope?.revert());
if (acceptedPage) {
  headerTitle.textContent = "Accepted";
  acceptedButton.textContent = "Review inbox";
  acceptedButton.addEventListener("click", () => location.assign("/"));
} else {
  acceptedButton.addEventListener("click", openAcceptedValues);
}
loadInbox();
