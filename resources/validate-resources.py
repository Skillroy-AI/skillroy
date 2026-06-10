#!/usr/bin/env python3
"""validate-resources — check a collection's external-resources manifest against the schema.

skillroy ships the schema (resources/resources-schema.md); a collection supplies `resources.yaml`.
This is the CLI "second door" for the external-resources convention (CONVENTIONS §11); `review`'s
lint-skill does a lighter presence/parse check and points here for the full validation.

    python3 validate-resources.py <resources.yaml> [--json]
    python3 validate-resources.py --self-test

Exit status is non-zero if any finding is an `error`.
"""
import argparse
import json
import os
import re
import sys

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TYPES = ("git-repo", "confluence-snapshot", "product-ref", "artifact", "live-env", "mcp")
# Two ways a plaintext credential shows up in a manifest value; each captures the credential itself.
BASIC_AUTH_RE = re.compile(r"-u\s+\S+?:(\S+)")                                   # curl -u user:PASS
KEYWORD_SECRET_RE = re.compile(
    r"(?i)\b(?:password|secret|api[_-]?key|access[_-]?token|private[_-]?key|app[_-]?password)\b"
    r"\s*[:=]\s*(\S{6,})")
# A credential that interpolates an env var (…$VAR / ${VAR}) is a reference, not a plaintext secret.


def has_plaintext_secret(v):
    for rx in (BASIC_AUTH_RE, KEYWORD_SECRET_RE):
        for m in rx.finditer(v):
            if "$" not in m.group(1):       # an env-var reference is fine; a literal is not
                return True
    return False


def load(path):
    if path.endswith(".json"):
        try:
            with open(path) as fh:
                return json.load(fh), None
        except Exception as exc:
            return None, f"invalid JSON: {exc}"
    try:
        import yaml
    except ImportError:
        return None, "PyYAML not installed — convert to .json, or `pip install pyyaml`"
    try:
        with open(path) as fh:
            return yaml.safe_load(fh), None
    except Exception as exc:
        return None, f"invalid YAML: {exc}"


def _check_entry(e, where, add, seen_ids, partial=False):
    """partial=True for a per-skill entry that overrides a collection resource by id — only the
    fields it restates are validated; type/description are inherited and not required."""
    if not isinstance(e, dict):
        add("error", f"{where}: not a mapping")
        return
    rid = e.get("id")
    if not rid:
        add("error", f"{where}: missing 'id'")
    elif not ID_RE.match(str(rid)):
        add("error", f"{where}: id '{rid}' is not kebab-case [a-z0-9-]")
    elif rid in seen_ids:
        add("error", f"{where}: duplicate id '{rid}' (already defined at {seen_ids[rid]})")
    else:
        seen_ids[rid] = where

    rtype = e.get("type")
    if not rtype and not partial:
        add("error", f"{where}: missing 'type'")
    elif rtype and rtype not in TYPES:
        add("error", f"{where}: type '{rtype}' invalid; choose {list(TYPES)}")

    if not e.get("description") and not partial:
        add("warn", f"{where}: no 'description' (what it is / why the skill needs it)")
    if "required" in e and not isinstance(e["required"], bool):
        add("warn", f"{where}: 'required' should be true/false")

    # Type-specific guidance (warn/info — the schema's handling rules). Skipped for partial
    # overrides, which inherit the collection entry's type and fields.
    if partial:
        rtype = None
    if rtype == "git-repo":
        if not e.get("remote"):
            add("warn", f"{where} (git-repo): no 'remote' (where the repo really lives)")
        if not e.get("local_default") and not e.get("env"):
            add("warn", f"{where} (git-repo): no 'local_default' or 'env' — where are clones expected?")
        if not e.get("fetch"):
            add("info", f"{where} (git-repo): no 'fetch' — the offered clone command helps the user")
    elif rtype == "confluence-snapshot":
        if not e.get("remote"):
            add("warn", f"{where} (confluence-snapshot): no 'remote' (the live page to refresh from)")
        ld = str(e.get("local_default") or "")
        if not ld:
            add("warn", f"{where} (confluence-snapshot): no 'local_default' (the bundled snapshot file)")
        elif not ld.endswith(".md"):
            add("info", f"{where} (confluence-snapshot): snapshot should be markdown")
        elif "seed" not in os.path.basename(ld):
            add("info", f"{where} (confluence-snapshot): name the snapshot '<topic>-seed.md' (a research seed doc; §11)")
    elif rtype == "product-ref":
        if not e.get("version"):
            add("warn", f"{where} (product-ref): no 'version' — pin the release(s) indexed")
        if not e.get("env") and not e.get("local_default"):
            add("warn", f"{where} (product-ref): no 'env'/'local_default' — how is the corpus located?")
    elif rtype == "artifact":
        if not e.get("fetch"):
            add("warn", f"{where} (artifact): no 'fetch' — how is it obtained?")
        if not e.get("version"):
            add("info", f"{where} (artifact): no 'version' — provenance-stamping wants the version used")

    # No plaintext secrets anywhere in the entry (env-var references are fine).
    for k, v in e.items():
        if isinstance(v, str) and has_plaintext_secret(v):
            add("error", f"{where}.{k}: looks like a plaintext secret — use an env var / secret-manager reference")


def validate_resources(data):
    findings = []

    def add(sev, msg):
        findings.append({"severity": sev, "message": msg})

    if not isinstance(data, dict):
        add("error", "manifest must be a mapping (version + resources)")
        return findings
    if data.get("version") != 1:
        add("warn", f"version is {data.get('version')!r}; this schema expects 1")
    if not isinstance(data.get("resources"), list) or not data["resources"]:
        add("error", "manifest needs a non-empty 'resources' list")
        return findings

    seen = {}
    for i, e in enumerate(data["resources"]):
        _check_entry(e, f"resources[{i}]", add, seen)

    skills = data.get("skills")
    if skills is not None:
        if not isinstance(skills, dict):
            add("error", "'skills' must be a mapping of <skill-name> -> {resources: [...]}")
        else:
            for name, body in skills.items():
                if not isinstance(body, dict) or not isinstance(body.get("resources"), list):
                    add("error", f"skills.{name}: must have a 'resources' list")
                    continue
                # Per-skill ids may intentionally override collection ids; check against a local view.
                local = dict(seen)
                for j, e in enumerate(body["resources"]):
                    rid = e.get("id") if isinstance(e, dict) else None
                    is_override = rid in seen   # restating a collection entry = partial merge
                    if is_override:
                        local.pop(rid, None)
                    _check_entry(e, f"skills.{name}.resources[{j}]", add, local, partial=is_override)
    return findings


def report(path, findings, as_json):
    if as_json:
        print(json.dumps({"file": path, "findings": findings}, indent=2))
    else:
        print(f"== {path} ==")
        if not findings:
            print("  ok — conforms to the resources schema")
        for f in findings:
            print(f"  [{f['severity']:5}] {f['message']}")
    return 1 if any(f["severity"] == "error" for f in findings) else 0


GOOD = {
    "version": 1,
    "resources": [
        {"id": "infra-repos", "type": "git-repo", "description": "IaC repos",
         "remote": "git@x:o/r.git", "local_default": "~/Projects/infra",
         "fetch": "git clone …"},
        {"id": "domain-kb", "type": "confluence-snapshot", "description": "kb",
         "remote": "https://x.atlassian.net/wiki/…", "local_default": "./knowledge/domain-seed.md",
         "version": "v3"},
        {"id": "product-reference", "type": "product-ref", "description": "corpus",
         "env": "PRODUCT_REF", "version": "3.161"},
        {"id": "server-war", "type": "artifact", "description": "war",
         "fetch": "curl -o s.war https://…", "version": "1.2.3"},
    ],
    "skills": {"data-lookup": {"resources": [
        {"id": "product-reference", "type": "product-ref", "description": "corpus", "env": "PRODUCT_REF",
         "version": "3.161", "required": True}]}},
}


def self_test():
    assert validate_resources(GOOD) == [], f"good manifest flagged: {validate_resources(GOOD)}"

    bad_type = {"version": 1, "resources": [{"id": "x", "type": "bogus", "description": "d"}]}
    assert any(f["severity"] == "error" and "type 'bogus'" in f["message"]
               for f in validate_resources(bad_type)), "bad type not caught"

    bad_id = {"version": 1, "resources": [{"id": "Bad_Id", "type": "mcp", "description": "d"}]}
    assert any("kebab-case" in f["message"] for f in validate_resources(bad_id)), "bad id not caught"

    dup = {"version": 1, "resources": [
        {"id": "a", "type": "mcp", "description": "d"},
        {"id": "a", "type": "mcp", "description": "d"}]}
    assert any("duplicate id" in f["message"] for f in validate_resources(dup)), "dup id not caught"

    secret = {"version": 1, "resources": [
        {"id": "a", "type": "artifact", "description": "d", "fetch": "curl -u admin:hunter2abcd https://x"}]}
    assert any("plaintext secret" in f["message"] for f in validate_resources(secret)), "secret not caught"
    envref = {"version": 1, "resources": [
        {"id": "a", "type": "artifact", "description": "d", "version": "1",
         "fetch": "curl -u $USER:$BITBUCKET_APP_PASSWORD https://x"}]}
    assert not any("plaintext secret" in f["message"] for f in validate_resources(envref)), \
        "env-var credential reference should be allowed"

    nolist = {"version": 1}
    assert any("non-empty 'resources'" in f["message"] for f in validate_resources(nolist)), "missing list not caught"

    seed_hint = {"version": 1, "resources": [
        {"id": "k", "type": "confluence-snapshot", "description": "d",
         "remote": "https://x", "local_default": "./knowledge/domain.md"}]}
    assert any("seed" in f["message"] for f in validate_resources(seed_hint)), "seed-doc naming hint missing"
    print("self-test OK")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a collection's external-resources manifest.")
    ap.add_argument("manifest", nargs="?", help="path to resources.yaml (or .json)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.manifest:
        ap.error("manifest path required (or --self-test)")
    data, err = load(args.manifest)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    return report(args.manifest, validate_resources(data), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
