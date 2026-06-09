# skillroy

skillroy is a *meta-skill*: a convention set plus reusable tooling for **authoring, reviewing,
researching, and migrating Agent Skills** (the [`SKILL.md`](https://agentskills.io) kind). Its goal
is that skills come out consistent, high-quality, and reusable by others — a shared house style for
naming, a canonical-token framework, a skill lifecycle ("phases"), behaviour evals with auditable
run logs, and scaffolding/linting that operationalizes all of it.

## The skills

All four live in `.claude/skills/` (read by Claude Code *and* Cursor; the format is the open Agent
Skills standard) and are at phase `publish` — each passed its lint bar, the official
`skills-ref validate`, and a recorded eval run. Every skill has **two front doors**: invoke it
conversationally, or run its script standalone (terminal / CI — stdlib-only, each with `--self-test`).

| Skill | What it does | CLI door |
|-------|--------------|----------|
| `research` | Gathers cited sources into a provenance-tracked *seed document* that authoring consumes; extensible via source adapters | `scripts/validate-seed.py` |
| `create` | Authors a new compliant skill (naming, `metadata.skillroy`, phase bar, evals scaffold) | `scripts/new-skill.py` |
| `review` | Lints a skill or collection against the conventions + token catalog; severity scales by phase | `scripts/lint-skill.py`, `scripts/run-evals.py` |
| `migrate` | Brings existing skills to compliance — in place or into a new project; mechanical changes scripted, judgment calls surfaced | `scripts/migrate-skill.py` |

The enforceable rules live in [`CONVENTIONS.md`](./CONVENTIONS.md) (each rule mapped to its lint
check); the *why* and full history live in [`DESIGN.md`](./DESIGN.md).

## Mechanism vs. policy

- **skillroy** ships the *mechanism* — generic, vendor-neutral: tier taxonomy, the canonical-token
  *schema* (`tokens/` — not the tokens), the phase model (`brainstorming → adhoc → publish`), and
  the scripts.
- An organisation *inherits* skillroy via an **overlay** (`<org>-skillroy`, declared with
  `depends-on: [skillroy]`) that supplies its *policy and data*: the actual token catalog, house
  bindings, org evals. The linter is parameterized by the catalog:
  `lint-skill.py <skills> --tokens <overlay>/tokens/canonical-tokens.yaml`.

## Quickstart

```bash
# author a new skill
python3 .claude/skills/create/scripts/new-skill.py my-skill --tier dx --kind action

# lint it (add --tokens <catalog> when you have an overlay)
python3 .claude/skills/review/scripts/lint-skill.py .claude/skills

# migrate existing skills to compliance (plan first — read-only)
python3 .claude/skills/migrate/scripts/migrate-skill.py plan <your-repo>
```

## License

Copyright 2026 Mike Mills <mike.mills@skillroy.ai>

Licensed under the Apache License, Version 2.0. See [`LICENSE`](./LICENSE).

## Collection metadata

```yaml
collection:
  name: skillroy            # brand-named — an allowed exception to <tier>-<domain>
  status: active
  owner: Mike Mills <mike.mills@skillroy.ai>
  license: Apache-2.0
  depends-on: []
```
