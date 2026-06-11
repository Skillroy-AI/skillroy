---
name: review
description: Lint a skill (or a whole collection) against skillroy conventions and the Agent Skills standard, and report what to fix. Checks frontmatter validity, name-equals-folder, the metadata.skillroy block, naming and tier rules, canonical-token usage, the two-front-doors principle, and the phase-appropriate quality bar (evals, license, no plaintext secrets). Use when reviewing, linting, auditing, or checking a skill for compliance, before advancing a skill's phase, or before publishing a skill or collection. Pairs with `create`, which authors compliant skills.
metadata:
  skillroy:
    phase: publish
    tier: meta
    version: 0.3.0
license: Apache-2.0
---

# Review

Checks a skill — or every skill in a collection — against skillroy's conventions and reports findings
by severity, scaled to the skill's **phase** (lenient while `brainstorming`, strict at `publish`). The
enforceable rules live in skillroy's repo-root `CONVENTIONS.md`; this skill *checks* them,
`create` *applies* them.

**Two front doors.** Run it conversationally, or run the linter directly:
`python3 scripts/lint-skill.py <skill-dir-or-collection> [--json]` (`--self-test` to verify it).

## Workflow

### 1. Scope
Identify what to review: a single skill folder (one that contains a `SKILL.md`) or a collection
directory (lint every `*/SKILL.md` under it).

### 2. Run the linter
`python3 scripts/lint-skill.py <path>` — it parses each `SKILL.md`'s frontmatter (definitively via
PyYAML when present, with a stdlib fallback), then checks the house rules and prints findings as
`error` / `warn` / `info`, scaled by phase. Add `--json` for machine output, `--phase` to override, and
`--tokens <catalog>` to check each skill's `metadata.skillroy.domain` against the canonical-token
catalog (unknown → flag; alias → use the canonical; legacy → note the replacement).

**Finding the token catalog (the lookup ladder):** use the first that applies —
1. an explicit `--tokens <path>` (or one the user names in chat);
2. the **`$SKILLROY_TOKENS`** environment variable (the linter reads it automatically when
   `--tokens` is absent);
3. the org overlay's documented clone location (e.g. `<org>-skillroy/overlay/tokens/…` cloned
   beside this repo).
If none resolves, lint without a catalog and say so — token checks were skipped, not passed.

### 3. Base-spec + behavioural checks (recommended at publish)
If `skills-ref` is installed, run `skills-ref validate <skill-dir>` for official base conformance. If
the collection has a `resources.yaml` (external-resources manifest, CONVENTIONS §11), validate it with
`python3 <skillroy>/resources/validate-resources.py <resources.yaml>` (lint-skill only checks it's
well-formed + nudges when it's missing; this is the full per-entry check). For
*behaviour*, run the skill's evals: `python3 scripts/run-evals.py <skill>` validates the `evals.json`
and lists the cases; run the skill against each `prompt` and check its `expectations` (CONVENTIONS §8)
— at publish, evals must exist **and pass**. `lint-skill` adds the skillroy house rules on top; it
does not replace these.

### 4. Interpret and fix
For each finding, explain it and propose the concrete fix (per the conventions):
- **error** — blocks the skill at its current phase; fix before proceeding.
- **warn** — a SHOULD at this phase; fix to advance toward `publish`.
- **info** — a publish-bar item not yet required at this phase.

Never invent a canonical token to silence a finding — if a token isn't in the catalog, surface it.

### 5. Report
Summarise: pass/fail at the skill's phase, the findings, and what it would take to advance to the next
phase. Offer to apply the fixes (re-scaffold with `create`, or edit), then re-run.

## What `lint-skill` enforces
Frontmatter is valid YAML; `name` is kebab-case and equals the folder; `description` is present (what
+ when); the `metadata.skillroy` block (phase / tier / version) is valid; both front doors exist when
`scripts/` is present; no plaintext secrets; and the phase bar (at `publish`: evals present, `license`
set, canonical tokens MUST). With `--tokens`, `metadata.skillroy.domain` is validated against the
catalog (never invent a token). See the conventions doc for the rationale.
