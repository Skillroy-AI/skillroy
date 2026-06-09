#!/usr/bin/env python3
"""validate-tokens — check a canonical token catalog against the skillroy schema (tokens/catalog-schema.md).

skillroy ships the schema; an org supplies the catalog (in its overlay). Accepts YAML (needs PyYAML)
or JSON (stdlib). Used by `create` (domain-token check) and `review`.

    python3 validate-tokens.py <catalog.yaml|catalog.json> [--json]
    python3 validate-tokens.py --self-test

Exit status is non-zero if any finding is an `error`.
"""
import argparse
import json
import os
import re
import sys

TOKEN_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STATUSES = ("confirmed", "proposed", "legacy")


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
        return None, "PyYAML not installed — convert the catalog to .json, or `pip install pyyaml`"
    try:
        with open(path) as fh:
            return yaml.safe_load(fh), None
    except Exception as exc:
        return None, f"invalid YAML: {exc}"


def validate(data):
    findings = []

    def add(sev, msg):
        findings.append({"severity": sev, "message": msg})

    if not isinstance(data, dict) or not isinstance(data.get("tokens"), list):
        add("error", "catalog must be a mapping with a 'tokens' list")
        return findings

    seen = {}
    alias_owner = {}
    for i, t in enumerate(data["tokens"]):
        where = f"tokens[{i}]"
        if not isinstance(t, dict):
            add("error", f"{where}: not a mapping")
            continue
        tok = t.get("token")
        if not tok:
            add("error", f"{where}: missing 'token'")
        else:
            where = f"token '{tok}'"
            if not TOKEN_RE.match(str(tok)):
                add("error", f"{where}: not lowercase kebab-case [a-z0-9-]")
            if tok in seen:
                add("error", f"{where}: duplicate (also at tokens[{seen[tok]}])")
            seen[tok] = i
        if not t.get("name"):
            add("warn", f"{where}: missing 'name'")
        status = t.get("status")
        if status not in STATUSES:
            add("error", f"{where}: status '{status}' invalid; choose {list(STATUSES)}")
        if status == "legacy" and not (t.get("replaced_by") or t.get("notes")):
            add("warn", f"{where}: legacy token has no 'replaced_by' or 'notes'")
        for field in ("aliases", "sources"):
            if field in t and not isinstance(t[field], list):
                add("error", f"{where}: '{field}' must be a list")
        for a in t.get("aliases") or []:
            if a in alias_owner and alias_owner[a] != tok:
                add("warn", f"{where}: alias '{a}' also used by token '{alias_owner[a]}'")
            alias_owner[a] = tok

    for alias, owner in alias_owner.items():
        if alias in seen:
            add("error", f"alias '{alias}' (of '{owner}') collides with a canonical token")
    return findings


def self_test():
    good = {"version": 1, "tokens": [
        {"token": "alpha", "name": "Alpha", "status": "confirmed"},
        {"token": "legacy-beta", "name": "Beta", "status": "legacy", "replaced_by": "alpha"}]}
    assert not [f for f in validate(good) if f["severity"] == "error"], "good catalog errored"

    bad = {"version": 1, "tokens": [
        {"token": "Alpha", "name": "A", "status": "confirmed"},                 # uppercase -> error
        {"token": "beta", "status": "bogus"},                                   # bad status -> error
        {"token": "beta", "name": "dup", "status": "confirmed"},                # duplicate -> error
        {"token": "gamma", "name": "G", "status": "confirmed", "aliases": ["alpha"]}]}  # alias==token? no 'alpha' token here
    errs = [f for f in validate(bad) if f["severity"] == "error"]
    assert errs, "bad catalog not caught"
    # alias/token collision
    coll = {"version": 1, "tokens": [
        {"token": "x", "name": "X", "status": "confirmed", "aliases": ["y"]},
        {"token": "y", "name": "Y", "status": "confirmed"}]}
    assert any("collides" in f["message"] for f in validate(coll)), "alias/token collision missed"
    print("self-test OK")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a canonical token catalog.")
    ap.add_argument("path", nargs="?", help="catalog file (.yaml or .json)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        self_test()
        return 0
    if not args.path:
        ap.error("path is required (or use --self-test)")
    data, err = load(args.path)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    findings = validate(data)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        n = len(data["tokens"]) if isinstance(data, dict) and isinstance(data.get("tokens"), list) else 0
        print(f"{os.path.basename(args.path)}: {n} tokens")
        for f in findings:
            print(f"  [{f['severity']:<5}] {f['message']}")
        if not findings:
            print("  ok — no findings")
    return 1 if any(f["severity"] == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
