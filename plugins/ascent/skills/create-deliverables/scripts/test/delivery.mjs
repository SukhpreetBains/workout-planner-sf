/** Regression coverage for reusable delivery structures and HLS composition. */
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { parseContentFile, validateContent } from '../lib/content.mjs';
import { loadTemplateModules, resolveGuidedContent, evaluateIntake } from '../lib/intake.mjs';
import { SKILL_ROOT } from '../lib/assets.mjs';
import { build, buildStructurePreview, loadArchetype } from '../build.mjs';
import { loadTemplateOptions } from '../lib/template-options.mjs';
import { validateBuild } from '../validate-brand.mjs';

export function registerDeliveryTests(test, tmp) {
  const template = loadArchetype('hls-project-kickoff');
  const modules = loadTemplateModules(template, SKILL_ROOT);
  const content = path.join(SKILL_ROOT, 'templates/hls-project-kickoff/content.example.yaml');
  const raw = parseContentFile(content);
  const document = () => resolveGuidedContent(structuredClone(raw), modules);
  const find = (doc, type) => doc.sections.find((s) => s.type === type);
  const intake = () => ({ schema_version: 1, template: template.name, build_status: 'draft', optional_review: 'skipped', answers: { "hls-project-kickoff.cover-background": {status:"answered",answer:"horizon",answered_by:"user",disposition:"rendered"}, ...Object.fromEntries(modules.flatMap((m) => m.questions.map((q) => [q.id, q.tier === 'optional' ? { status: 'missing' } : { status: 'answered', answer: q.answer_type === 'date' ? '2026-10-05' : ['text','person','decision'].includes(q.answer_type) ? 'Fictional example answer' : ['Fictional example answer'], answered_by: 'source', disposition: 'rendered', sources: [{source_id: 'fictional-example', locator: q.id}] }]))) } });
  test('template instructions: opt-in loading preserves legacy templates', () => {
    assert.match(template.instructionsText, /Display all three/);
    assert.equal(loadArchetype('project-kickoff').instructionsText, undefined);
    assert.throws(() => loadTemplateOptions({...template,instructions:'missing.md'},template.templateRoot), /does not exist/);
    assert.throws(() => loadTemplateOptions({...template,instructions:'../project-kickoff/README.md'},template.templateRoot), /inside|does not exist/);
    assert.throws(() => loadTemplateOptions({...template,instructions:'https:\/\/example.com/instructions.md'},template.templateRoot), /does not exist|relative/);
  });
  test('template preferences: missing choice is a required gap and optional skip cannot resolve it', () => {
    const value = intake(); delete value.answers['hls-project-kickoff.cover-background'];
    const result = evaluateIntake(value,template,modules);
    assert.deepEqual(result.requiredGaps.map(q=>q.id), ['hls-project-kickoff.cover-background']);
    value.build_status = 'final';
    assert.throws(()=>evaluateIntake(value,template,modules), /needs override/);
    value.override={required_gaps_confirmed_at:'2026-10-05T12:00:00Z'};
    assert.equal(evaluateIntake(value,template,modules).requiredGaps.length,1);
  });
  test('template preferences: validates saved choices and explicit user provenance', () => {
    const value=intake(), answer=value.answers['hls-project-kickoff.cover-background'];
    answer.answer='unknown';assert.throws(()=>evaluateIntake(value,template,modules),/available choice/);
    answer.answer='molecules';answer.answered_by='source';answer.sources=['example'];
    assert.throws(()=>evaluateIntake(value,template,modules),/explicit user/);
    answer.answered_by='user';
    assert.equal(evaluateIntake(JSON.parse(JSON.stringify(value)),template,modules).answers.find(a=>a.id.endsWith('.cover-background')).answer,'molecules');
    answer.status='conflicting';assert.equal(evaluateIntake(value,template,modules).requiredGaps.length,1);
    answer.status='not_applicable';answer.reason='Use a solid cover.';
    assert.equal(evaluateIntake(value,template,modules).requiredGaps.length,0);
  });
  test('template preferences: rejects broken image and question references', () => {
    assert.throws(()=>loadTemplateOptions({...template,cover_background_question:'unknown'},template.templateRoot),/reference/);
    const changed=structuredClone(template);changed.template_questions[0].choices[0].image='missing.png';
    assert.throws(()=>loadTemplateOptions(changed,template.templateRoot),/does not exist/);
    changed.template_questions[0].choices[0].image='brand:photography/molecules.png';changed.template_questions[0].choices[1].value='molecules';
    assert.throws(()=>loadTemplateOptions(changed,template.templateRoot),/unique values/);
  });
  test('template preferences: all backgrounds render locally; pending choice uses solid cover', async () => {
    for (const choice of ['molecules','horizon','winding-road',null]) {
      const value=intake();value.answers['hls-project-kickoff.cover-background']=choice ? {status:'answered',answer:choice,answered_by:'user',disposition:'rendered'} : {status:'missing'};
      const file=path.join(tmp,'hls-choice.json');writeFileSync(file,JSON.stringify(value));
      const result=await build(content,{intake:file,out:path.join(tmp,'hls-choice-'+choice)});
      assert.equal(result.html.includes('class="cover__background"'),Boolean(choice));
      assert.equal((result.html.match(/class="section__illustration"/g)||[]).length,3);
      const gallery=readFileSync(path.join(result.outDir,'template-choices.html'),'utf8');
      assert.equal((gallery.match(/<figure>/g)||[]).length,3);
      assert.ok(!gallery.includes('https://'));
      assert.equal(validateBuild(result.outDir).errors.length,0);
    }
  });
  test('HLS: full example validates and contains the agreed narrative', () => {
    const doc = validateContent(document(), { archetype: template });
    assert.equal(doc.sections.length, 14);
    assert.deepEqual(doc.sections.map((s) => s.view), ['purpose','agenda','profiles','phase-progression','workstream-schedule','meeting-cadence','team-norms','pipeline','readiness','raci','responsibilities','operating-model','summary','actions']);
  });
  for (const [name, mutate, expected] of [
    ['impossible date', (d) => find(d,'workstream-schedule').tasks[0].start = '2026-02-30', /real ISO/],
    ['reversed range', (d) => find(d,'workstream-schedule').tasks[0].end = '2026-10-01', /start must not follow/],
    ['outside range', (d) => find(d,'workstream-schedule').milestones[0].date = '2028-01-01', /outside/],
    ['unknown workstream', (d) => find(d,'workstream-schedule').tasks[0].workstream = 'unknown', /unknown workstream/],
    ['duplicate role', (d) => find(d,'profiles').roles[1].id = 'sponsor', /unique/],
    ['unknown RACI role', (d) => find(d,'raci').activities[0].assignments[0].role = 'unknown', /unknown role/],
    ['missing accountable role', (d) => find(d,'raci').activities[0].assignments[0].responsibility = 'C', /accountable/],
    ['unknown operating role', (d) => find(d,'operating-model').groups[0].roles.push('unknown'), /unknown role/],
    ['unknown stage', (d) => find(d,'workflow').transitions[0].to = 'unknown', /unknown stage/],
    ['unknown workflow role', (d) => find(d,'workflow').stages[0].roles.push('unknown'), /unknown role/],
    ['malformed role list', (d) => find(d,'workflow').stages[0].roles = null, /missing required field/],
    ['remote portrait', (d) => find(d,'profiles').roles[0].photo = 'https://example.com/image.png', /relative local/],
  ]) test(`HLS: rejects ${name}`, () => { const doc = document(); mutate(doc); assert.throws(() => validateContent(doc, {archetype: template}), expected); });

  test('HLS: complete and skipped-optional intake has no required gaps', () => assert.equal(evaluateIntake(intake(),template,modules).requiredGaps.length,0));
  for (const status of ['partial','conflicting','missing','deferred']) test(`HLS: ${status} stays a required gap`, () => {
    const value=intake(); value.answers['delivery-workflow.stages']={status};
    assert.equal(evaluateIntake(value,template,modules).requiredGaps.length,1);
  });
  test('HLS: only an explicit user not-applicable decision resolves a gap', () => {
    const value=intake(); value.answers['delivery-workflow.stages']={status:'not_applicable', answered_by:'user',reason:'This fictional project tracks outcomes outside a staged workflow.'};
    assert.equal(evaluateIntake(value,template,modules).requiredGaps.length,0);
    value.answers['delivery-workflow.stages'].answered_by='source';
    assert.throws(() => evaluateIntake(value,template,modules),/only the user/);
  });
  test('HLS: final gaps require confirmation; draft and final overrides retain gaps', () => {
    const value=intake(); value.answers['delivery-workflow.stages']={status:'missing'};
    assert.equal(evaluateIntake(value,template,modules).requiredGaps.length,1);
    value.build_status='final'; assert.throws(() => evaluateIntake(value,template,modules),/needs override/);
    value.override={required_gaps_confirmed_at:'2026-10-05T12:00:00Z'};
    assert.equal(evaluateIntake(value,template,modules).requiredGaps.length,1);
  });
  test('HLS: new questions and views do not change the original kickoff selection', () => {
    const original=loadTemplateModules(loadArchetype('project-kickoff'),SKILL_ROOT);
    assert.equal(original.find((m) => m.id==='team-and-responsibilities').output.length,2);
    assert.ok(!original.flatMap((m) => m.questions).some((q) => q.id.endsWith('.role-directory')));
  });
  test('HLS: isolated previews cover every owned view, template preview selects only its views', async () => {
    for (const id of ['team-and-responsibilities','delivery-approach','ways-of-working','delivery-workflow','kickoff-context']) {
      const result=await buildStructurePreview({moduleId:id,templateName:template.name,out:path.join(tmp,`hls-${id}`),bundle:true});
      const definition=JSON.parse(readFileSync(path.join(SKILL_ROOT,'modules',id,'module.json'),'utf8'));
      assert.equal(result.renderedDoc.sections.length,definition.default_output.filter((v) => v.type!=='cover').length);
      assert.ok(result.renderedDoc.sections.every((s) => s.module===id));
      assert.equal(validateBuild(result.outDir).errors.length,0);
    }
    const result=await buildStructurePreview({templateName:template.name,out:path.join(tmp,'hls-full')});
    assert.equal(result.renderedDoc.sections.length,14);
    assert.equal(validateBuild(result.outDir).errors.length,0);
  });
  test('HLS: long text and missing optional portraits build and bundle safely', async () => {
    const doc=structuredClone(raw); doc.sections.find((s) => s.view==='profiles').roles[0].detail='Detailed responsibilities and cross-workstream coordination. '.repeat(50);
    const file=path.join(tmp,'hls-stress.json');writeFileSync(file,JSON.stringify(doc));
    const intakeFile=path.join(tmp,'hls-intake.json');writeFileSync(intakeFile,JSON.stringify(intake()));
    const result=await build(file,{out:path.join(tmp,'hls-stress'),intake:intakeFile,bundle:true});
    assert.ok(result.html.includes('schedule-chronology'));
    assert.ok(!result.html.includes('class="profile__photo"'));
    assert.equal(validateBuild(result.outDir).errors.length,0);
    writeFileSync(path.join(tmp,'portrait.png'),Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=','base64'));
    doc.sections.find((s) => s.view==='profiles').roles[0].photo='portrait.png';
    writeFileSync(file,JSON.stringify(doc));
    const portraitBuild=await build(file,{out:path.join(tmp,'hls-portrait'),intake:intakeFile,bundle:true});
    assert.ok(readFileSync(portraitBuild.bundlePath,'utf8').includes('data:image/png;base64,'));
    doc.sections.find((s) => s.view==='profiles').roles[0].photo='missing.png';writeFileSync(file,JSON.stringify(doc));
    await assert.rejects(build(file,{out:path.join(tmp,'hls-missing-photo'),intake:intakeFile}),/profile photo.*does not exist/);
  });
}
