# Floating source panels

Add `citations` to an authored section when a displayed value needs an inspectable provenance note. The builder renders collapsed numbered tabs at the section's right edge. Opening a tab overlays the section; it does not resize content columns. On narrow screens, the tabs follow the section in normal reading order. Sections without citations render exactly as before.

```yaml
citations:
  - target: item-1
    label: Contact deflection
    value: 30% reduction in avoidable contacts
    status: source
    source_ref: workspace/.system/tracker-copies/requirements.yaml#OBJ-001.target
    excerpt: Target a 30% reduction in avoidable contacts.
```

`target` is `section` or a one-based `item-N`. Item targets are available for the objectives, timeline, and immediate-next-steps modules. The builder checks that the corresponding item or phase exists. At most one citation can target each item in a section. Use `section` for another module or for a note about the entire section.

`label` identifies the content, and `value` repeats the displayed value. Keep them synchronized with the authored content. `status` is one of:

- `source`: Use an exact current tracker-copy path, stable row ID, and field name in `source_ref`. Include `excerpt` only when that text is actually available from accepted evidence.
- `user`: Direct user input. Supply `note` explaining its origin. Do not claim a source.
- `changed`: The displayed content changed after a source-backed value was recorded. Supply the earlier `source_ref` and a `note` explaining what needs review. An excerpt is optional.
- `missing`: No recorded provenance. Supply `note`; never describe the value as verified.

The panel displays source references as text. It does not infer approval, fetch source files, or add links to unbundled workspace paths. Author the citations from accepted tracker rows or explicit user answers; do not copy fictional citations from the preview into a client draft. A bundled build includes the same panel UI with no network requests.

Build the fictional [implementation preview](../../../../../docs/mockups/kickoff-source-panels/implementation-preview.mjs) to review the integrated and isolated layouts. The preview script records inherited brand-gate errors alongside errors introduced by citations.
