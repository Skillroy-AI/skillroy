#!/usr/bin/env python3
"""new-skill — scaffold a skillroy-compliant Agent Skill.

The CLI "second door" for the `create` skill: deterministic skeleton generation,
runnable standalone (terminal / CI) or invoked by the agent. Stdlib only.

    python3 new-skill.py <name> [--dir .claude/skills] [--tier meta] \\
        [--kind action|knowledge] [--description "..."] [--phase brainstorming] \\
        [--domain <token>] [--version 0.1.0] [--license Apache-2.0] [--with-scripts] [--force]
    python3 new-skill.py --self-test
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PHASES = ("brainstorming", "adhoc", "publish")
TIERS = ("kb", "ops", "int", "dx", "core", "meta")


def validate_name(name):
    """Enforce conventions §1: kebab-case [a-z0-9-], <=64, no leading/trailing/double hyphen."""
    if not NAME_RE.match(name):
        raise ValueError(
            f"invalid name '{name}': use kebab-case [a-z0-9-] with no leading/trailing/double hyphen"
        )
    if len(name) > 64:
        raise ValueError(f"name too long ({len(name)} > 64)")
    return name


def title_of(name):
    return " ".join(w.capitalize() for w in name.split("-"))


def yaml_dq(s):
    """Double-quote a scalar for YAML frontmatter so colons/quotes can't break parsing."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def skill_md(name, description, phase, tier, version, domain, license_, with_scripts):
    desc = description or "TODO: what this skill does + when to use it (include trigger phrases)."
    out = ["---", f"name: {name}", f"description: {yaml_dq(desc)}", "metadata:", "  skillroy:",
           f"    phase: {phase}"]
    out.append(f"    tier: {tier}" if tier else "    tier: TODO  # kb | ops | int | core | meta")
    out.append(f"    version: {version}")
    if domain:
        out.append(f"    domain: {domain}")
    if license_:
        out.append(f"license: {license_}")
    out += ["---", "", f"# {title_of(name)}", "",
            desc if description else "TODO: one-line summary — what it does and when to use it.", "",
            f"> Scaffolded by skillroy `create` at phase `{phase}`. Fill in the sections below;",
            "> check the project conventions before advancing the phase.", "",
            "## Workflow", "", "1. TODO — the steps the agent follows.", "",
            "## References", "",
            "Put progressive-disclosure detail in `references/` and link it here."]
    if with_scripts:
        out += ["", '## Scripts (the CLI "second door")', "",
                f"Deterministic or heavy work lives in `scripts/`. This skill ships `scripts/{name}.py` —",
                "run it standalone (terminal / CI) or let the agent invoke it; the body above says which",
                "script to run and how to read its output, so the chat and CLI paths stay in sync."]
    return "\n".join(out) + "\n"


def evals_stub(name):
    return json.dumps({
        "skill_name": name,
        "evals": [{
            "id": 1,
            "prompt": "TODO: a representative user request that should invoke this skill.",
            "expected_output": "TODO: describe the expected behaviour.",
            "files": [],
            "expectations": ["TODO: a concrete, checkable assertion about the result."],
        }],
    }, indent=2) + "\n"


def starter_script(name):
    return (
        "#!/usr/bin/env python3\n"
        f'"""{name} — TODO: what this script does (stdlib only)."""\n'
        "import argparse\n\n\n"
        "def main():\n"
        "    ap = argparse.ArgumentParser()\n"
        '    ap.add_argument("--self-test", action="store_true")\n'
        "    args = ap.parse_args()\n"
        "    if args.self_test:\n"
        '        print("ok")\n'
        "        return\n"
        "    # TODO: implement\n\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def scaffold(name, dest_dir, description=None, phase="brainstorming", tier=None,
             version="0.1.0", domain=None, license_=None, with_scripts=False, force=False):
    validate_name(name)
    if phase not in PHASES:
        raise ValueError(f"invalid phase '{phase}'; choose from {PHASES}")
    if tier and tier not in TIERS:
        raise ValueError(f"invalid tier '{tier}'; choose from {TIERS}")
    root = os.path.join(dest_dir, name)
    if os.path.exists(root) and not force:
        raise FileExistsError(f"{root} already exists (use --force to overwrite)")
    created = []

    def write(rel, content, executable=False):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)
        if executable:
            os.chmod(path, 0o755)
        created.append(os.path.relpath(path, dest_dir))

    write("SKILL.md", skill_md(name, description, phase, tier, version, domain, license_, with_scripts))
    write("references/.gitkeep", "")
    write("evals/evals.json", evals_stub(name))
    if with_scripts:
        write(f"scripts/{name}.py", starter_script(name), executable=True)
    return root, created


def self_test():
    tmp = tempfile.mkdtemp(prefix="skillroy-newskill-")
    try:
        root, created = scaffold("test-skill", tmp, description="A test: trigger when X.", phase="adhoc",
                                 tier="meta", with_scripts=True)
        smd = open(os.path.join(root, "SKILL.md")).read()
        assert "name: test-skill" in smd, "name not stamped"
        assert 'description: "A test: trigger when X."' in smd, "description not safely quoted"
        assert "phase: adhoc" in smd, "phase not stamped"
        assert "tier: meta" in smd, "tier not stamped"
        assert os.path.basename(root) == "test-skill", "folder must equal name"
        assert os.path.exists(os.path.join(root, "evals", "evals.json")), "evals missing"
        assert os.path.exists(os.path.join(root, "scripts", "test-skill.py")), "script missing"
        for bad in ("Bad", "a--b", "-x", "x-", "a_b", ""):
            try:
                validate_name(bad)
                raise AssertionError(f"accepted bad name {bad!r}")
            except ValueError:
                pass
        print("self-test OK:", ", ".join(created))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scaffold a skillroy-compliant Agent Skill.")
    ap.add_argument("name", nargs="?", help="skill name (kebab-case [a-z0-9-], <=64)")
    ap.add_argument("--dir", default=".claude/skills", help="where to create it (default .claude/skills)")
    ap.add_argument("--tier", choices=TIERS, help="kb | ops | int | core | meta")
    ap.add_argument("--kind", choices=("action", "knowledge"), help="action -> verb; knowledge -> noun")
    ap.add_argument("--description", help="frontmatter description (what + when)")
    ap.add_argument("--phase", choices=PHASES, default="brainstorming")
    ap.add_argument("--domain", help="canonical token from the collection's catalog")
    ap.add_argument("--version", default="0.1.0")
    ap.add_argument("--license", dest="license_", help="e.g. Apache-2.0")
    ap.add_argument("--with-scripts", action="store_true", help="add scripts/ + a starter (CLI door)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="offline self-test in a temp dir")
    args = ap.parse_args(argv)

    if args.self_test:
        self_test()
        return 0
    if not args.name:
        ap.error("name is required (or use --self-test)")
    try:
        root, created = scaffold(args.name, args.dir, args.description, args.phase, args.tier,
                                 args.version, args.domain, args.license_, args.with_scripts, args.force)
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Scaffolded '{args.name}' (phase {args.phase}) at {root}")
    for rel in created:
        print(f"  + {rel}")
    if args.kind:
        hint = "verb (action)" if args.kind == "action" else "noun (knowledge)"
        print(f"Reminder: the name should read as a {hint}; don't repeat the repo/domain.")
    print("Next: write the description (what + when), fill the workflow, add evals, then run `review`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
