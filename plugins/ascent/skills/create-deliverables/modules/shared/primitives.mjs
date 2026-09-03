/** Shared, low-level HTML primitives used by module-owned renderers. */

export function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function typeset(text) {
  return esc(text)
    .replace(/(^|[\s(\[])&#39;/g, '$1‘')
    .replace(/&#39;/g, '’')
    .replace(/(^|[\s(\[])&quot;/g, '$1“')
    .replace(/&quot;/g, '”')
    .replace(/ -- /g, ' — ');
}

export function slug(text) {
  return String(text ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48);
}

function inline(text) {
  return typeset(text)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
}

export function renderProse(text) {
  const blocks = String(text ?? '').replace(/\r\n?/g, '\n').trim().split(/\n{2,}/);
  const out = [];
  for (const block of blocks) {
    const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
    if (!lines.length) continue;
    if (lines.every((line) => /^[-*]\s+/.test(line))) {
      const items = lines.map((line) => `<li>${inline(line.replace(/^[-*]\s+/, ''))}</li>`);
      out.push(`<ul>${items.join('')}</ul>`);
    } else {
      out.push(`<p>${inline(lines.join(' '))}</p>`);
    }
  }
  return out.join('');
}

export function meter(on, total, extraClass = '') {
  const steps = [];
  for (let i = 1; i <= total; i++) {
    steps.push(`<span class="meter__step${i <= on ? ' meter__step--on' : ''}"></span>`);
  }
  return `<span class="meter${extraClass ? ` ${extraClass}` : ''}" aria-hidden="true">${steps.join('')}</span>`;
}

export function toNumeric(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const decimals = (String(value).split('.')[1] ?? '').length;
    return { value, decimals };
  }
  if (typeof value === 'string' && /^-?\d{1,3}(,\d{3})*(\.\d+)?$/.test(value.trim())) {
    const plain = value.trim().replace(/,/g, '');
    return { value: Number(plain), decimals: (plain.split('.')[1] ?? '').length };
  }
  return null;
}

export function renderDataTable(section) {
  const head = section.columns.map((column) => `<th scope="col">${typeset(column)}</th>`).join('');
  const body = section.rows.map((row) => {
    const [first, ...rest] = row.cells;
    const cells = rest.map((cell) => `<td>${typeset(cell)}</td>`).join('');
    return `
          <tr>
            <th scope="row">${typeset(first ?? '')}</th>${cells}
          </tr>`;
  }).join('');
  return `
    <div class="data-table" data-motion="fade-up">
      <div class="data-table__scroll">
        <table>
          <thead><tr>${head}</tr></thead>
          <tbody>${body}
          </tbody>
        </table>
      </div>
    </div>`;
}

export const COLOR_BAR_ORDER = ['blue', 'cyan', 'coral-red', 'purple', 'chartreuse'];

export function colorBar() {
  const swatches = COLOR_BAR_ORDER
    .map((name) => `<span class="color-bar__swatch color-bar__swatch--${name}"></span>`)
    .join('');
  return `<div class="color-bar" data-motion="color-bar-draw" aria-hidden="true">${swatches}</div>`;
}

export function slalomLine() {
  return [
    '<svg class="slalom-line" data-motion="line-draw" viewBox="0 0 600 400"',
    ' preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">',
    '<path d="M-20 392C110 392 132 236 214 168 296 100 372 168 430 128 488 88 500 24 620 8"/>',
    '</svg>',
  ].join('');
}
