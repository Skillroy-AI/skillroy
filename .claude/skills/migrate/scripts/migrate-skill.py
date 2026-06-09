#!/usr/bin/env python3
"""migrate-skill: the mechanical half of migrating skills to skillroy compliance.

`plan` inventories a source (skill / collection / repo) read-only; `apply` copies (or, in place,
moves) skills into the home dir, injects the metadata.skillroy block — preserving existing
frontmatter text exactly — patches a `.claude/`-swallowing .gitignore, and adds the
`.agents/skills` symlink. Judgment calls (tier, domain tokens, renames) are INPUTS here, decided
by a human/agent; the script refuses to guess. No git operations. Stdlib only.

Usage:
  python3 migrate-skill.py plan  <source> [--json]
  python3 migrate-skill.py apply <source> --dest <repo-root> --tier <tier>
          [--home .claude/skills] [--phase adhoc] [--version 0.1.0]
          [--domain <skill>=<token> ...] [--license <SPDX>] [--json]
  python3 migrate-skill.py --self-test
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
import tempfile

TIERS = ("kb", "ops", "int", "dx", "core", "meta")
PHASES = ("brainstorming", "adhoc", "publish")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HOMES = (".claude/skills", ".agents/skills", "skills")  # search order


def find_skills(source):
    """Return (skills, homes_found): skills = {name: dir}; a skill dir is one containing SKILL.md."""
    source = os.path.abspath(source)
    if os.path.isfile(os.path.join(source, "SKILL.md")):
        return {os.path.basename(source): source}, ["(single skill)"]
    skills, homes = {}, []
    candidates = [os.path.join(source, h) for h in HOMES] + [source]
    for base in candidates:
        found = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(base, "*", "SKILL.md")))
        if not found:
            continue
        homes.append(os.path.relpath(base, source) if base != source else "(top level)")
        for d in found:
            name = os.path.basename(d)
            if name in skills and os.path.realpath(skills[name]) != os.path.realpath(d):
                print(f"warning: '{name}' found in two homes; keeping {skills[name]}", file=sys.stderr)
                continue
            skills.setdefault(name, d)
    return skills, homes


def read_frontmatter_text(path):
    """Return (full_text, fm_end_line_index) where lines[fm_end] is the closing '---', else (text, None)."""
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text, None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return text, i
    return text, None


def skill_report(skill_dir):
    smd = os.path.join(skill_dir, "SKILL.md")
    text, fm_end = read_frontmatter_text(smd)
    fm = "".join(text.splitlines(keepends=True)[1:fm_end]) if fm_end else ""
    folder = os.path.basename(skill_dir)
    return {
        "skill": folder,
        "path": skill_dir,
        "name_compliant": bool(NAME_RE.match(folder)),
        "frontmatter_parses": fm_end is not None,
        "instrumented": bool(re.search(r"^\s+skillroy:", fm, re.MULTILINE)),
        "has_license": bool(re.search(r"^license:", fm, re.MULTILINE)),
        "has_evals": os.path.isfile(os.path.join(skill_dir, "evals", "evals.json")),
        "has_scripts": os.path.isdir(os.path.join(skill_dir, "scripts")),
    }


def gitignore_trap(repo_root, home):
    """True if repo_root/.gitignore ignores the home dir's top (e.g. `.claude/` swallowing .claude/skills)."""
    gi = os.path.join(repo_root, ".gitignore")
    if not os.path.isfile(gi) or not home.startswith(".claude"):
        return False
    pats = [l.strip() for l in open(gi, encoding="utf-8") if l.strip() and not l.startswith("#")]
    return any(p in (".claude", ".claude/", "/.claude", "/.claude/") for p in pats) \
        and f"!{home.rstrip('/')}/" not in pats and f"!{home.rstrip('/')}" not in pats


def plan(source, home=".claude/skills"):
    skills, homes = find_skills(source)
    out = {"source": os.path.abspath(source), "homes_found": homes, "target_home": home,
           "skills": [], "actions": [], "decisions": []}
    if not skills:
        out["actions"].append("nothing to do: no SKILL.md found under the source")
        return out
    for name in sorted(skills):
        rep = skill_report(skills[name])
        out["skills"].append(rep)
        rel = os.path.relpath(skills[name], os.path.abspath(source))
        if not rel.startswith(home):
            out["actions"].append(f"move/copy {rel} -> {home}/{name}/")
        if not rep["instrumented"]:
            out["actions"].append(f"inject metadata.skillroy into {name} (tier=?, domain=?)")
        if not rep["has_evals"]:
            out["actions"].append(f"author or import evals for {name} (agent work; see CONVENTIONS §8)")
        if not rep["name_compliant"]:
            out["decisions"].append(f"'{name}' is not kebab-case — renames are breaking; decide explicitly")
    out["decisions"].insert(0, "tier: decide what these skills ARE (kb/ops/int/dx/core/meta) — not guessable")
    out["decisions"].append("domain tokens: only from the canonical catalog; otherwise propose, never invent")
    coll = os.path.basename(os.path.abspath(source))
    if not NAME_RE.match(coll) or re.search(r"(?i)-(tools|skills|repo)$", coll):
        out["decisions"].append(f"collection name '{coll}' is non-compliant (<tier>-<domain>) — repo rename is the owner's call")
    if gitignore_trap(source, home):
        out["actions"].append(f".gitignore ignores the skills home — patch to `.claude/*` + `!{home}/`")
    if not os.path.lexists(os.path.join(source, ".agents", "skills")) or homes == [".agents/skills"]:
        out["actions"].append("ensure .agents/skills symlink -> ../" + home)
    return out


SKILLROY_BLOCK = "metadata:\n  skillroy:\n    phase: {phase}\n    tier: {tier}\n    version: {version}\n"


def inject_metadata(text, tier, phase, version, domain=None, license_=None):
    """Insert metadata.skillroy (and optionally license) into frontmatter text, byte-preserving the rest.

    Returns (new_text, status) where status is 'injected' | 'already-instrumented' | 'no-frontmatter'.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text, "no-frontmatter"
    fm_end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if fm_end is None:
        return text, "no-frontmatter"
    fm = "".join(lines[1:fm_end])
    if re.search(r"^\s+skillroy:", fm, re.MULTILINE):
        return text, "already-instrumented"

    sub = "  skillroy:\n    phase: %s\n    tier: %s\n    version: %s\n" % (phase, tier, version)
    if domain:
        sub += f"    domain: {domain}\n"
    meta_idx = next((i for i in range(1, fm_end) if re.match(r"^metadata:\s*$", lines[i])), None)
    if meta_idx is not None:
        lines.insert(meta_idx + 1, sub)
        fm_end += 1
    else:
        lines.insert(fm_end, "metadata:\n" + sub)
        fm_end += 1
    if license_ and not re.search(r"^license:", fm, re.MULTILINE):
        lines.insert(fm_end, f"license: {license_}\n")
    return "".join(lines), "injected"


def patch_gitignore(repo_root, home):
    gi = os.path.join(repo_root, ".gitignore")
    lines = open(gi, encoding="utf-8").read().splitlines(keepends=True)
    out, patched = [], False
    for l in lines:
        if not patched and l.strip() in (".claude", ".claude/", "/.claude", "/.claude/"):
            out.append(".claude/*\n")
            out.append(f"!{home.rstrip('/')}/\n")
            patched = True
        else:
            out.append(l)
    if patched:
        open(gi, "w", encoding="utf-8").write("".join(out))
    return patched


def apply(source, dest, tier, phase="adhoc", version="0.1.0", domains=None,
          license_=None, home=".claude/skills"):
    if tier not in TIERS:
        raise SystemExit(f"--tier is required and must be one of {TIERS} — the tier is a decision, not a default")
    if phase == "publish":
        raise SystemExit("refusing --phase publish: publish is earned by an eval run (CONVENTIONS §7-8), not granted by migration")
    domains = domains or {}
    source, dest = os.path.abspath(source), os.path.abspath(dest)
    in_place = os.path.realpath(source) == os.path.realpath(dest)
    skills, _ = find_skills(source)
    if not skills:
        raise SystemExit("no SKILL.md found under the source")
    unknown = sorted(set(domains) - set(skills))
    if unknown:
        raise SystemExit(f"--domain for unknown skill(s): {unknown}")

    home_abs = os.path.join(dest, home)
    os.makedirs(home_abs, exist_ok=True)
    actions = []
    for name in sorted(skills):
        src_dir, dst_dir = skills[name], os.path.join(home_abs, name)
        if os.path.realpath(src_dir) != os.path.realpath(dst_dir):
            if os.path.exists(dst_dir):
                actions.append(f"{name}: destination already exists — left as-is")
                continue
            (shutil.move if in_place else shutil.copytree)(src_dir, dst_dir)
            actions.append(f"{name}: {'moved' if in_place else 'copied'} -> {os.path.relpath(dst_dir, dest)}")
        smd = os.path.join(dst_dir, "SKILL.md")
        text = open(smd, encoding="utf-8").read()
        new, status = inject_metadata(text, tier, phase, version, domains.get(name), license_)
        if status == "injected":
            open(smd, "w", encoding="utf-8").write(new)
        actions.append(f"{name}: metadata {status}" + (f" (domain={domains[name]})" if name in domains and status == "injected" else ""))

    if gitignore_trap(dest, home):
        if patch_gitignore(dest, home):
            actions.append(f".gitignore: patched to `.claude/*` + `!{home}/`")
    agents_link = os.path.join(dest, ".agents", "skills")
    if home != ".agents/skills" and not os.path.lexists(agents_link):
        os.makedirs(os.path.dirname(agents_link), exist_ok=True)
        os.symlink(os.path.join("..", *home.split("/")), agents_link)
        actions.append(f".agents/skills: symlinked -> ../{home}")
    elif in_place and os.path.isdir(agents_link) and not os.path.islink(agents_link) and not os.listdir(agents_link):
        os.rmdir(agents_link)
        os.symlink(os.path.join("..", *home.split("/")), agents_link)
        actions.append(f".agents/skills: emptied by the move; replaced with symlink -> ../{home}")
    actions.append("next: author/import evals per skill; lint with review (lint-skill.py --tokens <catalog>)")
    return {"source": source, "dest": dest, "in_place": in_place, "actions": actions}


def self_test():
    tmp = tempfile.mkdtemp(prefix="skillroy-migrate-")
    try:
        # Fixture repo: two skills under .agents/skills; one already instrumented; .claude/ gitignored.
        repo = os.path.join(tmp, "Old-Tools")
        for name, fm_extra in (("alpha", ""), ("beta", "metadata:\n  skillroy:\n    phase: adhoc\n    tier: dx\n    version: 0.1.0\n")):
            d = os.path.join(repo, ".agents", "skills", name)
            os.makedirs(d)
            open(os.path.join(d, "SKILL.md"), "w").write(
                f'---\nname: {name}\ndescription: "does {name}. Use when {name}ing."\n{fm_extra}license: MIT\n---\n# {name}\nBody.\n')
        open(os.path.join(repo, ".gitignore"), "w").write("target/\n.claude/\n")

        p = plan(repo)
        acts = " | ".join(p["actions"])
        assert any(s["skill"] == "alpha" and not s["instrumented"] for s in p["skills"]), p["skills"]
        assert any(s["skill"] == "beta" and s["instrumented"] for s in p["skills"]), p["skills"]
        assert "inject metadata.skillroy into alpha" in acts and "inject metadata.skillroy into beta" not in acts, acts
        assert ".gitignore ignores the skills home" in acts, acts
        assert any("tier:" in d for d in p["decisions"]) and any("collection name" in d for d in p["decisions"]), p["decisions"]
        # plan changed nothing
        assert not os.path.exists(os.path.join(repo, ".claude")), "plan must be read-only"

        # apply: tier is mandatory; publish refused
        try:
            apply(repo, os.path.join(tmp, "x"), tier="bogus")
            raise AssertionError("bogus tier accepted")
        except SystemExit:
            pass
        try:
            apply(repo, os.path.join(tmp, "x"), tier="dx", phase="publish")
            raise AssertionError("publish phase accepted")
        except SystemExit:
            pass

        # copy-mode apply into a fresh repo
        dest = os.path.join(tmp, "dx-alpha")
        os.makedirs(dest)
        open(os.path.join(dest, ".gitignore"), "w").write(".claude/\n")
        r = apply(repo, dest, tier="dx", domains={"alpha": "tok-a"})
        joined = " | ".join(r["actions"])
        assert "alpha: copied" in joined and "alpha: metadata injected (domain=tok-a)" in joined, joined
        assert "beta: metadata already-instrumented" in joined, joined
        assert ".gitignore: patched" in joined and ".agents/skills: symlinked" in joined, joined
        alpha_new = open(os.path.join(dest, ".claude", "skills", "alpha", "SKILL.md")).read()
        assert "    domain: tok-a\n" in alpha_new and "license: MIT" in alpha_new, alpha_new
        assert alpha_new.endswith("# alpha\nBody.\n"), "body must be byte-preserved"
        gi = open(os.path.join(dest, ".gitignore")).read()
        assert ".claude/*" in gi and "!.claude/skills/" in gi, gi
        assert os.path.islink(os.path.join(dest, ".agents", "skills")), "symlink missing"
        # original untouched
        assert os.path.isdir(os.path.join(repo, ".agents", "skills", "alpha")), "source was modified"
        assert "skillroy:" not in open(os.path.join(repo, ".agents", "skills", "alpha", "SKILL.md")).read()
        # idempotent re-apply
        r2 = apply(repo, dest, tier="dx", domains={"alpha": "tok-a"})
        j2 = " | ".join(r2["actions"])
        assert "alpha: destination already exists — left as-is" in j2 and "injected" not in j2, j2

        # in-place apply moves and replaces .agents/skills with a symlink
        r3 = apply(repo, repo, tier="dx")
        j3 = " | ".join(r3["actions"])
        assert "alpha: moved" in j3 and ".agents/skills: emptied by the move; replaced with symlink" in j3, j3
        assert os.path.islink(os.path.join(repo, ".agents", "skills")), "in-place symlink missing"
        assert os.path.isfile(os.path.join(repo, ".claude", "skills", "alpha", "SKILL.md"))
        print("self-test OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mechanical skill migration (plan/apply). Judgment calls are inputs.")
    ap.add_argument("command", nargs="?", choices=("plan", "apply"))
    ap.add_argument("source", nargs="?", help="skill folder, collection dir, or repo root")
    ap.add_argument("--dest", help="apply: target repo root (same as source = in place)")
    ap.add_argument("--home", default=".claude/skills", help="skills home inside dest (default .claude/skills)")
    ap.add_argument("--tier", help=f"apply: one of {TIERS} (required — a decision, not a default)")
    ap.add_argument("--phase", default="adhoc", choices=("brainstorming", "adhoc"),
                    help="apply: target phase (publish is earned, not granted)")
    ap.add_argument("--version", default="0.1.0")
    ap.add_argument("--domain", action="append", default=[], metavar="SKILL=TOKEN",
                    help="apply: canonical token for a skill (repeatable; omit for domain-less skills)")
    ap.add_argument("--license", dest="license_", help="apply: add to skills that lack one")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.command or not args.source:
        ap.error("usage: plan <source> | apply <source> --dest <repo> --tier <tier>")
    if args.command == "plan":
        result = plan(args.source, args.home)
    else:
        if not args.dest:
            ap.error("apply needs --dest (use the source itself for in-place)")
        domains = {}
        for d in args.domain:
            if "=" not in d:
                ap.error(f"--domain expects SKILL=TOKEN, got '{d}'")
            k, v = d.split("=", 1)
            domains[k] = v
        result = apply(args.source, args.dest, args.tier, args.phase, args.version,
                       domains, args.license_, args.home)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key in ("homes_found", "skills"):
            if key in result and result[key]:
                if key == "skills":
                    for s in result["skills"]:
                        flags = [k for k in ("instrumented", "has_evals", "has_license") if not s[k]]
                        print(f"  {s['skill']}: " + (f"missing {', '.join(flags)}" if flags else "compliant-ish"))
                else:
                    print(f"homes found: {result[key]}")
        for a in result.get("actions", []):
            print(f"  - {a}")
        if result.get("decisions"):
            print("decisions needed (yours, not the script's):")
            for d in result["decisions"]:
                print(f"  ? {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
