---
name: migrate
description: "Migrate an existing skill or collection to skillroy compliance — in place or into a new project. Inventories the source, surfaces the judgment calls (tier, domain tokens, renames, target phase), then applies the mechanical changes (move to the skills home, inject metadata.skillroy, fix .gitignore, add the .agents symlink) and verifies with review. Use when adopting skillroy for existing skills, converting or instrumenting a skill repo, moving skills between layout conventions, or making a skill compliant."
metadata:
  skillroy:
    phase: publish
    tier: meta
    version: 0.1.0
license: Apache-2.0
---

# Migrate

Takes skills that predate skillroy — wrong layout, no `metadata.skillroy`, no evals, gitignore traps —
and brings them to compliance without rewriting their content. The split matters: **mechanical changes
are scripted; judgment calls are surfaced.** Migration never silently picks a tier, invents a token,
or renames anything.

**Two front doors.** Run it conversationally (this workflow), or run the migrator directly:
`python3 scripts/migrate-skill.py plan <source>` then
`python3 scripts/migrate-skill.py apply <source> --dest <repo> --tier <t> ...`
(`--self-test` to verify it; `--json` for machine output).

## Workflow

### 1. Scope
Establish three things with the user:
- **Source** — a single skill folder, a collection, or a whole repo (skills may live in
  `.claude/skills/`, `.agents/skills/`, `skills/`, or bare top-level folders).
- **Destination** — *in place* (instrument where it stands) or *a new project* (e.g. migrating a
  non-compliantly-named repo to a `<tier>-<domain>` one). For a new project, settle how history is
  handled first: `git clone` preserves it (preferred — provenance, DESIGN §9 axis C); a bare copy
  doesn't. Leave the original untouched unless the user says otherwise.
- **Target phase** — almost always `adhoc`: migration makes skills *compliant*, not *proven*. A skill
  only reaches `publish` through an eval run (CONVENTIONS §7–8), which is a separate step.

### 2. Plan (read-only)
`python3 scripts/migrate-skill.py plan <source>` inventories the source: where skills live, which are
uninstrumented, name problems, missing evals/licenses, a `.gitignore` that would swallow the skills
home, whether an `.agents/skills` symlink is needed. Pair it with `review`'s linter for the full
finding list. The plan **changes nothing**.

### 3. Surface the judgment calls
From the plan, put the open decisions to the user before touching anything:
- **Tier** (`kb`/`ops`/`int`/`dx`/`core`/`meta`) — what the skills *are*; not guessable from layout.
- **Domain tokens** — only from the collection's canonical catalog. A domain that isn't in the
  catalog is *proposed to the catalog owner*, never invented (CONVENTIONS §5). Generic skills get no
  domain at all.
- **Renames** — names are API contracts; folder or repo renames happen only with explicit sign-off.
- **Repo/collection name** — if non-compliant (`<tier>-<domain>` rule), recommend the compliant name;
  whether and when to take the break is the owner's call.

### 4. Apply (mechanical)
`python3 scripts/migrate-skill.py apply <source> --dest <repo-root> --tier <tier>
[--phase adhoc] [--version 0.1.0] [--domain <skill>=<token> ...] [--license <SPDX>]`

It copies (or, in place, moves) each skill into the home (`.claude/skills/` by default), injects the
`metadata.skillroy` block into the frontmatter — *preserving the file's existing text exactly* —
patches a `.claude/`-swallowing `.gitignore` to the `.claude/*` + `!.claude/skills/` pattern, and adds
the `.agents/skills → ../.claude/skills` symlink for agents that read the `.agents` convention.
Already-instrumented skills are left untouched and reported (re-running apply is safe). The script
does **no** git operations — cloning, branching, committing stay with you/the user.

### 5. Evals — author or import (agent work, not script work)
Compliance needs `evals/evals.json` per skill (CONVENTIONS §8). Write behaviour tests from each
skill's documented workflow (happy path + key edges), or import existing ratified ones. The script
never fabricates evals.

### 6. Verify and report
Run `review` over the result (`lint-skill.py <home> --tokens <catalog>`), confirm the source is as
promised (untouched, or cleanly moved), and report: what moved, what was injected, the decisions the
user made, and what's still open (typically: run the evals to earn `publish`; the repo rename if
deferred). Stamp the migration commit message with what was done and why.

## What this skill refuses to do
- Pick a tier, mint a domain token, or rename a repo on its own.
- Set `phase: publish` as part of a migration — publish is earned by an eval run, not granted.
- Rewrite skill *content* (descriptions, workflows). That's authoring (`create`), not migration.
