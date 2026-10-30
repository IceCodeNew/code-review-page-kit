# Anti-patterns

These are the patterns the review page highlights in violet. Tag a block only
when the pattern is actually present; every tag must have a block-level
rationale in the note.

## 1. Hand-written standard-format parsing / serialization

Do not hand-roll parsers or serializers for OpenAPI, AsyncAPI, JSON Schema, OCI
manifests or similar standards. Version handling, references, unknown fields and
escaped pointers are the library/generator’s job.

Typical evidence: `serde_json::from_slice` plus a chain of `.get(...).and_then`,
manual `$ref` rewriting, string-prefix version checks.

## 2. Hand-written primitive schema guards

A forest of `isObject` / `isString` / `Array.isArray` is not a schema. It drifts
from the Rust response struct and only fails in tests, if at all. Define one
typed schema per response and derive the TypeScript type from it.

## 3. Hand-maintained protocol mappings

Model headers, message directions and extension fields spread across branches.
When the counterpart changes, the mapping silently diverges. Prefer a table or a
typed enum with exhaustive matches.

## 4. Hand-edited contracts or generated artifacts

Service documents, schemas and fixtures edited by hand drift from the
implementation. Generate them, or make the test compare bytes against the
generator output.

## 5. Re-implementing standard library / framework semantics

ETag comparison, JSON Pointer, HTTP method handling, merge-patch, base64, URL
parsing and similar already exist. A hand-written version is a compatibility
burden; use the standard implementation or a maintained crate.

## 6. Scattered extension points

Every new capability requires edits in several unrelated branches. Collect the
variation point in one place (a trait/enum/table) so adding a format or a
protocol is one localized change.

## 7. Repeated boundary validation

The same untrusted input is validated in several layers with different rules.
Pick one trust boundary; parse once into a type, then rely on the type.

## 8. Untyped `serde_json::Value` as the internal model

`Value` is fine at a genuinely open boundary (schema payloads, extensions, the
final serialization edge). Using it as the internal document model loses field
types, weakens error paths and allocates whole object/array trees.

Preferred treatment, in order:

1. Typed boundary structs for the stable envelope; use
   `#[serde(flatten)] extras: BTreeMap<String, Value>` (or
   `serde_json::Map<String, Value>`) to preserve unknown fields.
2. `&RawValue` / `Box<RawValue>` for pass-through payloads that must be
   transferred verbatim (references, examples, extension payloads). The
   serde_json docs describe `RawValue` as avoiding the cost of `Value`.
3. Keep `Value` at the open payload and final serialization boundaries only.
4. Avoid whole-tree clones used only for canonical ordering; sort and write in
   one traversal where possible, and keep budget charges unchanged.

Do **not** replace every `Value` mechanically. Measure document bytes, ETags and
the 32 MiB work / 4 MiB retained budgets before and after.

## Sources

- [serde_json::Value](https://docs.rs/serde_json/latest/serde_json/enum.Value.html)
- [serde_json::RawValue](https://docs.rs/serde_json/latest/serde_json/value/struct.RawValue.html)
- [serde flatten](https://serde.rs/attr-flatten.html)
- [Parse, don’t validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/)
- [psiace/skills — kill-ai-slop](https://github.com/psiace/skills/blob/main/skills/friendly-python/references/kill-ai-slop.md)
- [psiace/skills — review checklist](https://github.com/psiace/skills/blob/main/skills/friendly-python/references/review-checklist.md)
- [psiace/skills — modular-go review checklist](https://github.com/psiace/skills/blob/main/skills/modular-go/references/review-checklist.md)