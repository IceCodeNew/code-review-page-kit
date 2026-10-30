# QA checklist

Run this for every page. **Dark mode is part of the default check, not an extra.**

## Build and static checks

```bash
python3 review_page.py ... --output review-<slug>.html

# Rust
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace

# Python scripts (if the repository has them)
python3 -m unittest discover -s scripts

# Frontend (when the repository has one)
pnpm test
pnpm typecheck
```

Confirm the page has:

- [ ] exact integrated head and diff range in the footer;
- [ ] all changed files present (count matches `git diff --name-only`);
- [ ] one wire per note and one badge per note;
- [ ] production code expanded; only tests/fixtures/docs folded;
- [ ] 8 anti-pattern rows (or the current maintained count) and only genuine
      tagged blocks;
- [ ] English prompt section with a working copy button;
- [ ] per-note and global ask inputs; copy/download produce valid Markdown.

## Browser QA

```bash
PLAYWRIGHT_CORE=/path/to/playwright-core/index.mjs \
node qa.mjs \
  --url "file://$PWD/review-<slug>.html" \
  --chrome "/path/to/Google Chrome for Testing" \
  --out /tmp/review-<slug>-qa
```

The script must exit 0. It checks, in **light desktop, dark desktop, dark
mobile, light mobile**:

- [ ] no `pageerror` / console error;
- [ ] no horizontal overflow (`scrollWidth <= clientWidth + 1`);
- [ ] `notes == wires == badges == asks`;
- [ ] theme matches `prefers-color-scheme` on load;
- [ ] theme toggle changes preference and survives reload;
- [ ] anti filter shows only notes with an anti chip (and at least one);
- [ ] every visible text node meets 4.5:1 contrast (decorative line numbers,
      diff markers, dim stars and `\ No newline` are excluded);
- [ ] screenshots produced for light, dark, anti and the mobile modal;
- [ ] mobile badge opens the note dialog.

## Manual dark-mode pass

Look at the screenshots, not only the computed values:

- [ ] code context, additions and deletions are distinguishable without relying
      on colour alone (the +/− markers remain visible);
- [ ] annotation tint is visible but does not hide syntax;
- [ ] note text, “what/why” labels and the anti rationale are readable;
- [ ] badges still have a ring against the code background;
- [ ] wires and outlines are visible;
- [ ] tables, nav counts, captions, chips and inputs are readable;
- [ ] prompt body and ask textareas have a visible border and focus ring;
- [ ] print preview is light (the page forces light before printing).

## Anti-filter pass

- [ ] Click “反模式”. Only files with block-level anti notes remain.
- [ ] Every visible note has a violet chip and an anti rationale; notes unrelated
      to the anti-pattern are hidden.
- [ ] Non-anti annotated lines lose their tint/outline; code context is not
      deleted.
- [ ] Badges and wires for hidden notes disappear.
- [ ] Clearing the filter restores all notes and wires without overlap.

## Sign-off

Deliver with:

- the HTML page;
- the English prompt Markdown;
- the reusable tool/skill changes (if any);
- a short note listing the exact heads, commands run, and known gaps (for
  example dashboard tests not run because dependencies are absent).