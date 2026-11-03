// RAID log register: one table per RAID tab, rows expand to the fields the table does not show.
(function () {
  const log = window.raidLog;
  const vocab = log.vocabulary;
  const details = log.sourceDetails || {};
  const palette = [['Cyan', '#1BE1F2'], ['Coral Red', '#FF4D5F'], ['Purple', '#C7B9FF'], ['Chartreuse', '#DEFF4D']];
  const colorKey = 'raid-log-secondary-color:' + new URL('./', location.href).pathname;
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const state = {tab: vocab.tabs[0].id, status: 'all', kind: 'all', query: ''};
  const citeNumbers = new Map();
  let tipCount = 0;
  let lastCitation = null;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function parts(iso) {
    const [y, m, d] = iso.split('-').map(Number);
    return {y, m, d};
  }
  // Table cells use mm/dd/yyyy to save width; expanded details and the header use the long form.
  const shortDate = iso => { const {y, m, d} = parts(iso); return String(m).padStart(2, '0') + '/' + String(d).padStart(2, '0') + '/' + y; };
  const longDate = iso => { const {y, m, d} = parts(iso); return months[m - 1] + ' ' + d + ', ' + y; };

  const items = tabId => log.items.filter(item => item.tab === tabId);
  const tabOf = id => vocab.tabs.find(tab => tab.id === id);
  const fieldOf = (tab, key) => tab.fields.find(field => field.key === key);
  const isNeeded = item => item.category === 'open_question';

  function setAccent(hex) {
    const match = palette.find(([, h]) => h === hex) || palette[1];
    const n = parseInt(match[1].slice(1), 16);
    document.documentElement.style.setProperty('--accent', match[1]);
    document.documentElement.style.setProperty('--accent-rgb', [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(' '));
    document.querySelectorAll('.color-option').forEach(b => b.setAttribute('aria-checked', String(b.dataset.hex === match[1])));
  }

  function status(item) {
    const tone = vocab.tones[item.tone];
    const node = el('span', 'status' + (tone.hollow ? ' hollow' : '') + (item.open ? '' : ' closed') + (item.tone === 'done' ? ' done' : ''), item.status.charAt(0).toUpperCase() + item.status.slice(1).replace(/_/g, ' '));
    node.style.setProperty('--dot', 'var(--' + tone.color + ')');
    node.title = tone.label;
    return node;
  }

  // Render a field value: plain, a level with its colored square, or an assessed value with a tooltip.
  function value(target, field, v, display) {
    if (!v) {
      target.append(el('span', 'not-recorded', 'Not recorded'));
      return target;
    }
    if (field.link) return links(target, v);
    const text = field.type === 'date' ? (display === 'short' ? shortDate(v.value) : longDate(v.value)) : v.value;
    const level = vocab.levels[field.key] && vocab.levels[field.key][v.value];
    const shown = el('span', level ? 'level' + (level.squares > 1 ? ' double' : '') : '', text);
    if (level) shown.style.setProperty('--square', 'var(--' + level.color + ')');
    if (v.basis !== 'assessed') {
      target.append(shown);
      return target;
    }
    const wrap = el('button', 'assessed');
    wrap.type = 'button';
    const tip = el('span', 'tip');
    tip.id = 'tip-' + (++tipCount);
    tip.setAttribute('role', 'tooltip');
    tip.append(el('strong', '', 'Assessed'), el('span', '', ' — not stated in the sources. ' + v.reason));
    wrap.setAttribute('aria-describedby', tip.id);
    wrap.append(shown, tip);
    const place = () => {
      tip.style.transform = '';
      const overflow = tip.getBoundingClientRect().right - (innerWidth - 12);
      if (overflow > 0) tip.style.transform = 'translateX(' + -overflow + 'px)';
    };
    wrap.addEventListener('mouseenter', place);
    wrap.addEventListener('focus', place);
    wrap.addEventListener('click', event => event.stopPropagation());
    wrap.addEventListener('keydown', event => { if (event.key === 'Escape') wrap.blur(); });
    target.append(wrap);
    return target;
  }

  // A link field names other rows in the log, such as a next action; each name jumps to its row.
  function links(target, v) {
    v.from.forEach((key, n) => {
      const item = log.items.find(i => i.key === key);
      if (n) target.append(el('span', 'link-sep', '; '));
      if (!item) {
        target.append(el('span', '', key));
        return;
      }
      const link = el('button', 'item-link', item.title);
      link.type = 'button';
      link.append(el('span', 'link-id', item.id));
      link.addEventListener('click', event => { event.stopPropagation(); goTo(key); });
      target.append(link);
    });
    return target;
  }

  function goTo(key) {
    const item = log.items.find(i => i.key === key);
    const row = document.querySelector('.item-row[data-key="' + CSS.escape(key) + '"]');
    // Clear any filter that would hide the row, then open its tab and expand it.
    Object.assign(state, {status: 'all', kind: 'all', query: ''});
    document.getElementById('search').value = '';
    ['state-filter', 'kind-filter'].forEach(id =>
      document.querySelectorAll('#' + id + ' button').forEach((b, n) => b.setAttribute('aria-pressed', String(n === 0))));
    select(item.tab);
    const toggle = row.querySelector('.row-toggle');
    if (toggle.getAttribute('aria-expanded') === 'false') toggle.click();
    row.scrollIntoView({block: 'center'});
    toggle.focus();
  }

  function markers(tab, item) {
    const box = el('span', 'marks');
    if (tab.kinds && tab.kinds[item.category]) box.append(el('span', 'tag ' + (isNeeded(item) ? 'tag-needed' : 'tag-made'), tab.kinds[item.category]));
    return box;
  }

  function sourceLink(entry) {
    const safe = typeof entry.link === 'string' && /^sources\/[A-Za-z0-9_.-]+\.html$/.test(entry.link);
    if (!safe) return el('span', '', entry.sourceRef + ' (snapshot unavailable)');
    const a = el('a', '', entry.sourceRef);
    a.href = entry.link;
    a.target = '_blank';
    a.rel = 'noopener';
    return a;
  }

  function openSource(label, number, button) {
    lastCitation = button;
    const record = details[label];
    const root = document.getElementById('source-details');
    root.replaceChildren();
    document.getElementById('source-dialog-title').textContent = 'Source ' + number;
    document.getElementById('source-label').textContent = record && record.name !== label ? record.name + ' · ' + label : label;
    if (record) {
      if (record.description) root.append(el('p', '', record.description));
      const facts = el('dl', 'source-facts');
      Object.entries(record.facts || {}).forEach(([k, v]) => facts.append(el('dt', '', k), el('dd', '', v)));
      if (facts.children.length) root.append(el('h3', '', 'Current reviewed tracker row'), facts);
      if (record.evidence && record.evidence.length) {
        const list = el('ul', 'source-evidence');
        record.evidence.forEach(entry => { const li = el('li'); li.append(el('blockquote', '', entry.excerpt), sourceLink(entry)); list.append(li); });
        root.append(el('h3', '', 'Evidence excerpts'), list);
      }
      if (record.documents && record.documents.length) {
        const list = el('ul');
        record.documents.forEach(entry => { const li = el('li'); li.append(sourceLink(entry)); list.append(li); });
        root.append(el('h3', '', 'Source documents'), list);
      }
    } else {
      root.append(el('p', '', 'No packaged details are available for this source.'));
    }
    const link = document.getElementById('source-document');
    const first = record && (record.documents || []).find(entry => /^sources\/[A-Za-z0-9_.-]+\.html$/.test(entry.link || ''));
    link.hidden = !first;
    if (first) link.href = first.link;
    document.getElementById('source-dialog').showModal();
    document.getElementById('close-source').focus();
  }

  function citations(item) {
    const box = el('div', 'citations');
    box.append('Sources ');
    item.citations.forEach(label => {
      if (!citeNumbers.has(label)) citeNumbers.set(label, citeNumbers.size + 1);
      const n = citeNumbers.get(label);
      const button = el('button', 'cite', '[' + n + ']');
      button.type = 'button';
      button.setAttribute('aria-label', 'Source ' + n + ': ' + ((details[label] || {}).name || label));
      button.addEventListener('click', event => { event.stopPropagation(); openSource(label, n, button); });
      box.append(button);
    });
    return box;
  }

  function segment(id, options, key) {
    const box = document.getElementById(id);
    options.forEach(([val, label]) => {
      const b = el('button', '', label);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(state[key] === val));
      b.addEventListener('click', () => {
        state[key] = val;
        box.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
        filter();
      });
      box.append(b);
    });
  }

  function buildPanel(tab, index) {
    const tabItems = items(tab.id);
    const open = tabItems.filter(i => i.open).length;
    const t = el('button', 'tab');
    t.type = 'button';
    t.id = 'tab-' + tab.id;
    t.setAttribute('role', 'tab');
    t.setAttribute('aria-controls', 'panel-' + tab.id);
    t.append(el('span', 'tab-label', tab.label), el('span', 'tab-count', open + ' open'));
    t.addEventListener('click', () => select(tab.id));
    t.addEventListener('keydown', e => {
      const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!step) return;
      const next = vocab.tabs[(index + step + vocab.tabs.length) % vocab.tabs.length];
      select(next.id);
      document.getElementById('tab-' + next.id).focus();
    });
    document.getElementById('tabs').append(t);

    const columns = vocab.columns.map(key => fieldOf(tab, key)).filter(Boolean);
    const panel = el('section', 'panel');
    panel.id = 'panel-' + tab.id;
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', t.id);
    const table = el('table', 'register');
    const head = el('tr');
    ['ID', 'Item', 'Status'].concat(columns.map(f => f.key === 'target' ? 'Target date' : f.label), ['']).forEach(h => head.append(el('th', '', h)));
    head.lastChild.append(el('span', 'sr-only', 'Details'));
    // The caption row repeats on every printed page, so each row's type stays clear on paper.
    const caption = el('tr', 'print-caption');
    caption.append(el('th', '', tab.label));
    caption.firstChild.colSpan = head.children.length;
    table.appendChild(el('thead')).append(caption, head);
    const body = el('tbody');
    tabItems.forEach(item => {
      const row = el('tr', 'item-row' + (item.open ? '' : ' is-closed'));
      row.dataset.key = item.key;
      row.dataset.open = item.open;
      row.dataset.kind = isNeeded(item) ? 'needed' : 'made';
      row.dataset.text = [item.id, item.title, item.owner && item.owner.value, item.impactArea && item.impactArea.value].join(' ').toLowerCase();
      row.append(el('td', 'rid', item.id));
      const title = el('td', 'title-cell');
      const button = el('button', 'row-toggle', item.title);
      button.type = 'button';
      button.setAttribute('aria-expanded', 'false');
      title.append(button, markers(tab, item));
      row.append(title);
      const col = (label, cls) => { const td = row.appendChild(el('td', cls)); td.dataset.label = label; return td; };
      col('Status').append(status(item));
      const overdue = item.open && item.target && item.target.value < log.asOf;
      columns.forEach(f => {
        const td = value(col(f.key === 'target' ? 'Target date' : f.label, f.type === 'date' ? 'nowrap' : f.link ? 'link-cell' : ''), f, item[f.key], 'short');
        if (f.key === 'target' && overdue) {
          // Red marks an open item past its target; the hidden text keeps that meaning for screen readers.
          td.classList.add('overdue');
          td.title = 'Overdue';
          td.append(el('span', 'sr-only', ' (overdue)'));
        }
      });
      row.append(el('td', 'chev', '›'));
      const detail = el('tr', 'detail-row');
      detail.hidden = true;
      const cell = el('td');
      cell.colSpan = head.children.length;
      const list = el('dl', 'fields');
      tab.fields.filter(f => !vocab.columns.includes(f.key)).forEach(f => {
        const box = el('div', ['outcome', 'nextAction', 'addresses', 'resolutionPlan'].includes(f.key) ? 'wide' : '');
        box.append(el('dt', '', f.label));
        value(box.appendChild(el('dd')), f, item[f.key], 'long');
        list.append(box);
      });
      cell.append(el('p', 'desc', item.description), list, citations(item));
      detail.append(cell);
      const toggle = () => {
        const opening = detail.hidden;
        detail.hidden = !opening;
        button.setAttribute('aria-expanded', String(opening));
        row.classList.toggle('expanded', opening);
      };
      button.addEventListener('click', e => { e.stopPropagation(); toggle(); });
      row.addEventListener('click', toggle);
      body.append(row, detail);
    });
    table.append(body);
    const wrap = el('div', 'table-wrap');
    wrap.append(table);
    panel.append(wrap, el('p', 'empty', tabItems.length ? 'No items match these filters.' : 'No ' + tab.label.toLowerCase() + ' are recorded for this project.'));
    document.getElementById('panels').append(panel);
  }

  function select(id) {
    state.tab = id;
    vocab.tabs.forEach(tab => {
      const on = tab.id === id;
      const t = document.getElementById('tab-' + tab.id);
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById('panel-' + tab.id).classList.toggle('active', on);
    });
    document.getElementById('kind-group').hidden = !Object.keys(tabOf(id).kinds || {}).length;
    filter();
  }

  function filter() {
    vocab.tabs.forEach(tab => {
      const panel = document.getElementById('panel-' + tab.id);
      const hasKinds = Object.keys(tab.kinds || {}).length > 0;
      let shown = 0;
      panel.querySelectorAll('.item-row').forEach(row => {
        const ok = (state.status === 'all' || String(state.status === 'open') === row.dataset.open)
          && (!hasKinds || state.kind === 'all' || state.kind === row.dataset.kind)
          && (!state.query || row.dataset.text.includes(state.query));
        row.hidden = !ok;
        if (!ok) {
          row.nextElementSibling.hidden = true;
          row.classList.remove('expanded');
          row.querySelector('.row-toggle').setAttribute('aria-expanded', 'false');
        }
        shown += ok;
      });
      panel.classList.toggle('none', shown === 0);
      if (tab.id === state.tab) document.getElementById('result-count').textContent = shown + ' of ' + items(tab.id).length + ' ' + tab.label.toLowerCase();
    });
  }

  // Header
  document.getElementById('project').textContent = log.project;
  document.getElementById('as-of').textContent = 'As of ' + longDate(log.asOf);
  document.getElementById('sample-banner').hidden = !log.sample;
  document.title = 'RAID log — ' + log.project;
  const totals = document.getElementById('totals');
  [['Open items', log.items.filter(i => i.open).length],
   ['Decisions needed', log.items.filter(i => isNeeded(i) && i.open).length]]
    .forEach(([label, n]) => { const d = el('div'); d.append(el('dt', '', label), el('dd', '', String(n))); totals.append(d); });

  // Controls
  segment('state-filter', [['all', 'All'], ['open', 'Open'], ['closed', 'Closed']], 'status');
  segment('kind-filter', [['all', 'All'], ['made', 'Made'], ['needed', 'Needed']], 'kind');
  document.getElementById('search').addEventListener('input', e => { state.query = e.target.value.trim().toLowerCase(); filter(); });
  const sources = document.getElementById('sources-toggle');
  sources.addEventListener('click', () => {
    const on = document.body.classList.toggle('sources-on');
    sources.setAttribute('aria-pressed', String(on));
    sources.textContent = on ? 'Hide sources' : 'Show sources';
  });
  const toggle = document.getElementById('color-toggle');
  const menu = document.getElementById('color-menu');
  palette.forEach(([name, hex]) => {
    const option = el('button', 'color-option', name);
    option.type = 'button';
    option.setAttribute('role', 'menuitemradio');
    option.dataset.hex = hex;
    option.style.setProperty('--swatch', hex);
    option.addEventListener('click', () => {
      try { localStorage.setItem(colorKey, hex); } catch (_) { /* Storage can be unavailable. */ }
      setAccent(hex);
      menu.hidden = true;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    });
    menu.append(option);
  });
  toggle.addEventListener('click', () => {
    menu.hidden = !menu.hidden;
    toggle.setAttribute('aria-expanded', String(!menu.hidden));
    if (!menu.hidden) menu.querySelector('[aria-checked="true"]').focus();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !menu.hidden) { menu.hidden = true; toggle.setAttribute('aria-expanded', 'false'); toggle.focus(); }
  });
  let stored = null;
  try { stored = localStorage.getItem(colorKey); } catch (_) { /* Storage can be unavailable. */ }
  setAccent(stored || log.secondaryColor.hex);
  document.getElementById('print-button').addEventListener('click', () => window.print());
  const exportLink = document.getElementById('export-link');
  if (log.exportFile) exportLink.href = log.exportFile;
  else exportLink.hidden = true;
  const dialog = document.getElementById('source-dialog');
  document.getElementById('close-source').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => lastCitation && lastCitation.focus());

  vocab.tabs.forEach(buildPanel);
  select(state.tab);
})();
