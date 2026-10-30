# Review data schema

A review data module is plain Python. It is imported by `review_page.py` and
must define `GROUPS`, `ANTI`, `FILES` and optionally `REVIEW`.

## `GROUPS`

```python
GROUPS = [
    ("g1", "Public contract", "Read the externally visible contract first."),
    ("g2", "Core implementation", "How the request is parsed, validated and served."),
    ("g3", "Appendix: fixtures", "Golden files and fixtures, folded by default."),
]
```

- `g1` is the first section in the page; order matters.
- Keep related files in the same group and order files by importance.
- A group with `fold` files still renders its header.

## `ANTI`

```python
ANTI = {
    "parse": (
        "手写格式解析",
        "OpenAPI/AsyncAPI/OCI 这类格式的版本、未知字段和引用边界应由库或生成器处理。",
        "psiace/kill-ai-slop；手写 JSON parser 替换案例",
    ),
    "value": (
        "无类型 JSON（serde_json::Value）",
        "类型、错误路径与不变量都会丢失；边界用 typed struct，透传用 RawValue，未知字段用 flatten Map 收口。",
        "serde_json RawValue；serde flatten；parse, don't validate",
    ),
}
```

- Key is used in file/note `anti` lists.
- Value is `(display name, why, source label)`.
- The first row is rendered in the cover table; all rows get a filter count.
- Use a distinct visual only for anti-pattern annotations (the renderer forces
  the violet palette and adds an `.anti-why` rationale to the note).

## `FILES`

```python
FILES = {
    "src/api.rs": {
        "g": "g1",
        "s": 5,                 # 1..5 importance
        "pr": "1+2",             # "1", "2", "1+2"
        "one": "Adds the public endpoint and its cache semantics",
        "fold": False,           # True for tests/fixtures/README/generated files
        "anti": [],              # file-level anti ids (optional)
        "notes": [
            {
                "anchor": "async fn handler",
                "what": "Adds the anonymous endpoint",
                "why": "Removes the credential requirement for document readers",
                "anti": [],
                "span": None,     # optional: limit highlighted lines
            },
        ],
    },
}
```

- `anchor` is a substring of a line in the **diff** (context, added or removed);
  the renderer highlights the semantic block containing it.
- `what` / `why` should be short (one or two lines). The page is read at a
  glance; put the detailed argument in the English prompt, not in every card.
- `span` limits a highlight inside a large block (for example `40`).
- If several notes map to the same block, the renderer splits them into
  non-overlapping sub-ranges in anchor order.
- `fold: True` keeps the code collapsed; use it for tests, fixtures,
  generated files, README/AGENTS and lockfiles. Rust `#[cfg(test)] mod tests`
  sections are folded automatically from the source line.
- `pr` must contain the filter values used by `REVIEW["filters"]`
  (the default is `1` / `2`).

## `REVIEW`

```python
REVIEW = {
    "repo_name": "example",
    "title": "PR #12 + #13: Example review",
    "doc_title": "Code review · PR #12 + #13",
    "subtitle": "What changed and why, in one line.",
    "heads": "#12 `<sha1>`, #13 `<sha2>`",
    "diff_range": "<base>..<head>",
    "extra_stats": ["linter <b>0</b> warnings"],
    "hot": [("src/api.rs", "handler")],
    "hot_notes": {("src/api.rs", "handler"): "entry point"},
    "baseline": "Baseline: median CC 2, P95 17.",
    "conclusion": "Start with `handler`.",
    "filters": [("1", "PR 1"), ("2", "PR 2")],
}
```

- `subtitle`, `baseline`, `conclusion` and `extra_stats` accept trusted HTML.
- `hot` rows are looked up in `metrics.json` / `ts_metrics.json`; only names
  found there are rendered.
- `filters` drives the topbar buttons; filter values must match the `pr` field.

## Metrics JSON

`--metrics` is produced by the review workflow (rust-code-analysis for Rust and
Radon for Python). It maps a path to a record with `max_cc`, `max_cog`,
`changed`, `dcc`, `top` and `funcs` (each function with `name`, `start`, `end`,
`cc`, `cog`, `sloc`, `dcc`). Missing files render without a metric chip.

`--ts-metrics` maps a TS/TSX path to `max`, `max_dcc` and `top` from the ESLint
`complexity` rule. Files with only unchanged pre-existing hotspots should be
omitted rather than surfaced as new complexity.

## Files JSON

```json
[{"path": "src/api.rs", "add": 120, "del": 4, "status": "M"}]
```

Generated with `git diff --no-renames --numstat` and
`git diff --no-renames --name-status` between the review base and head.