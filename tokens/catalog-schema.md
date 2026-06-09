# Canonical Token Catalog — schema (v1)

skillroy ships this **schema** (mechanism); an organisation supplies the **catalog data** in its
overlay (e.g. `<org>-skillroy/tokens/canonical-tokens.yaml`). A *canonical token* is the single
authoritative short identifier for an application / service / component, used consistently across
repos, charts, metrics, docs, and skills.

> Distinct from **security** tokens (API keys, access tokens, etc.), which are secret, have their own
> lifecycle, and are out of scope here.

## File format (YAML; JSON with the same shape also accepted)

```yaml
version: 1
tokens:
  - token: data-flow              # REQUIRED. lowercase kebab-case [a-z0-9-]; the primary key.
    name: Data Flow Service       # REQUIRED. human-readable name.
    domain: data                  # optional. the suite/area this belongs to.
    status: confirmed             # REQUIRED. confirmed | proposed | legacy
    aliases: [DFS, data-flow-svc] # optional. legacy/human names that map to this token.
    sources: ["https://wiki/..."] # optional. where the token is evidenced.
    replaced_by: <token>          # optional; for status: legacy — the modern replacement.
    notes: "..."                  # optional.
```

## Rules (enforced by `validate-tokens.py`)

- `tokens` is a list; each entry has `token`, `name`, `status`.
- `token` is **unique** across the catalog and matches `^[a-z0-9]+(-[a-z0-9]+)*$`.
- `status` ∈ {`confirmed`, `proposed`, `legacy`}; a `legacy` token SHOULD set `replaced_by` or `notes`.
- `aliases` / `sources` are lists of strings. An alias MUST NOT collide with any canonical token.

## How skills use it

- Skills reference tokens as **primary keys**; legacy/human names are **aliases** only.
- `create` validates a skill's `metadata.skillroy.domain` against the catalog; `review` lints it.
- **Never invent or silently "fix" a token** — surface unknowns (add as `proposed`, flag for SME review).

## Governance

The catalog is a living, version-controlled artifact. Add/seed tokens as `proposed`; promote to
`confirmed` after domain-owner review; mark superseded ones `legacy` with `replaced_by`. Validate with
`python3 tokens/validate-tokens.py <catalog>`.
