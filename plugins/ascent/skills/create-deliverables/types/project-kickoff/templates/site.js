(() => {
  'use strict';
  const report = window.projectKickoff || {};
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
  const colorKey = 'project-kickoff-secondary-color:' + new URL('../', location.href).pathname;
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

  document.title = report.project + ' | Project kickoff';
  if (report.sample) document.querySelector('#sample-banner').hidden = false;
  report.sections.forEach((section, position) => {
    const page = element('section', undefined, 'page layout-' + section.layout);
    page.dataset.title = section.title;
    page.dataset.layout = section.layout;
    const head = element('div', undefined, 'page-head');
    head.append(element('span', String(position + 1).padStart(2, '0') + ' / ' + section.label, 'eyebrow'));
    head.append(element('span', report.project, 'project-label'));
    page.append(head);
    const title = element(position === 0 ? 'h1' : 'h2', section.title);
    title.tabIndex = -1;
    page.append(title);
    if (section.intro) page.append(element('p', section.intro, 'intro'));
    const root = element('div', undefined, 'composition');
    section.items.forEach((item, index) => {
      const article = element('article', undefined, 'story-item');
      article.append(element('span', String(index + 1).padStart(2, '0'), 'item-number'));
      if (item.frequency) article.append(element('p', item.frequency, 'frequency'));
      article.append(element('h3', item.title));
      article.append(element('p', item.text));
      if (item.detail) article.append(element('p', item.detail, 'item-detail'));
      if (item.state === 'unconfirmed') article.append(element('p', 'To agree at kickoff', 'unconfirmed'));
      cite(article, item.source);
      if (section.layout === 'milestones') {
        const disclosure = element('details');
        const summary = element('summary', item.date || 'Date to agree');
        summary.append(element('span', item.title, 'milestone-name'));
        disclosure.append(summary, article);
        root.append(disclosure);
      } else root.append(article);
    });
    if (section.layout === 'opening') {
      const stamp = element('div', undefined, 'opening-stamp');
      stamp.append(element('p', 'PROJECT KICKOFF', 'eyebrow'), element('p', report.date, 'kickoff-date'));
      const art = element('img', undefined, 'opening-art');
      art.src = '../assets/telescope.svg'; art.alt = '';
      stamp.append(art); root.append(stamp);
    }
    page.append(root);
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
    document.documentElement.style.setProperty('--entry-x', index < current ? '-25px' : '25px');
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
    document.body.dataset.layout = pages[current].dataset.layout;
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
  let closedMilestones = [];
  window.addEventListener('beforeprint', () => {
    closedMilestones = [...document.querySelectorAll('details:not([open])')];
    closedMilestones.forEach(node => { node.open = true; });
  });
  window.addEventListener('afterprint', () => closedMilestones.forEach(node => { node.open = false; }));
  document.body.classList.add('enhanced');
  show(0, false);
})();
