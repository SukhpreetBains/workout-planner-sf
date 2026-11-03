/*
 * Slalom components — framework-free behavior for the markup patterns in
 * components/reference/. Load after slalom-components.css, at the end of
 * <body> or with `defer`. Every interactive or animated pattern carries a
 * `data-sl="<name>"` attribute; SlalomUI.init() enhances each one once.
 *
 * Without this script every pattern still renders in its final, readable
 * state (the stylesheet only hides content once `html.sl-js` is set here).
 * Motion is ease-out, never bouncy, and settles under prefers-reduced-motion.
 */
(function () {
  'use strict';
  var doc = document;
  doc.documentElement.classList.add('sl-js');

  var uid = 0;
  function id(prefix) { uid += 1; return 'sl-' + prefix + '-' + uid; }
  function el(tag, cls, text) {
    var n = doc.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function num(v, d) { var n = parseFloat(v); return isNaN(n) ? d : n; }
  function pad2(n) { n = String(n); return n.length < 2 ? '0' + n : n; }
  function reducedMotion() { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }
  function fmt(n, decimals) {
    var d = decimals || 0;
    return Number(n.toFixed(d)).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function srOnly(text) { var s = el('span', 'sl-sr-only', text); return s; }

  /* Adds `cls` to `node` once it scrolls into view (at once without IntersectionObserver). */
  function onView(node, cls, threshold, cb) {
    function go() { node.classList.add(cls); if (cb) cb(); }
    if (!('IntersectionObserver' in window)) { go(); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { go(); io.disconnect(); } });
    }, { threshold: threshold == null ? 0.2 : threshold });
    io.observe(node);
  }
  /* Counts `target`'s text from 0 to `to` with an ease-out curve. */
  function countUp(target, to, decimals, duration, render) {
    if (reducedMotion()) { render(fmt(to, decimals)); return; }
    var start = null, d = duration || 1600;
    function step(t) {
      if (start == null) start = t;
      var p = Math.min(1, (t - start) / d), e = 1 - Math.pow(1 - p, 3);
      render(fmt(to * e, decimals));
      if (p < 1) requestAnimationFrame(step);
    }
    render(fmt(0, decimals));
    requestAnimationFrame(step);
  }

  var enhancers = {};

  /* ---------- Base controls ---------- */

  enhancers['menu-toggle'] = function (btn) {
    btn.setAttribute('aria-expanded', btn.classList.contains('sl-menu-open') ? 'true' : 'false');
    if (!btn.querySelector('.sl-menu-bar')) for (var i = 0; i < 3; i++) btn.appendChild(el('span', 'sl-menu-bar'));
    btn.addEventListener('click', function () {
      var open = !btn.classList.contains('sl-menu-open');
      btn.classList.toggle('sl-menu-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (!btn.hasAttribute('data-label-fixed')) btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      var target = btn.getAttribute('aria-controls') && doc.getElementById(btn.getAttribute('aria-controls'));
      if (target) target.hidden = !open;
      btn.dispatchEvent(new CustomEvent('sl:toggle', { bubbles: true, detail: { open: open } }));
    });
  };

  var PALETTE_ROWS = [
    ['Primary', 'slalom-blue slalom-dark-blue'],
    ['Cyan', 'cyan-dark-3 cyan-dark-2 cyan-dark-1 cyan cyan-light-1 cyan-light-2 cyan-light-3'],
    ['Coral Red', 'coral-red-dark-3 coral-red-dark-2 coral-red-dark-1 coral-red coral-red-light-1 coral-red-light-2 coral-red-light-3'],
    ['Purple', 'purple-dark-3 purple-dark-2 purple-dark-1 purple purple-light-1 purple-light-2 purple-light-3'],
    ['Chartreuse', 'chartreuse-dark-3 chartreuse-dark-2 chartreuse-dark-1 chartreuse chartreuse-light-1 chartreuse-light-2 chartreuse-light-3'],
    ['Neutrals', 'white light-gray dark-gray black']
  ];
  function toHex(rgb) {
    var m = /rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(rgb || '');
    if (!m) return rgb || '';
    return '#' + [m[1], m[2], m[3]].map(function (n) { return ('0' + parseInt(n, 10).toString(16)).slice(-2); }).join('').toUpperCase();
  }
  enhancers['color-selector'] = function (root) {
    root.classList.add('sl-dock');
    var tokens = root.getAttribute('data-tokens');
    var rows = tokens ? [[root.getAttribute('data-name') || '', tokens]] : PALETTE_ROWS;
    rows.forEach(function (r) {
      var row = el('div', 'sl-dock-row');
      if (r[0]) row.appendChild(el('span', 'sl-dock-name caption', r[0]));
      var items = el('div', 'sl-dock-items');
      r[1].split(' ').forEach(function (t) {
        var b = el('button', 'sl-swatch'); b.type = 'button';
        var chip = el('span', 'sl-swatch-chip'); chip.style.background = 'var(--' + t + ')';
        var tip = el('span', 'sl-swatch-tip caption'); tip.setAttribute('aria-hidden', 'true');
        b.appendChild(chip); b.appendChild(tip); items.appendChild(b);
        requestAnimationFrame(function () {
          var hex = toHex(getComputedStyle(chip).backgroundColor);
          tip.textContent = t + ' ' + hex; b.setAttribute('aria-label', t + ' ' + hex + ', copy hex');
          b.addEventListener('click', function () {
            var done = function () { tip.textContent = 'Copied'; setTimeout(function () { tip.textContent = t + ' ' + hex; }, 1200); };
            if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(hex).then(done, done); else done();
          });
        });
      });
      row.appendChild(items); root.appendChild(row);
    });
  };

  /* ---------- Storytelling ---------- */

  enhancers['kinetic'] = function (root) {
    var heading = root.querySelector('.sl-kh-text') || root.querySelector('h1, h2, h3');
    if (!heading) return;
    heading.classList.add('sl-kh-text');
    var text = heading.textContent.replace(/\s+/g, ' ').trim();
    var marks = (root.getAttribute('data-highlight') || '').toLowerCase().split(/\s+/).filter(Boolean);
    var words = text.split(' ');
    var wrap = el('span'); wrap.setAttribute('aria-hidden', 'true');
    words.forEach(function (w, i) {
      var bare = w.toLowerCase().replace(/[.,!?;:"“”‘]/g, '');
      var word = el('span', 'sl-kh-word' + (marks.indexOf(bare) >= 0 ? ' sl-kh-mark' : ''));
      word.style.setProperty('--i', i);
      word.appendChild(el('span', 'sl-kh-inner', w));
      wrap.appendChild(word);
      if (i < words.length - 1) wrap.appendChild(doc.createTextNode(' '));
    });
    heading.setAttribute('aria-label', text);
    heading.textContent = '';
    heading.appendChild(wrap);
    root.style.setProperty('--n', words.length);
    root.classList.add('sl-kh');
    onView(root, 'sl-kh-in', 0.3);
  };

  enhancers['reveal'] = function (root) {
    var delay = num(root.getAttribute('data-delay'), 0);
    var stagger = num(root.getAttribute('data-stagger'), 0);
    var from = root.getAttribute('data-from') || 'up';
    root.classList.add('sl-reveal-' + from);
    if (stagger) {
      root.classList.add('sl-reveal-group');
      Array.prototype.forEach.call(root.children, function (c, i) {
        c.classList.add('sl-reveal-item');
        c.style.transitionDelay = (delay + i * stagger) + 'ms';
      });
    } else {
      root.classList.add('sl-reveal');
      root.style.transitionDelay = delay + 'ms';
    }
    onView(root, 'sl-reveal-in', num(root.getAttribute('data-threshold'), 0.2));
  };

  enhancers['chapter'] = function (root) {
    var raw = root.getAttribute('data-number') || '1';
    var n = /^\d+$/.test(raw) ? pad2(raw) : raw;
    var numEl = el('div', 'sl-chapter-num'); numEl.setAttribute('aria-hidden', 'true');
    numEl.appendChild(el('span', 'sl-chapter-outline', n));
    numEl.appendChild(el('span', 'sl-chapter-fill', n));
    root.insertBefore(numEl, root.firstChild);
    var body = root.querySelector('.sl-chapter-body');
    var title = root.querySelector('.sl-chapter-title');
    if (title) title.insertBefore(srOnly('Chapter ' + n + ': '), title.firstChild);
    if (body && !body.querySelector('.sl-chapter-rule')) { var r = el('span', 'sl-chapter-rule'); r.setAttribute('aria-hidden', 'true'); body.appendChild(r); }
    onView(root, 'sl-chapter-in', 0.4);
  };

  enhancers['hero'] = function (root) {
    var media = root.querySelector('.sl-hero-media');
    if (media && !media.querySelector('.sl-hero-block')) {
      var frame = media.querySelector('.sl-hero-frame');
      var block = el('span', 'sl-hero-block ' + ((frame && frame.className.match(/sl-corner-\w+/)) || ['sl-corner-br'])[0] + ' sl-radius-l');
      block.setAttribute('aria-hidden', 'true');
      media.insertBefore(block, media.firstChild);
    }
    onView(root, 'sl-hero-in', 0.2);
  };

  enhancers['marquee'] = function (root) {
    var group = root.querySelector('.sl-mq-group');
    if (!group) return;
    Array.prototype.forEach.call(group.children, function (li) {
      li.classList.add('sl-mq-item');
      var sep = el('span', 'sl-mq-sep'); sep.setAttribute('aria-hidden', 'true');
      li.insertBefore(sep, li.firstChild);
    });
    var track = el('div', 'sl-mq-track');
    root.insertBefore(track, group);
    track.appendChild(group);
    var dup = group.cloneNode(true); dup.setAttribute('aria-hidden', 'true');
    track.appendChild(dup);
    if (!root.getAttribute('role')) root.setAttribute('role', 'region');
    if (!root.getAttribute('aria-label')) root.setAttribute('aria-label', 'Highlights');
    var btn = el('button', 'sl-mq-toggle caption', 'Pause'); btn.type = 'button'; btn.setAttribute('aria-pressed', 'false');
    btn.addEventListener('click', function () {
      var paused = !root.classList.contains('sl-mq-paused');
      root.classList.toggle('sl-mq-paused', paused);
      btn.textContent = paused ? 'Play' : 'Pause';
      btn.setAttribute('aria-pressed', paused ? 'true' : 'false');
    });
    root.appendChild(btn);
  };

  /* ---------- Data ---------- */

  enhancers['stat'] = function (root) {
    var value = num(root.getAttribute('data-value'), 0);
    var decimals = num(root.getAttribute('data-decimals'), 0);
    var prefix = root.getAttribute('data-prefix') || '';
    var suffix = root.getAttribute('data-suffix') || '';
    var numEl = root.querySelector('.sl-stat-num');
    if (!numEl) { numEl = el('p', 'sl-stat-num'); root.appendChild(numEl); }
    numEl.textContent = '';
    var vis = el('span'); vis.setAttribute('aria-hidden', 'true');
    var digits = el('span', null, fmt(value, decimals));
    vis.appendChild(doc.createTextNode(prefix)); vis.appendChild(digits);
    if (suffix) vis.appendChild(el('span', 'sl-stat-suffix', suffix));
    numEl.appendChild(vis);
    numEl.appendChild(srOnly(prefix + fmt(value, decimals) + suffix));
    var bar = root.getAttribute('data-bar');
    if (bar != null && !root.querySelector('.sl-stat-bar')) {
      var b = el('span', 'sl-stat-bar'); b.setAttribute('aria-hidden', 'true');
      b.style.setProperty('--sl-pct', Math.max(0, Math.min(100, num(bar, 0))) + '%');
      b.appendChild(el('span', 'sl-stat-bar-fill'));
      root.appendChild(b);
    }
    digits.textContent = fmt(0, decimals);
    onView(root, 'sl-stat-in', 0.4, function () {
      countUp(digits, value, decimals, num(root.getAttribute('data-duration'), 1600), function (t) { digits.textContent = t; });
    });
  };

  enhancers['waffle'] = function (root) {
    var value = Math.max(0, Math.min(100, Math.round(num(root.getAttribute('data-value'), 0))));
    var label = root.querySelector('.sl-waffle-label');
    var grid = el('div', 'sl-waffle-grid'); grid.setAttribute('role', 'img');
    grid.setAttribute('aria-label', value + ' of 100' + (label ? ' ' + label.textContent : ''));
    for (var i = 0; i < 100; i++) {
      var c = el('span', 'sl-waffle-cell' + (i < value ? ' sl-waffle-on' : ''));
      if (i < value) c.style.transitionDelay = (i * 10) + 'ms';
      grid.appendChild(c);
    }
    root.insertBefore(grid, root.firstChild);
    var numEl = root.querySelector('.sl-waffle-num');
    var digits = null;
    if (numEl) {
      numEl.setAttribute('aria-hidden', 'true');
      var unit = numEl.querySelector('.sl-stat-suffix');
      numEl.textContent = '';
      digits = el('span', null, '0'); numEl.appendChild(digits);
      if (unit) numEl.appendChild(unit);
    }
    onView(root, 'sl-waffle-in', 0.3, function () {
      if (digits) countUp(digits, value, 0, 1200, function (t) { digits.textContent = t; });
    });
  };

  enhancers['bars'] = function (root) {
    var items = Array.prototype.slice.call(root.querySelectorAll('.sl-mbar'));
    var values = items.map(function (li) { return num(li.getAttribute('data-value'), 0); });
    var max = num(root.getAttribute('data-max'), 0) || Math.max.apply(null, values.concat([1]));
    items.forEach(function (li, i) {
      var track = el('span', 'sl-mbar-track'); track.setAttribute('aria-hidden', 'true');
      var fill = el('span', 'sl-mbar-fill');
      fill.style.transitionDelay = (i * 120) + 'ms';
      track.style.setProperty('--sl-pct', Math.max(0, Math.min(100, values[i] / max * 100)) + '%');
      track.appendChild(fill); li.appendChild(track);
    });
    onView(root, 'sl-mbars-in', 0.3);
  };

  enhancers['compare'] = function (root) {
    var bl = root.getAttribute('data-before-label'), al = root.getAttribute('data-after-label');
    var before = root.querySelector('.sl-cmp-before');
    var pos = num(root.getAttribute('data-initial'), 50);
    if (bl) { var t1 = el('span', 'sl-cmp-tag sl-cmp-tag-before eyebrow', bl); t1.setAttribute('aria-hidden', 'true'); root.appendChild(t1); }
    if (al) { var t2 = el('span', 'sl-cmp-tag sl-cmp-tag-after eyebrow', al); t2.setAttribute('aria-hidden', 'true'); root.appendChild(t2); }
    var input = el('input', 'sl-cmp-input'); input.type = 'range'; input.min = 0; input.max = 100; input.value = pos;
    input.setAttribute('aria-label', root.getAttribute('data-label') || ('Compare ' + (bl || 'before') + ' and ' + (al || 'after')));
    var handle = el('span', 'sl-cmp-handle'); handle.setAttribute('aria-hidden', 'true');
    handle.appendChild(el('span', 'sl-cmp-knob', '‹ ›'));
    root.appendChild(input); root.appendChild(handle);
    function set(p) {
      if (before) before.style.clipPath = 'inset(0 ' + (100 - p) + '% 0 0)';
      handle.style.left = p + '%';
      input.setAttribute('aria-valuetext', p + '% ' + (bl || 'before'));
    }
    input.addEventListener('input', function () { set(Number(input.value)); });
    set(pos);
  };

  /* ---------- Navigation ---------- */

  enhancers['phases'] = function (root) {
    var sections = Array.prototype.slice.call(root.querySelectorAll(':scope > section'));
    if (!sections.length) return;
    var base = id('px');
    root.style.setProperty('--sl-px-n', sections.length);
    var tabs = el('div', 'sl-px-tabs'); tabs.setAttribute('role', 'tablist');
    tabs.setAttribute('aria-label', root.getAttribute('aria-label') || 'Phases');
    root.removeAttribute('aria-label');
    root.insertBefore(tabs, root.firstChild);
    var buttons = [];
    sections.forEach(function (s, k) {
      var label = s.getAttribute('data-label') || ('Phase ' + (k + 1));
      var b = el('button', 'sl-px-tab'); b.type = 'button'; b.id = base + '-t' + k;
      b.setAttribute('role', 'tab'); b.setAttribute('aria-controls', base + '-p' + k);
      var m = el('span', 'sl-px-marker'); m.setAttribute('aria-hidden', 'true');
      b.appendChild(m); b.appendChild(el('span', 'sl-px-num caption', pad2(k + 1))); b.appendChild(el('span', 'sl-px-label body-strong', label));
      tabs.appendChild(b); buttons.push(b);
      b.addEventListener('click', function () { select(k); });
      /* Turn the authored section into a panel. */
      s.id = base + '-p' + k; s.setAttribute('role', 'tabpanel'); s.setAttribute('aria-labelledby', b.id);
      s.className = 'sl-px-panel sl-corner-br sl-radius-l';
      var main = el('div', 'sl-px-main');
      var meta = s.getAttribute('data-meta');
      if (meta) main.appendChild(el('p', 'sl-px-meta eyebrow', meta));
      var list = s.querySelector(':scope > ul');
      Array.prototype.slice.call(s.childNodes).forEach(function (c) { if (c !== list) main.appendChild(c); });
      var h = main.querySelector('h2, h3, h4'); if (h) h.classList.add('sl-px-title', 'headline-m');
      Array.prototype.forEach.call(main.querySelectorAll('p:not(.sl-px-meta)'), function (p) { p.classList.add('sl-px-body', 'body'); });
      s.appendChild(main);
      if (list) {
        list.classList.add('sl-px-items');
        Array.prototype.forEach.call(list.children, function (li) { li.classList.add('body-strong'); });
        s.appendChild(list);
      }
      if (k < sections.length - 1) {
        var next = el('button', 'sl-px-next body-strong', 'Next: ' + (sections[k + 1].getAttribute('data-label') || 'Phase ' + (k + 2)) + ' →');
        next.type = 'button';
        next.addEventListener('click', function () { select(k + 1); buttons[k + 1].focus(); });
        s.appendChild(next);
      }
    });
    function select(i) {
      buttons.forEach(function (b, k) {
        b.setAttribute('aria-selected', k === i ? 'true' : 'false');
        b.tabIndex = k === i ? 0 : -1;
        b.classList.toggle('sl-px-active', k === i);
        b.classList.toggle('sl-px-done', k < i);
        sections[k].hidden = k !== i;
      });
      sections[i].classList.remove('sl-px-enter'); void sections[i].offsetWidth; sections[i].classList.add('sl-px-enter');
    }
    tabs.addEventListener('keydown', function (e) {
      var cur = buttons.indexOf(doc.activeElement); if (cur < 0) return;
      var n = buttons.length, to = null;
      if (e.key === 'ArrowRight') to = (cur + 1) % n; else if (e.key === 'ArrowLeft') to = (cur - 1 + n) % n;
      else if (e.key === 'Home') to = 0; else if (e.key === 'End') to = n - 1;
      if (to != null) { e.preventDefault(); select(to); buttons[to].focus(); }
    });
    select(Math.min(sections.length - 1, num(root.getAttribute('data-default'), 0)));
  };

  enhancers['timeline'] = function (root) {
    Array.prototype.forEach.call(root.querySelectorAll(':scope > li'), function (li) {
      li.classList.add('sl-tl-item');
      var content = el('div', 'sl-tl-content');
      while (li.firstChild) content.appendChild(li.firstChild);
      if (li.classList.contains('sl-tl-current')) content.insertBefore(el('span', 'sl-tl-now caption', li.getAttribute('data-current-label') || 'Now'), content.firstChild);
      var rail = el('span', 'sl-tl-rail'); rail.setAttribute('aria-hidden', 'true');
      rail.appendChild(el('span', 'sl-tl-line')); rail.appendChild(el('span', 'sl-tl-dot'));
      li.appendChild(el('span', 'sl-tl-date eyebrow', li.getAttribute('data-date') || ''));
      li.appendChild(rail); li.appendChild(content);
      onView(li, 'sl-tl-in', 0.5);
    });
  };

  enhancers['accordion'] = function (root) {
    var multiple = root.hasAttribute('data-multiple');
    var numbered = root.getAttribute('data-numbered') !== 'false';
    var open = (root.getAttribute('data-open') || '').split(/[\s,]+/).filter(Boolean).map(Number);
    var items = Array.prototype.slice.call(root.querySelectorAll(':scope > .sl-acc-item'));
    var api = [];
    items.forEach(function (item, k) {
      var h = item.querySelector('.sl-acc-h'), panel = item.querySelector('.sl-acc-panel');
      if (!h || !panel) return;
      var bid = id('acc-b'), pid = id('acc-p');
      var btn = el('button', 'sl-acc-btn'); btn.type = 'button'; btn.id = bid; btn.setAttribute('aria-controls', pid);
      if (numbered) btn.appendChild(el('span', 'sl-acc-num body-strong', pad2(k + 1)));
      btn.appendChild(el('span', 'sl-acc-title subhead', h.textContent.trim()));
      var icon = el('span', 'sl-acc-icon'); icon.setAttribute('aria-hidden', 'true'); btn.appendChild(icon);
      h.textContent = ''; h.appendChild(btn);
      panel.id = pid; panel.setAttribute('role', 'region'); panel.setAttribute('aria-labelledby', bid);
      if (!numbered) root.classList.add('sl-acc-plain');
      function set(on) {
        item.classList.toggle('sl-acc-open', on);
        btn.setAttribute('aria-expanded', on ? 'true' : 'false');
        if (on) panel.removeAttribute('inert'); else panel.setAttribute('inert', '');
      }
      api.push(set);
      set(open.indexOf(k) >= 0);
      btn.addEventListener('click', function () {
        var on = !item.classList.contains('sl-acc-open');
        if (on && !multiple) api.forEach(function (s, j) { if (j !== k) s(false); });
        set(on);
      });
    });
  };

  /* ---------- People ---------- */

  enhancers['profile'] = function (root) {
    var bio = root.querySelector('.sl-pcard-bio'), meta = root.querySelector('.sl-pcard-meta');
    var media = root.querySelector('.sl-pcard-media');
    var name = root.querySelector('.sl-pcard-name');
    if (media && !media.querySelector('img') && !media.querySelector('.sl-pcard-mono') && name) {
      var mono = el('span', 'sl-pcard-mono', name.textContent.split(/\s+/).filter(Boolean).slice(0, 2).map(function (w) { return w.charAt(0).toUpperCase(); }).join(''));
      mono.setAttribute('aria-hidden', 'true');
      media.insertBefore(mono, media.firstChild);
    }
    if (!bio || !meta) return;
    bio.id = bio.id || id('bio');
    var btn = el('button', 'sl-pcard-toggle body-small', 'Read bio'); btn.type = 'button';
    btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', bio.id);
    btn.addEventListener('click', function () {
      var open = !root.classList.contains('sl-pcard-open');
      root.classList.toggle('sl-pcard-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.textContent = open ? 'Close bio' : 'Read bio';
    });
    meta.appendChild(btn);
  };

  enhancers['quotes'] = function (root) {
    var slides = Array.prototype.slice.call(root.querySelectorAll(':scope > .sl-qc-slide'));
    if (!slides.length) return;
    var interval = num(root.getAttribute('data-interval'), 7000);
    var auto = root.getAttribute('data-autoplay') !== 'false' && slides.length > 1 && !reducedMotion();
    var i = 0, paused = false, hovering = false, timer = null;
    root.setAttribute('aria-roledescription', 'carousel');
    if (!root.getAttribute('aria-label')) root.setAttribute('aria-label', 'Customer quotes');
    root.style.setProperty('--sl-qc-int', interval + 'ms');
    var mark = el('span', 'sl-qc-mark', '“'); mark.setAttribute('aria-hidden', 'true');
    root.insertBefore(mark, root.firstChild);
    slides.forEach(function (s, k) { s.setAttribute('aria-roledescription', 'slide'); s.setAttribute('aria-label', (k + 1) + ' of ' + slides.length); });
    var foot = el('div', 'sl-qc-foot');
    var segs = el('div', 'sl-qc-segs'); segs.setAttribute('aria-hidden', 'true');
    var segEls = slides.map(function () { var s = el('span', 'sl-qc-seg'); segs.appendChild(s); return s; });
    var count = el('span', 'sl-qc-count caption');
    foot.appendChild(segs); foot.appendChild(count);
    var pauseBtn = null;
    if (auto) {
      pauseBtn = el('button', 'sl-qc-pause caption', 'Pause'); pauseBtn.type = 'button'; pauseBtn.setAttribute('aria-pressed', 'false');
      pauseBtn.addEventListener('click', function () { paused = !paused; pauseBtn.textContent = paused ? 'Play' : 'Pause'; pauseBtn.setAttribute('aria-pressed', paused ? 'true' : 'false'); render(); });
      foot.appendChild(pauseBtn);
    }
    var prev = el('button', 'sl-qc-btn', '←'); prev.type = 'button'; prev.setAttribute('aria-label', 'Previous quote');
    var next = el('button', 'sl-qc-btn', '→'); next.type = 'button'; next.setAttribute('aria-label', 'Next quote');
    prev.addEventListener('click', function () { go(i - 1); });
    next.addEventListener('click', function () { go(i + 1); });
    foot.appendChild(prev); foot.appendChild(next);
    root.appendChild(foot);
    root.addEventListener('mouseenter', function () { hovering = true; render(); });
    root.addEventListener('mouseleave', function () { hovering = false; render(); });
    root.addEventListener('focusin', function () { hovering = true; render(); });
    root.addEventListener('focusout', function (e) { if (!root.contains(e.relatedTarget)) { hovering = false; render(); } });
    function go(n) { i = (n + slides.length) % slides.length; render(); }
    function render() {
      var running = auto && !paused && !hovering;
      slides.forEach(function (s, k) {
        var on = k === i;
        if (on && s.hidden) { s.classList.remove('sl-qc-enter'); void s.offsetWidth; s.classList.add('sl-qc-enter'); }
        s.hidden = !on;
        s.setAttribute('aria-live', running ? 'off' : 'polite');
      });
      segEls.forEach(function (s, k) {
        s.className = 'sl-qc-seg' + (k < i ? ' sl-qc-seg-done' : '') + (k === i ? (running ? ' sl-qc-seg-run' : ' sl-qc-seg-done') : '');
        if (k === i && running) { void s.offsetWidth; }
      });
      count.textContent = pad2(i + 1) + ' / ' + pad2(slides.length);
      clearTimeout(timer);
      if (running) timer = setTimeout(function () { go(i + 1); }, interval);
    }
    render();
  };

  function init(scope) {
    var rootNode = scope || doc;
    Array.prototype.forEach.call(rootNode.querySelectorAll('[data-sl]'), function (node) {
      if (node.__slDone) return;
      var fn = enhancers[node.getAttribute('data-sl')];
      if (!fn) return;
      node.__slDone = true;
      fn(node);
    });
  }

  window.SlalomUI = { init: init, enhancers: enhancers };
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { init(); });
  else init();
})();
