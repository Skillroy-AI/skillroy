# skillroy conventions (v0.4 — 2026-06-10: external-resources manifest §11; collections §10; v0.3 run logs)

The house rules `create` scaffolds to and `review` lints against. **Rationale** (the *why*) lives in
`DESIGN.md`; this file is the *what*. The enforcement table (§9) ties each rule to the `lint-skill`
check that verifies it — keep the two in sync.

## 1. Format & layout
- A skill is a folder following the [Agent Skills](https://agentskills.io) open standard:
  `SKILL.md` (required) + optional `references/`, `scripts/`, `assets/`, `evals/`.
- **Home:** `.claude/skills/<name>/` (read by Claude Code *and* Cursor). The format is agent-neutral;
  only the discovery dir is `.claude/`-named.
- Frontmatter `name` **MUST equal the folder name**; kebab-case `[a-z0-9-]`, ≤ 64 chars, no
  leading/trailing or doubled hyphens.

## 2. Naming
- **Repo / collection name:** lowercase kebab-case `[a-z0-9-]`; pattern `<tier>-<domain>`; **no
  redundant suffix** (`-tools` / `-skills` / `-repo`) — the tier conveys that. (Brand-named products
  like `skillroy` are an allowed exception.)
- **Tier prefix:** `kb-` / `ops-` / `int-` / `dx-` / `core` (none) / `meta-` (`dx-` =
  developer-experience tooling & data-transformation utilities; skillroy itself = `meta`).
- **Skill name (inside a repo):** *action* → verb (`deploy`, `diagnose`); *knowledge* → noun
  (`xml-formats`). Don't repeat the repo/domain. Avoid reserved built-in command names (e.g. `/run`,
  `/verify`, `/loop`, `/review`, `/code-review`); a plugin namespace (`/skillroy:name`) resolves
  collisions. (skillroy's own `review` is a ratified exception, 2026-06-09: the verb is right, the
  description disambiguates for routing, and plugin distribution namespaces it.)
- Names are API contracts — a rename is breaking. The name encodes only `tier` + `domain`/identity;
  **no version numbers, status, owner, or environment in it** — those live in `metadata.skillroy`
  (e.g. `version`) or a tag.

## 3. Frontmatter
- Required by the standard: `name` (§1) and `description`. Optional standard fields: `license`,
  `compatibility` (environment requirements), `metadata` (§4). Claude Code adds optional extensions
  (`allowed-tools`, …); unknown keys are ignored safely (verified 2026-06-07).
- **`description`** — ≤ 1024 chars; write as **what it does + when to use it** (trigger phrases,
  including synonyms) so the agent auto-routes. The name is for humans; the description is for the agent.

## 4. `metadata.skillroy` block
The standard's `metadata` object is the spec-blessed home for tool-specific fields:
```yaml
metadata:
  skillroy:
    phase: brainstorming | adhoc | publish   # authoring maturity (§7)
    tier: kb | ops | int | dx | core | meta
    version: 0.1.0                            # skill version (semver) — version axis A
    domain: <canonical-token>                 # optional; from the collection's token catalog (§5)
    depends-on: [<skill-or-repo>]             # optional
```
A skill with **no** `metadata.skillroy` block is "not skillroy-instrumented" (a `warn`).

## 5. Canonical tokens
- Reference application/domain tokens from the **collection's vetted catalog** (YAML). Tokens are
  *primary keys*; legacy/human names are **aliases** that redirect to the canonical token.
- **Never invent or silently "fix" a token** — if it isn't in the catalog, surface it and ask.
- Keep *naming tokens* separate from *security tokens* (API keys, access tokens).
- Enforcement is phase-dependent: **SHOULD** in brainstorming/adhoc, **MUST** at publish.
- Base skillroy ships the *schema* (`tokens/catalog-schema.md`; validate with
  `tokens/validate-tokens.py`); the *catalog data* lives in the org overlay. `review` checks a skill's
  `metadata.skillroy.domain` against the catalog via `lint-skill --tokens <catalog>`; when `--tokens`
  is absent the linter falls back to the **`$SKILLROY_TOKENS`** env var (the catalog lookup ladder).

## 6. Two front doors
- **Chat door:** a trigger-rich description + clear `SKILL.md` instructions — a user invokes it
  conversationally, never needing to know a script exists.
- **CLI door:** deterministic/heavy work goes in standalone-runnable `scripts/` (terminal, CI, cron).
  **"Crunch once":** expensive derivation → a reusable artifact queried cheaply, provenance stamped in.
- At **publish**, a skill that *has* scripts MUST expose both doors; the body bridges them.

## 7. Phase bars (the bar rises by phase)
- **brainstorming** — structure only. The agent collaborates in *brainstorming style*: surface open
  questions, checkpoint, invite revision — don't drive to "done."
- **adhoc** (PoC) — SHOULD: compliant name, what+when description, canonical tokens, `metadata.skillroy`.
- **publish** — MUST: all of adhoc **+** canonical tokens **+** `license` **+** no plaintext secrets
  **+** both doors (if it has scripts) **+** evals present **and passing**, with a recorded run log
  (§8) **+** base-spec clean (`skills-ref validate`). Provenance-stamping of external deps is also
  required at publish but is **verified by hand** (not yet a `lint-skill` check).

## 8. Evals
Every skill ships behaviour tests at `evals/evals.json`:
```json
{ "skill_name": "<name>",
  "evals": [ { "id": 1,
               "prompt": "<a request that should invoke the skill>",
               "expected_output": "<prose: the expected behaviour>",
               "files": [],
               "expectations": ["<concrete, checkable assertion>", "..."] } ] }
```
**How they're run/verified (the process):** an agent runs the skill against each `prompt` (with any
`files`), then checks each `expectations` assertion against the actual behaviour/output, recording
pass/fail per assertion. A skill **passes** when every expectation holds for every eval. Cover the
happy path plus the important edges (elicitation when under-specified, graceful degradation, refusing
to fabricate). `review`'s `run-evals.py` validates the `evals.json` and lists the cases for the run;
the pass/fail judgement is the agent's. **At publish, evals must exist *and* pass.**

**Interactive steps are simulated.** When a skill's workflow pauses for the user (elicitation,
confirm-before-fetch, "how should I proceed?"), the eval driver plays the user's role and notes the
simulated replies in the run log. This is the documented norm for autonomous runs: an expectation
like "asks the user for X" is judged against the skill's actual output at that pause point.

**Run logs (the evidence).** Every verification run is recorded at
`<skill>/evals/runs/<YYYY-MM-DD>[-<n>].md` so "evals pass" is auditable, not asserted:

```markdown
# Eval run — <skill> v<version> (<phase at time of run>)
- **Date / runner:** <YYYY-MM-DD> / <model or person>
- **Inputs:** <token catalog, fixtures, simulated-user notes — or "none">
- **Result:** PASS (N/N evals, M/M expectations) | FAIL (...)

## Eval <id> — <one-line intent>
- [x] <expectation> — <one line of evidence>
- [ ] <expectation> — <what failed>
```

Scaffold one with `run-evals.py --log <skill>` and fill in the verdicts as you judge. A log
reconstructed after the fact (e.g. from a retro entry) must say "reconstructed" in its header. At
publish, the latest run log must be all-pass for the skill's current behaviour — re-run after
changes that could affect it (version axis A is the tell).

## 9. Enforcement — `lint-skill` checks (keep this in sync with the rules above)
`review` pairs `lint-skill` (the house rules below) with the official **`skills-ref validate`** (base
Agent-Skills conformance — run it separately if installed). Severity scales by phase: a SHOULD is
`info` at brainstorming, `warn` at adhoc, `error` at publish.

| Rule (§) | `lint-skill` code | Severity |
|----------|-------------------|----------|
| frontmatter is valid YAML | `frontmatter` | error |
| `name` kebab + ≤ 64 + == folder (§1) | `name` | error |
| `description` present (§3) | `description` | by phase |
| `metadata.skillroy` present (§4) | `metadata` | warn (not instrumented) |
| `phase` / `tier` value valid (§2, §4) | `phase` / `tier` | error |
| both doors when `scripts/` present (§6) | `two-doors` | by phase |
| no plaintext secrets | `secret` | error |
| evals present (§8) | `evals` | info → error at publish |
| eval run recorded in `evals/runs/` (§8) | `evals-run` | warn at publish |
| `license` present (§3, §7) | `license` | info → error at publish |
| `domain` in token catalog (§5; with `--tokens`) | `token` | by phase |
| repo/collection name kebab + no redundant suffix (§2) | `collection-name` | info |
| `resources.yaml` well-formed if present (§11) | `resources` | error |
| references external resources but no manifest (§11; non-meta) | `resources` | info → warn at publish |

Run: `python3 .claude/skills/review/scripts/lint-skill.py <skill-or-collection> [--tokens <catalog>]`.
Lint output is **provenance-stamped** (skillroy version / commit + token-catalog digest in `--json`;
a footer line in text mode) so a report can be traced to the rules and catalog that produced it.

## 10. Collections & overlays
- A **collection** is a repo of skills under the home dir (§1). Scaffold a new one with `create`'s
  `scripts/new-collection.py` (`--with-skill` adds the first skill; git init is a follow-up — the
  scripts are git-free). New collections start `status: experimental`; promote to `active` once
  there's real, linted content. Its README carries a **collection metadata block** — volatile facts
  live here, never in the repo name (§2):

  ```yaml
  collection:
    name: <repo-name>            # = the repo name, <tier>-<domain> or brand
    status: active | experimental | deprecated
    owner: <team or person>
    license: <SPDX or PROPRIETARY>
    depends-on: []               # e.g. [skillroy] for an overlay
  ```

- An **overlay** (e.g. `<org>-skillroy`) is a collection with `depends-on: [skillroy]` that supplies
  policy + data: the canonical-token catalog (§5), org evals, and any house-rule overrides. Base
  skillroy stays vendor-neutral; anything org-specific belongs in the overlay.
- **Watch for `.gitignore` swallowing the home dir.** Existing repos often ignore `.claude/`
  wholesale; the skills home then needs the `.claude/*` + `!.claude/skills/` re-include pattern.
- Agents that read the `.agents/skills/` convention get a symlink: `.agents/skills → ../.claude/skills`
  (requires `core.symlinks` on Windows checkouts).

## 11. External resources
- A collection declares the **external resources** its skills depend on (IaC repos, Confluence
  snapshots, large product references, binary artifacts, live environments, MCP connectors) in **one
  `resources.yaml` at the collection root** — collection-wide by default, with per-skill extensions
  in the same file. Schema + a worked example: `resources/resources-schema.md` +
  `resources/example-resources.yaml`.
- **Locate via an override ladder, fetch on offer — never auto-pull.** A resource resolves
  `--flag → $env → local_default`; if absent, the skill **reports it and offers the `fetch`
  command** (same shape as the `--tokens` / `$SKILLROY_TOKENS` catalog ladder, and DESIGN §9's
  detect-and-surface rule).
- **Match the handling to the type, not just the size:** bundle `confluence-snapshot`s (small) — and
  treat the bundled file as a **research seed document** (`<topic>-seed.md`, validated by
  `validate-seed.py`), with the live page as its source for refresh; **never** bundle a
  `product-ref` corpus (point at it + version-pin + index it); `artifact`s (incl. product zips in a
  Bitbucket **Downloads** area) are fetched per-use and **provenance-stamped** with the version used;
  `live-env`/`mcp` are documented requirements, not shipped files; secrets are always a reference to
  a secret manager, never stored.
- **Validate** a manifest with `resources/validate-resources.py <resources.yaml>` (the CLI door:
  type-specific checks + a plaintext-secret scan; `--self-test`). `review`/`lint-skill` adds two house
  checks: a present `resources.yaml` must be well-formed (`error` if not), and a **non-meta** skill
  that references a clone/URL/artifact while its collection has **no** manifest is nudged
  (`info` → `warn` at publish) to declare one. (Meta skills are exempt — their clone/path mentions are
  instructional, not dependencies.)
