# skillroy — Design (living document)

**Status:** publish-ready (conventions v0.3; all four skills at `phase: publish`). The whiteboard
history below is preserved; the retro cadence continues.
**Owner:** Mike Mills <mike.mills@skillroy.ai>
**Started:** 2026-06-06

> Started as a whiteboard, deliberately not rushed (§8). Open questions are tracked in §10;
> decisions and changes are logged in §11 (Retro log) — the retro log is the source of truth.

## Status — resume here (2026-06-09, session 3)

skillroy (this repo) is **vendor-neutral, Apache-2.0**; org-specific data (tokens, overrides) lives
in a separate `<org>-skillroy` overlay. Layout home = `.claude/skills/`. Authoritative rules =
`CONVENTIONS.md` (v0.3: rule→check→severity table, eval **run-log** convention,
simulated-interactive norm, collections/overlays §10).

**Built & green — all FOUR skills at `phase: publish`** (full bar each: lint clean at publish, evals
pass with a recorded run log in `evals/runs/`, official `skills-ref validate` Valid):
- **`research`** (v0.2.0, second door `validate-seed.py`), **`create`**, **`review`** (v0.2.0; name
  kept per the ratified §2 exception), **`migrate`** (new this session — mechanical migration
  scripted via `migrate-skill.py` plan/apply; judgment calls are inputs, publish refused by design).
- Scripts (stdlib, all `--self-test`): `new-skill`, `lint-skill` (+ provenance-stamped output,
  `evals-run` check), `run-evals` (+ `--log` run-log scaffolder), `validate-seed`, `validate-tokens`,
  `migrate-skill`.
- `tokens/` (schema + validator + generic example); README rewritten for publication (quickstart,
  collection metadata block).

**Proven downstream (org side, repos local-only until pushed):** the overlay
(`<org>-skillroy`: catalog 27 tokens, org conventions, research source-adapter extension) and the
first migrated consumer collection — both git-initialized with clean trees.

**Pending / next steps:**
1. Owner test runs: `research` + `create` a brand-new skill end-to-end; `migrate` the remaining
   sibling collections into the org hub's `collections/` (the deployment/monorepo structure was
   settled 2026-06-09 — see retro).
2. **skillroy is live: github.com/Skillroy-AI/skillroy** (pushed 2026-06-09; authors rewritten to
   the skillroy.ai identity pre-push; marketplace slug updated in the org hub). Remaining: hub +
   migrated repo → Bitbucket; run the hub README's plugin test checklist.
3. Deferred ideas: `explain` skill (CONVENTIONS+README currently serve this); overlay *install*
   tooling (adapter files are copied by hand today); `skills-ref` as a native dependency once a
   Linux-side node exists; Cursor user-level skills support (unverified) for the meta-skills.

(Org-specific in-flight work — e.g. an overlay instrumentation dry-run pending review — is tracked in
the session memory, not in this vendor-neutral doc.)

**Working agreement:** brainstorming = don't rush; checkpoint + periodic retros (memory:
`brainstorming-no-rush`).

## 1. What skillroy is

skillroy is a *meta-skill*: conventions + reusable tooling for **authoring, reviewing, explaining,
and migrating Agent Skills** (the `SKILL.md` kind). The goal is skills that are consistent,
high-quality, and reusable by others. skillroy is **agent-neutral** where possible (it leans on the
open Agent Skills `SKILL.md` format and notes Claude Code specifics only where they apply).

## 1.1 Guiding principles

*(This section will accrue more principles as we go; related cross-cutting items also live in §9.)*

- **Two front doors — ease-of-use *and* token economy.** Every skill should serve two audiences at
  once:
  - **Chat-interface users (ease of use):** rich frontmatter **triggers** + clear instructions let a
    less-experienced user invoke the capability conversationally, never needing to know a script
    exists.
  - **Advanced users (token economy):** the bundled **scripts are runnable standalone** — from a
    terminal, CI, or cron, outside any AI session — so heavy work doesn't burn chat tokens and is
    automatable.

  The skill body is the bridge: it tells the agent *which* script to run and how to read the result,
  so the chat path and the CLI path stay in sync.
- **"Crunch once."** Expensive parsing/derivation happens **once** in a script that emits a reusable
  artifact (an index / registry / dossier), then queried cheaply many times — rather than
  re-deriving from raw sources on every use. The crunch scripts are themselves standalone (above),
  and the artifact records its provenance (§9, axis C).

*(Lint implication: at `publish`, a skill that has scripts should expose both paths — frontmatter
triggers for the chat path and standalone-runnable scripts for the CLI path. See §5.)*

## 2. Core architecture — mechanism vs. policy

- **skillroy = mechanism** (generic, Apache-2.0): tier taxonomy, canonical-token *schema*, phase
  model, templates, and linter/scaffolder scripts. It knows tokens are *required*; it does not know
  what they are.
- **`<org>-skillroy` = policy + data**: supplies the actual canonical-token catalog and any house
  overrides. The linter/scaffolder are *parameterized* by the
  consumer's catalog + overrides.

This split is what makes skillroy reusable: the same framework serves any org; only the overlay
differs.

## 3. Tiers / prefixes

Generic tier taxonomy (org-specific bindings move to the overlay):

| Tier | Prefix | Holds |
|------|--------|-------|
| Knowledge | `kb-` | Reference knowledge about a domain / app / platform |
| Operational | `ops-` | Operate *your own* systems (diagnose, run, inspect) |
| Integration | `int-` | Act against *external* services / the cloud boundary |
| Core | *(none)* | Foundational cross-cutting bundles (rare) |

Proposed additions (kept deliberately small — predictability is the point):

- **`meta-`** — skills that act on *skills / agents themselves*. skillroy is the archetype.
  **Adopted 2026-06-06:** skillroy declares `tier: meta` in its metadata block. (The repo keeps the
  brand name `skillroy`; the `meta-<domain>` prefix applies to systematic skill repos and to the
  skills authored inside — brand-named products are an allowed exception. Confirm on review.)
- **`dx-`** — developer-experience tooling & data-transformation utilities. **Un-reserved 2026-06-09**
  (active tier; e.g. Tlog-Tools' `xslt` / `tlog-to-xml` will use it).

Inherited rules (from the repo-conventions research): lowercase kebab-case, ≤ 50 chars, no redundant
words (`-skills` / `-repo` / `<org>-`); the name encodes only `tier` + `domain` (stable identity).
Volatile facts (owner / status / deps / version) live in a README metadata block, **not** the name.
Names are API contracts; a rename is a breaking change.

## 4. Canonical-token framework

skillroy prescribes (but does not populate):

- A skillroy-compliant **collection** maintains exactly one **vetted token catalog** (collection-
  level, in the overlay). Individual skills **reference** tokens from it; they never mint their own.
- **Catalog schema** (skillroy owns): `name`, `token`, `aliases[]`, `domain`, `status`
  (`confirmed | proposed | legacy`), `sources[]`. Machine-readable **YAML** (decided 2026-06-07).
  **Implemented 2026-06-09:** `tokens/catalog-schema.md` + `tokens/validate-tokens.py` (base); the
  catalog *data* lives in the overlay.
- **Behavioral rules** for compliant skills:
  - Tokens are *primary keys*. Prefer the canonical token everywhere.
  - Legacy / human names appear only as **aliases** that redirect to the canonical token.
  - **Never invent or silently "fix" a token** — surface the ambiguity and ask.
  - Keep *naming tokens* strictly separate from *security tokens* (API keys, access tokens).
- **Enforcement is phase-dependent** (§5): SHOULD in brainstorming/adhoc, **MUST at publish**.

## 5. Phase model (authoring lifecycle)

Every skillroy-managed skill carries a **phase**: `brainstorming → adhoc → publish`.

| Phase | Meaning | Lint bar |
|-------|---------|----------|
| brainstorming | exploring what the skill should be | minimal; structure only |
| adhoc (PoC) | works for me / now; not generalized | SHOULD: naming, tokens, description quality |
| publish | vetted, reusable by others | MUST: naming, canonical tokens, license, provenance-stamped external deps, no plaintext secrets, description = what + when |

Two non-obvious properties:

1. **The bar rises by phase** — e.g. hardcoded `~/Projects/...` paths are fine in adhoc, a blocker
   at publish.
2. **The phase governs how the *assistant collaborates*.** A skill in `brainstorming` instructs the
   agent to checkpoint, surface open questions, and invite revision — not drive to done. (This
   encodes the project's working agreement; see §11.)

Distinct from the conventions' `status: active | experimental | deprecated` (operational state).
Phase = authoring maturity. *(open: where does the phase value live — frontmatter, README block,
STATUS file? §10)*

## 6. What skillroy ships (all four meta-skills landed; `explain` deliberately not built)

- **Meta-skills** (`meta-` tier) — skillroy is a **multi-skill repo** (confirmed 2026-06-07): scaffold
  a new compliant skill; review/lint an existing one; explain the conventions; migrate a
  non-compliant skill toward compliance.
  - **`research`** — *landed 2026-06-07* (imported from a PoC, scrubbed of org-specific terms; phase `adhoc`).
    Gathers cited sources into a provenance-tracked *seed document* that skill authoring consumes;
    extensible via pluggable **source adapters**. At `.claude/skills/research/` (the chosen home —
    read by Claude Code + Cursor).
    First real meta- skill and first to ship evals. Chat-first (its one natural CLI "second door"
    would be a seed-doc validator — deferred to publish, see §10).
  - **`create`** — *landed 2026-06-07; collection capability 2026-06-09*. Authors a compliant skill
    (chat door = the `SKILL.md` workflow; CLI doors = `scripts/new-skill.py` +
    `scripts/new-collection.py`). Workflow step 0 locates **or creates** the collection: one skill,
    two scripts (ratified over a split `create-collection` skill — the user's intent is "a skill",
    the collection is routing; and over an `init` name — `/init` is a reserved built-in).
    `new-collection.py` scaffolds the §10 shell (README metadata block at `status: experimental`,
    home, safe gitignore, `.agents` symlink; `--with-skill` adds the first skill, inheriting the
    collection tier; `--brand` is the explicit naming escape; git-free — init is a printed
    next-step). Enforces naming, the `metadata.skillroy` block, and the phase bar; consumes a
    `research` seed doc; ships evals (6).
  - **`review`** — *landed 2026-06-07*. Lints a skill/collection (chat door) via
    `scripts/lint-skill.py` (CLI door): frontmatter validity, `name==folder`, naming/tier,
    `metadata.skillroy`, two-doors, secrets, and the phase bar; severities scale by phase. Wraps the
    official `skills-ref validate` when present.
  - **`migrate`** — *landed 2026-06-09*. Brings existing skills to compliance, in place or into a
    new project (chat door = guided workflow; CLI door = `scripts/migrate-skill.py` `plan`/`apply`).
    Mechanical changes are scripted (layout move, `metadata.skillroy` injection byte-preserving the
    rest, `.gitignore` re-include patch, `.agents/skills` symlink); judgment calls (tier, domain
    tokens, renames) are *inputs* — the script refuses to guess, and refuses `--phase publish`
    (publish is earned by an eval run). First real use: the Tlog-Tools → `dx-tlog` migration.
- **Shared assets**: conventions docs; templates (SKILL.md, README metadata block, dependency
  manifest); the index + lookup scaffold (the proven house pattern from the sibling skills).
- **Scripts** (the centerpiece — they operationalize the prose): `lint-skill` + `run-evals` (in
  `review`), `new-skill` (in `create`), and `validate-tokens` (in `tokens/`) — **all landed**.
- **`tokens/`** (base): `catalog-schema.md` (the YAML catalog schema), `example-catalog.yaml`
  (generic), `validate-tokens.py`. The catalog *data* is an overlay artifact.

## 7. Inheritance mechanism

The overlay declares `depends-on: [skillroy]` (the dependency-manifest / overlay model). skillroy
resolves: base rules from skillroy + token catalog & overrides from the overlay. Provenance (which
skillroy version + which catalog commit) is stamped into any generated or linted output.

## 8. How we work on skillroy itself

skillroy's own phase is **brainstorming**. Per the working agreement we checkpoint and run retros
rather than racing to "done." Proposed cadence: a brief retro at each phase boundary and whenever an
item in §10 resolves — the prompt is always "does looking back change anything?"

## 9. Carried from the prior brainstorm (versioning & neutrality)

- Three version axes to keep distinct: **A** skill version (semver + changelog), **B** index schema
  version, **C** upstream-content provenance (the SHAs an answer reflects). Prioritize C, then B, then A.
- Keep tools as plain, path-invocable CLIs (stdlib-only house rule) for portability across agents.
- External deps: declare in a manifest, locate via override ladder, *detect-and-surface* staleness
  rather than auto-pull; stamp provenance into generated artifacts.
- **Adopt the Agent Skills open standard** ([agentskills.io](https://agentskills.io), open since
  2025-12-18; validator `skills-ref validate`) — confirmed by Step 0 (2026-06-07). Per-skill folder
  = `SKILL.md` (+ optional `scripts/`, `references/`, `assets/`); required frontmatter `name` (≤64,
  `[a-z0-9-]`, **must equal the folder name**) + `description` (≤1024); optional `license`,
  `compatibility`, and a **`metadata` object that is the spec-blessed home for tool-specific keys** →
  `metadata.skillroy.{phase,tier,version}` is standard, not a hack.
- **Reuse, don't reinvent base validation:** `review`/lint should wrap `skills-ref validate` (base
  spec) and layer the house rules (tier, canonical tokens, phase, two-front-doors) on top.
- **Discovery is via dotted dirs, not a bare `skills/`.** **Verified 2026-06-07** against the
  official "Where skills live" docs: Claude Code discovers skills only in `.claude/skills/`,
  `~/.claude/skills/`, plugins, and `.claude/skills/` under `--add-dir` — **`.agents/` is not
  supported by Claude Code** (it's an `.agents/skills/` convention honored by Codex/Cursor/OpenCode/
  Gemini, not CC). Cursor reads `.cursor/skills/`, `.agents/skills/`, **and `.claude/skills/`**.
  **Corollary for a Claude-Code-+-Cursor stack: `.claude/skills/` is the one dir both read;**
  `.agents/` would miss Claude Code. No single dotted dir is read by every tool → see §10. `SKILL.md`
  skills (incl. bundled scripts) port to Cursor/Codex essentially as-is.
- **`AGENTS.md`** (Linux-Foundation Agentic AI Foundation) is the complementary always-on
  project-context standard, broadly honored — optional companion for the monorepo. (Claude Code's
  AGENTS.md support is version-uncertain; use the CLAUDE.md-symlink trick if needed.)

## 10. Open questions / decisions pending

- [ ] Canonical-token enforcement: phase-dependent *(rec)* vs always-MUST vs always-SHOULD.
  Answer:  phase-dependent - brainstorming/poc = SHOULD, publish = MUST
- [x] skillroy's own tier: **`meta-`** (decided 2026-06-06). `dx-` stays reserved.
- [ ] skillroy shape: multi-skill repo (separate author / review / explain) vs single skill w/ modes.
  Answer: multi-skill repo
- [ ] Where the **phase** value lives (frontmatter vs README block vs STATUS file)
- [ ] Token-catalog format: YAML vs JSON.
  Answer:  YAML
- [ ] Does `phase` govern AI working-style *(rec)* or is it just metadata?
  Answer:  Phase should influence AI working style as you describe above, i.e., branstorming is the time to surface open questions, revisit decisions, etc.
- [ ] <org>-skillroy license (proprietary / internal vs other).
  Answer:  <org>-skillroy will be proprietary/internal only
- [ ] **Skill layout**: `.claude/skills/<skill>/` (used now — matches existing projects, loadable in
  Claude Code) vs the conventions-doc §10 top-level `<skill>/` layout (more agent-neutral). Reconcile
  when designing the monorepo. *(dogfooding tension surfaced by the research import.)*
  Answer:  Please use agent-neutral format where possible.  I'm open to the possibility of including agent-neutral and agent-specific conventions, if it provides a tangible benefit, so please surface if a situation like that arises.  For example, our company has widely deployed Cursor, and so if there is a Cursor-specific skill feature that might make it easier to use or install, I would want to know about that. 
- [ ] **Evals convention**: where eval files live + format (now `<skill>/evals/evals.json`). Make
  shipping evals a publish-bar item?
  Answer:  Let's assume evals should be a publish-bar item; we can revisit during development of actual skills to see how it goes.
- [ ] **Authoring-skill name** referenced by `research` ("skill-creator"): rename to a verb
  (`create` / `author`) to fit our own rules, or keep the Anthropic-style name?
  Answer:  Go with Anthropic conventions and your best judgment, ask me if a decision needs to be made.  The "research" skill was developed in a separate chat without this context.
- [x] **`research` second door** (optional): a standalone seed-doc *validator* script (template +
  provenance conformance) — the natural CLI companion, reusable by the linter. Defer to publish?
  Answer: Okay to defer until publish. — **Built at publish (2026-06-09):**
  `research/scripts/validate-seed.py` (structure + tag↔source traceability; stdlib, `--self-test`).
- [x] **`review` skill name vs reserved `/review`** — CONVENTIONS §2 lists `/review` among reserved
  built-in command names; skillroy's own skill is named `review` (the rule postdates the skill —
  surfaced during its publish run). Options: (a) keep, relying on the §2 plugin-namespace resolution
  (`/skillroy:review`) + a documented exception; (b) rename pre-publish while it's still free
  (`lint`? `audit`?); (c) soften the §2 rule.
  Answer: **(a) keep** (ratified 2026-06-09); exception documented in CONVENTIONS §2; `review` →
  `phase: publish`, v0.2.0.
- [x] **Canonical layout & install** → **(B) `.claude/skills/<name>/` as the home** (decided
  2026-06-07): zero tooling, read by both Claude Code and Cursor; the *format* stays the neutral
  Agent Skills standard, only the dir is `.claude/`-named; Codex/others (if added) get a
  `.agents/skills → .claude/skills` symlink. `create` writes here. — Context (Step 0, after verifying Claude Code
  does *not* read `.agents/`): **(A)** neutral `skills/<name>/` source + a symlink/`install` into the
  discovery dir(s) (for this stack: `.claude/skills/ → skills/`, which serves both Claude Code and
  Cursor) — *rec*; vs **(B)** use `.claude/skills/<name>/` directly as the home (read by **both**
  Claude Code and Cursor, zero tooling; downside: non-neutral, Anthropic-branded path).
  `.agents/skills/`-as-home is **dispreferred** — it misses Claude Code. Decides where `create`
  writes and the monorepo shape.
- [x] **Shared vs. bundled conventions** → **hoisted to repo-root `CONVENTIONS.md`** (decided
  2026-06-09): single source of truth; `create` and `review` reference it by name (no cross-skill
  path). Trade-off: a skill distributed *standalone* would need `CONVENTIONS.md` copied in — a
  non-issue for the co-located suite / whole-repo plugin.

## 11. Retro log

- **2026-06-06 — kickoff.** Established the mechanism/policy split (skillroy vs <org>-skillroy), the
  three-phase lifecycle, and the working agreement (brainstorming = don't rush; periodic retros).
  Anchor created: README, DESIGN, LICENSE, <org>-skillroy stub. Nothing "finished" on purpose.
- **2026-06-06 — decision.** skillroy's own tier = **`meta-`** (a new tier for skills that act on
  skills/agents); `dx-` reserved. Revisitable like everything else.
- **2026-06-06 — principle added (§1.1).** "Two front doors": skills serve chat users (frontmatter
  triggers, ease-of-use) *and* advanced users (standalone-runnable scripts, token economy); plus
  "crunch once." Contributed by Mike during review.
- **2026-06-07 — research skill imported (first meta- skill).** Brought a PoC `research` skill into
  `.claude/skills/research/` (SKILL.md + references + genericized evals). SKILL.md and references
  were already generic; the original evals were org-specific, so they were rewritten vendor-neutral
  (test intents preserved) and verified clean via a word-boundary grep gate. Originals left in
  `~/Projects/brainstorming/tmp-docs/`. The org-specific evals + a real Confluence/Atlassian-MCP
  source adapter belong in `<org>-skillroy`. Surfaced four new open items in §10.
- **2026-06-07 — §10 answers ratified + layout move.** Mike answered the open questions:
  enforcement phase-dependent (SHOULD→MUST); skillroy is a multi-skill repo; token catalog = YAML;
  phase governs AI working-style; <org>-skillroy proprietary/internal; **prefer agent-neutral
  layout** (open to per-agent adapters where beneficial, e.g. Cursor); evals = publish-bar item;
  research's seed-doc validator deferred to publish; authoring-skill name left to judgment.
  Actions: moved `research` from `.claude/skills/` → agent-neutral `skills/research/`; parked the
  original org-specific research evals in `<org>-skillroy/skills/research/evals/`. Still open:
  where the phase value lives (needed for the `create` skill).
- **2026-06-07 — Step 0 verification + decisions.** Two checks: Claude Code discovery/frontmatter
  (guide agent) + Cursor & the cross-agent standard (web). Findings (§9): the **Agent Skills open
  standard** (agentskills.io) is real and multi-vendor (Claude Code, Cursor, Codex, Copilot…);
  `metadata` is the spec-blessed home for custom keys; discovery is via dotted dirs (no universal
  one); `skills-ref validate` exists to reuse; `AGENTS.md` is complementary. **Decisions ratified:**
  skill names are **verbs** (creation skill = `create`); **phase → `metadata.skillroy.phase`**
  (spec-validated). New open item: canonical layout & install (§10) — pending a pick before `create`.
- **2026-06-07 — verification correction (layout).** Mike flagged a side-source claiming Claude Code
  reads `.agents/skills/`. Checked the official "Where skills live" docs (fetched live): CC discovers
  skills only in `.claude/skills/`, `~/.claude/skills/`, plugins, and `--add-dir` `.claude/skills/` —
  **no `.agents/` support documented**. The `.agents/` "universal" claim is secondary-source and
  applies to Codex/Cursor/OpenCode/Gemini, not CC. Corollary: `.claude/skills/` is read by **both**
  CC and Cursor. §10 layout options refined to A (neutral `skills/` + symlink/install) vs B
  (`.claude/skills/` home); `.agents/`-as-home dropped.
- **2026-06-07 — layout decided (B) + `create` build started.** Canonical home =
  `.claude/skills/<name>/` (read by Claude Code + Cursor; zero tooling). Moved `research` back to
  `.claude/skills/research/`. Began the `create` meta-skill: wrote `references/skillroy-conventions.md`
  (v0 distilled rules + `metadata.skillroy` schema + phase bars) and `create/SKILL.md` (authoring
  workflow; phase `adhoc`). Next slice: the `new-skill` scaffolder script + `create`'s evals, then
  dogfood on `research`.
- **2026-06-07 — `create` slice complete + dogfooded.** Built `scripts/new-skill.py` (stdlib,
  `--self-test`) — the CLI "second door" — and `create`'s evals (happy-path, elicitation,
  non-compliant-name, token-not-in-catalog). Dogfooding caught and fixed two real YAML-frontmatter
  bugs (unquoted descriptions with colons): the scaffolder now quotes descriptions, and `research`'s
  imported description was repaired (its stale `skill-creator` reference retired to `create`). A
  repo-wide gate now confirms every `SKILL.md` parses and `name == folder`. Also scrubbed all
  org-specific terms from DESIGN.md (→ `<org>`); base skillroy is fully vendor-neutral. Next: the `review` skill
  (wrap `skills-ref validate` + the house rules) and the token-catalog schema.
- **2026-06-07 — `review` landed + dogfooded.** Built `review` (chat door) + `scripts/lint-skill.py`
  (CLI door; stdlib + PyYAML-if-present; `--self-test`, `--json`): checks frontmatter validity,
  `name==folder`, naming/tier, `metadata.skillroy`, two-doors, secrets, and the phase bar (severities
  scale by phase). Linting skillroy's own collection found `create`/`review` clean and flagged that
  imported `research` lacked a `metadata.skillroy` block — now fixed (phase/tier/version + license).
  Surfaced the shared-vs-bundled-conventions open item (§10). Next: token-catalog schema (YAML);
  optionally `explain`/`migrate`; then point skillroy at the existing skills.
- **2026-06-09 — Tlog-Tools review + convention/linter updates.** Ran `review` over Tlog-Tools
  (`.agents/skills/`): 3 skills, no errors — well-formed but un-instrumented (no `metadata.skillroy`,
  no evals). Acting on findings: **un-reserved the `dx-` tier** (tooling/utilities — Tlog-Tools'
  destination); `lint-skill` now flags an un-instrumented skill at **`warn`** ("not
  skillroy-instrumented") and adds an `info` when a **collection name isn't kebab-case** (e.g.
  `Tlog-Tools`). Instrumenting Tlog-Tools (tier `dx`, tokens) is overlay work, deferred.
- **2026-06-09 — token machinery landed.** Base ships `tokens/` — `catalog-schema.md` (YAML catalog
  schema), `example-catalog.yaml` (generic), `validate-tokens.py` (YAML via PyYAML or JSON via
  stdlib; `--self-test`). The overlay got a starter `tokens/canonical-tokens.yaml`: 26 seeded tokens
  (its app/domain tokens — see the overlay catalog)
  with status/aliases/sources, from the research, flagged for SME validation. Example + overlay
  catalogs both validate clean against the base schema; base `tokens/` carries no org-specific tokens. **Next (not
  wired yet):** have `lint-skill` check `metadata.skillroy.domain` against a supplied catalog
  (`--tokens <catalog>`).
- **2026-06-09 — token catalog wired into `lint-skill`.** `lint-skill --tokens <catalog>` now checks
  each skill's `metadata.skillroy.domain`: unknown → flag ("never invent a token"), alias → "use the
  canonical token", legacy → note `replaced_by`; severity scales by phase (SHOULD adhoc → MUST
  publish). Dogfooded against the overlay's starter catalog: a known token passed clean, `frobnicator` → warn
  (not in catalog), an alias → warn (use the canonical token). Base `lint-skill.py` carries no org-specific terms.
  The **author → review → tokens loop is closed.**
- **2026-06-09 — conventions hoisted to repo root.** Moved `skillroy-conventions.md` from
  `create/references/` to repo-root **`CONVENTIONS.md`** (pairs with `DESIGN.md` / `tokens/`).
  `create` and `review` now reference it by name — no `../create/...` cross-skill path. Resolves the
  §10 shared-vs-bundled item; all skills still lint clean.
- **2026-06-09 — CONVENTIONS consolidated (v0.2) + evals process defined.** Rewrote `CONVENTIONS.md`
  to v0.2: fixed parity gaps (added `dx` to the `metadata` tier enum, the `license`/`compatibility`
  fields, the repo/collection-name rule, review's `--tokens` check) and added an explicit **rule →
  `lint-skill` code → severity** table so doc and linter can't silently drift. Defined the **evals
  process** (§8: schema + how an agent runs/verifies them + the pass criterion — publish ⇒ evals
  exist *and* pass) and added `review/scripts/run-evals.py` (validate + list cases; the agent judges).
  Dogfooding `run-evals` caught an imported `research` eval with no assertions — fixed (added 5).
  All skills lint clean; `CONVENTIONS.md` + `run-evals.py` carry no org-specific terms.
- **2026-06-09 — `create` promoted to `publish` (first skill through the bar).** Exercised the full
  publish bar. **Structural:** `lint-skill --phase publish` on `create` → clean. **Behavioural:** ran
  `create`'s 4 evals (the first *real* eval run) — happy-path scaffold ✓ (built a compliant
  `smoke-test`), elicitation-when-underspecified ✓, non-compliant-name rejected ✓
  (`MyDeploy_Helper_v2`), unknown-token flagged ✓ (`frobnicator`). The run **surfaced a spec gap** —
  eval 3 expects "version belongs in `metadata`, not the name," which §2 hadn't stated; now added
  (name encodes only tier+domain; no version/status/owner/env). With that, all 4 evals pass →
  `create` set to `phase: publish`. (Project stays in active development; per-skill phase ≠ project
  phase. `skills-ref validate` not installed here — recommended at publish but unavailable.)
- **2026-06-09 — `research` + `review` through the publish bar (session 2).** **Base-spec
  unblocked:** `skills-ref validate` (npm 0.1.5) is runnable from WSL via the *Windows* npx (copy
  the skill to a Windows temp path) — all three skills **Valid**, retroactively closing the gap from
  `create`'s promotion. **`review`:** lint clean at publish; evals 4/4 — eval 2 surfaced that broken
  YAML masked the `name==folder` check in the CLI door (the chat door catches it; the linter
  didn't) → added a raw-text fallback name check + self-test. The run also surfaced that `review`
  collides with the reserved built-in `/review` per our own §2; **ratified: keep the name** (right
  verb, description routes, plugin namespace at distribution) — exception documented in §2 →
  `phase: publish`, v0.2.0. **`research`:** built the deferred second door
  `scripts/validate-seed.py` (template structure + every inline `[Sn]` must trace to a Sources row;
  uncited rows warn); SKILL.md bridges to it (two-doors fires and passes); evals 4/4, 27
  expectations — happy path with real fetches ✓ (the eval's URLs now 301-redirect — handled, noted
  as provenance), elicitation ✓, unavailable-adapter degradation ✓, local-file runbook ✓; all
  produced docs validate clean through the new script → `phase: publish`, v0.2.0 (semver minor for
  the validator; phase and version move independently). Process notes: interactive eval steps are
  simulated by the eval driver in autonomous runs (as in `create`'s run); a persistent eval-run-log
  convention is worth considering.
- **2026-06-09 — first real collection instrumented (dry-run → applied).** The instrumentation
  dry-run of an existing 3-skill collection was reviewed and its judgment calls ratified (new
  domain token confirmed by the SME/owner; the generic XSLT skill stays domain-less; all three at
  `phase: adhoc`; external-jar provenance lands at publish). Applied for real on a branch in the
  source repo: skills moved to `.claude/skills/` with an `.agents/skills` symlink for
  `.agents`-reading agents, `metadata.skillroy` + evals landed, collection lints clean against the
  org catalog. **Field lessons for the layout decision (§10 B):** (1) existing repos often
  `.gitignore` the whole `.claude/` dir — the skills home needs a `.claude/*` + `!.claude/skills/`
  re-include (a candidate `lint-skill` check: skills dir ignored by git → warn); (2) the
  `.agents → .claude` symlink needs `core.symlinks` on Windows checkouts. Repo rename to
  `<tier>-<domain>` form deferred to the repo owner (breaking for clones/CI; the two
  `collection-name` infos stay until then).
- **2026-06-09 (session 3) — retro items landed: run logs + simulated-interactive norm
  (CONVENTIONS v0.3).** Eval evidence is now a convention, not a retro note: every verification run
  is recorded at `<skill>/evals/runs/<date>.md` (header + per-expectation verdicts + evidence;
  reconstructed logs must say so). `run-evals.py --log` scaffolds one; `lint-skill` warns at publish
  when a skill has evals but no recorded run (`evals-run`); the simulated-interactive norm (§8) makes
  the eval driver's user-role explicit. Logs written: `review` + `research` (fresh, 13/13 and 27/27
  expectations), `create` (reconstructed from the §11 entry, labelled). Lint output is now
  **provenance-stamped** (skillroy git version + token-catalog digest) per §7 of this doc —
  `--json` consumers note: output is now `{provenance, results}`.
- **2026-06-09 (session 3) — `migrate` built → published; Tlog-Tools migrated to `dx-tlog` for
  real.** Owner direction: the prior in-place branch was superseded — no one uses Tlog-Tools yet, so
  the compliant end-state is a **new project**. Built `migrate` (scaffolded via `create`'s CLI door):
  SKILL.md + `migrate-skill.py` (`plan` read-only inventory; `apply` = copy/move to the home, inject
  `metadata.skillroy` byte-preserving everything else, patch the `.gitignore` trap, add the
  `.agents/skills` symlink; idempotent; `--tier` mandatory; `--phase publish` refused — publish is
  earned). Eval run: 4/4 on fixtures (plan-is-read-only; ratified apply; token discipline;
  idempotence) + the real migration as supplementary evidence → `phase: publish`. Real run: cloned
  the source repo with full history (axis C), `plan` → ratified inputs → in-place `apply`, imported
  the previously-ratified evals, lint clean against the org catalog, then an identity commit
  (README title + collection metadata block, Maven parent artifactId, self-references; `mvn validate`
  clean). Original repo untouched; its instrumentation branch is now redundant (owner may delete).
- **2026-06-09 (session 3) — `create` grows the collection capability (v0.2.0).** Owner raised the
  gap: skills live in collections, but nothing scaffolds one for *new* work (`migrate` only shapes
  existing content). Ratified: **one `create` skill, two scripts** (not a split skill — intent is
  "a skill", the collection is routing detail; not `init` — reserved built-in); scripts stay
  **git-free** (uniform rule; init is a printed next-step the chat door offers to run); new
  collections start **`status: experimental`**. Built `scripts/new-collection.py` (validates
  `<tier>-<domain>` + redundant-suffix, `--brand` escape, scaffolds the §10 shell, `--with-skill`
  delegates to the sibling `new-skill.py` with the tier inherited, `--license` propagates;
  `--self-test`). SKILL.md gains workflow step 0 (locate-or-create the collection); evals 5–6 added
  (new-project one-shot; non-compliant collection name) → fresh 6/6 run log supersedes the
  reconstructed one. README quickstart updated earlier the same day (CLI vs Assisted split, where
  outputs land — prompted by owner questions about `--dir` semantics).
- **2026-06-09 (session 3) — deployment story + monorepo structure settled.** Verified against the
  official docs (guide agent): plugins bundle skills with a custom-path `skills` manifest field (so
  a collection keeps `.claude/skills/` as its single layout and a 5-line `plugin.json` re-points
  the plugin at it); a marketplace is any git repo with `.claude-plugin/marketplace.json`, private
  Bitbucket included, with **relative in-repo plugin sources**; updates via marketplace refresh
  (opt-in autoUpdate); project `.claude/settings.json` can auto-prompt marketplace+plugin install
  on first trusted open; symlinks into `~/.claude/skills/` are *undocumented* (README corrected).
  **Deployment is two-phase:** (1) manual — clone + `$SKILLROY_TOKENS` (new env rung in
  `lint-skill`, part of the documented catalog lookup ladder: flag → env → overlay clone);
  (2) plugin marketplace — skillroy carries `.claude-plugin/plugin.json`; the org hub doubles as
  the private marketplace. **Structure (ratified): "skills follow their subject."** The org hub
  (`<org>-skillroy`) = `overlay/` (the org plugin: tokens + extensions) + `collections/` (the
  monorepo home for *pure* collections — skills whose tools are bundled scripts; the owner's
  sibling-repo survey confirmed nearly all existing skills qualify) + the marketplace index.
  Code-bound collections (skills driving a co-built artifact, e.g. the migrated `dx-tlog` jar)
  stay with their code — deploy by clone; fold-in route = publish the tool as a versioned external
  dep. Team bootstrap: the migrated repo carries the settings.json example. Collection naming on
  migration: org prefix + `-skills`/`-tools` suffixes drop (`<org>-dfm-kb-skills` → `kb-dfm`). skillroy: README rewritten for publication
  (skills table, quickstart, mechanism-vs-policy, collection metadata block §10), git-initialized
  with the full tree as the initial commit (GitHub push = owner). Overlay (`<org>-skillroy`):
  README finalized (license ratified proprietary-internal; `depends-on: [skillroy]` block), org
  CONVENTIONS (tier bindings, token-governance: proposed → SME-ratified → confirmed), and the
  research **source-adapter extension** (Confluence-over-MCP adapter file authored against the base
  contract; tool names flagged for verification against the live connector — the parked org evals
  exist to verify it). Deliberate scope choices, revisitable: no `explain` skill (README +
  CONVENTIONS serve it); overlay install remains copy-by-hand.
