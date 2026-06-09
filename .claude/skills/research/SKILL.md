---
name: research
description: Gathers cited sources and synthesizes them into a "seed document" — the foundational reference doc a new skill is built on. Prompts for a topic/brief and a set of sources (web pages, local files, pasted notes, plus any sources added by an extension, such as an internal wiki via MCP), retrieves each, and writes a structured, provenance-tracked reference. Use whenever creating a new skill, bootstrapping background documentation, or when the user mentions seed docs, gathering sources, researching a topic for documentation, Confluence/internal-wiki research, or wants source material pulled together into a single reference — even if they don't say "research" outright. Pairs with the `create` skill, which consumes the seed doc this produces.
metadata:
  skillroy:
    phase: publish
    tier: meta
    version: 0.2.0
license: Apache-2.0
---

# Research

A *seed document* is the foundational reference a new skill is built on — a single, structured, source-backed file that captures what's known about a topic before any skill instructions are written. This skill produces one. It collects the user's brief and their cited sources, retrieves each source, and synthesizes the material into a seed document with full provenance.

The skill is deliberately extensible. It handles universal sources (web pages, local files, pasted notes) out of the box, and **source adapters** let you add more — for example, a company-internal extension that pulls from Confluence over MCP. See `references/source-adapters.md`.

**Two front doors.** Gathering and synthesis are conversational (this workflow); conformance checking is scripted. Validate any seed document — generated here or by hand — with
`python3 scripts/validate-seed.py <seed-doc.md> [--json]` (`--self-test` to verify it): it checks the template structure and that every inline `[Sn]` tag traces to a Sources row.

## Workflow

Work through these steps in order. If the conversation or the invocation already supplies some of this (a topic, a list of URLs, an attached file), extract what's there first and only ask for what's missing — don't re-ask for what the user already gave you.

### 1. Capture the brief

Ask the user for the following, skipping anything already answered:

- **Topic & purpose** — what is this seed document about, and what skill will it support? (a sentence or two)
- **Intended use & audience** — how will the document be used? (e.g. a reference for Claude when authoring or operating a skill; human onboarding). This shapes depth and tone.
- **Scope** — what's in and out of scope; a broad survey or a deep dive on a narrow area.
- **Sources** — the material to synthesize. Invite as many as the user has, of any supported type:
  - web pages (URLs)
  - local files or uploads (paths)
  - pasted text or notes
  - any source type provided by an installed extension (e.g. Confluence spaces/pages via MCP — list what's actually available; see `references/source-adapters.md`)
- **Output** — desired filename and location. Default to a kebab-case `*-seed.md` (e.g. `<application>-xml-feeds-seed.md`) in the new skill's folder or a `docs/` directory.

Confirm the brief back to the user in a line or two before proceeding.

### 2. Resolve sources to adapters

Each source is handled by a **source adapter** — a small contract describing how to recognise and retrieve one type of source (`references/source-adapters.md`).

- Enumerate the adapters available *now*: the built-ins (`web`, `local-file`, `pasted-text`) plus any extension adapters present in `references/sources/` and the MCP tools they require.
- Route each source the user gave to an adapter.
- If a source doesn't match any available adapter (e.g. the user references Confluence but no Confluence extension is installed), say so plainly and ask how to proceed. Don't guess at a source you can't actually reach.
- Show the user the resolved list — each source and how it will be retrieved — and get a quick confirmation before fetching. Retrieval touches the network and may use authenticated connectors, so confirming here catches wrong URLs and unintended access before anything is fetched.

### 3. Gather

Retrieve each source through its adapter. For every source, record provenance: a stable identifier (URL, file path, or page reference), its title, and the date retrieved. You'll need these for the Sources section.

While gathering:

- Keep every fact traceable to a source. **Do not fill gaps from prior knowledge** — if the sources don't cover something the brief needs, record it as an open question rather than inventing an answer. The point of a seed document is that it is grounded in real sources.
- Prefer primary and authoritative sources. Where sources disagree, capture the disagreement rather than silently choosing one.
- Respect copyright and confidentiality: synthesise in your own words, quote only briefly and with attribution, and never bulk-copy passages — especially from internal sources. For extension/MCP sources, follow the retrieval and access notes in that adapter, and retrieve only material the user is authorised to see.

### 4. Synthesise the seed document

Assemble the document using the structure in `references/seed-document-template.md`. Key principles:

- **Organise by theme, not by source.** Merge what multiple sources say about the same thing; deduplicate.
- Write in the domain's own language, neutral and reference-style — this is documentation, not an essay.
- Tag each section with the source(s) it draws on using a lightweight marker (e.g. `[S1]`, `[S2, S4]`) that maps to the Sources list, so any statement can be traced back.
- Surface uncertainty and conflicts explicitly rather than papering over them.
- Include an **Open questions & gaps** section for anything the sources left unanswered — this tells the skill author what still needs filling in.

### 5. Write, validate, and hand off

- Write the file to the agreed location (default: kebab-case `*-seed.md`).
- Run `python3 scripts/validate-seed.py <the-file>` and fix anything it flags — it enforces the template structure and tag↔source traceability mechanically, so you don't have to eyeball it.
- Summarise for the user: what the document covers, which sources fed it, and the open questions worth resolving.
- Offer the next step. A seed document exists to bootstrap a new skill, so offer to feed it into the `create` skill (it turns this seed doc into a new skill).

## Source adapters and extensions

Source handling is pluggable. Built-in adapters cover web pages, local files, and pasted text. To support a new source type — an internal wiki, a ticketing system, a docs platform — add an extension: a file under `references/sources/<name>.md` that follows the adapter contract and names any MCP tool it relies on. The skill discovers these at gather time. `references/source-adapters.md` documents the contract and includes a Confluence-over-MCP example stub.

## Output format

The seed document must follow `references/seed-document-template.md`, which requires at minimum: a metadata header (topic, purpose, status, generated date), purpose & scope, a themed body, an **Open questions & gaps** section, and a **Sources** list with identifiers and retrieval dates. Always include the Sources section — provenance is the point of a seed document. `scripts/validate-seed.py` checks all of this mechanically; run it on every document you produce.

## Example

**Invocation:** `/research`

**Brief:** "Seed doc for a skill about `<application>` XML feeds. Sources: our internal feed spec (Confluence), the public XML schema docs at `<url>`, and a sample feed file I'll attach."

**Result:** the skill confirms the brief; routes the Confluence page to the `confluence` adapter (if installed), the URL to the `web` adapter, and the attachment to the `local-file` adapter; shows the resolved list for confirmation; retrieves all three; and writes `<application>-xml-feeds-seed.md` — a themed reference with `[S1]`–`[S3]` provenance tags, a Sources table, and an Open questions section flagging anything the three sources didn't pin down.
