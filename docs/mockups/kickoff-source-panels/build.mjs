/** Local UI study. Uses current Ascent renderers, then edits detached source only. */
import { mkdirSync, readFileSync, writeFileSync, cpSync, existsSync, rmSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from '../../../plugins/ascent/skills/create-deliverables/scripts/build.mjs';
import { parseContentFile } from '../../../plugins/ascent/skills/create-deliverables/scripts/lib/content.mjs';
import { detachBuild } from '../../../plugins/ascent/skills/create-deliverables/scripts/detach.mjs';
import { rebuildDetached } from '../../../plugins/ascent/skills/create-deliverables/scripts/rebuild-detached.mjs';
import { validateBuild } from '../../../plugins/ascent/skills/create-deliverables/scripts/validate-brand.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const output = path.join(root, 'build/kickoff-source-panels');
const detached = path.join(output, 'editable');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
mkdirSync(output, {recursive:true});
const content = parseContentFile(path.join(root, 'plugins/ascent/skills/create-deliverables/templates/project-kickoff/static-example.yaml'));
content.sections = content.sections.filter(s => ['objectives-and-success','timeline-roadmap','immediate-next-steps'].includes(s.module));
content.meta.classification = 'Internal mockup · Fictional example';
for (const copy of content.meta.copy ?? []) if (copy.key === 'hero-meta-span-3') copy.text = content.meta.classification;
writeFileSync(path.join(output,'content.json'), JSON.stringify(content,null,2));
await build(path.join(output,'content.json'), {out:path.join(output,'baseline'), structurePreview:true});
// This directory belongs to this reproducible mockup builder, not a client deliverable.
if (existsSync(detached)) rmSync(detached,{recursive:true});
detachBuild(path.join(output,'baseline'), detached);
const src = path.join(detached,'src');
const phases = content.sections.find(s => s.module === 'timeline-roadmap').phases;
const groups = [
  {id:'outcome-contacts',module:'objectives-and-success',anchor:'.ref-outcome-card:nth-child(1)',label:'Contact deflection',value:'30% reduction in avoidable contacts',row:'OBJ-001',quote:'Target a 30% reduction in avoidable contacts by resolving more issues in the digital journey before agent escalation.',doc:'success-measures'},
  {id:'outcome-handle',module:'objectives-and-success',anchor:'.ref-outcome-card:nth-child(2)',label:'Average handle time',value:'20% reduction in handle time',row:'OBJ-002',quote:'Target a 20% reduction in average handle time through unified service context.',doc:'success-measures'},
  {id:'outcome-adoption',module:'objectives-and-success',anchor:'.ref-outcome-card:nth-child(3)',label:'Proficiency at launch',value:'85% proficiency at launch',row:'OBJ-003',quote:'The proficiency target at launch is 85% of agents and managers completing priority journeys.',doc:'success-measures'},
  ...phases.map((p,i)=>({id:`phase-${i}`,module:'timeline-roadmap',anchor:`.execution-map__row:nth-child(${i+1})`,label:p.name,value:`${p.start} to ${p.end}`,row:`REQ-00${i+1}`,quote:`${p.name} is scheduled from ${p.start} to ${p.end}. ${p.summary}`,doc:'delivery-schedule'})),
  {id:'action-sme',module:'immediate-next-steps',anchor:'.ref-launch-actions article:nth-child(1)',label:'Confirm SME calendar',value:'Rina · Sep 15',row:'REQ-006',quote:'Rina will confirm the SME calendar by September 15.',doc:'kickoff-notes'},
  {id:'action-sandbox',module:'immediate-next-steps',anchor:'.ref-launch-actions article:nth-child(2)',label:'Sandbox provisioning',value:'Jordan · Sep 15',status:'user',note:'The owner and target date were supplied directly during intake. No supporting document was recorded.'},
  {id:'action-test-data',module:'immediate-next-steps',anchor:'.ref-launch-actions article:nth-child(3)',label:'Test-data pattern',value:'Jordan + Theo · Sep 16',status:'changed',row:'REQ-007',approvedValue:'Jordan + Theo · Sep 18',quote:'Jordan and Theo will resolve the test-data pattern by September 18.',doc:'kickoff-notes'},
  {id:'action-boundary',module:'immediate-next-steps',anchor:'.ref-launch-actions article:nth-child(4)',label:'Approve MVP boundary',value:'Avery · Sep 16',status:'missing',note:'The example contains this action, but no source or review record is attached. It must not appear as a verified commitment.'}
];
const docs = {
  'success-measures':{title:'Success measures',path:'reference/success-measures.md',kind:'Original text'},
  'delivery-schedule':{title:'Delivery schedule',path:'reference/delivery-schedule.md',kind:'Converted Markdown'},
  'kickoff-notes':{title:'Kickoff notes',path:'meetings/kickoff-notes.md',kind:'Original text'}
};
mkdirSync(path.join(src,'sources'),{recursive:true});
for (const [id,doc] of Object.entries(docs)) {
  const lines = [`# ${doc.title}`,'','Fictional evidence fixture for a UI mockup. Not client evidence.',''];
  for (const group of groups.filter(g=>g.doc===id)) {
    lines.push(`## ${group.label}`,'');
    group.line = lines.length+1;
    lines.push(group.quote,'');
  }
  doc.lines=lines;
  writeFileSync(path.join(src,'sources',`${id}.md`),lines.join('\n'));
}
const sourceEntry = g => g.doc ? `<article class="source-evidence"><p class="source-caption">Original evidence</p><h4>${esc(docs[g.doc].title)}</h4><blockquote>${esc(g.quote)}</blockquote><p class="source-location">${esc(docs[g.doc].kind)} · line ${g.line}</p><p class="source-path">${esc(docs[g.doc].path)}</p><a class="source-link" href="evidence.html#${g.doc}-L${g.line}" target="_blank" rel="noopener">Open source passage <span aria-hidden="true">↗</span></a></article>` : `<p class="source-empty">${esc(g.note)}</p>`;
function note(g,index) {
  const status = g.status==='user' ? 'Direct user input' : g.status==='missing' ? 'No recorded source' : g.status==='changed' ? 'Needs review after edit' : 'Human reviewed · Example';
  return `<details class="source-note" id="note-${g.id}" data-anchor="${esc(g.anchor)}" data-source-id="${g.id}">
  <summary aria-label="Sources for ${esc(g.label)}"><span class="source-number">${String(index+1).padStart(2,'0')}</span><span>Sources</span><span class="source-plus" aria-hidden="true">+</span></summary>
  <div class="source-panel" role="region" aria-label="Evidence for ${esc(g.label)}">
    <header class="source-panel-head"><div><p class="source-caption">${g.module==='timeline-roadmap'?'Timeline / roadmap':g.module==='objectives-and-success'?'Objectives / success':'Immediate next steps'}</p><h3>${esc(g.label)}</h3></div><button type="button" class="source-close" aria-label="Close sources for ${esc(g.label)}">×</button></header>
    <div class="source-status ${g.status==='changed'||g.status==='missing'?'source-status--review':''}">${esc(status)}</div>
    <div class="source-value"><p class="source-caption">${g.status==='changed'?'Current display':'Supports this content'}</p><p>${esc(g.value)}</p>${g.status==='changed'?`<p class="source-change">Previously reviewed: ${esc(g.approvedValue)}. The displayed date has changed; confirm its support.</p>`:''}</div>
    ${sourceEntry(g)}
    ${g.row?`<details class="source-trace"><summary>Review trail · ${esc(g.row)}</summary><p>Sample accepted value: ${esc(g.approvedValue??g.value)}</p><p>Example review accepted September 14, 2026.</p><p>Tracker → intake → ${esc(g.module)} → ${esc(g.label)}</p><a href="evidence.html#review-${g.id}" target="_blank" rel="noopener">Inspect sample review record ↗</a></details>`:''}
    <p class="source-disclaimer">Illustrative provenance · Not a real approval</p>
  </div></details>`;
}
let html = readFileSync(path.join(src,'index.html'),'utf8');
// Find outer section boundaries while respecting nested inspector sections.
const tokens = [...html.matchAll(/<\/?section\b[^>]*>/g)];
const sections = []; let depth=0, start=null, module=null;
for(const token of tokens){
  if(token[0].startsWith('</')) {depth--; if(depth===0&&start!==null){sections.push({start,end:token.index+token[0].length,module});start=null;}}
  else {if(depth===0){start=token.index;module=token[0].match(/data-preview-module="([^"]+)"/)?.[1];}depth++;}
}
for(const section of sections.reverse()){
  const relevant=groups.filter(g=>g.module===section.module); if(!relevant.length)continue;
  const original=html.slice(section.start,section.end);
  html=html.slice(0,section.start)+`<div class="citation-region" data-citation-module="${section.module}"><div class="citation-content">${original}</div><aside class="source-rail" aria-label="Sources for ${section.module.replaceAll('-',' ')}">${relevant.map(note).join('\n')}</aside></div>`+html.slice(section.end);
}
html=html.replace('</head>','<link rel="stylesheet" href="css/citations.css">\n</head>');
html=html.replace('<body>','<body data-citation-mode="floating">');
html=html.replace('<div class="page">',`<header class="study-bar"><div class="study-identity"><img src="assets/logos/slalom-logo-white.svg" alt="Slalom"><span>Kickoff / Source UI study</span></div><nav class="study-options" aria-label="Citation layout"><button type="button" data-mode="floating" aria-pressed="true">A · Floating notes</button><button type="button" data-mode="margin" aria-pressed="false">B · Margin notes</button></nav><button type="button" id="sources-toggle" aria-pressed="true">Sources on</button></header><div class="study-context"><span>Internal mockup · Fictional facts, quotes, and review records</span><a href="#s2-timeline-roadmap">Jump to timeline ↓</a></div><p class="study-mode-caption" id="mode-caption">Floating notes · Open a numbered tab to see evidence beside its content.</p><noscript><p class="study-context">JavaScript is off. Source disclosures remain available below each section.</p></noscript><div class="page">`);
// Reuse the actual emitted white wordmark filename.
const footerLogo=html.match(/<footer[\s\S]*?<img[^>]+src="([^"]+)"/)?.[1];
if(footerLogo)html=html.replace('assets/logos/slalom-logo-white.svg',footerLogo);
html=html.replace('</body>','<script src="js/citations.js" defer></script>\n</body>');
writeFileSync(path.join(src,'index.html'),html);
cpSync(path.join(here,'citations.css'),path.join(src,'css/citations.css'));
cpSync(path.join(here,'citations.js'),path.join(src,'js/citations.js'));
writeFileSync(path.join(src,'provenance.mock.json'),JSON.stringify({fictional:true,groups,documents:docs},null,2));
const evidenceSections=Object.entries(docs).map(([id,doc])=>`<section class="evidence-document"><h2>${esc(doc.title)}</h2><p>${esc(doc.kind)} · ${esc(doc.path)}</p><a href="sources/${id}.md">Readable Markdown copy</a><ol class="evidence-lines">${doc.lines.map((line,i)=>`<li id="${id}-L${i+1}"><span>${i+1}</span><div>${esc(line)||'&nbsp;'}</div></li>`).join('')}</ol></section>`).join('');
const reviewSections=groups.filter(g=>g.row).map(g=>`<article class="sample-review" id="review-${g.id}"><h3>${esc(g.row)} / ${esc(g.label)}</h3><p>Example decision: accepted · September 14, 2026</p><p>Example accepted value: ${esc(g.approvedValue??g.value)}</p><p>Evidence: ${esc(docs[g.doc].path)}, line ${g.line}</p><p>Display mapping: ${g.module} / ${esc(g.label)}</p></article>`).join('');
writeFileSync(path.join(src,'evidence.html'),`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Sample source passages · Ascent UI study</title><link rel="stylesheet" href="css/tokens.css"><link rel="stylesheet" href="css/base.css"><link rel="stylesheet" href="css/citations.css"></head><body class="evidence-page"><header><p class="eyebrow">Fictional evidence fixtures</p><h1>Read the supporting passage.</h1><p>These documents and review records were created only to demonstrate the interface. They are not client evidence.</p><a href="index.html#s2-timeline-roadmap">Back to kickoff mockup</a></header>${evidenceSections}<section class="evidence-document"><h2>Sample review records</h2>${reviewSections}</section></body></html>`);
const result=rebuildDetached(detached);
const baselineGate=validateBuild(path.join(output,'baseline'));
const baselineErrors=new Set(baselineGate.errors.map(e=>JSON.stringify(e)));
const introducedErrors=result.gate.errors.filter(e=>!baselineErrors.has(JSON.stringify(e)));
writeFileSync(path.join(output,'validation.json'),JSON.stringify({
  brand_gate_passed:result.gate.ok,
  baseline_errors:baselineGate.errors.length,
  mockup_errors:result.gate.errors.length,
  introduced_errors:introducedErrors,
  warnings:result.gate.warnings,
  all_errors:result.gate.errors,
},null,2));
console.log(`Brand gate: ${result.gate.errors.length} errors (${introducedErrors.length} introduced; ${baselineGate.errors.length} in the unmodified template baseline).`);
introducedErrors.forEach(e=>console.error(`${e.rule}: ${e.message}`));
result.gate.warnings.forEach(w=>console.log(`Warning ${w.rule}: ${w.message}`));
console.log(`\nPreview: ${result.outDir}/index.html`);
// Full gate remains failing when inherited template errors exist. This does not
// convert a local comparison into a client-ready brand-approved deliverable.
if(!result.gate.ok)process.exitCode=1;
