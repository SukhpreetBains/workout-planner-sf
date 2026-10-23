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
  const sourceDialog = document.querySelector('#source-dialog');
  let lastCitation = null;

  const accent = report.secondaryColor && /^#[0-9A-Fa-f]{6}$/.test(report.secondaryColor.hex) ? report.secondaryColor.hex : '#FF4D5F';
  const channels = [1, 3, 5].map(index => parseInt(accent.slice(index, index + 2), 16));
  document.documentElement.style.setProperty('--accent', accent);
  document.documentElement.style.setProperty('--accent-rgb', channels.join(' '));

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
        const href = sourceLinks[label];
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
  fill('#accomplishments', list(report.accomplishments), []);
  fill('#next-steps', list(report.nextSteps), [['Owner', 'owner'], ['Due', 'due']]);
  const suggestions = list(report.suggestedNextSteps);
  if (suggestions.length) {
    document.querySelector('#suggestions-heading').hidden = false;
    const target = document.querySelector('#suggestions');
    suggestions.forEach((item, index) => {
      const card = cardFor(item, [['Why this is suggested', 'rationale']], index);
      card.prepend(element('span', 'Suggested, not committed', 'suggestion-label'));
      target.append(card);
    });
  }
  function buildMilestones(root, rows) {
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
      button.setAttribute('aria-controls', 'ms-panel-' + index);
      const dot = element('span', undefined, 'ms-dot');
      dot.setAttribute('aria-hidden', 'true');
      button.append(dot, element('span', item.date, 'ms-date-text'), element('span', ', ' + text(item.name), 'sr-only'));
      button.addEventListener('click', () => toggle(index));
      node.append(button);
      track.append(node);
      buttons.push(button);

      const panel = element('section', undefined, 'ms-panel');
      panel.id = 'ms-panel-' + index;
      panel.hidden = true;
      panel.setAttribute('aria-labelledby', 'ms-title-' + index);
      const body = element('div', undefined, 'ms-panel-body');
      addIcon(body, item);
      const copy = element('div', undefined, 'ms-copy');
      copy.append(element('p', 'Milestone ' + (index + 1) + ' of ' + rows.length, 'ms-kicker'));
      const title = element('h3', item.name, 'ms-title');
      title.id = 'ms-title-' + index;
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
  buildMilestones(document.querySelector('#milestones'), list(report.milestones));
  fill('#risks', list(report.risks), [['Impact', 'impact'], ['Owner', 'owner'], ['Action', 'action']]);
  fill('#decisions', list(report.decisions), [['Owner', 'owner'], ['Due', 'due']]);

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
    if (sourceDialog.open || event.altKey || event.ctrlKey || event.metaKey || event.isComposing) return;
    if (event.target && (event.target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName))) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(current - 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); show(current + 1); }
  });
  document.body.classList.add('enhanced');
  show(0, false);
})();
