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
const headerCount = document.querySelector("#header-count");
const headerControls = document.querySelector("#header-controls");
const acceptedPage = location.pathname === "/accepted";
let cards = [];
let categories = [];
let groups = [];
let relationshipTypes = [];
let progressSummary = { pending: 0, accepted: 0, rejected: 0, flagged: 0, completed: 0, total: 0, categories: {} };
let currentIndex = 0;
let activeCategory = "";
let searchQuery = "";
let reviewFilter = "all";
let completenessFilter = "all";
let sortMode = "queue";
let saveTimer = null;
let filterTimer = null;
let scope = null;
let filtersExpanded = false;
let linkableAcceptedItems = null;
let linkOptionsLoading = null;

const label = value => String(value || "").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
const categoryLabel = id => categories.find(category => category.id === id)?.label || label(id);
const fieldLabel = definition => definition.label || definition.name;
const longTextField = name => /description/i.test(name);
const percentValue = value => {
  const decimal = Number(value);
  return Number.isFinite(decimal) && value !== "" ? String(decimal * 100) : "";
};
const percentInput = (attrs, value) => el("input", { ...attrs, type: "number", value: percentValue(value), step: "1", min: "10", max: "90", inputmode: "numeric" });

function applyCatalog(result) {
  categories = result.categories || [];
  groups = result.groups || [];
  relationshipTypes = result.relationships || [];
}

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

function filterIcon() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M4 6h16M7 12h10M10 18h4");
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-width", "2");
  svg.append(path);
  return svg;
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 4500);
}

function acceptedItemTitle(item) {
  return [item.title, item.fields?.Name].map(value => String(value || "").trim()).find(Boolean) || "Untitled";
}

function renderAcceptedPage(items) {
  setHeaderCount(items.length);
  const content = el("div", { class: "accepted-values-content" });
  let activeCategory = items[0]?.category || "";
  let selected = items[0] || null;
  const render = () => {
    content.replaceChildren();
    if (!selected) { content.append(el("p", {}, "No tracker values have been accepted yet.")); return; }
    const byCategory = items.reduce((result, item) => { (result[item.category] ||= []).push(item); return result; }, {});
    if (!byCategory[activeCategory]) {
      activeCategory = Object.keys(byCategory)[0];
      selected = byCategory[activeCategory][0];
    }
    const tabs = el("div", { class: "category-groups" });
    groups.forEach(group => {
      const groupCategories = categories.filter(category => category.group === group.id && byCategory[category.id]);
      if (!groupCategories.length) return;
      const nav = el("nav", { class: "category-tabs", "aria-label": `Accepted ${group.label.toLowerCase()}` });
      groupCategories.forEach(category => nav.append(el("button", { class: `quiet category-${category.id}`, type: "button", "aria-current": category.id === activeCategory ? "true" : undefined, onclick: () => { activeCategory = category.id; selected = byCategory[category.id][0]; render(); } }, `${category.label} (${byCategory[category.id].length})`)));
      tabs.append(el("section", { class: "category-group" }, [el("h2", { class: "eyebrow category-group-label" }, group.label), nav]));
    });
    const list = el("aside", { class: "proposal-list", "aria-label": "Accepted values" });
    byCategory[activeCategory].forEach(item => {
      const row = el("article", { class: `proposal-list-item category-${item.category}${item === selected ? " is-selected" : ""}` });
      row.append(el("button", { class: "proposal-list-title", type: "button", onclick: () => { selected = item; render(); } }, acceptedItemTitle(item)));
      list.append(row);
    });
    const form = el("form", { class: `accepted-editor expanded-card-content category-${selected.category}` });
    const schema = selected.field_schema || Object.keys(selected.fields)
      .filter(name => !/(^.* ID$|Source Refs|Notes|Created At|Updated At)/.test(name))
      .map(name => ({ name: name, type: /date/i.test(name) ? "date" : "text" }));
    schema.forEach(definition => {
      if (definition.computed || isRelationshipField(definition)) return;
      const value = selected.fields[definition.name] ?? "";
      let control;
      let labelFor = definition.name;
      if (definition.enum) {
        const picker = enumPicker(`accepted-${definition.name.replace(/[^a-z0-9]/gi, "-")}`, definition.name, definition.enum, value);
        control = picker.control;
        labelFor = picker.labelFor;
      } else {
        control = definition.name === "Probability" ? percentInput({ name: definition.name }, value) : longTextField(definition.name) ? el("textarea", { name: definition.name }, value) : el("input", { name: definition.name, type: definition.type === "date" ? "date" : definition.type === "number" ? "number" : "text", value });
      }
      form.append(el("div", { class: `field${longTextField(definition.name) ? " field-wide" : ""}` }, [el("label", { for: labelFor }, definition.name === "Probability" ? "Probability (%)" : fieldLabel(definition)), control]));
    });
    const relationshipDefinition = schema.find(isRelationshipField);
    if (relationshipDefinition) form.append(relationshipsSection([selected.tracker_id], relationshipDefinition, selected.fields[relationshipDefinition.name] ?? ""));
    const status = el("span", { class: "save-state", role: "status" }, "");
    form.append(el("div", { class: "modal-actions" }, [
      el("button", { class: "quiet", type: "button", onclick: () => moveAcceptedToPending(selected) }, "Move to pending"),
      el("button", { class: "danger", type: "button", onclick: () => rejectAccepted(selected) }, "Reject approved value"),
      el("button", { class: "primary", type: "submit" }, "Save"), status,
    ]));
    form.addEventListener("submit", async event => {
      event.preventDefault(); status.textContent = "Saving";
      const fields = Object.fromEntries(new FormData(form).entries());
      if (fields.Probability !== undefined && fields.Probability !== "") fields.Probability = Number(fields.Probability) / 100;
      try { await api("/api/accepted/update", { method: "POST", body: JSON.stringify({ category: selected.category, tracker_id: selected.tracker_id, fields }) }); invalidateLinkOptions(); Object.assign(selected.fields, fields); selected.title = fields.Name || selected.title; status.textContent = "Saved"; }
      catch (error) { status.textContent = error.message || "Could not save"; }
    });
    content.append(tabs, el("div", { class: "review-layout accepted-layout" }, [list, form, evidence(selected)]));
  };
  render();
  flow.hidden = false;
  flow.replaceChildren(content);
  content.querySelector("button")?.focus();
}

async function refreshAcceptedAfterAction(message) {
  invalidateLinkOptions();
  showToast(message);
  const refreshed = await api("/api/accepted");
  renderAcceptedPage(refreshed.items || []);
}

async function rejectAccepted(item) {
  try {
    await api("/api/accepted/reject", { method: "POST", body: JSON.stringify({ category: item.category, tracker_id: item.tracker_id }) });
    await refreshAcceptedAfterAction("Approved value rejected and removed from its tracker.");
  } catch (error) {
    showToast(error.message || "Could not reject the approved value.");
  }
}

async function moveAcceptedToPending(item) {
  try {
    await api("/api/accepted/pending", { method: "POST", body: JSON.stringify({ category: item.category, tracker_id: item.tracker_id }) });
    await refreshAcceptedAfterAction("Approved value moved to the pending review inbox.");
  } catch (error) {
    showToast(error.message || "Could not move the approved value to pending.");
  }
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

function setHeaderCount(count) {
  headerCount.textContent = String(count);
  headerCount.setAttribute("aria-label", `${count} ${count === 1 ? "item" : "items"}`);
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

function scheduleFilterRender(options = {}) {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(() => renderCategory(options), 140);
}

function triageControls() {
  const search = el("input", { class: "triage-search", type: "search", value: searchQuery,
    placeholder: "Search titles, fields, sources, or evidence", "aria-label": "Search pending proposals" });
  search.addEventListener("input", () => {
    searchQuery = search.value;
    scheduleFilterRender({ focusSearch: true });
  });
  const review = enumPicker("filter-review-state", "review-filter", [
    { value: "all", text: "All review states" }, { value: "pending", text: "Pending only" }, { value: "flagged", text: "Flagged only" },
  ], reviewFilter, { ariaLabel: "Filter by review state", includeEmpty: false });
  review.input.addEventListener("input", () => { reviewFilter = review.input.value; scheduleFilterRender(); });
  const completeness = enumPicker("filter-completeness", "completeness-filter", [
    { value: "all", text: "Any completeness" }, { value: "incomplete", text: "Needs required fields" }, { value: "complete", text: "Required fields complete" },
  ], completenessFilter, { ariaLabel: "Filter by completeness", includeEmpty: false });
  completeness.input.addEventListener("input", () => { completenessFilter = completeness.input.value; scheduleFilterRender(); });
  const sort = enumPicker("filter-sort", "sort-filter", [
    { value: "queue", text: "Queue order" }, { value: "attention", text: "Needs attention first" }, { value: "title", text: "Title A to Z" },
  ], sortMode, { ariaLabel: "Sort proposals", includeEmpty: false });
  sort.input.addEventListener("input", () => { sortMode = sort.input.value; scheduleFilterRender(); });
  const reset = el("button", { class: "quiet filter-reset", type: "button", onclick: () => {
    searchQuery = "";
    reviewFilter = "all";
    completenessFilter = "all";
    sortMode = "queue";
    renderCategory({ focusSearch: true });
  } }, "Reset");
  const filterButton = el("button", {
    class: "quiet filter-toggle", type: "button", "aria-expanded": String(filtersExpanded),
    onclick: () => { filtersExpanded = !filtersExpanded; renderCategory({ focusFilter: true }); },
  }, [filterIcon(), "Filters"]);
  const filterPanel = el("div", { class: "triage-filter-panel", hidden: filtersExpanded ? undefined : "" }, [
    el("div", { class: "triage-selects" }, [review.control, completeness.control, sort.control, reset]),
  ]);
  const controls = el("section", { class: "triage-controls", "aria-label": "Find and organize proposals" }, [
    search,
    filterButton,
    filterPanel,
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

function isRelationshipField(definition) { return definition.type === "relationships"; }

function parseRelationships(value) {
  return String(value || "").split(";").map(part => part.trim()).filter(Boolean).map(part => {
    const index = part.indexOf(":");
    return index < 0 ? { meaning: "", target: part } : { meaning: part.slice(0, index).trim(), target: part.slice(index + 1).trim() };
  });
}

function formatRelationships(entries) {
  return [...new Set(entries.map(entry => `${entry.meaning}: ${entry.target}`))].join("; ");
}

function relationshipType(id) { return relationshipTypes.find(type => type.id === id); }

function relationshipsValue(category, fields) {
  const definition = categories.find(item => item.id === category)?.field_schema?.find(isRelationshipField);
  return definition ? fields?.[definition.name] : "";
}

async function linkOptions() {
  if (linkableAcceptedItems) return linkableAcceptedItems;
  if (!linkOptionsLoading) {
    linkOptionsLoading = api("/api/link-options").then(result => {
      linkableAcceptedItems = result.items || [];
      return linkableAcceptedItems;
    }).finally(() => { linkOptionsLoading = null; });
  }
  return linkOptionsLoading;
}

function invalidateLinkOptions() {
  linkableAcceptedItems = null;
}

function knownRecords() {
  return [
    ...(linkableAcceptedItems || []).map(item => ({ id: item.tracker_id, title: item.title, category: item.category,
      category_label: item.category_label, state: "Accepted", fields: item.fields || {} })),
    ...cards.map(card => ({ id: card.proposal_id, title: cardTitle(card), category: card.category,
      category_label: card.category_label, state: "Pending", fields: card.fields || {} })),
  ];
}

function relationshipRow(meaningLabel, targetId, action) {
  const record = knownRecords().find(item => item.id === targetId);
  return el("li", { class: "relationship-item" }, [
    el("span", { class: "relationship-meaning" }, meaningLabel),
    el("span", { class: "relationship-target" }, [
      el("strong", {}, record?.title || targetId),
      el("small", {}, record ? `${record.category_label} · ${record.state}` : "Not found in the trackers or the inbox"),
    ]),
    ...(action ? [action] : []),
  ]);
}

function openRelationshipPicker(ownIds, trigger, onPick) {
  const modal = el("div", { class: "review-note-modal link-picker-modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "relationship-picker-title" });
  const meaning = enumPicker("relationship-meaning", "relationship-meaning",
    relationshipTypes.map(type => ({ value: type.id, text: type.label })), "",
    { ariaLabel: "Relationship meaning", emptyLabel: "Choose a relationship meaning" });
  const hint = el("p", { class: "relationship-hint" }, "Choose what the relationship means, then the record it points to.");
  meaning.input.addEventListener("input", () => { hint.textContent = relationshipType(meaning.input.value)?.definition || ""; });
  const search = el("input", { type: "search", placeholder: "Search records", "aria-label": "Search records to relate" });
  const list = el("div", { class: "link-picker-list", role: "radiogroup", "aria-label": "Related record" });
  const problem = el("p", { class: "validation", role: "alert", hidden: "" });
  meaning.input.addEventListener("input", () => { problem.hidden = true; });
  list.addEventListener("change", () => { problem.hidden = true; });
  const render = () => {
    const query = search.value.trim().toLowerCase();
    const selectedTarget = list.querySelector("input[name='relationship-target']:checked")?.value;
    const records = knownRecords().filter(record => record.id && !ownIds.includes(record.id))
      .filter(record => !query || `${record.title} ${record.category_label} ${record.state} ${Object.values(record.fields).join(" ")}`.toLowerCase().includes(query));
    list.replaceChildren();
    if (!records.length) list.append(el("p", {}, "No matching records."));
    categories.forEach(category => {
      const matching = records.filter(record => record.category === category.id);
      if (!matching.length) return;
      list.append(el("h3", { class: "link-picker-category" }, category.label));
      matching.forEach(record => {
        const details = [record.fields.Status && label(record.fields.Status), String(record.fields.Description || "").slice(0, 160)].filter(Boolean).join(" · ");
        const radio = el("input", { type: "radio", name: "relationship-target", value: record.id });
        radio.checked = record.id === selectedTarget;
        list.append(el("label", { class: "link-picker-item" }, [
          radio,
          el("span", {}, [el("strong", {}, record.title), el("small", {}, `${record.category_label} · ${record.state}`), el("span", {}, details)]),
        ]));
      });
    });
  };
  const form = el("form", {});
  form.append(el("p", { class: "eyebrow" }, "Relationship"), el("h2", { id: "relationship-picker-title" }, "Add relationship"),
    el("div", { class: "field" }, [el("label", { for: meaning.labelFor }, "Meaning"), meaning.control]), hint,
    el("div", { class: "field" }, [el("label", {}, "Related record"), search]),
    el("p", { class: "relationship-hint" }, "Search narrows the list. Select a record using its circle."), list, problem,
    el("div", { class: "modal-actions" }, [
      el("button", { class: "quiet", type: "button", onclick: () => closeModal(modal, trigger) }, "Cancel"),
      el("button", { class: "primary", type: "submit" }, "Add relationship"),
    ]));
  form.addEventListener("submit", event => {
    event.preventDefault();
    const target = form.querySelector("input[name='relationship-target']:checked")?.value;
    if (!meaning.input.value || !target) {
      problem.textContent = !meaning.input.value && !target
        ? "Choose a relationship meaning and select a record from the results."
        : !meaning.input.value ? "Choose a relationship meaning." : "Select a record from the results.";
      problem.hidden = false;
      (!meaning.input.value ? meaning.control.querySelector("button") : search).focus();
      return;
    }
    onPick(meaning.input.value, target);
    closeModal(modal, trigger);
  });
  search.addEventListener("input", render);
  modal.append(form);
  showModal(modal, meaning.control.querySelector("button"), trigger);
  render();
  linkOptions().then(render).catch(error => { list.replaceChildren(el("p", {}, error.message || "Could not load records.")); });
}

function relationshipsSection(ownIds, definition, value, onChange) {
  const input = el("input", { type: "hidden", name: definition.name, value });
  if (onChange) input.addEventListener("input", onChange);
  const outgoing = el("ul", { class: "relationship-list" });
  const incoming = el("ul", { class: "relationship-list" });
  const add = el("button", { class: "quiet relationship-add", type: "button" }, "Add relationship");
  const change = entries => {
    input.value = formatRelationships(entries);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    render();
  };
  const render = () => {
    const entries = parseRelationships(input.value);
    outgoing.replaceChildren(...(entries.length ? entries.map((entry, index) => {
      const meaningLabel = relationshipType(entry.meaning)?.label || entry.meaning || "Unspecified meaning";
      return relationshipRow(meaningLabel, entry.target, el("button", {
        class: "quiet relationship-remove", type: "button", "aria-label": `Remove ${meaningLabel} relationship`,
        onclick: () => change(entries.filter((_, position) => position !== index)),
      }, "Remove"));
    }) : [el("li", { class: "relationship-empty" }, "This record does not point to any other record yet.")]));
    const pointing = knownRecords().flatMap(record => parseRelationships(relationshipsValue(record.category, record.fields))
      .filter(entry => ownIds.includes(entry.target)).map(entry => ({ record, meaning: entry.meaning })));
    incoming.replaceChildren(...(pointing.length ? pointing.map(({ record, meaning }) =>
      relationshipRow(relationshipType(meaning)?.inverse_label || meaning, record.id))
      : [el("li", { class: "relationship-empty" }, "No other record points to this one yet.")]));
  };
  add.addEventListener("click", () => openRelationshipPicker(ownIds, add,
    (meaning, target) => change([...parseRelationships(input.value), { meaning, target }])));
  render();
  linkOptions().then(render).catch(() => {});
  return el("section", { class: "relationships-section field-wide", "aria-label": "Relationships" }, [
    input,
    el("h3", {}, "Relationships"),
    el("p", { class: "relationship-subheading" }, "From this record"), outgoing, add,
    el("p", { class: "relationship-subheading" }, "Pointing to this record"), incoming,
  ]);
}

function enumPicker(id, name, options, value, { ariaLabel, includeEmpty = true, emptyLabel = "Select an option" } = {}) {
  const input = el("input", { id, name, type: "hidden", value });
  const button = el("button", {
    id: `${id}-button`, class: "field-picker-button", type: "button",
    "aria-haspopup": "listbox", "aria-expanded": "false", "aria-label": ariaLabel,
  });
  const list = el("div", { class: "field-options", role: "listbox", hidden: "" });
  const close = () => { list.hidden = true; button.setAttribute("aria-expanded", "false"); };
  const open = () => { list.hidden = false; button.setAttribute("aria-expanded", "true"); };
  const choices = options.map(option => typeof option === "string" ? { value: option, text: label(option) } : option);
  if (includeEmpty) choices.unshift({ value: "", text: emptyLabel });
  button.textContent = choices.find(option => option.value === value)?.text || emptyLabel;
  choices
    .forEach(option => list.append(el("button", {
      type: "button", role: "option", "aria-selected": String(option.value === value), onclick: () => {
        input.value = option.value;
        button.textContent = option.text;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        close();
        button.focus();
      }, onmousedown: event => event.preventDefault(),
    }, option.text)));
  button.addEventListener("click", () => list.hidden ? open() : close());
  button.addEventListener("blur", () => setTimeout(close, 120));
  return { input, control: el("div", { class: "field-picker" }, [input, button, list]), labelFor: button.id };
}

function fieldControl(card, definition) {
  const name = definition.name;
  const id = `field-${card.proposal_id}-${name.replace(/[^a-z0-9]/gi, "-")}`;
  const value = card.fields[name] ?? "";
  let input;
  let control;
  let labelFor = id;
  if (definition.enum) {
    const picker = enumPicker(id, name, definition.enum, value);
    input = picker.input;
    control = picker.control;
    labelFor = picker.labelFor;
  } else if (definition.computed) {
    input = el("input", { id, name, value, readonly: "", "aria-describedby": `${id}-hint` });
    control = input;
  } else if (definition.type === "date") {
    input = el("input", { id, name, type: "date", value: normalizeDate(value) });
    control = input;
  } else if (name === "Probability") {
    input = percentInput({ id, name }, value);
    control = input;
  } else if (definition.type === "number") {
    input = el("input", { id, name, type: "number", value, step: "0.1",
      min: definition.minimum, max: definition.maximum, inputmode: "decimal" });
    control = input;
  } else if (longTextField(name)) {
    input = el("textarea", { id, name }, value);
    control = input;
  } else {
    input = el("input", { id, name, type: "text", value });
    control = input;
  }
  if (definition.required) input.required = true;
  if (!definition.computed) input.addEventListener("input", () => {
    scheduleSave(card);
    updateFieldGroupStatus();
  });
  const labelChildren = [name === "Probability" ? "Probability (%)" : fieldLabel(definition)];
  if (definition.required) {
    labelChildren.push(
      el("span", { class: "required-marker", "aria-hidden": "true" }, " *"),
      el("span", { class: "sr-only" }, " required"),
    );
  }
  const fieldName = name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const quickClass = name === "Name" ? "field-quick-title" : name === "Status" ? "field-quick-status" : name === "Description" ? "field-quick-statement" : "";
  const wrapper = el("div", { class: `field field-${fieldName} ${quickClass} ${control.tagName === "TEXTAREA" ? "field-wide" : ""}`,
    "data-required": definition.required ? "true" : "false" }, [
    el("label", { for: labelFor }, labelChildren), control,
  ]);
  if (definition.computed) wrapper.append(el("small", { id: `${id}-hint` }, "Calculated from the proposal inputs."));
  return wrapper;
}

function fieldSection(definition) {
  if (definition.type === "date") return "Dates";
  if (definition.computed || definition.weights || definition.name === "Probability") return "Assessment";
  return "Details";
}

function updateFieldGroupStatus() {
  document.querySelectorAll(".field-group").forEach(group => {
    let completed = 0;
    const fields = [...group.querySelectorAll(".field")];
    fields.forEach(field => {
      const input = field.querySelector("input, select, textarea");
      const populated = String(input?.value || "").trim() !== "";
      if (populated) completed += 1;
    });
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
      fields[definition.name] = definition.name === "Probability" && input.value !== "" ? Number(input.value) / 100 : definition.type === "number" && input.value !== "" ? Number(input.value) : input.value;
    }
  }
  return fields;
}

function riskDerived(card, fields) {
  const impact = card.field_schema.find(definition => definition.weights);
  const scoreField = card.field_schema.find(definition => definition.computed === "risk_score");
  const severityField = card.field_schema.find(definition => definition.computed === "risk_severity");
  if (!impact || !scoreField || !severityField) return;
  const score = Number(fields.Probability) * impact.weights[fields[impact.name]];
  if (!Number.isFinite(score)) return;
  fields[scoreField.name] = Number(score.toFixed(3));
  fields[severityField.name] = score >= .5 ? "Sev 1" : score >= .2 ? "Sev 2" : "Sev 3";
  const form = document.querySelector("#proposal-form");
  for (const name of [scoreField.name, severityField.name]) {
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
  const entries = card.evidence?.length ? card.evidence : (card.source_refs || []).map(source_ref => ({ source_ref, excerpt: "" }));
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
      showToast(result.warning || "Rejected. No tracker row was written.");
    }
    invalidateLinkOptions();
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

function categoryNavigation() {
  const container = el("div", { class: "category-groups" });
  const grouped = groupedCards();
  groups.forEach(group => {
    const nav = el("nav", { class: "category-tabs", "aria-label": `${group.label} categories` });
    categories.filter(category => category.group === group.id).forEach(category => {
      const items = grouped[category.id] || [];
      const summary = progressSummary.categories?.[category.id] || { completed: 0, total: items.length, pending: items.length };
      const remaining = summary.pending ?? items.length;
      nav.append(el("div", { class: `category-tab category-${category.id}` }, [
        el("button", { class: "quiet category-selector", type: "button", title: category.definition,
          "aria-current": category.id === activeCategory ? "true" : "false",
          "aria-label": `${category.label}, ${remaining} remaining`,
          onclick: () => openFlow(category.id),
        }, [
          el("span", { class: "category-tab-label" }, category.label),
          el("span", { class: "category-tab-meta" }, String(remaining)),
        ]),
        el("button", { class: "quiet category-tab-create", type: "button", title: `Create ${category.label} proposal`,
          "aria-label": `Create ${category.label} proposal`, onclick: () => createManualProposal(category.id) }, "+"),
      ]));
    });
    container.append(el("section", { class: "category-group" }, [el("h2", { class: "eyebrow category-group-label" }, group.label), nav]));
  });
  return container;
}

function quickDefinitions(card) {
  return ["Name", "Status", "Description"]
    .map(name => card.field_schema.find(definition => definition.name === name)).filter(Boolean);
}

function cardTitle(card) {
  return String(card.fields.Name || "").trim() || `${card.category_label} proposal`;
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
      ...(missing ? [el("span", { class: "proposal-badge needs-attention" }, `${missing} required`)] : []),
      el("span", {}, `${sources} ${sources === 1 ? "source" : "sources"}`),
    ]),
  ]));
  return article;
}

function reviewActions(card) {
  return el("div", { class: "category-actions", "aria-label": "Review decision" }, [
    el("button", { class: "primary", type: "button", onclick: () => decide(card, "accept") }, "Accept"),
    el("button", { class: "danger", type: "button", onclick: () => decide(card, "reject") }, "Reject"),
  ]);
}

function expandedCardContent(card, position, categoryTotal) {
  const content = el("section", { class: `expanded-card-content category-${card.category}`, "aria-label": `${card.category_label} details` });
  const stickyHeader = el("header", { class: "review-sticky-header" }, [
    el("div", { class: "review-heading" }, [
      el("h2", { title: cardTitle(card) }, cardTitle(card)),
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
  const advanced = card.field_schema.filter(definition => !quickNames.has(definition.name) && !isRelationshipField(definition));
  if (advanced.length) {
    const sections = new Map();
    advanced.forEach(definition => {
      const section = fieldSection(definition);
      if (!sections.has(section)) sections.set(section, []);
      sections.get(section).push(definition);
    });
    const groupContainer = el("div", { class: "field-groups" });
    sections.forEach((definitions, section) => {
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
    form.append(el("section", { class: "advanced-section", "aria-label": "Additional fields" }, groupContainer));
  }
  const relationshipDefinition = card.field_schema.find(isRelationshipField);
  if (relationshipDefinition) {
    const ownIds = [card.proposal_id, card.tracker_id].filter(Boolean);
    form.append(relationshipsSection(ownIds, relationshipDefinition, card.fields[relationshipDefinition.name] ?? "",
      () => scheduleSave(card)));
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

function categoryToolbar(card) {
  return el("section", { class: "category-toolbar", "aria-label": `${categoryLabel(activeCategory)} review actions` });
}

function renderCategory(options = {}) {
  clearTimeout(saveTimer);
  if (!activeCategory) activeCategory = categories[0]?.id || "";
  const matches = visibleCards();
  const categoryCards = matches.filter(item => item.category === activeCategory);
  const card = categoryCards.includes(cards[currentIndex]) ? cards[currentIndex] : categoryCards[0] || null;
  if (card) activeCategory = card.category;
  setHeaderCount(progressSummary.pending ?? cards.length);
  headerControls.replaceChildren(triageControls());
  flow.replaceChildren(categoryNavigation());
  const list = el("aside", { class: "proposal-list", "aria-label": `${categoryLabel(activeCategory)} proposals` });
  categoryCards.forEach(item => list.append(renderProposalListItem(item, item === card)));
  const review = el("div", { class: `category-review${card ? "" : " empty-category-review"}` }, card ? [] : [categoryToolbar(card)]);
  if (card) review.append(expandedCardContent(card, categoryCards.indexOf(card) + 1, categoryCards.length));
  else review.append(el("section", { class: "state-panel empty-category-state" }, [
    el("p", { class: "eyebrow" }, `${categoryLabel(activeCategory)} results`),
    el("h2", {}, `No ${categoryLabel(activeCategory).toLowerCase()} proposals match.`),
    el("p", {}, cards.some(item => item.category === activeCategory)
      ? "Adjust the search or filters to see more proposals."
      : "No proposals in this category are pending."),
  ]));
  flow.append(el("div", { class: "review-layout" }, card ? [list, review] : [review]));
  if (options.focusSearch) {
    const search = headerControls.querySelector(".triage-search");
    search?.focus();
    search?.setSelectionRange(search.value.length, search.value.length);
  }
  if (options.focusFilter) headerControls.querySelector(".filter-toggle")?.focus();
  if (!card) return;
  riskDerived(card, card.fields);
  updateFieldGroupStatus();
  animateStack(flow.querySelector(".expanded-card-content"));
  if (!options.focusSearch && !options.focusFilter) flow.querySelector("#proposal-form .quick-field-grid input, #proposal-form .quick-field-grid select, #proposal-form .quick-field-grid textarea, #proposal-form .field-group input, #proposal-form .field-group select, #proposal-form .field-group textarea")?.focus({ preventScroll: true });
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

async function createManualProposal(category) {
  try {
    const created = await api("/api/create", { method: "POST", body: JSON.stringify({ category, source_ref: userSubmittedSource }) });
    await refreshInbox();
    activeCategory = category;
    currentIndex = cards.findIndex(card => card.proposal_id === created.proposal_id);
    renderCategory();
    showToast("Blank manual entry created.");
  } catch (error) {
    showToast(error.message || "Could not create the manual entry.");
  }
}

function applyInboxResult(result) {
  cards = result.cards || [];
  applyCatalog(result);
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
  const inbox = await api("/api/inbox");
  applyInboxResult(inbox);
  linkOptions().catch(() => {});
}

async function loadInbox() {
  errorState.hidden = true;
  errorState.replaceChildren();
  loading.hidden = false;
  try {
    if (acceptedPage) {
      const [result, inbox] = await Promise.all([api("/api/accepted"), api("/api/inbox")]);
      applyCatalog(result);
      cards = inbox.cards || [];
      loading.hidden = true;
      renderAcceptedPage(result.items || []);
      return;
    }
    await refreshInbox();
    loading.hidden = true;
    flow.hidden = false;
    renderCategory();
  } catch (error) {
    loading.hidden = true;
    errorState.hidden = false;
    errorState.append(el("p", { class: "eyebrow" }, "Unable to load"),
      el("h1", {}, "The review inbox is unavailable."), el("p", {}, error.message),
      el("button", { type: "button", onclick: () => loadInbox() }, "Retry"));
  }
}

const syncIndicator = el("span", { class: "sync-indicator", role: "status" }, "Working locally");
const syncButton = el("button", { class: "quiet sync-button", type: "button", onclick: async () => {
  syncButton.disabled = true;
  try {
    await api("/api/sync-now", { method: "POST", body: "{}" });
    syncIndicator.textContent = "Sync requested";
    setTimeout(refreshSyncStatus, 1500);
  } catch (error) {
    showToast(error.message || "Could not request sync.");
  } finally {
    syncButton.disabled = false;
  }
} }, "Sync now");
acceptedButton.before(syncIndicator, syncButton);

async function refreshSyncStatus() {
  try {
    const status = await api("/api/sync-status");
    const details = status.conflicts || [];
    syncIndicator.title = details.join("\n") || status.error || "";
    if (status.state === "conflict") {
      syncIndicator.textContent = `Sync paused: ${details.length} conflicting file${details.length === 1 ? "" : "s"}`;
    } else if (status.state === "offline") {
      syncIndicator.textContent = "Saved locally; OneDrive unavailable";
    } else if (status.state === "syncing") {
      syncIndicator.textContent = "Syncing to OneDrive";
    } else if (status.state === "synced") {
      syncIndicator.textContent = "Synced to OneDrive";
    } else {
      syncIndicator.textContent = "Saved locally; sync pending";
    }
  } catch {
    syncIndicator.textContent = "Working locally";
  }
}
refreshSyncStatus();
setInterval(refreshSyncStatus, 30000);

window.addEventListener("beforeunload", () => scope?.revert());
if (acceptedPage) {
  headerTitle.textContent = "Accepted";
  acceptedButton.textContent = "Review inbox";
  acceptedButton.addEventListener("click", () => location.assign("/"));
} else {
  acceptedButton.addEventListener("click", openAcceptedValues);
}
loadInbox();
