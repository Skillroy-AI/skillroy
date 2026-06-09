---
name: create
description: Author a new skillroy-compliant Agent Skill — in an existing collection or in a brand-new one — or bring an existing skill toward compliance. Scaffolds the collection shell when needed (README metadata block, skills home, gitignore, .agents symlink) and the skill folder with a conventions-correct SKILL.md (tier-aware name, what+when description, the metadata.skillroy block), plus references/, scripts/, and evals/, applying the phase-appropriate quality bar. Use when creating, scaffolding, or authoring a new skill or skill collection/repo; starting a skill from a research seed document; or making an existing skill skillroy-compliant. Pairs with `research` (turns sources into the seed doc this consumes) and `review` (lints the result).
metadata:
  skillroy:
    phase: publish
    tier: meta
    version: 0.2.0
license: Apache-2.0
---

# Create

Authors a **skillroy-compliant** skill — a folder following the [Agent Skills](https://agentskills.io)
open standard, written to skillroy's house conventions. The enforceable rules are in
skillroy's repo-root `CONVENTIONS.md` (rationale lives in `DESIGN.md`); read that first.

**Two front doors.** Drive this conversationally (you need know nothing about the scripts), or run
the bundled scaffolders directly outside a chat (`--help` / `--self-test` on each):
- `python3 scripts/new-skill.py <name> --tier <tier> --dir <collection>/.claude/skills` — a skill
  into an existing collection;
- `python3 scripts/new-collection.py <tier>-<domain> --dir <parent> [--with-skill <name>]` — a new
  compliant collection (README metadata block, skills home, safe gitignore, `.agents` symlink), and
  optionally its first skill in the same shot.

## Workflow

Work in order; skip anything already supplied (a seed doc, a stated tier, a chosen name).

### 0. Locate or create the collection
Skills live in **collections** (a repo of related skills in one domain — CONVENTIONS §10). Establish
where this skill goes:
- **Existing collection** → scaffold into its `.claude/skills/` and move on.
- **New collection** → settle the collection name (`<tier>-<domain>`; brand names are the ratified
  exception) and scaffold the shell with `scripts/new-collection.py` (use `--with-skill` to create
  the first skill in the same run). The script is git-free by design — offer to `git init -b main`
  and make the initial commit as a follow-up, and remind the user a new collection starts
  `status: experimental` in its README metadata block (promote to `active` once it has real,
  linted content).

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
