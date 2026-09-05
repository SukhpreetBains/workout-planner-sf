# HXL template and module selector

`scripts/generate-hxl-selector.mjs` emits two experimental [HXL Mosaic](https://www.headlessexperiencelayer.com/playground/) fragments for the guided template workflow.

```bash
node scripts/generate-hxl-selector.mjs template-picker --out template-picker.mosaic.json
node scripts/generate-hxl-selector.mjs module-picker project-kickoff --out module-picker.mosaic.json
```

The template picker contains:

- one required `tile/select` for the template;
- a preview control for every template; and
- a primary Continue button that returns the selected template.

After the agent validates that template, render the module picker. It contains:

- one `tile/checkbox` for each module in that template;
- a preview control for the full template and every module; and
- a primary Submit button with `action/sendMessage`.

Pass `--preview-base https://host.example/previews` only when the preview builds
are hosted. This emits `action/openLink` controls for `/template/<id>/index.html`
and `/module/<id>/index.html`. Without it, preview controls request the preview
from the host agent, which must render it with the existing `build.mjs`
`--preview-template` or `--preview-module` command.

The host must expose live form values through `selection.template` and
`selection.modules`. The generated Submit message uses HXL expressions:

```text
template={!$selection.template}; modules={!$selection.modules}
```

This is an experimental integration. HXL currently labels Select and Checkbox
support as coming soon for its advertised hosts. Do not remove the standard
conversational selection and confirmation fallback. Treat the message as an
untrusted user selection, validate it against the current template registry,
and then confirm the resulting module list before intake begins.

This selector is an agent-facing workflow surface. It is never copied into a
generated client microsite.
