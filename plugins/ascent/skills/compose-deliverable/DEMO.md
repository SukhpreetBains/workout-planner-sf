# Monday demo runbook

## Evaluation workbench

The demoable branch is `feature/skill-evals`, not the main checkout's
`feature/sgaf-717-skill-evals`. Start the server with the absolute script path so
terminal working-directory reuse cannot serve the stale workbench:

```bash
python3 /Users/andrewfischer/Projects/ascent-worktrees/skill-evals/docs/evals_workbench.py --port 8765
```

Open <http://127.0.0.1:8765/evals-workbench.html>. Confirm the page says all 17
rules held and the API reports a metric catalogue size of 24. The four checked
acceptance commands are:

```bash
cd /Users/andrewfischer/Projects/ascent-worktrees/skill-evals
python3 tests/context_skills_acceptance.py
python3 tests/initial_setup_acceptance.py
python3 tests/skill_evals_acceptance.py
python3 tests/telemetry_acceptance.py
```

Do not edit or demo the stale main checkout. Its four uncommitted files remain
untouched.

## Editable PowerPoint spike

```bash
cd /Users/andrewfischer/Projects/ascent-worktrees/dom-to-pptx-skill/skills/compose-deliverable
npm ci
npm test
npm run demo
open build/reference-informed-demo.pptx
```

Show the synthetic `examples/reference-informed-content.yaml`, its explicit
`examples/reference-informed-storyboard.json`, the generated manifest and
browser preview, and then edit one title in PowerPoint to demonstrate native
text. The structural gate should report section coverage, native text and
shapes, fonts, colors, classification, packaged logos, dimensions, and speaker
notes—not merely a valid ZIP package.

Run `npm run validate:broken` if the audience wants to see the validator reject
deliberately broken fonts, colors, copy, image relationships, notes, dimensions,
and empty text slides.

State the boundary plainly: the authenticated SharePoint example informed the
section types and relative density, while the demo fixture contains no customer
content. Final comparison against approved customer screenshots, review in
Microsoft PowerPoint, and the agentic cost/time evaluation remain separate
delivery gates.
