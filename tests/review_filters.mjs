// Exercise the inbox's actual filtering functions without a browser or server.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync(new URL('../plugins/ascent/skills/workspace-review/assets/review-app/app.js', import.meta.url), 'utf8');
const filters = source.slice(source.indexOf('function defaultReviewFilter('), source.indexOf('function knownRecords('));
const dates = source.slice(source.indexOf('function normalizeDate('), source.indexOf('// ---------------------------------------------------------------- relationships'));
const context = vm.createContext({});
vm.runInContext(`
let reviewFilter = new Set(['pending']);
let searchQuery = '';
let sortMode = 'oldest';
const recordSearchText = record => record.title.toLowerCase();
let records = [
  {key: 'later', state: 'pending', title: 'Later', fields: {Date: '2026-10-20'}},
  {key: 'unknown', state: 'pending', title: 'Unknown', fields: {}},
  {key: 'earlier', state: 'pending', title: 'Earlier', fields: {Date: '2026-10-01'}},
  {key: 'accepted', state: 'accepted', title: 'Accepted', fields: {Date: '2026-09-01'}},
  {key: 'created', state: 'pending', title: 'Created', fields: {}, created_at: '2026-10-10T10:00:00Z'},
];
${dates}\n${filters}
`, context);
const run = code => JSON.parse(JSON.stringify(vm.runInContext(code, context)));
assert.deepEqual(run('visibleRecords().map(record => record.key)'), ['earlier', 'created', 'later', 'unknown']);
assert.deepEqual(run("sortMode = 'newest'; visibleRecords().map(record => record.key)"), ['later', 'created', 'earlier', 'unknown']);
assert.equal(run("reviewFilter.add('accepted'); visibleRecords().length"), 5);
assert.equal(run("reviewFilter.clear(); visibleRecords().length"), 0);
assert.deepEqual(run("[...defaultReviewFilter(records, '/') ]"), ['pending']);
assert.deepEqual(run("[...defaultReviewFilter(records.filter(record => record.state !== 'pending'), '/') ]"), ['accepted']);
assert.deepEqual(run("[...defaultReviewFilter([], '/') ]"), ['accepted']);
assert.deepEqual(run("[...defaultReviewFilter(records, '/accepted') ]"), ['accepted']);
assert.deepEqual(run("reviewFilter = new Set(['pending', 'accepted']); searchQuery = 'earlier'; visibleRecords().map(record => record.key)"), ['earlier']);
console.log('Passed review status defaults, multiselect, search, and date ordering checks');
