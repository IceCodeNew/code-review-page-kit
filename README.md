# code-review-page-kit

A reusable, self-contained toolkit for producing **block-level code review
pages**: annotated diffs, margin notes connected to code, maintainability
hotspots, anti-pattern highlighting, a copyable English implementation prompt,
per-block question inputs, and light/dark themes.

The repository contains both the renderer and the agent-facing skill, so a
review can be reproduced end to end from this directory.

## Contents

| Path | Purpose |
|---|---|
| `SKILL.md` | Agent workflow and non-negotiable review requirements |
| `references/` | Requirements, QA checklist, anti-pattern list, prompt template, data schema |
| `review_page.py` | CLI: parse a diff, resolve anchors to blocks, render the page |
| `assets/theme.css` | Light/dark shell: layout, annotations, notes, prompt, ask UI |
| `assets/app.js` | Theme toggle, note/wire layout, filters, ask composer, prompt copy |
| `assets/theme-init.js` | Pre-paint theme selection (no flash) |
| `qa.mjs` | Light/dark/desktop/mobile QA: contrast, overflow, wires, persistence |
| `schema.md` | Data-module schema (`GROUPS`, `ANTI`, `FILES`, `REVIEW`) |

## Quick start

1. Read [`SKILL.md`](SKILL.md) and the references.
2. Produce the review artifacts: a unified diff, per-file stats, complexity
   metrics, and a Python data module (see [`schema.md`](schema.md)).
3. Write `review-prompt.md` for the implementing agent.
4. Render:

```bash
python3 review_page.py \
  --data /path/to/review_data.py \
  --diff /path/to/full.diff \
  --files-json /path/to/files.json \
  --metrics /path/to/metrics.json \
  --ts-metrics /path/to/ts_metrics.json \
  --prompt review-prompt.md \
  --workspace /path/to/integrated-worktree \
  --output review.html
```

5. QA in **both** themes:

```bash
PLAYWRIGHT_CORE=/path/to/playwright-core/index.mjs \
node qa.mjs \
  --url "file:///absolute/path/review.html" \
  --chrome "/path/to/Google Chrome for Testing" \
  --out /tmp/review-qa
```

`qa.mjs` exits non-zero on console errors, horizontal overflow, note/wire/badge/
ask mismatch, a broken theme toggle/persistence, an irrelevant anti-filter, or
text below 4.5:1 contrast. Dark desktop and dark mobile are mandatory checks.

## CLI inputs

- `--data` imports `GROUPS`, `ANTI`, `FILES` and `REVIEW` from a Python file.
- `--diff` is `git diff --no-renames <base> <head>`.
- `--files-json` is per-file metadata (`path`, `add`, `del`, `status`).
- `--metrics` is the Rust/Python complexity JSON; `--ts-metrics` is the
  TypeScript ESLint complexity JSON. Both may be `{}` when not measured.
- `--workspace` is the integrated worktree: footer head and test-section mapping.
- `--prompt` is mandatory; every page embeds the English prompt.
- `REVIEW["validation_note"]` controls the footer claim. The generator does not
  run linters; do not claim a tool ran unless it did.

## Design rules

- Production code is expanded; only tests, fixtures, generated files and docs
  are folded.
- Each note belongs to a code block and says what changed and why, briefly.
- Purple is reserved for anti-pattern annotations; the anti filter is
  **block-level**, not file-level.
- The page is static: ask inputs compose Markdown locally and never call a
  network or an agent.
- Dark mode defaults to the system preference and is part of default QA.

## Privacy

This repository intentionally contains **no review data, no repository names,
no commit SHAs, no credentials, and no internal paths**. Bring your own data
module and prompt; do not commit generated review pages or secrets.

## License

MIT — see [LICENSE](LICENSE).
