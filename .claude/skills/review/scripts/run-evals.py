#!/usr/bin/env python3
"""run-evals — validate a skill's evals and list the cases to run (the deterministic slice).

The pass/fail judgement is an agent's job: run the skill against each `prompt` (with any `files`) and
check the `expectations` (see CONVENTIONS.md §8). This script validates `evals/evals.json`'s structure
and prints the cases so an agent (or human) can execute them. Stdlib only.

    python3 run-evals.py <skill-dir-or-collection> [--json]
    python3 run-evals.py --log <skill-dir>     # scaffold evals/runs/<date>.md (CONVENTIONS §8)
    python3 run-evals.py --self-test

Exit status is non-zero if any finding is an `error`.
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import tempfile


def check_evals(skill_dir):
    folder = os.path.basename(os.path.abspath(skill_dir))
    res = {"skill": folder, "evals_file": None, "cases": [], "findings": []}

    def add(sev, msg):
        res["findings"].append({"severity": sev, "message": msg})

    res["runs"] = sorted(os.path.basename(p)
                         for p in glob.glob(os.path.join(skill_dir, "evals", "runs", "*.md")))

    path = os.path.join(skill_dir, "evals", "evals.json")
    if not os.path.isfile(path):
        add("info", "no evals/evals.json (publish-bar item)")
        return res
    res["evals_file"] = path
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        add("error", f"evals.json is not valid JSON: {exc}")
        return res
    evals = data.get("evals") if isinstance(data, dict) else None
    if not isinstance(evals, list) or not evals:
        add("error", "evals.json has no non-empty 'evals' list")
        return res
    for i, e in enumerate(evals):
        if not isinstance(e, dict):
            add("error", f"evals[{i}]: not an object")
            continue
        cid = e.get("id", i)
        if not e.get("prompt"):
            add("error", f"eval {cid}: missing 'prompt'")
        exps = e.get("expectations")
        if not isinstance(exps, list) or not exps:
            add("warn", f"eval {cid}: no 'expectations' (assertions) to check")
        res["cases"].append({
            "id": cid,
            "prompt": (e.get("prompt") or "")[:140],
            "files": e.get("files") or [],
            "expectations": len(exps) if isinstance(exps, list) else 0,
        })
    return res


def run_path(path):
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        return [check_evals(path)]
    dirs = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(path, "*", "SKILL.md")))
    return [check_evals(d) for d in dirs]


def scaffold_log(skill_dir, date=None):
    """Scaffold evals/runs/<date>[-n].md from evals.json (CONVENTIONS §8). Returns (path, err)."""
    res = check_evals(skill_dir)
    if not res["evals_file"]:
        return None, "no evals/evals.json to scaffold from"
    if any(f["severity"] == "error" for f in res["findings"]):
        return None, "evals.json has errors — fix them first"
    data = json.load(open(res["evals_file"], encoding="utf-8"))

    version = phase = "?"
    smd_path = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(smd_path):
        smd = open(smd_path, encoding="utf-8").read()
        m = re.search(r"^\s*version:\s*['\"]?([0-9][\w.+-]*)", smd, re.MULTILINE)
        version = m.group(1) if m else "?"
        m = re.search(r"^\s*phase:\s*(\w+)", smd, re.MULTILINE)
        phase = m.group(1) if m else "?"

    runs_dir = os.path.join(skill_dir, "evals", "runs")
    os.makedirs(runs_dir, exist_ok=True)
    date = date or datetime.date.today().isoformat()
    path, n = os.path.join(runs_dir, f"{date}.md"), 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(runs_dir, f"{date}-{n}.md")

    total = sum(len(e.get("expectations") or []) for e in data["evals"])
    lines = [
        f"# Eval run — {res['skill']} v{version} ({phase})",
        f"- **Date / runner:** {date} / <model or person>",
        '- **Inputs:** <token catalog, fixtures, simulated-user notes — or "none">',
        f"- **Result:** <PASS | FAIL> (?/{len(data['evals'])} evals, ?/{total} expectations)",
    ]
    for e in data["evals"]:
        intent = " ".join((e.get("prompt") or "").split())[:90]
        lines += ["", f"## Eval {e.get('id', '?')} — {intent}"]
        lines += [f"- [ ] {x} — <evidence>" for x in (e.get("expectations") or [])]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return path, None


def self_test():
    tmp = tempfile.mkdtemp(prefix="skillroy-evals-")
    try:
        good = os.path.join(tmp, "good")
        os.makedirs(os.path.join(good, "evals"))
        json.dump({"skill_name": "good", "evals": [
            {"id": 1, "prompt": "do x", "expectations": ["x happened"]}]},
            open(os.path.join(good, "evals", "evals.json"), "w"))
        r = check_evals(good)
        assert not [f for f in r["findings"] if f["severity"] == "error"], r["findings"]
        assert r["cases"] and r["cases"][0]["expectations"] == 1, "case not parsed"

        bad = os.path.join(tmp, "bad")
        os.makedirs(os.path.join(bad, "evals"))
        open(os.path.join(bad, "evals", "evals.json"), "w").write("{ not json")
        assert any(f["severity"] == "error" for f in check_evals(bad)["findings"]), "bad json missed"

        noexp = os.path.join(tmp, "noexp")
        os.makedirs(os.path.join(noexp, "evals"))
        json.dump({"skill_name": "noexp", "evals": [{"id": 1, "prompt": "p"}]},
                  open(os.path.join(noexp, "evals", "evals.json"), "w"))
        assert any("expectations" in f["message"] for f in check_evals(noexp)["findings"]), "missing-exp missed"

        p1, err = scaffold_log(good, date="2026-01-01")
        assert err is None and p1.endswith("2026-01-01.md"), (p1, err)
        body = open(p1, encoding="utf-8").read()
        assert "- [ ] x happened — <evidence>" in body and "# Eval run — good" in body, body
        p2, _ = scaffold_log(good, date="2026-01-01")
        assert p2.endswith("2026-01-01-2.md"), f"collision suffix missed: {p2}"
        assert check_evals(good)["runs"] == ["2026-01-01-2.md", "2026-01-01.md"], "runs not listed"
        assert scaffold_log(bad)[1], "scaffold should refuse a broken evals.json"
        print("self-test OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate + list a skill's evals (run them with an agent).")
    ap.add_argument("path", nargs="?", help="a skill folder or a collection directory")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--log", action="store_true",
                    help="scaffold evals/runs/<date>.md for this skill (CONVENTIONS §8)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.path:
        ap.error("path is required (or use --self-test)")
    if args.log:
        if not os.path.isfile(os.path.join(args.path, "SKILL.md")):
            ap.error("--log needs a single skill folder (one containing SKILL.md)")
        path, err = scaffold_log(args.path)
        if err:
            print(f"error: {err}")
            return 1
        print(f"run log scaffolded: {path} — fill in the verdicts as you judge")
        return 0
    results = run_path(args.path)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"\n== {r['skill']} ==")
            for f in r["findings"]:
                print(f"  [{f['severity']:<5}] {f['message']}")
            for c in r["cases"]:
                files = f" files={c['files']}" if c["files"] else ""
                print(f"  - eval {c['id']}: {c['expectations']} assertion(s){files} -- {c['prompt']}")
            if r.get("runs"):
                print(f"  runs recorded: {len(r['runs'])} (latest: {r['runs'][-1]})")
            elif r["cases"]:
                print("  runs recorded: none — scaffold one with --log")
            if not r["findings"] and not r["cases"]:
                print("  (no evals)")
    errors = sum(1 for r in results for f in r["findings"] if f["severity"] == "error")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
