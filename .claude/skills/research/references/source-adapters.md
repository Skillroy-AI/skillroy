# Source Adapters

A **source adapter** is a small contract describing one type of source: how to recognise it, how to retrieve its content, and what provenance to record. Adapters are what make the research skill extensible — the base skill ships with universal adapters, and extensions add more (for example, a company-internal Confluence adapter that retrieves over MCP).

## The adapter contract

Each adapter defines:

- **name** — short identifier (e.g. `web`, `confluence`).
- **recognises** — which inputs route to this adapter (e.g. `http(s)://` URLs; a filesystem path; `SPACE/Page Title` references).
- **retrieve** — how to get the content: which tool or steps to use.
- **records** — the provenance fields to capture for the Sources list (always at least: identifier, title, date retrieved).
- **notes** — auth, rate limits, access scope, and copyright/confidentiality cautions.

## Built-in adapters

### web
- **recognises:** `http://` / `https://` URLs.
- **retrieve:** fetch the page (use `web_fetch`; use `web_search` first if a source needs to be discovered rather than given). Extract the main text.
- **records:** URL, page title, date retrieved.
- **notes:** prefer primary/authoritative pages. Paraphrase; quote only briefly and with attribution.

### local-file
- **recognises:** a filesystem path or an uploaded file.
- **retrieve:** read the file, routing by type — plain text/markdown directly; for PDF/DOCX/XLSX and similar, extract text appropriately rather than dumping raw bytes.
- **records:** file path/name, file type, date retrieved.
- **notes:** for large files, extract the relevant sections rather than the whole thing.

### pasted-text
- **recognises:** text or notes the user pastes directly into the conversation.
- **retrieve:** use the provided text as-is.
- **records:** a short label for the note, date provided.
- **notes:** treat as user-authored unless they say otherwise.

## Writing an extension

An extension adds one or more adapters without modifying the base skill:

1. Create `references/sources/<name>.md` describing the adapter against the contract above.
2. Name any MCP tool (or other capability) the adapter depends on, and any setup the user must do first (e.g. configuring a connector).
3. At gather time, the research skill enumerates `references/sources/*.md` as available adapters and checks that the tools each requires are actually present. If a required tool is missing, it tells the user instead of failing silently.

Keep extensions self-contained: one file per source type, each describing recognition, retrieval, provenance, and cautions.

## Example extension (stub): Confluence over MCP

> Starting stub. Fill in the tool names and field mappings for your Confluence MCP connector. Save the finished version as `references/sources/confluence.md`.

- **name:** `confluence`
- **recognises:** Confluence page URLs, or `SPACE/Page Title` references the user provides.
- **retrieve:** use the Confluence MCP connector — search for the page, then fetch its content by id. (Replace with your connector's actual search/fetch tool names.)
- **records:** space key, page id, page title, page version, date retrieved.
- **notes:**
  - Requires the Confluence MCP connector to be configured and connected.
  - Respect access controls — retrieve only pages the user is authorised to read; never widen access.
  - These are internal documents: synthesise and paraphrase, don't bulk-copy, and keep the seed document's confidentiality consistent with the source.
