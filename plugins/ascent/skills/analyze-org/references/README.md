# analyze-org references

This folder holds the **templates and procedure** the `analyze-org` skill uses to generate an architecture map. The generated map itself does **not** live here — it is written to an `architecture/` folder at the **project root**.

## What's here (in the skill)

```
references/
├── README.md                     # this file
├── bootstrap.md                  # first-run / refresh procedure
├── LANGUAGE.md                   # guide for building the shared vocabulary with the user
├── _architecture-template.md     # template for the index
├── _vocabulary-template.md       # template for the shared vocabulary
└── _feature-template.md          # template for a single feature file
```

Files prefixed with `_` are **templates** — copy them to the project, don't fill them in directly.

## What gets generated (at the project root)

```
architecture/
├── architecture.md               # the index / map — start here
├── vocabulary.md                 # the org's shared domain language — read before the features
└── features/
    ├── <feature-a>.md
    ├── <feature-b>.md
    └── ...
```

## For agents

If `architecture/architecture.md` exists at the project root, read it first — it's the cached map and saves a full org scan. Only re-run the skill's Bootstrap when no map exists or the user asks to refresh.

## Manual notes

You can add hand-written context to any generated file under a `## Notes` heading. The skill preserves content under that heading on refresh; everything above it may be regenerated.
