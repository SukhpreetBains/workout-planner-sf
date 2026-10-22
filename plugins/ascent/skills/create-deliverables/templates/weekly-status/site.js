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
  document.querySelector('#coverage').textContent = text(report.coverageNote || 'Evidence gaps were not provided.');
  if (report.sample === true) document.querySelector('#sample-banner').hidden = false;
  const assessment = report.healthAssessment || (report.health === 'Not assessed' ? 'not_assessed' : 'reported');
  if (assessment === 'reasoned') document.querySelector('#provisional').hidden = false;
  if (report.healthBasis) document.querySelector('#health-basis').textContent = text(report.healthBasis);
  else document.querySelector('#health-basis').hidden = true;
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
  const milestoneTarget = document.querySelector('#milestones');
  const milestones = list(report.milestones);
  if (document.body.dataset.variant === 'animated') {
    const rail = element('span', undefined, 'timeline-rail');
    rail.setAttribute('aria-hidden', 'true');
    milestoneTarget.append(rail);
  }
  if (!milestones.length) milestoneTarget.append(element('li', 'No evidence selected for this section.', 'empty'));
  milestones.forEach((item, index) => {
    const li = element('li', undefined, 'checkpoint');
    li.append(cardFor(item, [['Date', 'date'], ['Status', 'status']], index, 'name'));
    milestoneTarget.append(li);
  });
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
