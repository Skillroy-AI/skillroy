#!/usr/bin/env python3
"""validate-seed: check a seed document against the research skill's template.

Stdlib-only. Validates the structure from references/seed-document-template.md
(metadata header, required sections, Sources table) and provenance conformance
(every inline [Sn] tag maps to a Sources row; every row is cited). The CLI
"second door" of the research skill, and reusable by review's linter.

Usage:
  python3 validate-seed.py <seed-doc.md> [--json]
  python3 validate-seed.py --self-test
"""
import argparse
import json
import re
import sys

HEADER_REQUIRED = ("Status", "Purpose", "Generated", "Sources")
HEADER_OPTIONAL = ("Audience",)
SECTIONS_REQUIRED = ("Purpose & scope", "Open questions & gaps", "Sources")
TAG_RE = re.compile(r"\[(S\d+(?:\s*,\s*S\d+)*)\]")
ROW_RE = re.compile(r"^\|\s*(S\d+)\s*\|(.*)\|\s*$")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def validate_seed(text):
    findings = []

    def add(sev, code, msg):
        findings.append({"severity": sev, "code": code, "message": msg})

    lines = text.splitlines()

    # H1 title
    h1 = next((l for l in lines if l.startswith("# ")), None)
    if h1 is None:
        add("error", "title", "no H1 title (expected '# <Topic> — Seed Document')")
    elif "seed document" not in h1.lower():
        add("warn", "title", f"H1 doesn't say 'Seed Document': {h1!r}")

    # Metadata header: **Key:** value lines
    header = {}
    for l in lines:
        m = re.match(r"\*\*([A-Za-z ]+):\*\*\s*(.+)", l)
        if m:
            header.setdefault(m.group(1).strip(), m.group(2).strip())
    for key in HEADER_REQUIRED:
        if key not in header:
            add("error", "header", f"metadata header line '**{key}:** ...' missing")
    for key in HEADER_OPTIONAL:
        if key not in header:
            add("warn", "header", f"metadata header line '**{key}:** ...' missing (template has it)")
    status = header.get("Status", "")
    if status and status.lower() != "draft (generated)":
        add("warn", "status", f"Status is {status!r}; generated docs should start as 'Draft (generated)'")

    # Required sections
    section_names = [re.sub(r"^#{2,}\s*", "", l).strip() for l in lines if re.match(r"^#{2,}\s", l)]
    for sec in SECTIONS_REQUIRED:
        if not any(s.lower() == sec.lower() for s in section_names):
            add("error", "section", f"required section '## {sec}' missing")

    # Sources table rows (| S1 | title | type | identifier | retrieved |)
    rows = {}
    for l in lines:
        m = ROW_RE.match(l.strip())
        if m:
            rows[m.group(1)] = m.group(2)
    if not rows and not any(f["code"] == "section" and "Sources" in f["message"] for f in findings):
        add("error", "sources", "Sources section has no table rows (| S1 | ... |)")
    for sid, rest in sorted(rows.items()):
        if not DATE_RE.search(rest):
            add("warn", "sources", f"source {sid} has no YYYY-MM-DD retrieved/provided date")

    # Source-count header vs table
    m = re.match(r"(\d+)", header.get("Sources", ""))
    if m and rows and int(m.group(1)) != len(rows):
        add("warn", "header", f"header says {m.group(1)} sources but the table has {len(rows)}")

    # Provenance tags: collect inline [Sn] outside the Sources table
    cited = set()
    for l in lines:
        if ROW_RE.match(l.strip()):
            continue
        for grp in TAG_RE.findall(l):
            cited.update(t.strip() for t in grp.split(","))
    if not cited:
        add("error", "provenance", "no inline [Sn] provenance tags — provenance is the point of a seed doc")
    for tag in sorted(cited):
        if tag not in rows:
            add("error", "provenance", f"inline tag [{tag}] has no row in the Sources table (untraceable claim)")
    for sid in sorted(rows):
        if sid not in cited:
            add("warn", "provenance", f"source {sid} is in the table but never cited in the body")

    return findings


def report(path, findings, as_json):
    if as_json:
        print(json.dumps({"file": path, "findings": findings}, indent=2))
    else:
        print(f"== {path} ==")
        if not findings:
            print("  ok — conforms to the seed-document template")
        for f in findings:
            print(f"  [{f['severity']:5}] {f['code']}: {f['message']}")
    return 1 if any(f["severity"] == "error" for f in findings) else 0


GOOD = """# Widget Feeds — Seed Document

**Status:** Draft (generated)
**Purpose:** reference for the widget-feeds skill
**Audience:** skill author
**Generated:** 2026-06-09 by the research skill
**Sources:** 2 (see Sources section)

## Purpose & scope

Covers widget feed formats. [S1]

## Feed structure

Feeds are XML documents with one entry per widget. [S1, S2]

## Open questions & gaps

- Retry semantics undocumented. [S2]

## Sources

| ID | Title | Type | Identifier (URL / path / page) | Retrieved |
|----|-------|------|--------------------------------|-----------|
| S1 | Widget spec | web | https://example.com/spec | 2026-06-09 |
| S2 | Ops notes | pasted-text | (user notes) | 2026-06-09 |
"""


def self_test():
    assert validate_seed(GOOD) == [], f"good doc flagged: {validate_seed(GOOD)}"

    bad = GOOD.replace("## Open questions & gaps\n\n- Retry semantics undocumented. [S2]\n", "")
    codes = {f["code"] for f in validate_seed(bad)}
    assert "section" in codes, f"missing-section not caught: {codes}"

    orphan = GOOD.replace("[S1, S2]", "[S1, S3]").replace("undocumented. [S2]", "undocumented. [S3]")
    fs = validate_seed(orphan)
    assert any(f["code"] == "provenance" and "[S3]" in f["message"] and f["severity"] == "error" for f in fs), \
        f"unknown tag not caught: {fs}"
    assert any(f["code"] == "provenance" and "S2" in f["message"] and f["severity"] == "warn" for f in fs), \
        f"uncited source not caught: {fs}"

    untagged = re.sub(r" ?\[S[^\]]*\]", "", GOOD)
    assert any(f["code"] == "provenance" and "no inline" in f["message"] for f in validate_seed(untagged)), \
        "tagless doc not caught"

    miscount = GOOD.replace("**Sources:** 2", "**Sources:** 5")
    assert any(f["code"] == "header" and "table has 2" in f["message"] for f in validate_seed(miscount)), \
        "source-count drift not caught"

    nostatus = GOOD.replace("**Status:** Draft (generated)\n", "")
    assert any(f["code"] == "header" and "Status" in f["message"] and f["severity"] == "error"
               for f in validate_seed(nostatus)), "missing Status not caught"
    print("self-test OK")


def main():
    ap = argparse.ArgumentParser(description="Validate a seed document against the template.")
    ap.add_argument("seed", nargs="?", help="path to the seed document (.md)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--self-test", action="store_true", help="run the built-in tests")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.seed:
        ap.error("seed document path required (or --self-test)")
    with open(args.seed, encoding="utf-8") as fh:
        text = fh.read()
    return report(args.seed, validate_seed(text), args.json)


if __name__ == "__main__":
    sys.exit(main())
