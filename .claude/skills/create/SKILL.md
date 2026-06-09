---
name: create
description: Author a new skillroy-compliant Agent Skill — or bring an existing one toward compliance. Scaffolds the skill folder and a conventions-correct SKILL.md (tier-aware name, what+when description, the metadata.skillroy block), plus references/, scripts/, and evals/, and applies the phase-appropriate quality bar (naming, canonical tokens, two front doors). Use when creating, scaffolding, or authoring a new skill; starting a skill from a research seed document; or making an existing skill skillroy-compliant. Pairs with `research` (turns sources into the seed doc this consumes) and `review` (lints a finished skill).
metadata:
  skillroy:
    phase: publish
    tier: meta
    version: 0.1.0
license: Apache-2.0
---

# Create

Authors a **skillroy-compliant** skill — a folder following the [Agent Skills](https://agentskills.io)
open standard, written to skillroy's house conventions. The enforceable rules are in
skillroy's repo-root `CONVENTIONS.md` (rationale lives in `DESIGN.md`); read that first.

**Two front doors.** Drive this conversationally (you need know nothing about the scripts), or run
the bundled scaffolder directly — `scripts/new-skill.py` — outside a chat. Run it as
`python3 scripts/new-skill.py <name> --tier <tier> --phase <phase>` (`--help` for all options;
`--self-test` to verify it offline).

## Workflow

Work in order; skip anything already supplied (a seed doc, a stated tier, a chosen name).

### 1. Capture intent
Establish, asking only for what's missing:
- **What & when** — what the skill does, and the trigger conditions that should invoke it.
- **Kind** — *action* (→ verb name: `deploy`, `diagnose`) or *knowledge* (→ noun: `xml-formats`).
- **Tier** — `kb` / `ops` / `int` / `core` / `meta` (conventions §2).
- **Domain / canonical token** — the app or area. Validate against the collection's token catalog;
  **never invent a token** — if it isn't in the catalog, surface it and ask (don't guess).
- **Phase** — `brainstorming` / `adhoc` / `publish` (sets the quality bar, §7).
- **Seed doc?** — if `research` produced one, use it as the grounding reference and cite it.

Confirm the brief back in a line or two before proceeding.

### 2. Decide the name
Apply conventions §1–§2: kebab-case `[a-z0-9-]`, ≤ 64, `name` == folder name; verb-or-noun by kind;
don't repeat the repo/domain; avoid reserved built-in command names. Propose the name plus an
alternative or two.

### 3. Scaffold the skeleton
Generate it deterministically with the scaffolder (`python3 scripts/new-skill.py <name> …`), or by hand:
```
<name>/
├── SKILL.md            # frontmatter + body
├── references/         # progressive disclosure
├── scripts/            # the CLI "second door" — only if the skill has deterministic/heavy work
└── evals/evals.json    # behaviour tests (publish-bar)
```
Stamp the **`metadata.skillroy`** block — phase, tier, version (and domain / depends-on if known).
See conventions §4.

### 4. Write the SKILL.md
- **Description** = *what* + *when*, trigger-rich (§3) — this is how the agent auto-routes to it.
- Keep the body lean; push detail into `references/` (progressive disclosure).
- **Two front doors** (§6): if the skill does deterministic/heavy work, add a standalone script and
  have the body tell the agent which script to run and how to read its output.

### 5. Apply the phase bar (§7)
- **brainstorming** — structure only; *collaborate in brainstorming style*: surface open questions,
  checkpoint, don't drive to "done."
- **adhoc** — SHOULD: compliant name, what+when description, canonical tokens, the metadata block.
- **publish** — MUST: all of adhoc **+** canonical tokens **+** `license` **+** provenance-stamped
  external deps **+** no plaintext secrets **+** both doors (if it has scripts) **+** evals present
  **+** base-spec clean (`skills-ref validate`).

### 6. Hand off
Summarise what was created, the phase and what it would take to advance, and offer `review` to lint
it. If a seed doc fed it, cite that doc in the new skill's references.

## Conventions
The authoritative, enforceable rules are in skillroy's repo-root `CONVENTIONS.md`. This skill *applies*
them; the `review` skill *checks* them.
