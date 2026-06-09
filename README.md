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

## Quickstart — CLI

The scripts are plain stdlib Python: run them **from anywhere** by giving the path to the script.
What your current directory *does* affect is where output lands — `new-skill.py` creates the skill
folder at `<--dir>/<name>/`, and `--dir` defaults to `.claude/skills` **relative to where you run
it**. Pass an absolute `--dir` (or `--dest` for migrate) to be explicit:

```bash
SKILLROY=~/Projects/skillroy/.claude/skills

# start a whole new collection (repo) + its first skill in one shot
#   -> creates ~/Projects/dx-widgets/ (README metadata block, .claude/skills/ home,
#      safe .gitignore, .agents symlink); git init is the printed next step
python3 $SKILLROY/create/scripts/new-collection.py dx-widgets --dir ~/Projects \
    --with-skill reshape --owner "You" --license Apache-2.0

# or: author a new skill into an existing collection -> creates <--dir>/my-skill/
python3 $SKILLROY/create/scripts/new-skill.py my-skill --tier dx --kind action \
    --dir ~/Projects/my-app/.claude/skills

# lint one skill or a whole collection (--tokens <catalog> once you have an overlay)
python3 $SKILLROY/review/scripts/lint-skill.py ~/Projects/my-app/.claude/skills

# validate a skill's evals; --log scaffolds the eval-run record (CONVENTIONS §8)
python3 $SKILLROY/review/scripts/run-evals.py ~/Projects/my-app/.claude/skills/my-skill --log

# bring an existing repo's skills to compliance (plan is read-only; apply is idempotent)
python3 $SKILLROY/migrate/scripts/migrate-skill.py plan  ~/Projects/old-repo
python3 $SKILLROY/migrate/scripts/migrate-skill.py apply ~/Projects/old-repo \
    --dest ~/Projects/old-repo --tier dx
```

Every script takes `--help` and `--self-test`.

## Quickstart — Assisted (AI agent)

Make the skills visible to your agent, then just ask — the frontmatter descriptions route the
request, and the agent drives the same scripts underneath (the two-front-doors principle):

- **In this repo:** Claude Code and Cursor discover `.claude/skills/` automatically — just open it.
- **Everywhere (user-wide):** copy the skill folders into `~/.claude/skills/` (symlinks to a clone
  work in practice but aren't documented behaviour), or — the supported route — install skillroy as
  a **plugin**, which also namespaces the skills (`/skillroy:create`).

| Say | Skill that answers |
|-----|--------------------|
| "Research X into a seed doc — here are my sources." | `research` |
| "Create a new skill from this seed doc — in this repo or a brand-new project." | `create` |
| "Review my skills — is X ready to publish?" | `review` |
| "Migrate this repo's skills to skillroy compliance." | `migrate` |

Assisted mode adds what the scripts deliberately *don't* do: gathering sources, authoring
descriptions/workflows/evals, judging eval runs, and surfacing the judgment calls (tier, domain
tokens, renames) for you to decide.

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
