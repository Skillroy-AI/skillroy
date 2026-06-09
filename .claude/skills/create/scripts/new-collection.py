#!/usr/bin/env python3
"""new-collection — bootstrap a skillroy-compliant skill collection (CONVENTIONS §10).

The second CLI door of the `create` skill: scaffolds the collection shell — README with the
collection metadata block, the safe .gitignore (.claude/* + !.claude/skills/), .gitattributes,
the .claude/skills/ home, and the .agents/skills symlink. With --with-skill it also scaffolds
the first skill (via the sibling new-skill.py). Git-free by design: it prints the git init
next-steps instead of running them. Stdlib only.

    python3 new-collection.py <tier>-<domain> [--dir <parent>] [--owner "..."] [--license SPDX]
        [--depends-on <collection> ...] [--with-skill <skill-name>] [--brand] [--force]
    python3 new-collection.py --self-test
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TIERS = ("kb", "ops", "int", "dx", "core", "meta")
REDUNDANT_SUFFIX_RE = re.compile(r"(?i)-(tools|skills|repo)$")
HOME = ".claude/skills"

README_TMPL = """\
# {name}

TODO: one paragraph — what domain this collection covers and who it serves.

Skills live in `{home}/` (`.agents/skills` is a symlink for agents that read that convention).
Author with skillroy's `create`, lint with `review`; every skill ships evals (skillroy CONVENTIONS §8).

## Collection metadata

```yaml
collection:
  name: {name}
  status: experimental   # promote to active once it has real, linted content
  owner: {owner}
  license: {license}
  depends-on: [{depends}]
```
"""

GITIGNORE = """\
# Local agent session state stays out; the skills home is a project artifact (skillroy CONVENTIONS §10)
.claude/*
!.claude/skills/
__pycache__/
*.pyc
.DS_Store
"""


def validate_collection_name(name, brand=False):
    """Return the tier encoded in the name (None for --brand). Raises ValueError when non-compliant."""
    if not NAME_RE.match(name):
        raise ValueError(f"invalid name '{name}': lowercase kebab-case [a-z0-9-] only")
    if REDUNDANT_SUFFIX_RE.search(name):
        raise ValueError(f"'{name}' has a redundant suffix (-tools/-skills/-repo) — the tier conveys that")
    if brand:
        return None
    tier = name.split("-", 1)[0]
    if tier not in TIERS or "-" not in name:
        raise ValueError(
            f"'{name}' doesn't match <tier>-<domain> (tiers: {', '.join(TIERS)}); "
            "brand-named collections are the exception — pass --brand if this is one")
    return tier


def scaffold_collection(name, parent=".", owner=None, license_=None, depends_on=None,
                        brand=False, with_skill=None, force=False):
    tier = validate_collection_name(name, brand)
    root = os.path.join(os.path.abspath(parent), name)
    if os.path.exists(root) and not force:
        raise FileExistsError(f"{root} already exists (use --force to overwrite files into it)")
    created, notes = [], []

    def write(rel, content):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)
        created.append(rel)

    write("README.md", README_TMPL.format(
        name=name, home=HOME, owner=owner or "TODO",
        license=license_ or "TODO",
        depends=", ".join(depends_on or [])))
    write(".gitignore", GITIGNORE)
    write(".gitattributes", "* text=auto eol=lf\n")

    home_abs = os.path.join(root, *HOME.split("/"))
    os.makedirs(home_abs, exist_ok=True)
    if not with_skill:
        write(f"{HOME}/.gitkeep", "")

    link = os.path.join(root, ".agents", "skills")
    if not os.path.lexists(link):
        os.makedirs(os.path.dirname(link), exist_ok=True)
        try:
            os.symlink(os.path.join("..", *HOME.split("/")), link)
            created.append(".agents/skills -> ../" + HOME)
        except OSError as exc:
            notes.append(f".agents/skills symlink not created ({exc}) — create it manually if needed")

    if with_skill:
        sibling = os.path.join(os.path.dirname(os.path.abspath(__file__)), "new-skill.py")
        if not os.path.isfile(sibling):
            raise FileNotFoundError(f"sibling scaffolder not found: {sibling}")
        cmd = [sys.executable, sibling, with_skill, "--dir", home_abs]
        if tier:
            cmd += ["--tier", tier]
        if license_:
            cmd += ["--license", license_]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"new-skill.py failed: {(r.stderr or r.stdout).strip()}")
        created.append(f"{HOME}/{with_skill}/ (via new-skill.py" + (f", tier {tier})" if tier else ", tier TODO)"))
        if not tier:
            notes.append(f"--brand collection: set the skill's tier in {HOME}/{with_skill}/SKILL.md yourself")

    notes.append(f"next: cd {root} && git init -b main && git add -A && git commit  (scripts are git-free by design)")
    notes.append("then: fill the README TODOs; author skills (new-skill.py --dir "
                 f"{name}/{HOME}); lint with review's lint-skill.py")
    return root, created, notes


def self_test():
    tmp = tempfile.mkdtemp(prefix="skillroy-newcoll-")
    try:
        root, created, notes = scaffold_collection(
            "dx-widgets", tmp, owner="Test Owner", license_="Apache-2.0",
            depends_on=["acme-skillroy"], with_skill="reshape")
        readme = open(os.path.join(root, "README.md")).read()
        assert "name: dx-widgets" in readme and "status: experimental" in readme, readme
        assert "depends-on: [acme-skillroy]" in readme, readme
        gi = open(os.path.join(root, ".gitignore")).read()
        assert ".claude/*" in gi and "!.claude/skills/" in gi, gi
        assert os.path.islink(os.path.join(root, ".agents", "skills")), "symlink missing"
        smd = open(os.path.join(root, ".claude", "skills", "reshape", "SKILL.md")).read()
        assert "tier: dx" in smd, "skill must inherit the collection tier"
        assert not os.path.exists(os.path.join(root, ".claude", "skills", ".gitkeep")), \
            ".gitkeep should be skipped when a skill is scaffolded"
        assert any("git init" in n for n in notes), "git next-step note missing"

        empty_root, _, _ = scaffold_collection("ops-store", tmp)
        assert os.path.isfile(os.path.join(empty_root, ".claude", "skills", ".gitkeep")), \
            "empty home needs .gitkeep"

        for bad in ("Widgets", "dx-widgets-tools", "widgets", "dx_widgets", "dx"):
            try:
                scaffold_collection(bad, tmp)
                raise AssertionError(f"accepted bad collection name {bad!r}")
            except ValueError:
                pass
        brand_root, _, brand_notes = scaffold_collection("widgetroy", tmp, brand=True, with_skill="frob")
        assert "tier: TODO" in open(os.path.join(brand_root, ".claude", "skills", "frob", "SKILL.md")).read(), \
            "brand collection skill should carry tier TODO"
        assert any("set the skill's tier" in n for n in brand_notes), brand_notes
        try:
            scaffold_collection("dx-widgets", tmp)
            raise AssertionError("existing dir accepted without --force")
        except FileExistsError:
            pass
        print("self-test OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bootstrap a skillroy-compliant skill collection.")
    ap.add_argument("name", nargs="?", help="collection name: <tier>-<domain> (or --brand)")
    ap.add_argument("--dir", default=".", help="parent directory to create it in (default: cwd)")
    ap.add_argument("--owner", help="owner for the README metadata block")
    ap.add_argument("--license", dest="license_", help="e.g. Apache-2.0 or PROPRIETARY")
    ap.add_argument("--depends-on", action="append", default=[], metavar="COLLECTION",
                    help="dependency for the metadata block (repeatable; e.g. your org overlay)")
    ap.add_argument("--with-skill", metavar="SKILL", help="also scaffold the first skill (inherits the tier)")
    ap.add_argument("--brand", action="store_true",
                    help="brand-named collection — skip the <tier>-<domain> name rule")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.name:
        ap.error("collection name required (or --self-test)")
    try:
        root, created, notes = scaffold_collection(
            args.name, args.dir, args.owner, args.license_, args.depends_on,
            args.brand, args.with_skill, args.force)
    except (ValueError, FileExistsError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Scaffolded collection '{args.name}' at {root}")
    for rel in created:
        print(f"  + {rel}")
    for n in notes:
        print(f"  ! {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
