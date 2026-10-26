(() => {
  'use strict';
  const report = window.weeklyStatus || {};
  const text = value => value === undefined || value === null || String(value).trim() === '' ? 'Not provided' : String(value);
  const list = value => Array.isArray(value) ? value : [];
  const element = (tag, value, className) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = text(value);
    return node;
  };
  const sourceNumbers = new Map();
  const sourceLinks = report.sourceLinks && typeof report.sourceLinks === 'object' ? report.sourceLinks : {};
  const sourceDetails = report.sourceDetails && typeof report.sourceDetails === 'object' ? report.sourceDetails : {};
  const sourceDialog = document.querySelector('#source-dialog');
  let lastCitation = null;

  const palette = [
    {name: 'Cyan', hex: '#1BE1F2'},
    {name: 'Coral Red', hex: '#FF4D5F'},
    {name: 'Purple', hex: '#C7B9FF'},
    {name: 'Chartreuse', hex: '#DEFF4D'}
  ];
  const colorKey = 'weekly-status-secondary-color:' + new URL('../', location.href).pathname;
  const initialColor = palette.find(color => color.hex === report.secondaryColor?.hex) || palette[1];
  let savedColor;
  try { savedColor = localStorage.getItem(colorKey); } catch (_) { /* Storage can be unavailable. */ }
  const selectedColor = palette.find(color => color.hex === savedColor) || initialColor;
  function applyColor(color) {
    document.documentElement.style.setProperty('--accent', color.hex);
    document.documentElement.style.setProperty('--accent-rgb', [1, 3, 5].map(index => parseInt(color.hex.slice(index, index + 2), 16)).join(' '));
    document.querySelector('#color-toggle').setAttribute('aria-label', 'Secondary color: ' + color.name);
    document.querySelectorAll('.color-option').forEach(button => button.setAttribute('aria-checked', String(button.dataset.color === color.hex)));
    try { localStorage.setItem(colorKey, color.hex); } catch (_) { /* The page still updates. */ }
  }
  const colorToggle = document.querySelector('#color-toggle');
  const colorMenu = document.querySelector('#color-menu');
  palette.forEach(color => {
    const button = element('button', color.name, 'color-option');
    button.type = 'button';
    button.role = 'menuitemradio';
    button.dataset.color = color.hex;
    button.style.setProperty('--swatch', color.hex);
    button.addEventListener('click', () => {
      applyColor(color);
      colorMenu.hidden = true;
      colorToggle.setAttribute('aria-expanded', 'false');
      colorToggle.focus();
    });
    colorMenu.append(button);
  });
  colorToggle.addEventListener('click', () => {
    colorMenu.hidden = !colorMenu.hidden;
    colorToggle.setAttribute('aria-expanded', String(!colorMenu.hidden));
    if (!colorMenu.hidden) colorMenu.querySelector('.color-option[aria-checked="true"]').focus();
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.color-picker')) {
      colorMenu.hidden = true;
      colorToggle.setAttribute('aria-expanded', 'false');
    }
  });
  colorMenu.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      colorMenu.hidden = true;
      colorToggle.setAttribute('aria-expanded', 'false');
      colorToggle.focus();
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const options = [...colorMenu.querySelectorAll('.color-option')];
      const index = options.indexOf(document.activeElement);
      options[(index + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length].focus();
    }
  });
  applyColor(selectedColor);
  window.addEventListener('storage', event => {
    if (event.key === colorKey) {
      const color = palette.find(option => option.hex === event.newValue);
      if (color) applyColor(color);
    }
  });

  function cite(parent, source) {
    const labels = Array.isArray(source) ? source : text(source).split(';').map(part => part.trim()).filter(Boolean);
    if (!labels.length) return;
    const wrap = element('div', undefined, 'citations');
    wrap.append(element('span', 'Sources: '));
    labels.forEach((label, index) => {
      if (!sourceNumbers.has(label)) sourceNumbers.set(label, sourceNumbers.size + 1);
      if (index) wrap.append(document.createTextNode(' '));
      const number = sourceNumbers.get(label);
      const button = element('button', '[' + number + ']', 'cite');
      button.type = 'button';
      button.setAttribute('aria-label', 'Source ' + number + ': ' + label);
      button.addEventListener('click', () => {
        lastCitation = button;
        document.querySelector('#source-label').textContent = label;
        const record = sourceDetails[label];
        const detailRoot = document.querySelector('#source-details');
        detailRoot.replaceChildren();
        if (record) {
          if (record.description) detailRoot.append(element('p', record.description));
          const facts = element('dl', undefined, 'source-facts');
          Object.entries(record.facts || {}).forEach(([key, value]) => facts.append(element('dt', key), element('dd', value)));
          if (facts.children.length) detailRoot.append(element('h3', 'Current reviewed tracker row'), facts);
          if (record.evidence?.length) {
            const evidence = element('ul', undefined, 'source-evidence');
            record.evidence.forEach(item => {
              const li = element('li');
              li.append(element('blockquote', item.excerpt));
              li.append(sourceReference(item));
              evidence.append(li);
            });
            detailRoot.append(element('h3', 'Historical accepted evidence excerpts'), evidence);
          } else if (record.facts && Object.keys(record.facts).length) {
            detailRoot.append(element('p', 'No accepted evidence excerpt is available for this row.'));
          }
          if (record.documents?.length) {
            const documents = element('ul');
            record.documents.forEach(item => { const li = element('li'); li.append(sourceReference(item)); documents.append(li); });
            detailRoot.append(element('h3', 'Source documents'), documents);
          }
        }
        const href = sourceLinks[label] || (record?.documents || []).find(item => item.link)?.link;
        const safe = typeof href === 'string' && (/^https:\/\//.test(href) || /^\.\.\/sources\/[A-Za-z0-9_.-]+\.html$/.test(href));
        const link = document.querySelector('#source-document');
        link.hidden = !safe;
        document.querySelector('#source-unavailable').hidden = safe;
        if (safe) link.href = href;
        else link.removeAttribute('href');
        sourceDialog.showModal();
        document.querySelector('#close-source').focus();
      });
      wrap.append(button);
    });
    parent.append(wrap);
  }

  function sourceReference(item) {
    const link = item.link;
    if (typeof link === 'string' && /^\.\.\/sources\/[A-Za-z0-9_.-]+\.html$/.test(link)) {
      const anchor = element('a', item.sourceRef || 'Open source snapshot');
      anchor.href = link;
      anchor.target = '_blank';
      anchor.rel = 'noopener';
      return anchor;
    }
    return element('span', (item.sourceRef || 'Source') + ' (document unavailable in this package)');
  }

  document.querySelector('#close-source').addEventListener('click', () => sourceDialog.close());
  sourceDialog.addEventListener('close', () => lastCitation && lastCitation.focus());
  document.querySelector('#sources-toggle').addEventListener('click', event => {
    const shown = document.body.classList.toggle('sources-on');
    event.currentTarget.textContent = shown ? 'Hide sources' : 'Show sources';
    event.currentTarget.setAttribute('aria-pressed', String(shown));
  });
  document.querySelector('#print-button').addEventListener('click', () => window.print());

  document.title = text(report.project) + ' | Weekly status';
  document.querySelector('#project').textContent = text(report.project);
  document.querySelector('#period').textContent = text(report.period);
  document.querySelector('#health').textContent = text(report.health);
  document.querySelector('#summary').textContent = text(report.summary);
  if (report.sample === true) document.querySelector('#sample-banner').hidden = false;
  if (report.healthSource) cite(document.querySelector('#health-sources'), report.healthSource);
  if (report.summarySources) cite(document.querySelector('#summary-sources'), report.summarySources);

  function addIcon(card, item) {
    if (!report.useIconography || !item.icon) return;
    const image = document.createElement('img');
    image.className = 'icon';
    image.src = '../assets/iconography/' + item.icon + '.svg';
    image.alt = '';
    image.setAttribute('aria-hidden', 'true');
    card.append(image);
  }
  function detail(card, label, value) {
    const line = element('p', undefined, 'detail');
    line.append(element('strong', label + ': '), document.createTextNode(text(value)));
    card.append(line);
  }
  function cardFor(item, fields, index, titleKey) {
    const card = element('article', undefined, 'card' + (index % 2 ? ' accent' : ''));
    addIcon(card, item);
    card.append(element(titleKey ? 'h3' : 'p', titleKey ? item[titleKey] : item.text, titleKey ? '' : 'item-text'));
    if (titleKey && item.text && item.text !== item[titleKey]) card.append(element('p', item.text));
    fields.forEach(([label, key]) => detail(card, label, item[key]));
    cite(card, item.source);
    return card;
  }
  function fill(targetSelector, rows, fields, titleKey) {
    const target = document.querySelector(targetSelector);
    if (!rows.length) {
      target.append(element('p', 'No evidence selected for this section.', 'empty'));
      return;
    }
    rows.forEach((item, index) => target.append(cardFor(item, fields, index, titleKey)));
  }
  function buildMilestones(root, rows, prefix) {
    if (!rows.length) {
      root.append(element('p', 'No evidence selected for this section.', 'empty'));
      return;
    }
    const track = element('ol', undefined, 'ms-track');
    track.setAttribute('aria-label', 'Milestone dates in source order');
    const stage = element('div', undefined, 'ms-stage');
    ['ms-stem', 'ms-caret', 'ms-beam'].forEach(name => {
      const connector = element('div', undefined, 'ms-connector ' + name);
      connector.setAttribute('aria-hidden', 'true');
      stage.append(connector);
    });
    const drawer = element('div', undefined, 'ms-panels');
    const buttons = [];
    const panels = [];
    rows.forEach((item, index) => {
      const node = element('li', undefined, 'ms-node');
      const button = element('button', undefined, 'ms-date');
      button.type = 'button';
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-controls', prefix + '-ms-panel-' + index);
      const dot = element('span', undefined, 'ms-dot');
      dot.setAttribute('aria-hidden', 'true');
      button.append(dot, element('span', item.date, 'ms-date-text'), element('span', ', ' + text(item.name), 'sr-only'));
      button.addEventListener('click', () => toggle(index));
      node.append(button);
      track.append(node);
      buttons.push(button);

      const panel = element('section', undefined, 'ms-panel');
      panel.id = prefix + '-ms-panel-' + index;
      panel.hidden = true;
      panel.setAttribute('aria-labelledby', prefix + '-ms-title-' + index);
      const body = element('div', undefined, 'ms-panel-body');
      addIcon(body, item);
      const copy = element('div', undefined, 'ms-copy');
      copy.append(element('p', 'Milestone ' + (index + 1) + ' of ' + rows.length, 'ms-kicker'));
      const title = element('h3', item.name, 'ms-title');
      title.id = prefix + '-ms-title-' + index;
      copy.append(title);
      detail(copy, 'Date', item.date);
      detail(copy, 'Status', item.status);
      cite(copy, item.source);
      body.append(copy);
      panel.append(body);
      drawer.append(panel);
      panels.push(panel);
    });
    stage.append(drawer, element('p', 'Select a date to open its milestone.', 'ms-hint'));
    root.append(track, stage);

    let open = -1;
    function place() {
      if (open < 0 || !root.offsetParent) return;
      const box = stage.getBoundingClientRect();
      const date = buttons[open].getBoundingClientRect();
      const x = Math.max(14, Math.min(box.width - 14, date.left + date.width / 2 - box.left));
      // Keep a narrower drawer near the open date without overflowing the stage.
      const offset = Math.max(0, Math.min(box.width - drawer.offsetWidth, x - 40));
      root.style.setProperty('--ms-x', x + 'px');
      root.style.setProperty('--ms-panel-x', offset + 'px');
    }
    function toggle(index) {
      const previous = open;
      open = index === open ? -1 : index;
      buttons.forEach((button, i) => button.setAttribute('aria-expanded', String(i === open)));
      panels.forEach((panel, i) => { panel.hidden = i !== open; });
      root.classList.toggle('has-open', open >= 0);
      // The first open snaps into place; only moves between dates transition.
      root.classList.toggle('ms-jump', previous < 0);
      place();
      void root.offsetWidth;
      root.classList.remove('ms-jump');
      root.dispatchEvent(new CustomEvent('milestonechange', {bubbles: true, detail: {previous, current: open, panel: panels[open] || null}}));
    }
    // Stop propagation so date navigation does not also turn the page.
    track.addEventListener('keydown', event => {
      const index = buttons.indexOf(document.activeElement);
      const target = {ArrowLeft: index - 1, ArrowRight: index + 1, Home: 0, End: buttons.length - 1}[event.key];
      if (index < 0 || target === undefined) return;
      event.preventDefault();
      event.stopPropagation();
      const next = buttons[Math.max(0, Math.min(buttons.length - 1, target))];
      next.focus();
      next.scrollIntoView({block: 'nearest', inline: 'nearest'});
    });
    root.addEventListener('keydown', event => {
      if (event.key !== 'Escape' || open < 0) return;
      const button = buttons[open];
      toggle(open);
      button.focus();
    });
    window.addEventListener('resize', place);
    track.addEventListener('scroll', place, {passive: true});
    document.addEventListener('reportpagechange', place);
  }
  const sectionPages = list(report.sections);
  sectionPages.forEach((section, position) => {
    const page = element('section', undefined, 'page section-page layout-' + section.layout);
    page.dataset.title = text(section.title);
    const header = element('div', undefined, 'page-head');
    header.append(element('span', String(position + 2).padStart(2, '0') + ' · Weekly status', 'eyebrow'));
    page.append(header);
    const title = element('h2', section.title);
    title.tabIndex = -1;
    page.append(title);
    const items = list(section.items);
    if (section.layout === 'timeline') {
      page.append(element('p', 'Dates are evenly spaced in source order. Spacing does not show elapsed time.', 'timeline-note'));
      const root = element('div', undefined, 'ms');
      buildMilestones(root, items, section.id);
      page.append(root);
    } else if (section.layout === 'table') {
      if (!items.length) page.append(element('p', 'No evidence selected for this section.', 'empty'));
      else {
        const table = element('table', undefined, 'section-table');
        const head = element('thead');
        const headRow = element('tr');
        list(section.columns).forEach(column => headRow.append(element('th', column)));
        headRow.append(element('th', 'Sources'));
        head.append(headRow);
        const body = element('tbody');
        items.forEach(item => {
          const row = element('tr');
          list(section.columns).forEach(column => row.append(element('td', item[column] ?? item[column.toLowerCase().replaceAll(' ', '')] ?? 'Not provided')));
          const source = element('td');
          cite(source, item.source);
          row.append(source);
          body.append(row);
        });
        table.append(head, body);
        page.append(table);
      }
    } else {
      const root = element('div', undefined, section.layout === 'list' || section.layout === 'ask' ? 'section-list' : 'cards');
      if (!items.length) root.append(element('p', 'No evidence selected for this section.', 'empty'));
      items.forEach((item, index) => {
        const card = element('article', undefined, 'card' + (index % 2 ? ' accent' : ''));
        addIcon(card, item);
        const heading = item.name || item.title || item.kind || (section.layout === 'ask' ? 'Request' : null);
        if (heading) card.append(element('h3', heading));
        card.append(element('p', item.text || item.description || 'Not provided', 'item-text'));
        Object.entries(item).forEach(([key, value]) => {
          if (!['name', 'title', 'kind', 'text', 'description', 'source', 'icon'].includes(key) && typeof value === 'string') detail(card, key.charAt(0).toUpperCase() + key.slice(1), value);
        });
        cite(card, item.source);
        root.append(card);
      });
      page.append(root);
    }
    document.querySelector('#presentation').append(page);
  });

  const pages = [...document.querySelectorAll('.page')];
  const direct = document.querySelector('#direct');
  let current = 0;
  pages.forEach((page, index) => {
    const button = element('button', String(index + 1));
    button.type = 'button';
    button.setAttribute('aria-label', 'Go to page ' + (index + 1) + ': ' + page.dataset.title);
    button.addEventListener('click', () => show(index));
    direct.append(button);
  });
  const previous = document.querySelector('#previous');
  const next = document.querySelector('#next');
  function show(index, focus = true) {
    current = Math.max(0, Math.min(pages.length - 1, index));
    pages.forEach((page, pageIndex) => {
      page.classList.toggle('active', pageIndex === current);
      page.setAttribute('aria-hidden', String(pageIndex !== current));
      page.inert = pageIndex !== current;
    });
    [...direct.children].forEach((button, buttonIndex) => {
      if (buttonIndex === current) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    previous.disabled = current === 0;
    next.disabled = current === pages.length - 1;
    const heading = pages[current].querySelector('h1,h2');
    document.querySelector('#page-announcement').textContent = 'Page ' + (current + 1) + ' of ' + pages.length + ': ' + pages[current].dataset.title;
    if (focus && heading) heading.focus({preventScroll: true});
    window.scrollTo({top: 0, behavior: 'instant'});
    document.dispatchEvent(new CustomEvent('reportpagechange', {detail: {page: pages[current], index: current}}));
  }
  previous.addEventListener('click', () => show(current - 1));
  next.addEventListener('click', () => show(current + 1));
  document.addEventListener('keydown', event => {
    if (sourceDialog.open || !colorMenu.hidden || event.altKey || event.ctrlKey || event.metaKey || event.isComposing) return;
    if (event.target && (event.target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName))) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(current - 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); show(current + 1); }
  });
  document.body.classList.add('enhanced');
  show(0, false);
})();
