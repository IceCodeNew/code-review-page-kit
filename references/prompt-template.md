# English review prompt template

The prompt is written for an implementing agent, not for the reviewer. It must be
self-contained, prioritized and behavior-preserving unless the review explicitly
asks for a behavior change.

## Structure

```markdown
# Review follow-up prompt — <theme> for PR #<n1> + #<n2>

## Role
You are a senior <language> engineer working in `<repo>`.
Implement the follow-up on the integrated tree (reviewed head `<sha>`, based on
`<base-sha>`).

## Context
- What the PRs add, in two or three bullets.
- What was validated and what remains risky.
- The measured baseline (function count, CC median/P95/P99).

## Non-negotiable constraints
1. No public contract, bytes, ETag, digest, diagnostics, budget, key or error
   semantics change.
2. Preserve deadlines, depth limits, cache limits and deterministic ordering.
3. One commit/PR per item; no refactor mixed with a behavior change.
4. No new dependency without proof and justification.
5. Read the named contract docs before editing.

## Current evidence
A table: function | file | CC | cognitive | SLOC (and delta). Include only
measured values; state the tool and the production-function baseline.

## P0 — <riskiest structural problem>
### 1. `<function>` (CC <n>, <n> SLOC)
**Location:** `path`, function.
**Why:** concrete failure mode, not “it is long”.
**Suggested change:** named intermediate types/functions, order of extraction,
what must not change.
**Acceptance:** golden bytes, tests, target complexity.

## P1 — <policy/view splits>
...

## P2 — <hand-maintained JS / untyped JSON>
...

## Suggested sequence
Characterization tests first, then P0, P1, P2; separate commits.

## Validation
Exact commands (`cargo fmt`, `clippy`, tests, `radon`, ESLint, Playwright) and
the golden-fixture byte check. Do not claim tests that were not run.

## Deliverables
Commits grouped by priority, before/after table, tests added, no contract change.
```

## Rules

- **Locations are exact.** File and symbol, not “the control crate”.
- **Evidence is measured.** Every CC/SLOC number must come from the local tool
  run; do not estimate.
- **The “why” is a failure mode.** “Would make a naming change affect every
  operation” beats “is complex”.
- **Suggestions are concrete.** Name the extracted functions/types and the
  invariants they must preserve.
- **Acceptance is testable.** Golden bytes, named test suites, target CC/SLOC and
  a no-behavior-change statement.
- **Priority is explicit.** P0 = highest risk / highest maintenance cost; do not
  dump a flat list.
- **No hidden scope.** If a change is optional or requires a dependency, say so.
- **No test-count bragging** in the PR body; put evidence in the delivery notes.
- **Include the anti-pattern guidance** relevant to the review, but do not turn
  the prompt into a generic style guide.

## Anti-patterns in prompts

Avoid:

- “Refactor for readability” without a target or acceptance test.
- A giant bullet list with no ordering.
- Mixing a behavior fix into a structural split.
- Asking for a new library without checking unknown-field/version support.
- Repeating the whole review page narrative; link to the page and keep the
  prompt action-oriented.
- Claiming “all tests pass” when only a check or a subset ran.