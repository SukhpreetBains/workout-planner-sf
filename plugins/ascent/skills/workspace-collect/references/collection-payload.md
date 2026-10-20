# Collection payload

`COLLECT write --input <file>` takes one JSON object per source. The source's
contract `document` entry says how its material maps onto this shape.

```json
{
  "source_id": "slack-ascent-pod-3",
  "documents": [
    {
      "key": "optional stable ID, such as a transcript ID",
      "title": "optional heading for the inbox file",
      "format": "messages",
      "started_at": "optional ISO time that entry offsets count from",
      "cursor_at": "optional ISO time that marks this whole document as new",
      "entries": [
        {
          "id": "1792425730.598959",
          "at": "2026-10-19T16:02:10.598959Z",
          "author": "Calvin O'Keefe",
          "text": "Full message text",
          "parent": "optional id of the thread parent",
          "context": false
        }
      ]
    }
  ]
}
```

- `source_id` must be a source that `COLLECT plan` returned.
- `format` is `messages` (the default; replies are grouped under their
  parent) or `transcript` (one line per entry).
- Each entry needs `at`, or `offset` (`HH:MM:SS.fff`) with the document's
  `started_at`. Times must carry a timezone; `Z` is fine.
- Without `cursor_at`, only entries after the source's cursor are kept, and
  the cursor advances to the newest of them. Entries with `context: true` are
  shown only as the parent of a kept reply and never move the cursor.
- With `cursor_at`, the whole document is kept when `cursor_at` is after the
  cursor, and the cursor advances to `cursor_at`.
- A document whose `key` was already written is skipped.
- Include every new item in full. Do not summarize, translate, or trim text.
- If any timestamp cannot be read, `write` writes nothing and exits with an
  error; fix the payload and run it again.
