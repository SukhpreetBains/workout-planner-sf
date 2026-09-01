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
const flow = document.querySelector("#review-flow");
const loading = document.querySelector("#loading");
const errorState = document.querySelector("#error-state");
const toast = document.querySelector("#toast");
const acceptedButton = document.querySelector("#view-accepted");
const headerTitle = document.querySelector("#header-title");
const acceptedPage = location.pathname === "/accepted";
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
      row.append(el("button", { class: "proposal-list-title", type: "button", onclick: () => { selected = item; render(); } }, item.title));
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
      const input = definition.name === "Statement" ? el("textarea", { name: definition.name }, value) : definition.enum ? el("select", { name: definition.name }) : el("input", { name: definition.name, type: definition.type === "date" ? "date" : definition.type === "number" ? "number" : "text", value });
      if (definition.enum) { input.append(el("option", { value: "" }, "Select an option")); definition.enum.forEach(option => input.append(el("option", { value: option }, label(option)))); input.value = value; }
      form.append(el("div", { class: `field${definition.name === "Statement" ? " field-wide" : ""}` }, [el("label", { for: definition.name }, definition.name), input]));
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
  return cards.reduce((groups, card) => {
    (groups[card.category] ||= []).push(card);
    return groups;
  }, {});
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
  const fieldName = name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const quickClass = name.endsWith(" Title") ? "field-quick-title" : name === "Status" ? "field-quick-status" : name === "Statement" ? "field-quick-statement" : "";
  const wrapper = el("div", { class: `field field-${fieldName} ${quickClass} ${input.tagName === "TEXTAREA" ? "field-wide" : ""}` }, [
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

async function revealSource(sourceRef) {
  try {
    await api(`/api/reveal-source?path=${encodeURIComponent(sourceRef)}`);
    showToast("Revealed the source file in Finder.");
  } catch (error) {
    showToast(error.message || "The source file could not be revealed in Finder.");
  }
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
      el("button", { class: "source-ref", type: "button", onclick: () => revealSource(entry.source_ref || "") },
        `${entry.source_ref || "Unknown source"}${lines}`),
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
      card.revision = result.revision;
      card.review = { state: "flagged", clarification_note: note };
      showToast("Flagged for AI review and kept in the pending inbox.");
      renderCategory();
      return;
    }
    cards.splice(currentIndex, 1);
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

function categoryNavigation() {
  const nav = el("nav", { class: "category-tabs", "aria-label": "Proposal categories" });
  Object.entries(groupedCards()).forEach(([category, items]) => {
    nav.append(el("button", { class: `quiet category-${category}`, type: "button",
      "aria-current": category === activeCategory ? "true" : "false",
      onclick: () => openFlow(category),
    }, `${label(category)} (${items.length})`));
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
  article.append(el("button", { class: "proposal-list-title", type: "button", "aria-current": selected ? "true" : undefined, onclick: selectCard }, cardTitle(card)));
  return article;
}

function expandedCardContent(card) {
  const content = el("section", { class: `expanded-card-content category-${card.category}`, "aria-label": `${card.category_label} details` });
  const form = el("form", { id: "proposal-form", novalidate: "" });
  const quickGrid = el("div", { class: "quick-field-grid" });
  const quick = quickDefinitions(card);
  quick.forEach(definition => quickGrid.append(fieldControl(card, definition)));
  form.append(quickGrid);

  const quickNames = new Set(quick.map(definition => definition.name));
  const advanced = orderedFieldSchema(card).filter(definition => !quickNames.has(definition.name));
  if (advanced.length) {
    const advancedFields = el("div", { class: "field-grid" });
    advanced.forEach(definition => advancedFields.append(fieldControl(card, definition)));
    const preview = el("dl", { class: "advanced-preview" });
    advanced.forEach(definition => {
      const value = card.fields[definition.name];
      if (value !== undefined && value !== "") preview.append(el("dt", {}, definition.name), el("dd", {}, String(value)));
    });
    form.append(el("div", { class: "advanced-section" }, [
      el("details", { class: "advanced-fields" }, [
        el("summary", {}, `Edit all fields (${advanced.length} more)`), advancedFields,
      ]),
      preview,
    ]));
  }

  content.append(
    form,
    el("span", { class: "save-state form-status", id: "save-state", role: "status" }, "All changes saved"),
    el("div", { id: "validation", class: "validation", hidden: "", role: "alert" }),
    comparison(card),
    evidence(card),
  );
  if (card.review?.state === "flagged") {
    content.append(el("div", { class: "flagged-state" }, [
      el("strong", {}, "Flagged for AI review"),
      el("p", {}, card.review.clarification_note || "No clarification note was supplied."),
    ]));
  }
  return content;
}

function openDecisionModal(card, decision) {
  const isReject = decision === "reject";
  const modal = el("div", { class: "review-note-modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "review-note-title" });
  const form = el("form", {});
  const note = el("textarea", { id: "decision-note", placeholder: isReject
    ? "Optionally explain why this proposal is being rejected."
    : "Optionally describe what should be reviewed." });
  form.append(
    el("p", { class: "eyebrow" }, isReject ? "Reject proposal" : "Flag for AI review"),
    el("h2", { id: "review-note-title" }, isReject ? "Add a rejection note" : "Add a review note"),
    el("p", {}, isReject ? "The proposal will be archived without writing to a tracker." : "The proposal will remain pending for clarification."),
    el("label", { for: "decision-note" }, "Optional reviewer note"),
    note,
    el("div", { class: "modal-actions" }, [
      el("button", { class: "quiet", type: "button", onclick: () => modal.remove() }, "Cancel"),
      el("button", { class: isReject ? "danger" : "secondary", type: "submit" }, isReject ? "Reject proposal" : "Flag for AI review"),
    ]),
  );
  form.addEventListener("submit", event => {
    event.preventDefault();
    const value = note.value.trim();
    modal.remove();
    decide(card, decision, value);
  });
  modal.append(form);
  document.body.append(modal);
  note.focus();
}

function categoryToolbar(card) {
  return el("section", { class: "category-toolbar", "aria-label": `${card.category_label} review actions` }, [
    el("div", { class: "toolbar-actions" }, [
      el("div", { class: "category-actions", "aria-label": "Review decision" }, [
        el("button", { class: "primary", type: "button", onclick: () => decide(card, "accept") }, "Accept"),
        el("button", { class: "danger", type: "button", onclick: () => openDecisionModal(card, "reject") }, "Reject"),
        el("button", { class: "secondary", type: "button", onclick: () => openDecisionModal(card, "flag") }, "Flag for AI review"),
      ]),
    ]),
  ]);
}

function renderCategory() {
  if (!cards.length) { renderEmptyReview(); return; }
  clearTimeout(saveTimer);
  const card = cards[currentIndex];
  activeCategory = card.category;
  flow.replaceChildren(progress());
  const categoryCards = cards.filter(item => item.category === activeCategory);
  const list = el("aside", { class: "proposal-list", "aria-label": `${label(activeCategory)} proposals` });
  categoryCards.forEach(item => list.append(renderProposalListItem(item, item === card)));
  flow.append(categoryNavigation(), el("div", { class: "review-layout" }, [
    list, el("div", { class: "category-review" }, [categoryToolbar(card), expandedCardContent(card)]),
  ]));
  riskDerived(card, card.fields);
  animateStack(flow.querySelector(".expanded-card-content"));
  flow.querySelector("input, select, textarea")?.focus({ preventScroll: true });
}

function renderEmptyReview() {
  flow.hidden = false;
  flow.replaceChildren(progress(), el("section", { class: "state-panel" }, [
    el("p", { class: "eyebrow" }, "Inbox clear"),
    el("h1", {}, "You are all caught up."),
    el("p", {}, "New validated ingestion proposals will appear here."),
  ]));
}

function openFlow(category) {
  if (!cards.length) return;
  currentIndex = cards.findIndex(card => card.category === category);
  if (currentIndex < 0) currentIndex = 0;
  flow.hidden = false;
  renderCategory();
}

async function loadInbox() {
  try {
    if (acceptedPage) {
      const result = await api("/api/accepted");
      loading.hidden = true;
      renderAcceptedPage(result.items || []);
      return;
    }
    const result = await api("/api/inbox");
    cards = result.cards;
    initialTotal = cards.length;
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
