# Seed Document Template

Use this structure for every seed document the research skill produces. It mirrors the shape of a good reference doc: a metadata header, a stated purpose, a themed body, explicit gaps, and full source provenance. Adapt the section headings to the topic, but always keep the metadata header, **Open questions & gaps**, and **Sources** sections.

## Template

```markdown
# <Topic> — Seed Document

**Status:** Draft (generated)
**Purpose:** <what skill / use this supports, one line>
**Audience:** <who or what consumes this>
**Generated:** <YYYY-MM-DD> by the research skill
**Sources:** <N> (see Sources section)

## Purpose & scope

<1–2 short paragraphs: what this document covers, what it deliberately leaves out.>

## <Theme 1>

<Synthesised content, organised by topic. Tag the source(s) each part draws on: [S1], [S2].>

## <Theme 2>

<...>

## Key facts / quick reference

<Optional: the most-used facts, definitions, or values, collected for fast lookup.>

## Open questions & gaps

<Anything the sources did not answer, conflicts left unresolved, or areas needing a human decision. Be specific — this tells the skill author what still needs filling in.>

## Sources

| ID | Title | Type | Identifier (URL / path / page) | Retrieved |
|----|-------|------|--------------------------------|-----------|
| S1 | <title> | web | <url> | <YYYY-MM-DD> |
| S2 | <title> | local-file | <path> | <YYYY-MM-DD> |
| S3 | <title> | confluence | <space/page> | <YYYY-MM-DD> |
```

## Conventions

- **Provenance tags.** Use `[S1]`, `[S2, S4]` inline so any statement can be traced to its source(s). A reader should never have to guess where a fact came from.
- **Themed, not source-by-source.** The body is organised around the subject. Don't produce one section per source — merge and deduplicate.
- **Honest gaps.** A seed document's value is partly in marking what it *doesn't* cover. Always fill in Open questions & gaps, even if briefly.
- **Status.** Mark new documents `Draft (generated)`. They're a starting point for a human — and the skill author — to refine.
