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
const siteHeader = document.querySelector(".site-header");
const headerCount = document.querySelector("#header-count");
const headerControls = document.querySelector("#header-controls");
const reviewStates = { pending: "Pending", accepted: "Accepted", rejected: "Rejected" };
let records = [];
let categories = [];
let groups = [];
let relationshipTypes = [];
let selectedKey = "";
let activeCategory = "";
let searchQuery = "";
let reviewFilter = location.pathname === "/accepted" ? "accepted" : "pending";
let completenessFilter = "all";
let sortMode = "queue";
let saveTimer = null;
let pendingSaveRecord = null;
let filterTimer = null;
let scope = null;
let filtersExpanded = false;
let categoriesOpen = false;
const collapsedGroups = new Set();
const showEmptyGroups = new Set();

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

function icon(...paths) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  paths.forEach(d => {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    path.setAttribute("stroke-width", "2");
    svg.append(path);
  });
  return svg;
}
const filterIcon = () => icon("M4 6h16M7 12h10M10 18h4");
const pencilIcon = () => icon("M4 20h4L19 9l-4-4L4 16v4z", "M13.5 6.5l4 4");
const trashIcon = () => icon("M4 7h16", "M9 7V4h6v3", "M6 7l1 13h10l1-13", "M10 11v6", "M14 11v6");

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 4500);
}

// ---------------------------------------------------------------- records

function pendingRecord(card) {
  return { ...card, state: "pending", key: `pending:${card.proposal_id}` };
}

function acceptedRecord(item) {
  return { ...item, state: "accepted", key: `accepted:${item.category}:${item.tracker_id}` };
}

function rejectedRecord(item) {
  return { ...item, state: "rejected", key: `rejected:${item.rejected_id}` };
}

function linkId(record) {
  return record.state === "pending" ? record.proposal_id : record.state === "accepted" ? record.tracker_id : "";
}

function ownIds(record) {
  if (record.state === "pending") return [record.proposal_id, record.tracker_id].filter(Boolean);
  if (record.state === "accepted") return [record.tracker_id];
  return [];
}

function isFlagged(record) {
  return record.state === "pending" && record.review?.state === "flagged";
}

function recordTitle(record) {
  return String(record.fields?.Name || record.title || "").trim() || `${record.category_label} item`;
}

function selectedRecord() {
  return records.find(record => record.key === selectedKey) || null;
}

function setHeaderCount(count) {
  headerCount.textContent = String(count);
  headerCount.setAttribute("aria-label", `${count} ${count === 1 ? "item" : "items"}`);
}

function missingRequired(record) {
  return (record.field_schema || []).filter(definition => definition.required
    && String(record.fields?.[definition.name] ?? "").trim() === "").length;
}

function recordSearchText(record) {
  return [recordTitle(record), record.category_label, reviewStates[record.state], record.tracker_id,
    ...Object.values(record.fields || {}),
    ...(record.source_refs || []),
    ...(record.evidence || []).flatMap(entry => [entry.source_ref, entry.excerpt]),
  ].join(" ").toLowerCase();
}

function matchesReviewFilter(record) {
  if (reviewFilter === "all") return true;
  return record.state === reviewFilter;
}

function visibleRecords() {
  const query = searchQuery.trim().toLowerCase();
  const filtered = records.filter(record => {
    if (query && !recordSearchText(record).includes(query)) return false;
    if (!matchesReviewFilter(record)) return false;
    const incomplete = missingRequired(record) > 0;
    if (completenessFilter === "incomplete" && !incomplete) return false;
    if (completenessFilter === "complete" && incomplete) return false;
    return true;
  });
  if (sortMode === "title") filtered.sort((a, b) => recordTitle(a).localeCompare(recordTitle(b)));
  if (sortMode === "attention") filtered.sort((a, b) => missingRequired(b) - missingRequired(a));
  return filtered;
}

function knownRecords() {
  return records.filter(record => record.state !== "rejected").map(record => ({
    id: linkId(record), key: record.key, title: recordTitle(record), category: record.category,
    category_label: record.category_label, state: reviewStates[record.state], fields: record.fields || {},
    pendingUpdate: record.state === "pending" && record.action === "update",
  }));
}

// A pending update to an existing row is offered as that row, so a rejected update cannot drop the link.
function linkableRecords() {
  return knownRecords().filter(record => !record.pendingUpdate);
}

// ---------------------------------------------------------------- filters

function scheduleFilterRender(options = {}) {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(() => renderCategory(options), 140);
}

function triageControls() {
  const search = el("input", { class: "triage-search", type: "search", value: searchQuery,
    placeholder: "Search titles, fields, sources, or evidence", "aria-label": "Search review items" });
  search.addEventListener("input", () => {
    searchQuery = search.value;
    flushSave();
    scheduleFilterRender({ focusSearch: true });
  });
  const review = enumPicker("filter-review-state", "review-filter", [
    { value: "all", text: "All review states" }, { value: "pending", text: "Pending" },
    { value: "accepted", text: "Accepted" }, { value: "rejected", text: "Rejected" },
  ], reviewFilter, { ariaLabel: "Filter by review state", includeEmpty: false });
  review.input.addEventListener("input", () => { reviewFilter = review.input.value; flushSave(); scheduleFilterRender(); });
  const completeness = enumPicker("filter-completeness", "completeness-filter", [
    { value: "all", text: "Any completeness" }, { value: "incomplete", text: "Needs required fields" }, { value: "complete", text: "Required fields complete" },
  ], completenessFilter, { ariaLabel: "Filter by completeness", includeEmpty: false });
  completeness.input.addEventListener("input", () => { completenessFilter = completeness.input.value; flushSave(); scheduleFilterRender(); });
  const sort = enumPicker("filter-sort", "sort-filter", [
    { value: "queue", text: "Queue order" }, { value: "attention", text: "Needs attention first" }, { value: "title", text: "Title A to Z" },
  ], sortMode, { ariaLabel: "Sort items", includeEmpty: false });
  sort.input.addEventListener("input", () => { sortMode = sort.input.value; flushSave(); scheduleFilterRender(); });
  const reset = el("button", { class: "quiet filter-reset", type: "button", onclick: () => {
    flushSave();
    searchQuery = "";
    reviewFilter = "pending";
    completenessFilter = "all";
    sortMode = "queue";
    renderCategory({ focusSearch: true });
  } }, "Reset");
  const filterButton = el("button", {
    class: "quiet filter-toggle", type: "button", "aria-expanded": String(filtersExpanded),
    onclick: () => { filtersExpanded = !filtersExpanded; flushSave(); renderCategory({ focusFilter: true }); },
  }, [filterIcon(), "Filters"]);
  const filterPanel = el("div", { class: "triage-filter-panel", hidden: filtersExpanded ? undefined : "" }, [
    el("div", { class: "triage-selects" }, [review.control, completeness.control, sort.control, reset]),
  ]);
  return el("section", { class: "triage-controls", "aria-label": "Find and organize review items" }, [
    search, filterButton, filterPanel,
  ]);
}

// ---------------------------------------------------------------- update comparison

function currentRows(row) {
  if (!row) return el("p", {}, "The tracker row is no longer available.");
  const list = el("dl");
  Object.entries(row).filter(([, value]) => value !== "").forEach(([key, value]) => {
    list.append(el("dt", {}, key), el("dd", {}, value));
  });
  return list;
}

function comparison(record) {
  if (record.state !== "pending" || record.action !== "update") return document.createDocumentFragment();
  return el("details", { class: "comparison" }, [
    el("summary", {}, `Compare with current tracker row ${record.tracker_id || ""}`),
    el("div", { class: "comparison-grid" }, [
      el("div", {}, [el("h3", {}, "Current tracker row"), currentRows(record.current_row)]),
      el("div", {}, [el("h3", {}, "Proposed change"), currentRows(record.fields)]),
    ]),
  ]);
}

function normalizeDate(value) {
  const match = String(value || "").match(/^\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : "";
}

// ---------------------------------------------------------------- relationships

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

function relationshipRow(meaningLabel, targetId, actions = [], { incoming = false } = {}) {
  const record = knownRecords().find(item => item.id === targetId);
  const title = record
    ? el("button", { class: "relationship-link", type: "button", title: `Open ${record.title}`,
      onclick: () => navigateTo(record.key) }, record.title)
    : el("strong", {}, targetId);
  return el("li", { class: `relationship-item${incoming ? " is-incoming" : ""}` }, [
    el("span", { class: "relationship-meaning" }, meaningLabel),
    el("span", { class: "relationship-target" }, [
      title,
      el("small", {}, record ? `${record.category_label} · ${record.state}` : "Not found in the trackers or the inbox"),
    ]),
    el("span", { class: "relationship-actions" }, actions),
  ]);
}

function meaningOptions() {
  return relationshipTypes.map(type => ({ value: type.id, text: type.label }));
}

// A small "i" button whose explanation shows on hover or keyboard focus.
function infoTip(id, about, text) {
  const tip = el("span", { class: "info-tip-text", role: "tooltip", id }, text);
  const button = el("button", { class: "info-tip", type: "button", "aria-label": `About ${about}`, "aria-describedby": id }, "i");
  return { node: el("span", { class: "info-tip-wrap" }, [button, tip]), setText: value => { tip.textContent = value; } };
}

function labelWithTip(forId, text, tip) {
  return el("div", { class: "field-label-row" }, [el("label", { for: forId }, text), tip.node]);
}

// Add mode lets the reviewer tick several records; edit mode changes one relationship.
function openRelationshipPicker({ ownIds: excluded, trigger, onSave, existing = null }) {
  const editing = Boolean(existing);
  const selected = new Map(editing ? [[existing.target, ""]] : []);
  const modal = el("div", { class: "review-note-modal link-picker-modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "relationship-picker-title" });
  const meaning = enumPicker("relationship-meaning", "relationship-meaning", meaningOptions(), existing?.meaning || "",
    { ariaLabel: "Relationship meaning", emptyLabel: "Choose a relationship meaning" });
  const meaningTip = infoTip("relationship-meaning-tip", "relationship meanings", relationshipType(existing?.meaning)?.definition
    || (editing ? "Choose what the relationship means and the record it points to."
      : "This meaning applies to every record you select, unless you choose a different meaning for a record."));
  const recordsTip = infoTip("relationship-records-tip", "choosing related records", editing
    ? "Search narrows the list. Select one record."
    : "Search narrows the list. Tick every record to relate; each one can take its own meaning.");
  const search = el("input", { id: "relationship-search", type: "search", placeholder: "Search records", "aria-label": "Search records to relate" });
  const list = el("div", { class: "link-picker-list", role: editing ? "radiogroup" : "group", "aria-label": "Related records" });
  const problem = el("p", { class: "validation", role: "alert", hidden: "" });
  const submit = el("button", { class: "primary", type: "submit" }, editing ? "Save relationship" : "Add relationship");
  const updateSubmit = () => {
    if (!editing) submit.textContent = selected.size > 1 ? `Add ${selected.size} relationships` : "Add relationship";
  };
  meaning.input.addEventListener("input", () => {
    problem.hidden = true;
    const definition = relationshipType(meaning.input.value)?.definition;
    if (definition) meaningTip.setText(definition);
  });
  const render = () => {
    const query = search.value.trim().toLowerCase();
    const matching = linkableRecords().filter(record => record.id && !excluded.includes(record.id))
      .filter(record => selected.has(record.id) || !query
        || `${record.title} ${record.category_label} ${record.state} ${Object.values(record.fields).join(" ")}`.toLowerCase().includes(query));
    list.replaceChildren();
    if (!matching.length) list.append(el("p", {}, "No matching records."));
    categories.forEach(category => {
      const inCategory = matching.filter(record => record.category === category.id);
      if (!inCategory.length) return;
      list.append(el("h3", { class: "link-picker-category" }, category.label));
      inCategory.forEach(record => {
        const details = [record.fields.Status && label(record.fields.Status), String(record.fields.Description || "").slice(0, 160)].filter(Boolean).join(" · ");
        const choice = el("input", { type: editing ? "radio" : "checkbox", name: "relationship-target", value: record.id });
        choice.checked = selected.has(record.id);
        const item = el("div", { class: "link-picker-item" }, [
          el("label", { class: "link-picker-choice" }, [
            choice,
            el("span", {}, [el("strong", {}, record.title), el("small", {}, `${record.category_label} · ${record.state}`), el("span", {}, details)]),
          ]),
        ]);
        const showRowMeaning = () => {
          item.classList.toggle("is-selected", choice.checked);
          item.querySelector(".link-picker-row-meaning")?.remove();
          if (!choice.checked || editing) return;
          const rowMeaning = enumPicker(`relationship-row-meaning-${record.id.replace(/[^a-z0-9]/gi, "-")}`, "relationship-row-meaning",
            meaningOptions(), selected.get(record.id) || "",
            { ariaLabel: `Meaning for ${record.title}`, emptyLabel: "Use the meaning above" });
          rowMeaning.input.addEventListener("input", () => { selected.set(record.id, rowMeaning.input.value); problem.hidden = true; });
          item.append(el("div", { class: "link-picker-row-meaning" }, [el("small", {}, "Meaning for this record"), rowMeaning.control]));
        };
        choice.addEventListener("change", () => {
          problem.hidden = true;
          if (editing) {
            selected.clear();
            list.querySelectorAll(".link-picker-item").forEach(other => other.classList.remove("is-selected"));
          }
          if (choice.checked) selected.set(record.id, selected.get(record.id) || "");
          else selected.delete(record.id);
          showRowMeaning();
          updateSubmit();
        });
        showRowMeaning();
        list.append(item);
      });
    });
  };
  const form = el("form", {});
  form.append(el("p", { class: "eyebrow" }, "Relationship"),
    el("h2", { id: "relationship-picker-title" }, editing ? "Edit relationship" : "Add relationships"),
    el("div", { class: "field" }, [labelWithTip(meaning.labelFor, editing ? "Meaning" : "Meaning for all selected records", meaningTip), meaning.control]),
    el("div", { class: "field" }, [labelWithTip("relationship-search", editing ? "Related record" : "Related records", recordsTip), search]),
    list, problem,
    el("div", { class: "modal-actions" }, [
      el("button", { class: "quiet", type: "button", onclick: () => closeModal(modal, trigger) }, "Cancel"),
      submit,
    ]));
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!selected.size) {
      problem.textContent = editing ? "Select a record from the results." : "Select at least one record from the results.";
      problem.hidden = false;
      search.focus();
      return;
    }
    const titles = Object.fromEntries(knownRecords().map(record => [record.id, record.title]));
    const missing = [...selected].filter(([, rowMeaning]) => !rowMeaning && !meaning.input.value).map(([id]) => titles[id] || id);
    if (missing.length) {
      problem.textContent = `Choose a meaning above, or for each record without one: ${missing.join(", ")}.`;
      problem.hidden = false;
      meaning.control.querySelector("button").focus();
      return;
    }
    onSave([...selected].map(([target, rowMeaning]) => ({ meaning: rowMeaning || meaning.input.value, target })));
    closeModal(modal, trigger);
  });
  search.addEventListener("input", render);
  modal.append(form);
  showModal(modal, meaning.control.querySelector("button"), trigger);
  render();
  updateSubmit();
}

function relationshipsSection(record, definition, onChange) {
  const ids = ownIds(record);
  const readOnly = record.state === "rejected";
  const input = el("input", { type: "hidden", name: definition.name, value: record.fields?.[definition.name] ?? "" });
  if (onChange) input.addEventListener("input", onChange);
  const outgoing = el("ul", { class: "relationship-list" });
  const incoming = el("ul", { class: "relationship-list" });
  const add = el("button", { class: "quiet relationship-add", type: "button" }, "Add relationships");
  const change = entries => {
    input.value = formatRelationships(entries);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    render();
  };
  const render = () => {
    const entries = parseRelationships(input.value);
    outgoing.replaceChildren(...(entries.length ? entries.map((entry, index) => {
      const meaningLabel = relationshipType(entry.meaning)?.label || entry.meaning || "Unspecified meaning";
      const actions = readOnly ? [] : [
        el("button", { class: "quiet icon-button", type: "button", title: "Edit relationship",
          "aria-label": `Edit ${meaningLabel} relationship`, onclick: event => openRelationshipPicker({
            ownIds: ids, trigger: event.currentTarget, existing: entry,
            onSave: ([edited]) => change(entries.map((current, position) => position === index ? edited : current)),
          }) }, pencilIcon()),
        el("button", { class: "quiet icon-button danger-icon", type: "button", title: "Remove relationship",
          "aria-label": `Remove ${meaningLabel} relationship`,
          onclick: () => change(entries.filter((_, position) => position !== index)) }, trashIcon()),
      ];
      return relationshipRow(meaningLabel, entry.target, actions);
    }) : [el("li", { class: "relationship-empty" }, "This record does not point to any other record yet.")]));
    const pointing = ids.length ? knownRecords().flatMap(other => parseRelationships(relationshipsValue(other.category, other.fields))
      .filter(entry => ids.includes(entry.target)).map(entry => ({ other, meaning: entry.meaning }))) : [];
    incoming.replaceChildren(...(pointing.length ? pointing.map(({ other, meaning }) =>
      relationshipRow(relationshipType(meaning)?.inverse_label || meaning, other.id, [], { incoming: true }))
      : [el("li", { class: "relationship-empty" }, "No other record points to this one yet.")]));
  };
  add.addEventListener("click", () => openRelationshipPicker({
    ownIds: ids, trigger: add,
    onSave: added => change([...parseRelationships(input.value), ...added]),
  }));
  render();
  return el("section", { class: "relationships-section field-wide", "aria-label": "Relationships" }, [
    input,
    el("h3", {}, "Relationships"),
    el("p", { class: "relationship-subheading" }, "From this record"), outgoing, ...(readOnly ? [] : [add]),
    el("p", { class: "relationship-subheading" }, "Pointing to this record"), incoming,
  ]);
}

// ---------------------------------------------------------------- fields

function enumPicker(id, name, options, value, { ariaLabel, includeEmpty = true, emptyLabel = "Select an option", disabled = false } = {}) {
  const input = el("input", { id, name, type: "hidden", value });
  const button = el("button", {
    id: `${id}-button`, class: "field-picker-button", type: "button",
    "aria-haspopup": "listbox", "aria-expanded": "false", "aria-label": ariaLabel,
  });
  button.disabled = disabled;
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

function fieldControl(record, definition) {
  const name = definition.name;
  const readOnly = record.state === "rejected";
  const id = `field-${record.key.replace(/[^a-z0-9]/gi, "-")}-${name.replace(/[^a-z0-9]/gi, "-")}`;
  const value = record.fields?.[name] ?? "";
  let input;
  let control;
  let labelFor = id;
  if (definition.enum) {
    const picker = enumPicker(id, name, definition.enum, value, { disabled: readOnly });
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
  if (readOnly && !definition.enum) input.readOnly = true;
  if (definition.required) input.required = true;
  if (!definition.computed && !readOnly) input.addEventListener("input", () => {
    scheduleSave(record);
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

function collectFields(record) {
  const form = document.querySelector("#proposal-form");
  const fields = {};
  if (!form) return { ...record.fields };
  for (const definition of record.field_schema) {
    const input = form.elements.namedItem(definition.name);
    if (!input) continue;
    if (input.value !== "" || Object.hasOwn(record.fields, definition.name)) {
      fields[definition.name] = definition.name === "Probability" && input.value !== "" ? Number(input.value) / 100 : definition.type === "number" && input.value !== "" ? Number(input.value) : input.value;
    }
  }
  return fields;
}

function riskDerived(record, fields) {
  const impact = record.field_schema.find(definition => definition.weights);
  const scoreField = record.field_schema.find(definition => definition.computed === "risk_score");
  const severityField = record.field_schema.find(definition => definition.computed === "risk_severity");
  if (!impact || !scoreField || !severityField) return;
  const score = Number(fields.Probability) * impact.weights[fields[impact.name]];
  if (!Number.isFinite(score)) return;
  fields[scoreField.name] = Number(score.toFixed(3));
  fields[severityField.name] = score >= .5 ? "Sev 1" : score >= .2 ? "Sev 2" : "Sev 3";
  const form = document.querySelector("#proposal-form");
  for (const name of [scoreField.name, severityField.name]) {
    const input = form?.elements.namedItem(name);
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

// ---------------------------------------------------------------- saving

function setSaveState(text) {
  const state = document.querySelector("#save-state");
  if (state) state.textContent = text;
}

async function save(record) {
  clearTimeout(saveTimer);
  saveTimer = null;
  const fields = collectFields(record);
  riskDerived(record, fields);
  const showing = () => selectedKey === record.key;
  setSaveState("Saving changes");
  try {
    let problems = [];
    if (record.state === "pending") {
      const result = await api("/api/autosave", { method: "POST", body: JSON.stringify({
        proposal_id: record.proposal_id, revision: record.revision, fields,
      }) });
      record.revision = result.revision;
      problems = result.validation;
    } else if (record.state === "accepted") {
      await api("/api/accepted/update", { method: "POST", body: JSON.stringify({
        category: record.category, tracker_id: record.tracker_id, fields,
      }) });
    }
    record.fields = { ...record.fields, ...fields };
    if (showing()) {
      setSaveState(problems.length ? "Saved with validation needs" : record.state === "accepted" ? "Saved to tracker" : "All changes saved");
      renderValidation(problems);
    }
  } catch (error) {
    if (showing()) {
      setSaveState("Changes not saved");
      renderValidation(error.payload?.validation || [error.message]);
    }
    if (error.status === 409) showToast("This proposal changed elsewhere. Reload the inbox before continuing.");
    throw error;
  }
}

function scheduleSave(record) {
  setSaveState("Unsaved changes");
  clearTimeout(saveTimer);
  pendingSaveRecord = record;
  saveTimer = setTimeout(() => save(record).catch(() => {}), record.state === "accepted" ? 700 : 350);
}

// Save immediately (before the form is replaced) when the reviewer moves on.
function flushSave() {
  if (!saveTimer || !pendingSaveRecord) return;
  save(pendingSaveRecord).catch(() => {});
}

async function ensureSaved(record) {
  clearTimeout(saveTimer);
  saveTimer = null;
  if (record.state === "rejected") return;
  const fields = collectFields(record);
  const changed = Object.entries(fields).some(([name, value]) => String(value ?? "") !== String(record.fields?.[name] ?? ""));
  if (changed) await save(record);
}

// ---------------------------------------------------------------- sources

async function revealSource(sourceRef) {
  try {
    await api(`/api/reveal-source?path=${encodeURIComponent(sourceRef)}`);
    showToast("Revealed the source file in Finder.");
  } catch (error) {
    showToast(error.message || "The source file could not be revealed in Finder.");
  }
}

function evidence(record) {
  const entries = record.evidence?.length ? record.evidence : (record.source_refs || []).map(source_ref => ({ source_ref, excerpt: "" }));
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

// ---------------------------------------------------------------- review actions

async function decide(record, decision) {
  const buttons = [...document.querySelectorAll(".category-actions button")];
  buttons.forEach(button => { button.disabled = true; });
  const position = visibleRecords().filter(item => item.category === record.category).indexOf(record);
  try {
    await ensureSaved(record);
    let message = "";
    let nextKey = "";
    if (record.state === "rejected") {
      const restored = await api("/api/rejected/pending", { method: "POST", body: JSON.stringify({ rejected_id: record.rejected_id }) });
      nextKey = `pending:${restored.proposal_id}`;
      message = "Moved back to pending.";
      if (decision === "accept") {
        try {
          const result = await api("/api/accept", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() },
            body: JSON.stringify({ proposal_id: restored.proposal_id, revision: 1 }) });
          nextKey = `accepted:${record.category}:${result.tracker_id}`;
          message = `Accepted and written as ${result.tracker_id}.`;
        } catch (error) {
          message = "Moved back to pending; it needs fixes before it can be accepted.";
        }
      }
    } else if (record.state === "accepted") {
      if (decision === "reject") {
        await api("/api/accepted/reject", { method: "POST", body: JSON.stringify({ category: record.category, tracker_id: record.tracker_id }) });
        message = "Rejected and removed from its tracker.";
      } else {
        const returned = await api("/api/accepted/pending", { method: "POST", body: JSON.stringify({ category: record.category, tracker_id: record.tracker_id }) });
        nextKey = `pending:${returned.proposal_id}`;
        message = "Moved back to pending.";
      }
    } else {
      const body = { proposal_id: record.proposal_id, revision: record.revision };
      if (decision === "accept") {
        const result = await api("/api/accept", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(body) });
        message = `Accepted and written as ${result.tracker_id}.`;
      } else {
        const result = await api("/api/reject", { method: "POST", body: JSON.stringify(body) });
        message = result.warning || "Rejected. No tracker row was written.";
      }
    }
    showToast(message);
    await refreshRecords();
    const stillVisible = nextKey && visibleRecords().some(item => item.key === nextKey);
    if (stillVisible) selectedKey = nextKey;
    else {
      const remaining = visibleRecords().filter(item => item.category === record.category);
      selectedKey = remaining[Math.min(Math.max(position, 0), remaining.length - 1)]?.key || "";
    }
    renderCategory();
  } catch (error) {
    renderValidation(error.payload?.validation || [error.message]);
    buttons.forEach(button => { button.disabled = false; });
  }
}

function reviewActions(record) {
  const action = (className, text, decision) => el("button", { class: className, type: "button", onclick: () => decide(record, decision) }, text);
  const buttons = record.state === "pending" ? [action("primary", "Accept", "accept"), action("danger", "Reject", "reject")]
    : record.state === "accepted" ? [action("quiet", "Move to pending", "pending"), action("danger", "Reject", "reject")]
      : [action("primary", "Accept", "accept"), action("quiet", "Move to pending", "pending")];
  return el("div", { class: "category-actions", "aria-label": "Review decision" }, buttons);
}

// ---------------------------------------------------------------- layout

// Sidebar of categories grouped as entities and signals, with empty ones folded away.
function categoryNavigation(visible) {
  const counts = Object.fromEntries(categories.map(category => [category.id, 0]));
  visible.forEach(record => { counts[record.category] = (counts[record.category] || 0) + 1; });
  const activeGroup = groups.find(group => group.id === categories.find(category => category.id === activeCategory)?.group);
  const nav = el("nav", { class: `category-nav${categoriesOpen ? " is-open" : ""}`, "aria-label": "Categories" });
  const toggle = el("button", { class: "category-nav-toggle", type: "button", "aria-expanded": String(categoriesOpen),
    onclick: () => { categoriesOpen = !categoriesOpen; renderCategory(); } }, [
    el("span", {}, `${activeGroup ? `${activeGroup.label} › ` : ""}${categoryLabel(activeCategory)}`),
    el("span", { class: "category-nav-toggle-hint" }, categoriesOpen ? "Hide categories ▴" : "Change category ▾"),
  ]);
  const body = el("div", { class: "category-nav-body" });
  groups.forEach(group => {
    const inGroup = categories.filter(category => category.group === group.id);
    const collapsed = collapsedGroups.has(group.id);
    const showEmpty = showEmptyGroups.has(group.id);
    const shown = inGroup.filter(category => showEmpty || counts[category.id] || category.id === activeCategory);
    const emptyCount = inGroup.filter(category => !counts[category.id]).length;
    const total = inGroup.reduce((sum, category) => sum + counts[category.id], 0);
    const listId = `category-nav-${group.id}`;
    const heading = el("button", { class: "category-nav-heading", type: "button", "aria-expanded": String(!collapsed),
      "aria-controls": listId, title: group.definition, onclick: () => {
        if (collapsed) collapsedGroups.delete(group.id); else collapsedGroups.add(group.id);
        renderCategory();
      } }, [
      el("span", { class: "category-nav-chevron", "aria-hidden": "true" }, collapsed ? "▸" : "▾"),
      el("span", {}, group.label),
      el("span", { class: "category-nav-count", "aria-label": `${total} shown` }, String(total)),
    ]);
    const list = el("ul", { class: "category-nav-list", id: listId, hidden: collapsed ? "" : undefined });
    shown.forEach(category => list.append(el("li", {}, el("button", {
      class: "category-nav-item", type: "button", title: category.definition,
      "aria-current": category.id === activeCategory ? "true" : undefined,
      onclick: () => { categoriesOpen = false; openFlow(category.id); },
    }, [
      el("span", { class: "category-nav-label" }, category.label),
      el("span", { class: "category-nav-count", "aria-label": `${counts[category.id]} shown` }, String(counts[category.id])),
    ]))));
    const hiddenCount = inGroup.length - shown.length;
    if (hiddenCount || (showEmpty && emptyCount)) {
      list.append(el("li", {}, el("button", { class: "category-nav-more", type: "button", onclick: () => {
        if (showEmpty) showEmptyGroups.delete(group.id); else showEmptyGroups.add(group.id);
        renderCategory();
      } }, showEmpty ? "Hide empty" : `+ ${hiddenCount} empty`)));
    }
    body.append(el("section", { class: "category-nav-group" }, [heading, list]));
  });
  nav.append(toggle, body);
  return nav;
}

function listHeader(count) {
  const name = categoryLabel(activeCategory);
  return el("div", { class: "proposal-list-header" }, [
    el("h2", { class: "proposal-list-heading" }, [name, el("span", { class: "category-nav-count" }, String(count))]),
    el("button", { class: "quiet proposal-list-new", type: "button", title: `Create a ${name} proposal`,
      "aria-label": `Create a ${name} proposal`, onclick: () => createManualProposal(activeCategory) }, "+ New"),
  ]);
}

function quickDefinitions(record) {
  return ["Name", "Status", "Description"]
    .map(name => record.field_schema.find(definition => definition.name === name)).filter(Boolean);
}

function animateStack(target) {
  scope?.revert();
  if (reduceMotion || !animate || !createScope || !target) return;
  scope = createScope({ root: flow }).add(() => {
    animate(target, { opacity: [0.35, 1], y: [30, 0], scale: [0.97, 1], duration: 420, ease: "outExpo" });
  });
}

function stateBadge(record) {
  return el("span", { class: `review-state-badge state-${record.state}` }, reviewStates[record.state]);
}

function renderProposalListItem(record, selected) {
  const article = el("article", { class: `proposal-list-item category-${record.category} state-${record.state}${selected ? " is-selected" : ""}`,
    "aria-label": `${record.category_label} ${reviewStates[record.state].toLowerCase()} item: ${recordTitle(record)}` });
  const missing = missingRequired(record);
  const sources = (record.evidence?.length || record.source_refs?.length || 0);
  article.append(el("button", { class: "proposal-list-title", type: "button", "aria-current": selected ? "true" : undefined,
    onclick: () => { flushSave(); selectedKey = record.key; renderCategory(); } }, [
    el("span", { class: "proposal-title-copy" }, recordTitle(record)),
    el("span", { class: "proposal-list-meta" }, [
      ...(reviewFilter === "all" ? [stateBadge(record)] : []),
      ...(isFlagged(record) ? [el("span", { class: "proposal-badge flagged" }, "Flagged")] : []),
      ...(missing ? [el("span", { class: "proposal-badge needs-attention" }, `${missing} required`)] : []),
      el("span", {}, `${sources} ${sources === 1 ? "source" : "sources"}`),
    ]),
  ]));
  return article;
}

function recordNotice(record) {
  if (isFlagged(record)) {
    return el("div", { class: "flagged-state" }, [
      el("strong", {}, "Flagged for AI review"),
      el("p", {}, record.review.clarification_note || "No clarification note was supplied."),
    ]);
  }
  if (record.state === "rejected") {
    const when = record.reviewed_at ? ` on ${String(record.reviewed_at).slice(0, 10)}` : "";
    const details = [record.previous_tracker_id ? `It was previously accepted as ${record.previous_tracker_id}.` : "",
      record.review_note ? `Reason: ${record.review_note}` : ""].filter(Boolean).join(" ");
    return el("div", { class: "flagged-state" }, [
      el("strong", {}, `Rejected${when}`),
      el("p", {}, `${details} Fields are read-only. Move it to pending to edit it, or accept it as is.`.trim()),
    ]);
  }
  if (record.state === "accepted") {
    return el("p", { class: "accepted-note" }, `Accepted as ${record.tracker_id}. Edits save straight to the tracker.`);
  }
  return null;
}

function expandedCardContent(record) {
  const content = el("section", { class: `expanded-card-content category-${record.category} state-${record.state}`, "aria-label": `${record.category_label} details` });
  const stickyHeader = el("header", { class: "review-sticky-header" }, [
    el("div", { class: "review-heading" }, [
      el("p", { class: "eyebrow review-state-line" }, ["Review state ", stateBadge(record)]),
      el("h2", { title: recordTitle(record) }, recordTitle(record)),
    ]),
    el("div", { class: "review-sticky-actions" }, [
      el("span", { class: "save-state", id: "save-state", role: "status" }, record.state === "rejected" ? "Read-only" : "All changes saved"),
      reviewActions(record),
    ]),
  ]);
  const form = el("form", { id: "proposal-form", novalidate: "" });
  const quickGrid = el("div", { class: "quick-field-grid" });
  const quick = quickDefinitions(record);
  quick.forEach(definition => quickGrid.append(fieldControl(record, definition)));
  form.append(quickGrid);

  const quickNames = new Set(quick.map(definition => definition.name));
  const advanced = record.field_schema.filter(definition => !quickNames.has(definition.name) && !isRelationshipField(definition));
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
      definitions.forEach(definition => fields.append(fieldControl(record, definition)));
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
  const relationshipDefinition = record.field_schema.find(isRelationshipField);
  if (relationshipDefinition) {
    form.append(relationshipsSection(record, relationshipDefinition, () => scheduleSave(record)));
  }
  const notice = recordNotice(record);
  const formPane = el("div", { class: "form-pane" }, [
    ...(notice ? [notice] : []),
    form,
    el("div", { id: "validation", class: "validation", hidden: "", role: "alert" }),
    comparison(record),
  ]);
  content.append(stickyHeader, el("div", { class: "review-body" }, [formPane, evidence(record)]));
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

function emptyStateMessage() {
  const stateText = { all: "", pending: "pending ", accepted: "accepted ", rejected: "rejected " }[reviewFilter];
  return records.some(record => record.category === activeCategory && matchesReviewFilter(record))
    ? "Adjust the search or filters to see more items."
    : `No ${stateText}items in this category.`;
}

function renderCategory(options = {}) {
  clearTimeout(saveTimer);
  saveTimer = null;
  if (!activeCategory) activeCategory = categories[0]?.id || "";
  const visible = visibleRecords();
  const inCategory = visible.filter(item => item.category === activeCategory);
  const record = inCategory.find(item => item.key === selectedKey) || inCategory[0] || null;
  selectedKey = record?.key || "";
  setHeaderCount(visible.length);
  headerControls.replaceChildren(triageControls());
  flow.replaceChildren(categoryNavigation(visible));
  const list = el("aside", { class: "proposal-list", "aria-label": `${categoryLabel(activeCategory)} items` }, [listHeader(inCategory.length)]);
  inCategory.forEach(item => list.append(renderProposalListItem(item, item === record)));
  if (!inCategory.length) list.append(el("p", { class: "proposal-list-empty" }, "No items match."));
  const review = el("div", { class: "category-review" });
  if (record) review.append(expandedCardContent(record));
  else review.append(el("section", { class: "state-panel empty-category-state" }, [
    el("p", { class: "eyebrow" }, `${categoryLabel(activeCategory)} results`),
    el("h2", {}, `No ${categoryLabel(activeCategory).toLowerCase()} items match.`),
    el("p", {}, emptyStateMessage()),
  ]));
  flow.append(el("div", { class: "review-layout" }, [list, review]));
  if (options.focusSearch) {
    const search = headerControls.querySelector(".triage-search");
    search?.focus();
    search?.setSelectionRange(search.value.length, search.value.length);
  }
  if (options.focusFilter) headerControls.querySelector(".filter-toggle")?.focus();
  if (!record) return;
  riskDerived(record, { ...record.fields });
  updateFieldGroupStatus();
  animateStack(flow.querySelector(".expanded-card-content"));
  if (!options.focusSearch && !options.focusFilter && record.state !== "rejected") {
    flow.querySelector("#proposal-form .quick-field-grid input, #proposal-form .quick-field-grid textarea")?.focus({ preventScroll: true });
  }
}

function openFlow(category) {
  flushSave();
  activeCategory = category;
  selectedKey = "";
  flow.hidden = false;
  renderCategory();
}

// Open any record from a relationship link, widening the filters if they hide it.
function navigateTo(key) {
  const target = records.find(record => record.key === key);
  if (!target) return;
  flushSave();
  if (!visibleRecords().includes(target)) {
    reviewFilter = "all";
    searchQuery = "";
    completenessFilter = "all";
  }
  activeCategory = target.category;
  selectedKey = target.key;
  renderCategory();
  window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
}

async function createManualProposal(category) {
  try {
    flushSave();
    const created = await api("/api/create", { method: "POST", body: JSON.stringify({ category, source_ref: userSubmittedSource }) });
    await refreshRecords();
    if (!["all", "pending"].includes(reviewFilter)) reviewFilter = "pending";
    activeCategory = category;
    selectedKey = `pending:${created.proposal_id}`;
    renderCategory();
    showToast("Blank manual entry created.");
  } catch (error) {
    showToast(error.message || "Could not create the manual entry.");
  }
}

async function refreshRecords() {
  const [inbox, accepted, rejected] = await Promise.all([api("/api/inbox"), api("/api/accepted"), api("/api/rejected")]);
  applyCatalog(inbox);
  records = [
    ...(inbox.cards || []).map(pendingRecord),
    ...(accepted.items || []).map(acceptedRecord),
    ...(rejected.items || []).map(rejectedRecord),
  ];
}

async function loadInbox() {
  errorState.hidden = true;
  errorState.replaceChildren();
  loading.hidden = false;
  try {
    await refreshRecords();
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
siteHeader.append(syncIndicator, syncButton);

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

window.addEventListener("beforeunload", () => { flushSave(); scope?.revert(); });
loadInbox();
