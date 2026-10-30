# Requirements collected from earlier reviews

This file is the memory of the review-page format. Treat it as requirements, not
suggestions.

## 1. Review the PRs, not just the diff summary

- Read each changed file and explain what it does, in the order a reviewer needs
  it: most important files first, related files adjacent.
- Build a temporary local integration worktree from the exact PR heads. Do not
  reason from the GitHub diff alone when a stacked PR depends on another.
- When upstream changes, fetch again, update the local PR branches, rebuild the
  integration worktree from scratch and rerun the analysis. Do not reuse an old
  merge commit or stale metrics.
- Record the exact base/head SHAs in the page footer and the prompt.

## 2. Word-review-like page, block-level annotations

- The page should read like a Word review view: code in the centre, comments in
  the margin, a visible connector between the commented block and the comment.
- Do **not** default-collapse production code. Only tests, fixtures, generated
  files and pure documentation may be folded. Rust test modules fold by
  `#[cfg(test)] mod tests`.
- If a diff has blocks A, B, C, outline A and C, label them with letters, and
  connect each outline to its margin note. Explain what A and C changed.
- Notes are block-level, not file-level. A file header must not carry a long
  essay.
- Each note is short: “改了什么” and “为什么”. Put long reasoning in the English
  prompt.
- Use colour to make scope visible: colour-coded outlines/badges and matching
  wires; the violet palette is reserved for anti-pattern notes.
- Support filters (all / per-PR / key / anti), search, mobile badge dialog,
  print, and a fixed navigation sidebar.

## 3. Maintainability and anti-patterns

- The reviewer cares most about maintainability. Include local measurements:
  cyclomatic/cognitive complexity, SLOC, function locations and deltas from the
  base. Use rust-code-analysis, Radon, ESLint `complexity` and clippy.
- Surface hotspots with a “what to look at” column. Do not invent numbers; keep
  the raw JSON and build the table from it.
- Maintain a list of code that should normally not be hand-maintained:
  hand-written standard-format parsing, primitive schema guards, protocol
  mappings, hand-edited contracts/generated artifacts, re-implemented standard
  library semantics, scattered extension points, repeated boundary validation,
  and untyped `serde_json::Value` as the internal model.
- Tag only genuine instances. A tag must have a block-level rationale, not just
  a file-level label. The anti filter must show only anti blocks; unrelated notes,
  badges and wires must be hidden. Do not leave a “why” that is unrelated to the
  anti-pattern.
- Keep sources in the per-row `依据` column. Do not add a long “sources list /
  download JSON” paragraph at the bottom; the reviewer explicitly removed it.

## 4. English prompt first

- Turn the review findings into an English Markdown prompt for an implementing
  agent. Put it before the code in the delivery, and embed it in the review page.
- The prompt must include: context, non-negotiable constraints, measured
  evidence, prioritized items with exact code locations and suggested changes,
  acceptance criteria, validation commands, and deliverables.
- Every future review page must display the English prompt. A page without one
  is incomplete.
- Provide copy and `.md` download for the prompt.

## 5. Ask the agent from the page

- Every review comment has an input allowing an ad-hoc question or a request
  aimed at that code block.
- The composed Markdown must include the file, block letter, line range, the
  review note, the exact annotated diff excerpt and the question.
- A global input covers whole-review questions and references the English prompt.
- Support copy and `.md` download, persist drafts, and keep the same input in the
  mobile note dialog.
- The page is static: it must not send network requests or pretend to call an
  agent. The user copies/downloads the request and hands it to the agent.

## 6. Dark mode and default dark QA

- The page must support light and dark themes, default to the system preference,
  and allow `Auto → Light → Dark`, persisted across reloads without a flash.
- Dark mode is not “invert the background”: check code diff colours, annotation
  tints, note text, anti-pattern chips, tables, inputs, prompt, modal, wires and
  print.
- QA must include dark mode by default, alongside light and mobile, and check
  contrast (4.5:1 for normal text), overflow, connectors, note/badge parity and
  console errors.
- Print must use light colours.

## 7. Reusable and self-documenting

- Keep the reusable shell (CSS/JS, diff/annotation engine, metrics table,
  filters, prompt, ask UI, theme) in ``.
- Keep review-specific data in a data module, not in the renderer.
- Keep this skill and its references up to date so the next review starts from
  the same standard rather than re-deriving it.