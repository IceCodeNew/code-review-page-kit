# Data schema

The canonical schema lives with the renderer:

[`schema.md`](../schema.md)

Minimum module contract:

```python
GROUPS = [("g1", "title", "one-line intro")]
ANTI = {"parse": ("name", "why", "source")}
FILES = {
    "path": {
        "g": "g1",
        "s": 5,
        "pr": "1+2",
        "one": "one-line purpose",
        "fold": False,
        "anti": [],
        "notes": [{"anchor": "...", "what": "...", "why": "...", "anti": []}],
    }
}
REVIEW = {...}  # title, heads, diff_range, hot, hot_notes, baseline, filters
```

Keep review-specific data out of ``; the renderer is shared,
the annotations are not.