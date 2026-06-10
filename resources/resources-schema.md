# External-resources manifest schema

A skillroy collection declares the **external resources** its skills depend on — IaC repos, Confluence
snapshots, product references, binary artifacts, live environments, MCP connectors — in **one
`resources.yaml` at the collection root**. This mirrors the token-catalog pattern: *declared data,
an override ladder for locating it, provenance, and detect-and-surface (never silently auto-fetch).*

skillroy ships this **schema** (and `example-resources.yaml`); the *data* lives in each collection.

## Granularity

Collection-level by default, with per-skill extensions in the **same file**:

```yaml
version: 1
resources:                 # collection-wide (the default)
  - id: ...
skills:                    # optional per-skill extensions / overrides (merged onto the defaults)
  <skill-name>:
    resources:
      - id: ...            # same id → overrides that field set; new id → adds for this skill
```

A skill sees the union of the collection-wide resources and its own; an entry with a matching `id`
overrides the collection default field-by-field.

## Resource entry fields

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | stable kebab-case name (may match a canonical token from the catalog) |
| `type` | yes | one of the six below |
| `description` | yes | one line: what it is / why the skill needs it |
| `remote` | type-dep. | where it really lives (git URL / Confluence URL / artifact coords / service) |
| `local_default` | optional | where it's expected on disk (the bottom rung of the ladder) |
| `env` | optional | environment variable that overrides the location |
| `fetch` | optional | the command/steps to obtain it — **offered to the user, never auto-run** |
| `version` | optional | freshness pin (product version, git branch/SHA, Confluence page version) |
| `provenance` | optional | what gets stamped into any artifact generated from it (§9 axis C) |
| `required` | optional | `true` = the skill can't function without it; `false`/omitted = enrich-if-present |

**Location resolution (the ladder):** `--flag` (if the skill's tool takes one) → `$env` →
`local_default` → not found ⇒ **report it and offer `fetch`**. Same shape as the `--tokens` /
`$SKILLROY_TOKENS` catalog ladder.

## The six types and how each is handled

| `type` | Examples | Bundled? | Convention |
|--------|----------|----------|------------|
| `git-repo` | IaC repos (Ansible/Terraform/Jsonnet), per-customer config repos | no | `remote` = git URL; `local_default` = clone root; detect `.git`; offer `git clone`. (The proven `--repo-root` / `cloned:true\|false` pattern.) |
| `confluence-snapshot` | a Confluence page captured for offline use | **yes** (small) | The bundled file **is a research seed document** (`<topic>-seed.md`, validated by `validate-seed.py`); `remote` + `version` point at the live page. Strategy = **both**: live MCP when present, the provenance-stamped snapshot as the offline fallback. Refresh via the `research` skill. |
| `product-ref` | large versioned corpora (schemas, source snapshots) | **never** | Too large to bundle. `env` + `local_default` locate it; `version` pins the release; `fetch` downloads + unpacks from the artifact store. The small **index** built over it ("crunch once") may be bundled; the corpus is not. |
| `artifact` | WAR/jar/zip — incl. product-reference zips in a Bitbucket **Downloads** area | no | `remote` = registry / Bitbucket-Downloads URL; `fetch` = authenticated download (e.g. `curl`); **provenance-stamp the version actually used** into outputs. |
| `live-env` | a running cloud environment reached via a CLI | n/a | Not fetched. Document the required CLI (`gcloud`…) + access (IAP). State lives in a per-env **registry/dossier**; secrets are a `creds_ref` → a secret manager, **never stored**. |
| `mcp` | an MCP connector (Confluence, etc.) | n/a | Declare the required connector by name; **graceful degradation** when absent (the research source-adapter pattern). |

## Why this fits skillroy

It's the same shape as the token catalog — declared data + override ladder + provenance — so a future
`review`/`lint-skill` check can verify that **every external path or URL a skill references is declared
here**, the way `--tokens` closed the loop for domains. See `example-resources.yaml` for a generic,
fully-worked instance.
