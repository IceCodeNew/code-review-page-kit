---
name: code-review-page
description: Build a dark-mode-aware, block-level HTML code review page for one or more PRs. Use when asked to review PRs and deliver an annotated page with per-block review notes, complexity hotspots, anti-pattern highlighting, an English implementation prompt, and per-block question inputs.
---

# Code review page

Generate a self-contained HTML review page that a reviewer can read at a glance:
code is annotated by block, annotations are connected to short “what changed /
why” notes, maintainability hotspots are visible, anti-patterns are called out,
and an English prompt is ready to hand to an implementing agent.

## Non-negotiables

- **Integrate first.** Read the PRs from exact head SHAs in a fresh temporary
  worktree. When upstream moves, fetch again, rebuild the worktree and rerun the
  analysis; never reuse metrics from another SHA.
- **Block-level, not file-level.** Each review note belongs to one code block.
  Outline the block, give it a letter badge and connect it to the note. Do not
  put a long explanation in the file header.
- **Do not collapse production code by default.** Only tests, fixtures,
  generated files, lockfiles and pure documentation are folded. Rust
  `#[cfg(test)] mod tests` sections fold automatically.
- **Terse notes.** “改了什么 / 为什么” should each fit on one or two lines. Long
  reasoning belongs in the English prompt.
- **Importance order.** Order groups and files by importance; keep related files
  adjacent. The first group is the one a reviewer must read first.
- **Maintainability evidence.** Include locally measured CC/cognitive/SLOC
  (rust-code-analysis, Radon, ESLint `complexity`) and clippy results. Show
  hotspots with deltas against the base.
- **Anti-patterns.** Maintain the list below and tag only genuine instances with
  the violet treatment. The anti filter must show only anti blocks and hide
  unrelated notes, badges and wires.
- **English prompt is mandatory.** Every page embeds a Markdown prompt written
  for the implementing agent, ordered by priority, with locations, suggested
  changes and acceptance criteria.
- **Ask inputs.** Every note has a “提问 / 要求 agent” textarea; the prompt
  section has a global one. Compose Markdown containing file, block letter,
  line range, review note, code excerpt and the question; support copy and
  `.md` download; persist drafts. The page is static and must not call an agent
  or the network.
- **Dark mode is required.** Default to `auto` (system), allow
  `Auto → Light → Dark`, persist the choice, avoid a first-paint flash. QA must
  run **both** themes on every page and check contrast, not just “it loads”.
- **Responsive and accessible.** Steps: 1440px and 390px; no horizontal page
  overflow; mobile opens a note dialog from the badge; print must use light
  colors; console must be clean.

## Delivery order

1. The English prompt (or a direct link plus the full prompt in a collapsed
   block).
2. The upstream/update evidence: exact SHAs, worktree head, commands run.
3. The page changes and QA results.
4. The files and any cleanup command.

Do not include a long “sources / download JSON” paragraph in the page. Keep the
per-row `依据` column, and cite external sources in the delivery message.

## Workflow

1. **Pin the review targets.**
   ```bash
   git fetch origin main <pr1-branch> <pr2-branch>
   gh pr view <N> --json headRefOid,state,baseRefName,title,updatedAt
   ```
   Record the exact base/head SHAs. For stacked PRs, confirm one contains the
   other before merging.

2. **Build the integration worktree.**
   ```bash
   git worktree add --detach /tmp/review-<slug>/ws origin/main
   git -C /tmp/review-<slug>/ws switch -c integrate/<slug>
   git -C /tmp/review-<slug>/ws merge --no-edit <pr1-head>
   git -C /tmp/review-<slug>/ws merge --no-edit <pr2-head>
   ```
   Verify no conflicts, record the merge head, and remove stale worktrees.

3. **Collect the diff and metrics.**
   ```bash
   git -C ws diff --no-renames <base> <head> > full.diff
   git -C ws diff --no-renames --numstat <base> <head> > numstat
   git -C ws diff --no-renames --name-status <base> <head> > name-status
   ```
   Run `rust-code-analysis` on changed Rust files at head **and** base,
   `radon cc` on changed Python files, and ESLint `complexity` on changed
   TypeScript files. Run clippy on the workspace. Keep the raw JSON; do not
   hand-write numbers.

4. **Write the review data module.**
   Use the schema in `schema.md`: `GROUPS`, `ANTI`, `FILES`,
   `REVIEW`. For each note choose an anchor that exists in the diff, and write a
   short what/why. Tag anti-patterns at the note level. Mark tests/fixtures/
   README/generated files as `fold: True`.

5. **Write the English prompt.**
   Follow `references/prompt-template.md`: context, constraints, current
   evidence, P0/P1/P2 items with locations and suggested changes, acceptance
   criteria, validation and deliverables. Save it as `review-prompt.md`. The
   page embeds it and exposes a copy button.

6. **Generate the page.**
   ```bash
   python3 review_page.py \
     --data reviews/<slug>/data.py \
     --diff /tmp/review-<slug>/full.diff \
     --files-json /tmp/review-<slug>/files.json \
     --metrics /tmp/review-<slug>/metrics.json \
     --ts-metrics /tmp/review-<slug>/ts_metrics.json \
     --prompt review-prompt.md \
     --workspace /tmp/review-<slug>/ws \
     --output review-<slug>.html
   ```

7. **QA both themes, then deliver.**
   ```bash
   PLAYWRIGHT_CORE=/path/to/playwright-core/index.mjs \
   node qa.mjs \
     --url "file://$PWD/review-<slug>.html" \
     --chrome "/path/to/Google Chrome for Testing" \
     --out /tmp/review-<slug>-qa
   ```
   The script checks errors, overflow, note/wire/badge/ask parity, theme toggle
   and persistence, anti-filter relevance, and 4.5:1 contrast in light, dark and
   mobile. Fix failures before delivering. Also capture one dark and one light
   screenshot for the delivery note.

## Anti-pattern list (maintain it)

Keep this list in the data module and in the page. Add a row when a new class of
hand-maintained behaviour appears; do not over-tag ordinary code.

1. Hand-written standard-format parsing/serialization.
2. Hand-written primitive guards recreating a schema.
3. Hand-maintained protocol constants/mappings.
4. Hand-edited contracts or generated artifacts.
5. Re-implementing standard library/framework semantics.
6. Scattered if/else extension points.
7. Repeated boundary validation.
8. Untyped `serde_json::Value` as the internal model.

See `references/anti-patterns.md` for wording, sources and instances.

## Reusable assets

- `review_page.py` — diff/annotation engine and renderer.
- `assets/theme.css` — light/dark shell.
- `assets/app.js` — theme, wires, filters, ask composer.
- `assets/theme-init.js` — pre-paint theme.
- `qa.mjs` — mandatory light/dark QA.
- `schema.md` — data contract.

## References

- `references/requirements.md` — every requirement collected from earlier reviews.
- `references/qa-checklist.md` — exact commands and assertions.
- `references/anti-patterns.md` — the maintained anti-pattern list and sources.
- `references/prompt-template.md` — how to write the English implementation prompt.
- `references/data-schema.md` — short pointer to the tool schema.