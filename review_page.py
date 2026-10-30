# -*- coding: utf-8 -*-
"""Reusable block-level code review page generator.

The review content lives in a Python data module (`--data`) with GROUPS, ANTI,
FILES and REVIEW. The generic shell (CSS/JS/theme/wires/ask/prompt) lives in
`assets/`. See README.md and SKILL.md.
"""

import argparse
import codecs
import hashlib
import html
import importlib.util
import json
import re
import shlex
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--data", required=True, type=Path, help="review data module (GROUPS/ANTI/FILES/REVIEW)")
parser.add_argument("--diff", required=True, type=Path)
parser.add_argument("--files-json", required=True, type=Path)
parser.add_argument("--metrics", required=True, type=Path)
parser.add_argument("--ts-metrics", required=True, type=Path)
parser.add_argument("--prompt", required=True, type=Path, help="English review prompt (Markdown)")
parser.add_argument("--workspace", required=True, type=Path, help="integrated git worktree")
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--assets", type=Path, default=Path(__file__).with_name("assets"))
args = parser.parse_args()

spec = importlib.util.spec_from_file_location("review_data", args.data)
data_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_module)
ANTI = data_module.ANTI
FILES = data_module.FILES
GROUPS = data_module.GROUPS
REVIEW = getattr(data_module, "REVIEW", {})

OUT = args.output
PROMPT = args.prompt.read_text(encoding="utf-8")
assert PROMPT.strip(), "the English review prompt must not be empty"
WS = args.workspace
ASSETS = args.assets
CSS = (ASSETS / "theme.css").read_text(encoding="utf-8")
JS = (ASSETS / "app.js").read_text(encoding="utf-8")
THEME_INIT = (ASSETS / "theme-init.js").read_text(encoding="utf-8")
try:
    HEAD = subprocess.check_output(["git", "-C", str(WS), "rev-parse", "--short", "HEAD"], text=True).strip()
except subprocess.CalledProcessError:
    HEAD = "unknown"

DIFF = args.diff.read_text(encoding="utf-8", errors="replace")
META = {x["path"]: x for x in json.loads(args.files_json.read_text(encoding="utf-8"))}
RUST_METRICS = json.loads(args.metrics.read_text(encoding="utf-8"))
TS_METRICS = json.loads(args.ts_metrics.read_text(encoding="utf-8"))


TITLE = REVIEW.get("title", "Code review")
DOC_TITLE = REVIEW.get("doc_title", TITLE)
SUBTITLE = REVIEW.get("subtitle", "")
HEADS = REVIEW.get("heads", "")
DIFF_RANGE = REVIEW.get("diff_range", "")
EXTRA_STATS = REVIEW.get("extra_stats", [])
HOT = REVIEW.get("hot", [])
HOT_NOTES = REVIEW.get("hot_notes", {})
BASELINE = REVIEW.get("baseline", "")
CONCLUSION = REVIEW.get("conclusion", "")
FILTERS = REVIEW.get("filters", [("1", "PR 1"), ("2", "PR 2")])
REPO_NAME = REVIEW.get("repo_name", "repository")
VALIDATION = REVIEW.get("validation_note", "未记录 linter 运行状态；仅渲染提供的指标文件")
REVIEW_KEY = hashlib.sha1((REPO_NAME + TITLE + HEADS + DIFF_RANGE + DIFF).encode("utf-8")).hexdigest()[:12]

COLORS = ["#b42318", "#1d4ed8", "#0f766e", "#b45309", "#6d28d9", "#be185d"]
HEAT = {5: "关键", 4: "重要", 3: "关注", 2: "一般", 1: "细节"}

assert set(META) == set(FILES), (set(META) - set(FILES), set(FILES) - set(META))

# ---------------------------------------------------------------- diff parse

def _unquote_git_path(token):
    """Decode a path token from `diff --git`, including Git's C-style quoting."""
    token = token.strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        raw = codecs.escape_decode(token[1:-1].encode("utf-8"))[0]
        return raw.decode("utf-8")
    return token


def _diff_dst_path(line):
    """Return the destination path of a `diff --git` header, without the b/ prefix."""
    rest = line[len("diff --git "):]
    if not rest.startswith('"'):
        # --no-renames: header is "a/<path> b/<path>", and a path with spaces
        # is not quoted. Recover it from the known identical left/right halves.
        if rest.startswith("a/") and len(rest) >= 5:
            n = (len(rest) - 5) // 2
            if n > 0 and rest[2 + n:2 + n + 3] == " b/" and rest[2 + n + 3:] == rest[2:2 + n]:
                return rest[2 + n + 3:]
        path = rest.rsplit(" b/", 1)[-1]
        if path != rest:
            return path
    try:
        parts = shlex.split(rest, posix=False)
    except ValueError as exc:
        raise ValueError(f"cannot parse diff header: {line!r}") from exc
    if len(parts) != 2:
        raise ValueError(f"cannot parse diff header: {line!r}")
    dst = _unquote_git_path(parts[1])
    if dst.startswith("b/"):
        dst = dst[2:]
    return dst


def parse_diff(text):
    files = {}
    cur = None
    hunk = None
    for line in text.split("\n"):
        if line == "":
            continue
        if line.startswith("diff --git "):
            cur = {"items": [], "hunk_count": 0}
            files[_diff_dst_path(line)] = cur
            hunk = None
        elif cur is None:
            continue
        elif line.startswith("@@ "):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            hunk = {"old": int(m.group(1)), "new": int(m.group(2))}
            cur["items"].append({"kind": "hunk", "text": line})
            cur["hunk_count"] += 1
        elif hunk is None and (line.startswith("--- ") or line.startswith("+++ ")):
            continue
        elif line.startswith("\\"):
            cur["items"].append({"kind": "meta", "text": line})
        elif line.startswith("+"):
            cur["items"].append({"kind": "add", "text": line[1:], "new": hunk["new"]})
            hunk["new"] += 1
        elif line.startswith("-"):
            cur["items"].append({"kind": "del", "text": line[1:], "old": hunk["old"]})
            hunk["old"] += 1
        elif line.startswith(" "):
            cur["items"].append({"kind": "ctx", "text": line[1:], "old": hunk["old"], "new": hunk["new"]})
            hunk["old"] += 1
            hunk["new"] += 1
    return files


PARSED = parse_diff(DIFF)
assert set(PARSED) == set(META)

RUST_START = re.compile(
    r"^\s*(pub(\([^)]*\))?\s+)?(async\s+)?(unsafe\s+)?fn\s"
    r"|^\s*(pub(\([^)]*\))?\s+)?(struct|enum|trait|impl|mod|const|static|type)\s"
    r"|^\s*#\[cfg\(test\)\]"
)
PY_START = re.compile(r"^(async\s+)?def\s|^class\s|^@app\.")
TS_START = re.compile(
    r"^(export\s+)?(async\s+)?function\s"
    r"|^(export\s+)?(const|let)\s+\w+\s*[=:]"
    r"|^(export\s+)?(interface|type|class|enum)\s"
    r"|^export\s+default"
)
MD_START = re.compile(r"^#{1,4}\s")
YAML_START = re.compile(r"^\s*-\s+name:|^  [\w-]+:\s*$")


def start_re(path):
    if path.endswith(".rs"):
        return RUST_START
    if path.endswith(".py"):
        return PY_START
    if path.endswith((".ts", ".tsx")):
        return TS_START
    if path.endswith(".md"):
        return MD_START
    if path.endswith((".yaml", ".yml")):
        return YAML_START
    return None


def test_item_ranges(path, items):
    """Return item-index ranges that are Rust `#[cfg(test)] mod tests` code.

    Test modules are located in the *new* source, then mapped to the diff item
    sequence. Deleted lines before the module must not be mistaken for test
    code, and production code after a test module is not folded.
    """
    if not path.endswith(".rs"):
        return []
    src = WS / path
    source = src.read_text(encoding="utf-8", errors="replace").split("\n") if src.exists() else []
    line_ranges = []
    i = 0
    while i < len(source):
        if source[i].strip() != "#[cfg(test)]":
            i += 1
            continue
        j = i + 1
        while j < len(source) and not source[j].strip():
            j += 1
        if j >= len(source) or not source[j].strip().startswith("mod tests"):
            i += 1
            continue
        depth = 0
        started = False
        end = j
        for k in range(j, len(source)):
            depth += source[k].count("{") - source[k].count("}")
            if "{" in source[k]:
                started = True
            if started and depth <= 0:
                end = k
                break
        line_ranges.append((i + 1, end + 1))
        i = end + 1

    item_ranges = []
    for lo, hi in line_ranges:
        idxs = [
            n for n, item in enumerate(items)
            if item.get("new") is not None and lo <= item["new"] <= hi
        ]
        if idxs:
            item_ranges.append((min(idxs), max(idxs)))
    # merge overlapping or adjacent ranges
    merged = []
    for lo, hi in item_ranges:
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def _keep_test_range(path, items, lo, hi):
    """Keep a test range visible when a review note anchors inside it."""
    for note in FILES[path]["notes"]:
        anchor = note["anchor"]
        if any(lo <= n <= hi and anchor in items[n].get("text", "") for n in range(lo, hi + 1)):
            return True
    return False


def build_blocks(path, items):
    """Return (main_blocks, folded_test_ranges).

    A test range containing a review note stays visible, so the note is never
    silently dropped by folding. Other test ranges are folded separately; code
    after a test module remains reviewable.
    """
    test_ranges = test_item_ranges(path, items)
    folded = [
        (lo, hi) for lo, hi in test_ranges
        if not _keep_test_range(path, items, lo, hi)
    ]
    excluded = {n for lo, hi in folded for n in range(lo, hi + 1)}
    rx = start_re(path)
    blocks = []
    cur = None
    for i, item in enumerate(items):
        if i in excluded:
            if cur:
                blocks.append(cur)
                cur = None
            continue
        if item["kind"] == "hunk":
            if cur:
                blocks.append(cur)
                cur = None
            continue
        if rx and rx.match(item.get("text", "")) and item["kind"] != "meta":
            if cur:
                blocks.append(cur)
            cur = [i, i]
        elif cur is None:
            cur = [i, i]
        else:
            cur[1] = i
    if cur:
        blocks.append(cur)
    return blocks, folded


def new_line_at(items, idx):
    for i in range(idx, len(items)):
        if "new" in items[i]:
            return items[i]["new"]
    return None


# --------------------------------------------------------------- annotations

def resolve_notes(path):
    data = FILES[path]
    items = PARSED[path]["items"]
    blocks, folded = build_blocks(path, items)
    notes = []
    used = set()
    for note in data["notes"]:
        anchor = note["anchor"]
        found = None
        for i, item in enumerate(items):
            if anchor in item.get("text", ""):
                found = i
                break
        if found is None:
            raise SystemExit(f"UNRESOLVED {path}: {anchor!r}")
        block = next((b for b in blocks if b[0] <= found <= b[1]), None)
        if block is None:
            raise SystemExit(f"NOBLOCK {path}: {anchor!r}")
        if note.get("span"):
            start = found
            end = min(block[1], found + note["span"] - 1)
        elif block[1] - block[0] > 90:
            start = found
            end = min(block[1], found + 70)
        else:
            start, end = block
        notes.append({**note, "found": found, "start": start, "end": end, "block": block})
        used.add(tuple(block))
    # multiple notes in one block: split into non-overlapping sub-ranges
    by_block = {}
    for n in notes:
        by_block.setdefault(tuple(n["block"]), []).append(n)
    for key, group in by_block.items():
        if len(group) == 1:
            continue
        group.sort(key=lambda n: n["found"])
        for i, n in enumerate(group):
            start = n["found"]
            end = (group[i + 1]["found"] - 1) if i + 1 < len(group) else key[1]
            end = min(end, start + 70)
            n["start"], n["end"] = start, max(start, end)
    notes.sort(key=lambda n: n["start"])
    return notes, blocks, folded


RESOLVED = {}
for path in FILES:
    RESOLVED[path] = resolve_notes(path)

# ------------------------------------------------------------------- metrics

def fn_meta(path, line, anchor):
    m = RUST_METRICS.get(path)
    if m and line:
        cands = [f for f in m.get("funcs", []) if f["start"] <= line <= f["end"]]
        if cands:
            name = None
            mm = re.search(r"\b(?:fn|def)\s+([A-Za-z_][\w]*)", anchor)
            if mm:
                name = mm.group(1)
            if name:
                exact = [f for f in cands if f["name"].split("::")[-1] == name]
                if exact:
                    return exact[0]
            return min(cands, key=lambda f: f["sloc"])
    t = TS_METRICS.get(path)
    if t:
        mm = re.search(r"\b(?:function|const)\s+([A-Za-z_][\w]*)", anchor)
        if mm:
            for f in t["top"]:
                if f["name"] == mm.group(1):
                    return {"name": f["name"], "cc": f["cc"], "cog": 0, "sloc": 0, "dcc": f.get("dcc")}
    return None


def file_metrics(path):
    m = RUST_METRICS.get(path)
    if m and m.get("changed"):
        return {
            "cc": m["max_cc"], "cog": m["max_cog"], "changed": m["changed"],
            "dcc": m.get("max_dcc"), "tool": "RCA", "clippy": 0,
        }
    t = TS_METRICS.get(path)
    if t and path not in {"dashboard/src/server/api.ts"}:
        dcc = t.get("max_dcc")
        if dcc == 0 and not META[path]["status"] == "A":
            return None
        return {"cc": t["max"], "cog": None, "changed": len(t["top"]), "dcc": dcc, "tool": "ESLint", "clippy": None}
    return None


def heat_class(cc):
    if cc is None:
        return ""
    if cc >= 30:
        return "hot"
    if cc >= 15:
        return "warm"
    return "cool"


# ------------------------------------------------------------------- render

def esc(text):
    return html.escape(text, quote=False)


def attr(text):
    return html.escape(text, quote=True)


def file_id(path):
    """Collision-free, stable id for links and DOM lookups."""
    return "f-" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]


def render_line(item, note=None, first=False, last=False, color=0, badge=""):
    kind = item["kind"]
    text = esc(item.get("text", ""))
    old = item.get("old", "")
    new = item.get("new", "")
    mark = {"add": "+", "del": "−", "ctx": ""}.get(kind, "")
    classes = ["dl", kind]
    if note is not None:
        classes += ["ann", f"c{color}"]
        if first:
            classes.append("first")
        if last:
            classes.append("last")
    attrs = ""
    if note is not None:
        attrs += f' data-note="{note}"'
    if kind in ("ctx", "add", "del"):
        return (
            f'<div class="{" ".join(classes)}"{attrs}><span class="ln">{old}</span>'
            f'<span class="ln">{new}</span><span class="mark">{mark}</span>'
            f'<span class="code">{text or " "}{badge}</span></div>'
        )
    return f'<div class="dl {kind}"><span class="ln"></span><span class="ln"></span><span class="code">{text}</span></div>'


def render_block(path, block, items, note_map, colors, first_badge):
    start, end = block
    out = []
    for i in range(start, end + 1):
        item = items[i]
        if item["kind"] == "hunk":
            out.append(f'<div class="hunk-sep">{esc(item["text"])}</div>')
            continue
        info = note_map.get(i)
        if info:
            note_id, color, first, last = info
            out.append(render_line(item, note_id, first, last, color, ""))
        else:
            out.append(render_line(item))
    return "".join(out)


def render_raw(items):
    out = []
    for item in items:
        if item["kind"] == "hunk":
            out.append(f'<div class="hunk-sep">{esc(item["text"])}</div>')
        else:
            out.append(render_line(item))
    return "".join(out)


def metric_chip(m, path):
    if not m:
        return ""
    parts = []
    if m.get("cc") is not None:
        d = m.get("dcc")
        delta = f" ({d:+d})" if isinstance(d, int) and d else ""
        parts.append(f'<span class="m {heat_class(m["cc"])}">CC {m["cc"]}{delta}</span>')
    if m.get("cog"):
        parts.append(f'<span class="m">认知 {m["cog"]}</span>')
    if m.get("changed"):
        parts.append(f'<span class="m">{m["changed"]} 个变更函数</span>')
    if m.get("tool") == "ESLint":
        parts.append('<span class="m">ESLint</span>')
    return "".join(parts)


def note_metric(note, path):
    line = new_line_at(PARSED[path]["items"], note["found"])
    fn = fn_meta(path, line, note["anchor"])
    if not fn:
        return ""
    bits = [f'所在函数 CC {fn["cc"]}']
    dcc = fn.get("dcc")
    if isinstance(dcc, (int, float)) and dcc:
        bits[0] += f' ({int(dcc):+d})'
    if fn.get("cog"):
        bits.append(f'认知 {fn["cog"]}')
    if fn.get("sloc"):
        bits.append(f'{fn["sloc"]} 行')
    return " · ".join(bits)


NON_ANTI = [0, 1, 2, 3, 5]


def note_color(n, idx):
    return 4 if n.get("anti") else NON_ANTI[idx % len(NON_ANTI)]


def line_span(items, start, end):
    nums = [items[i]["new"] for i in range(start, end + 1) if "new" in items[i]]
    if not nums:
        nums = [items[i]["old"] for i in range(start, end + 1) if "old" in items[i]]
    if not nums:
        return ""
    lo, hi = min(nums), max(nums)
    return str(lo) if lo == hi else f"{lo}–{hi}"


def render_file(path, index):
    meta = META[path]
    data = FILES[path]
    items = PARSED[path]["items"]
    notes, blocks, folded = RESOLVED[path]
    status = "新增" if meta["status"] == "A" else "修改"
    status_cls = "addfile" if meta["status"] == "A" else "modfile"
    anti_file = data.get("anti", [])
    note_anti = sorted({a for n in notes for a in n.get("anti", [])})
    all_anti = list(dict.fromkeys(anti_file + note_anti))
    pr = str(data.get("pr", ""))
    pr_text = "+".join(f"#{x}" for x in pr.split("+")) if pr else ""
    chips = [f'<span class="chip {status_cls}">{status}</span>']
    if pr_text:
        chips.append(f'<span class="chip pr">{pr_text}</span>')
    if data.get("fold") and not notes:
        chips.append('<span class="chip foldc">折叠</span>')
    elif data.get("fold") and notes:
        chips.append('<span class="chip foldc">含批注 · 展开</span>')
    for a in all_anti:
        chips.append(f'<span class="chip anti">{esc(ANTI[a][0])}</span>')
    fm = file_metrics(path)
    metric_html = metric_chip(fm, path)
    hunk_count = PARSED[path]["hunk_count"]

    head = f"""
<header class="file-head">
  <div class="fh-top">
    <span class="idx">{index}</span>
    <code class="path">{esc(path)}</code>
    {''.join(chips)}
    <span class="stars s{data['s']}" title="{HEAT[data['s']]}">{'●' * data['s']}<span class="dim">{'●' * (5 - data['s'])}</span></span>
    <span class="stat"><b class="plus">+{meta['add']:,}</b><b class="minus">−{meta['del']:,}</b></span>
  </div>
  <div class="fh-bottom">
    <span class="one">{esc(data['one'])}</span>
    <span class="fmetrics">{metric_html}</span>
  </div>
</header>"""

    if data.get("fold") and not notes:
        summary = f'<summary><span class="fold-label">默认折叠</span>测试 / 夹具 / 说明 · {meta["add"]:,} 增 / {meta["del"]:,} 删 · {hunk_count} hunk</summary>'
        return f"""<section class="file folded" id="{file_id(path)}" data-pr="{attr(data['pr'])}" data-stars="{data['s']}" data-anti="{1 if all_anti else 0}" data-search="{attr(path + ' ' + data['one'])}">
{head}
<details class="fold">{summary}<div class="raw-code">{render_raw(items)}</div></details>
</section>"""

    fold_open = ""
    if data.get("fold") and notes:
        fold_open = f'<div class="fold-open-note">该文件通常默认折叠，但包含 {len(notes)} 条块级批注；为保证批注可见，代码已展开。</div>'

    # line -> note mapping
    note_map = {}
    badges = {}
    letters = {}
    for idx, n in enumerate(notes):
        letter = chr(ord("A") + idx)
        letters[id(n)] = letter
        color = note_color(n, idx)
        for i in range(n["start"], n["end"] + 1):
            old = note_map.get(i)
            note_map[i] = (id(n), color, i == n["start"], i == n["end"])
        badges[id(n)] = f'<button type="button" class="badge c{color}" data-note="{id(n)}" style="--c:{COLORS[color]}" title="批注 {letter}" aria-label="打开批注 {letter}">{letter}</button>'
    # compact note ids
    compact = {}
    for i, n in enumerate(notes):
        compact[id(n)] = f"n{i}"
    note_map2 = {k: (compact[v[0]],) + v[1:] for k, v in note_map.items()}
    badges2 = {compact[k]: v.replace(f'data-note="{k}"', f'data-note="{compact[k]}"') for k, v in badges.items()}

    body_parts = []
    for b in blocks:
        body_parts.append(f'<div class="block">{render_block(path, b, items, note_map2, COLORS, badges2)}</div>')
    code = "".join(body_parts)

    notes_html = []
    for i, n in enumerate(notes):
        nid = compact[id(n)]
        color = note_color(n, i)
        letter = letters[id(n)]
        anti = "".join(f'<span class="chip anti">{esc(ANTI[a][0])}</span>' for a in n.get("anti", []))
        mm = note_metric(n, path)
        span = line_span(items, n["start"], n["end"])
        key = f"{path}#{letter}"
        anti_note = "1" if n.get("anti") else "0"
        anti_why = "".join(
            f'<div><b>{esc(ANTI[a][0])}</b>{esc(ANTI[a][1])}</div>' for a in n.get("anti", [])
        )
        notes_html.append(f"""
<aside class="note c{color}" data-note="{nid}" data-path="{attr(path)}" data-letter="{letter}" data-anti="{anti_note}"
 data-span="{attr(span)}" data-what="{attr(n['what'])}" data-why="{attr(n['why'])}" style="--c:{COLORS[color]}">
  <div class="note-head"><span class="letter c{color}">{letter}</span><div><div class="whatk">改了什么</div><h4>{esc(n['what'])}</h4></div></div>
  <p class="why"><span class="k">为什么</span>{esc(n['why'])}</p>
  <div class="note-foot">{f'<span class="mm">{esc(mm)}</span>' if mm else ''}{anti}</div>
  {f'<div class="anti-why">{anti_why}</div>' if anti_why else ''}
  <details class="ask">
    <summary>提问 / 要求 agent</summary>
    <textarea class="ask-input" rows="3" data-key="{attr(key)}" placeholder="针对 {letter} 块提问，或写下修改要求…"></textarea>
    <div class="ask-actions"><button type="button" class="btn ask-copy">复制提问</button><button type="button" class="btn ask-download">下载 .md</button></div>
  </details>
</aside>""")

    tests = ""
    for lo, hi in folded:
        test_items = items[lo:hi + 1]
        test_lines = sum(1 for x in test_items if x["kind"] in ("add", "del", "ctx"))
        tests += f'<details class="fold tests"><summary><span class="fold-label">默认折叠</span>测试代码 · {test_lines:,} 行</summary><div class="raw-code">{render_raw(test_items)}</div></details>'

    badge_html = ''.join(
        f'<button type="button" class="badge c{note_color(n, i)}" data-note="{compact[id(n)]}" style="--c:{COLORS[note_color(n, i)]}" title="批注 {letters[id(n)]}" aria-label="打开批注 {letters[id(n)]}">{letters[id(n)]}</button>'
        for i, n in enumerate(notes)
    )
    body_cls = "file-body" if notes else "file-body no-notes"
    return f"""<section class="file" id="{file_id(path)}" data-pr="{attr(data['pr'])}" data-stars="{data['s']}" data-anti="{1 if all_anti else 0}"
 data-search="{attr(path + ' ' + data['one'] + ' ' + ' '.join(n['what'] + ' ' + n['why'] for n in notes))}">
{head}
{fold_open}
<div class="{body_cls}">
  <div class="code-col">{code}</div>
  <div class="note-col">{''.join(notes_html)}</div>
  <div class="badge-layer">{badge_html}</div>
  <svg class="wires" aria-hidden="true"></svg>
</div>
{tests}
</section>"""


# --------------------------------------------------------------- cover data



def hot_row(path, name):
    m = RUST_METRICS.get(path)
    cc = dcc = None
    if m:
        for f in m.get("funcs", []):
            if f["name"].split("::")[-1] == name:
                cc = f["cc"]
                dcc = f.get("dcc")
                break
    if cc is None:
        t = TS_METRICS.get(path)
        if t:
            for f in t["top"]:
                if f["name"] == name:
                    cc = f["cc"]
                    dcc = f.get("dcc")
                    break
    if cc is None:
        return ""
    delta = f'<span class="delta">{int(dcc):+d}</span>' if isinstance(dcc, (int, float)) and dcc else ""
    note = HOT_NOTES.get((path, name), "")
    short = path.split("/")[-1]
    return f'<tr><td class="fn"><a href="#{file_id(path)}">{esc(name)}</a></td><td class="srcfile">{esc(short)}</td><td class="cc {heat_class(cc)}">{cc}{delta}</td><td>{esc(note)}</td></tr>'


hot_rows = "".join(hot_row(p, n) for p, n in HOT)



anti_rows = []
for aid, (aname, why, source) in ANTI.items():
    hits = [p for p, d in FILES.items() if aid in d.get("anti", []) or any(aid in n.get("anti", []) for n in d.get("notes", []))]
    examples = ", ".join(Path(p).name for p in hits[:2]) + ("…" if len(hits) > 2 else "") if hits else "—"
    anti_rows.append(
        f'<tr><td><span class="chip anti">{esc(aname)}</span></td><td class="why">{esc(why)}</td>'
        f'<td class="cnt">{len(hits)}</td><td class="src">{esc(source)}</td></tr>'
    )

group_counts = {gid: sum(1 for p, d in FILES.items() if d["g"] == gid) for gid, _, _ in GROUPS}

nav = []
for gid, title, _ in GROUPS:
    nav.append(f'<div class="nav-group"><div class="nav-title">{esc(title)}<span>{group_counts[gid]}</span></div>')
    for path, d in FILES.items():
        if d["g"] != gid:
            continue
        nav.append(f'<a class="nav-file" href="#{file_id(path)}" data-pr="{attr(d["pr"])}" data-stars="{d["s"]}" data-anti="{1 if (d.get("anti") or any(n.get("anti") for n in d.get("notes", []))) else 0}"><span class="dot s{d["s"]}"></span>{esc(Path(path).name)}</a>')
    nav.append("</div>")

sections = []
for gid, title, desc in GROUPS:
    cards = []
    idx = 0
    for path, d in FILES.items():
        if d["g"] != gid:
            continue
        idx += 1
        cards.append(render_file(path, idx))
    # global numbering later
    label = "附录 A" if gid == "g1b" else f"第 {[g[0] for g in GROUPS].index(gid) + 1} 组"
    sections.append(f"""
<article class="sheet group" id="group-{gid}">
  <div class="group-head"><span class="kicker">{label} · {len(cards)} 个文件</span><h2>{esc(title)}</h2><p>{esc(desc)}</p></div>
  {''.join(cards)}
</article>""")

# Re-number files globally (render_file used per-group index)
offset = 0
out_sections = []
for gid, title, desc in GROUPS:
    count = group_counts[gid]
    seg = sections[[g[0] for g in GROUPS].index(gid)]
    # re-render with global indices
    cards = []
    n = offset
    for path, d in FILES.items():
        if d["g"] != gid:
            continue
        n += 1
        cards.append(render_file(path, n))
    offset = n
    label = "附录 A" if gid == "g1b" else f"第 {[g[0] for g in GROUPS].index(gid) + 1} 组"
    out_sections.append(f"""
<article class="sheet group" id="group-{gid}">
  <div class="group-head"><span class="kicker">{label} · {count} 个文件</span><h2>{esc(title)}</h2><p>{esc(desc)}</p></div>
  {''.join(cards)}
</article>""")

notes_total = sum(len(RESOLVED[p][0]) for p in FILES)
folded_total = sum(1 for p, d in FILES.items() if d["fold"] and not RESOLVED[p][0])
total_add = sum(m["add"] for m in META.values())
total_del = sum(m["del"] for m in META.values())
new_files = sum(1 for m in META.values() if m["status"] == "A")

filter_buttons = "".join(
    f'<button class="btn flt" data-f="{f}" aria-pressed="false" type="button">{esc(label)}</button>'
    for f, label in FILTERS
)

page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(DOC_TITLE)}</title>
<style>{CSS}</style>
<script>{THEME_INIT}</script>
</head>
<body data-heads="{attr(HEADS)}" data-title="{attr(DOC_TITLE)}" data-review-key="{REVIEW_KEY}">
<div class="topbar">
  <span class="doc">{esc(DOC_TITLE)}</span>
  <span class="meta">{esc(REPO_NAME)} · {len(FILES)} 文件 · 本地集成</span>
  <span class="spacer"></span>
  <button class="btn" id="expand" type="button">展开测试/夹具</button>
  <button class="btn" id="collapse" type="button">折叠测试/夹具</button>
  <span class="sep"></span>
  <button class="btn flt" data-f="all" aria-pressed="true" type="button">全部</button>
  {filter_buttons}
  <button class="btn flt" data-f="key" aria-pressed="false" type="button">关键</button>
  <button class="btn flt" data-f="anti" aria-pressed="false" type="button">反模式</button>
  <a class="btn" href="#prompt">Prompt</a>
  <button class="btn" id="theme" type="button" aria-label="Theme">Auto</button>
  <input id="search" type="search" placeholder="搜索文件或批注…" aria-label="搜索">
</div>

<div class="layout">
  <nav class="nav" aria-label="文件目录">
    <div class="nav-head">文件 · {len(FILES)}</div>
    <a class="nav-file nav-prompt" href="#prompt"><span class="dot s5"></span>Review prompt (EN)</a>
    {''.join(nav)}
  </nav>
  <main>
    <article class="sheet cover">
      <div class="crumb">Code review · block-level</div>
      <h1>{esc(TITLE)}</h1>
      <p class="sub">{SUBTITLE}</p>
      <div class="stats">
        <span class="stat-chip"><b>{len(FILES)}</b> 文件</span>
        <span class="stat-chip"><b>+{total_add:,}</b> / <b>−{total_del:,}</b></span>
        <span class="stat-chip"><b>{new_files}</b> 个新增</span>
        <span class="stat-chip"><b>{notes_total}</b> 条块级批注</span>
        <span class="stat-chip"><b>{folded_total}</b> 个测试/夹具/说明默认折叠</span>
        {''.join(f'<span class="stat-chip">{s}</span>' for s in EXTRA_STATS)}
      </div>

      <div class="two">
        <div>
          <h3>复杂度热点（先看这些函数）</h3>
          <div class="table-wrap"><table class="hot">
            <thead><tr><th>函数</th><th>文件</th><th>CC</th><th>怎么看</th></tr></thead>
            <tbody>{hot_rows}</tbody>
          </table></div>
          <p class="caption">{BASELINE}<br><b>结论：</b>{CONCLUSION}</p>
        </div>
        <div>
          <h3>通常不该手工维护的代码行为</h3>
          <div class="table-wrap"><table class="anti">
            <thead><tr><th>反模式</th><th>为什么</th><th>命中</th><th>依据</th></tr></thead>
            <tbody>{''.join(anti_rows)}</tbody>
          </table></div>

        </div>
      </div>

      <div class="how">
        <div><b>圈出的块</b> = 一条批注的范围；字母 A/B/C 只用于区分相邻批注。</div>
        <div><b>连线</b>指向右侧批注框：先读“改了什么”，再看“为什么”。</div>
        <div><b>测试、夹具、说明</b>默认折叠；主代码默认全部展开。</div>
        <div><b>筛选</b>按 PR、关键、反模式；搜索会匹配批注文字。</div>
      </div>
      <div class="legend">
        <span><span class="k ins">新增</span> 绿色行 = 插入</span>
        <span><span class="k rem">删除</span> 红色行 = 删除</span>
        <span><span class="k badgek">A</span> 圈出的代码块</span>
        <span><span class="wirek"></span> 连线到批注</span>
        <span><span class="k antik">反模式</span> 紫色圈/标签 = 通常不应手写</span>
        <span>灰底 = 未改动的上下文行</span>
      </div>
    </article>

    <article class="sheet prompt-sheet" id="prompt">
      <div class="prompt-head">
        <div>
          <div class="crumb">Review follow-up · English</div>
          <h2>Implementation prompt</h2>
          <p class="prompt-lead">可复制给实现代理的英文 prompt：按优先级列出最值得改的代码位置、原因、建议与验收标准。未来的审阅页面同样会包含这一节。</p>
        </div>
        <button class="btn" id="copy-prompt" type="button">复制 Markdown</button>
      </div>
      <div class="ask-global">
        <label for="global-ask">我的问题 / 附加要求（可针对整个审阅，或引用下方 prompt）</label>
        <textarea id="global-ask" placeholder="例如：先只做 P0 的 assemble 拆分；解释为什么保留 Value；把 P1 拆成两个 PR…"></textarea>
        <div class="ask-actions">
          <button class="btn" id="global-copy" type="button">复制问题</button>
          <button class="btn" id="global-download" type="button">下载 .md</button>
          <span class="meta">页面不联网；复制/下载后交给 agent</span>
        </div>
      </div>
      <pre class="prompt-body" id="prompt-body">{esc(PROMPT)}</pre>
    </article>

    {''.join(out_sections)}

    <div class="footer">本地集成：<code>{esc(str(WS))}</code> @ <code>{HEAD}</code> · 差异 {esc(DIFF_RANGE)} · {esc(VALIDATION)}</div>
  </main>
</div>

<div class="modal" id="modal" role="dialog" aria-modal="true"><div class="modal-card"><button class="btn close" type="button">关闭</button><div id="modal-body"></div></div></div>

<script>{JS}</script>
</body>
</html>"""

OUT.write_text(page, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size/1024/1024:.1f} MiB)")
