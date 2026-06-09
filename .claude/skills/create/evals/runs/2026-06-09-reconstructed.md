# Eval run — create v0.1.0 (publish) — RECONSTRUCTED
- **Date / runner:** 2026-06-09 (session 1) / Claude (Claude Code session); log reconstructed the
  same day from DESIGN.md §11 ("create promoted to publish") because the run predates the run-log
  convention (CONVENTIONS §8, added later on 2026-06-09). Assertion-level detail was not preserved;
  verdicts below are per-eval.
- **Inputs:** scaffolds exercised via scripts/new-skill.py + the SKILL.md workflow; elicitation
  simulated by the eval driver.
- **Result:** PASS (4/4 evals) — after one spec fix found by eval 3 (see below)

## Eval 1 — Happy-path scaffold
- [x] Built a compliant `smoke-test` skill (name/frontmatter/metadata.skillroy correct; linted clean).

## Eval 2 — Elicitation when under-specified
- [x] Asked for the missing brief instead of guessing.

## Eval 3 — Non-compliant name rejected
- [x] `MyDeploy_Helper_v2` rejected with the compliant alternative explained. The run surfaced that
  "version belongs in metadata, not the name" was unstated in CONVENTIONS §2 — fixed during the run
  (name encodes only tier+domain), then the eval passed.

## Eval 4 — Unknown token flagged
- [x] `frobnicator` flagged as not-in-catalog; no token invented.

Post-run: structural lint at publish clean. `skills-ref validate` was unavailable in session 1; run
retroactively in session 2 (0.1.5 via Windows npx) → Valid.
