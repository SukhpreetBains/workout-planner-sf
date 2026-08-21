/**
 * report.mjs — the shared console reporter.
 *
 * Errors block delivery. Warnings print and pass. The distinction is the whole
 * point of the gate, so warnings are printed last and counted out loud rather
 * than scrolled past in a wall of green.
 */

const useColor = process.env.NO_COLOR === undefined && process.stdout?.isTTY;
const paint = (code, text) => (useColor ? `\u001b[${code}m${text}\u001b[0m` : text);

export const style = {
  bold: (t) => paint('1', t),
  dim: (t) => paint('2', t),
  red: (t) => paint('31', t),
  green: (t) => paint('32', t),
  yellow: (t) => paint('33', t),
  blue: (t) => paint('34', t),
};

export class Report {
  /**
   * @param {string} title
   * @param {{summary?: boolean}} options `summary: false` for a report that
   *   only carries notes, so a build summary does not print "0 checks".
   */
  constructor(title, { summary = true } = {}) {
    this.title = title;
    this.summary = summary;
    this.errors = [];
    this.warnings = [];
    this.notes = [];
    this.checks = 0;
  }

  /** Record a rule's outcome. `ok === true` passes, `false` fails. */
  check(ok, rule, message, { warn = false } = {}) {
    this.checks++;
    if (ok) return true;
    (warn ? this.warnings : this.errors).push({ rule, message });
    return false;
  }

  error(rule, message) { return this.check(false, rule, message); }
  warn(rule, message) { return this.check(false, rule, message, { warn: true }); }
  note(message) { this.notes.push(message); }

  get ok() { return this.errors.length === 0; }

  print(out = console) {
    out.log('');
    out.log(style.bold(this.title));

    for (const note of this.notes) out.log(`  ${style.dim('·')} ${note}`);
    if (this.notes.length) out.log('');

    if (!this.summary && this.errors.length === 0 && this.warnings.length === 0) return true;

    for (const { rule, message } of this.errors) {
      out.log(`  ${style.red('FAIL')} ${style.dim(rule)}  ${message}`);
    }
    for (const { rule, message } of this.warnings) {
      out.log(`  ${style.yellow('WARN')} ${style.dim(rule)}  ${message}`);
    }

    out.log('');
    const counts = [
      `${this.checks} checks`,
      this.errors.length ? style.red(`${this.errors.length} failed`) : style.green('0 failed'),
      this.warnings.length ? style.yellow(`${this.warnings.length} warnings`) : '0 warnings',
    ].join(' · ');
    out.log(`  ${counts}`);

    if (this.ok && this.warnings.length) {
      out.log(`  ${style.green('PASS')} — with warnings. Read them before this reaches a client.`);
    } else if (this.ok) {
      out.log(`  ${style.green('PASS')}`);
    } else {
      out.log(`  ${style.red('BLOCKED')} — fix the failures above. Nothing here ships to a client yet.`);
    }
    out.log('');
    return this.ok;
  }
}

export function fatal(err) {
  const name = err?.name ?? 'Error';
  console.error('');
  console.error(`  ${style.red(name)}  ${err?.message ?? err}`);
  console.error('');
  process.exitCode = 1;
}
