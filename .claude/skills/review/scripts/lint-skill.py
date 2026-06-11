#!/usr/bin/env python3
"""lint-skill — check a skill (or a directory of skills) against skillroy conventions.

The CLI "second door" for the `review` skill. Stdlib only; uses PyYAML if present for a definitive
frontmatter parse, otherwise a lightweight extractor + pitfall heuristics. For authoritative Agent
Skills base-spec conformance, also run `skills-ref validate <skill-dir>` if it is installed.

    python3 lint-skill.py <skill-dir-or-collection> [--phase P] [--json]
    python3 lint-skill.py --self-test

Exit status is non-zero if any finding is an `error`.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PHASES = ("brainstorming", "adhoc", "publish")
TIERS = ("kb", "ops", "int", "dx", "core", "meta")
REDUNDANT_SUFFIX_RE = re.compile(r"(?i)-(tools|skills|repo)$")
SECRET_RE = re.compile(
    r"(?i)\b(password|secret|api[_-]?key|access[_-]?token|private[_-]?key)\b\s*[:=]\s*['\"]?\S{8,}")
SEV_ORDER = {"info": 0, "warn": 1, "error": 2}
SKIP_DIRS = {"skills", ".claude", ".agents", ".cursor", ".codex"}
# Strong signals that a skill leans on an external resource that ought to be declared (CONVENTIONS §11).
EXTERNAL_REF_RE = re.compile(r"(git clone |~/Projects/|https?://\S*atlassian\.net|\bbitbucket\.org|\bgs://|\.war\b)")


def find_collection_root(skill_or_home_dir):
    """The collection root above a skill dir or a skills-home dir (the part before .claude/.agents/.cursor)."""
    p = os.path.abspath(skill_or_home_dir)
    parts = p.split(os.sep)
    for marker in (".claude", ".agents", ".cursor"):
        if marker in parts:
            return os.sep.join(parts[:parts.index(marker)]) or os.sep
    return os.path.dirname(os.path.dirname(p))


def split_frontmatter(text):
    if not text.startswith("---"):
        return None, "no YAML frontmatter (file must start with '---')"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "frontmatter not closed (needs a second '---')"
    return parts[1], None


def parse_frontmatter(raw):
    """(data, error). PyYAML if available (definitive); else lightweight extraction."""
    try:
        import yaml
    except ImportError:
        return _extract(raw)
    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        return None, f"frontmatter is not valid YAML: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, None


def _extract(raw):
    """Stdlib fallback: pull the keys we check; flag the unquoted-colon pitfall."""
    for ln in raw.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+):\s+(.*)$", ln)
        if m and m.group(2) and m.group(2)[0] not in "\"'[{" and ": " in m.group(2):
            return None, f"unquoted value for '{m.group(1)}' contains ': ' — quote it"

    def grab(key):
        m = re.search(r"(?m)^\s*%s:\s*(.+?)\s*$" % re.escape(key), raw)
        if not m:
            return None
        v = m.group(1)
        if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
            v = v[1:-1]
        return v

    data = {k: grab(k) for k in ("name", "description", "license") if grab(k) is not None}
    sr = {k: grab(k) for k in ("phase", "tier", "version", "domain") if grab(k) is not None}
    if sr:
        data["metadata"] = {"skillroy": sr}
    return data, None


def _by_phase(phase, should="warn"):
    """publish -> error; adhoc -> `should`; brainstorming/unknown -> info."""
    return "error" if phase == "publish" else (should if phase == "adhoc" else "info")


def load_catalog(path):
    """Load a token catalog (.yaml via PyYAML / .json via stdlib) into lookup maps.

    Returns (index, error); index = {"tokens": {tok: status}, "aliases": {alias: tok},
    "legacy": {tok: replaced_by}}.
    """
    if path.endswith(".json"):
        try:
            with open(path) as fh:
                data = json.load(fh)
        except Exception as exc:
            return None, f"invalid JSON: {exc}"
    else:
        try:
            import yaml
        except ImportError:
            return None, "PyYAML not installed — use a .json catalog or `pip install pyyaml`"
        try:
            with open(path) as fh:
                data = yaml.safe_load(fh)
        except Exception as exc:
            return None, f"invalid YAML: {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("tokens"), list):
        return None, "catalog has no 'tokens' list"
    idx = {"tokens": {}, "aliases": {}, "legacy": {}}
    for t in data["tokens"]:
        if not isinstance(t, dict) or not t.get("token"):
            continue
        idx["tokens"][t["token"]] = t.get("status")
        if t.get("status") == "legacy":
            idx["legacy"][t["token"]] = t.get("replaced_by")
        for a in t.get("aliases") or []:
            idx["aliases"][a] = t["token"]
    return idx, None


def lint_skill(skill_dir, phase_override=None, catalog=None):
    findings = []

    def add(sev, code, msg):
        findings.append({"severity": sev, "code": code, "message": msg})

    folder = os.path.basename(os.path.abspath(skill_dir))
    result = {"skill": folder, "path": skill_dir, "phase": None, "findings": findings}
    smd = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(smd):
        add("error", "no-skill-md", "SKILL.md not found")
        return result

    text = open(smd, encoding="utf-8").read()
    raw, err = split_frontmatter(text)
    if err:
        add("error", "frontmatter", err)
        return result
    data, perr = parse_frontmatter(raw)
    if perr:
        add("error", "frontmatter", perr)
        # Frontmatter is unparseable, but name==folder is still checkable from the raw text.
        m = re.search(r"^name:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", raw, re.MULTILINE)
        if m and m.group(1) != folder:
            add("error", "name", f"name '{m.group(1)}' must equal the folder name '{folder}'")
        return result

    name = data.get("name")
    desc = data.get("description")
    meta = (data.get("metadata") or {}).get("skillroy") or {}
    phase = phase_override or meta.get("phase")
    result["phase"] = phase

    if not name:
        add("error", "name", "frontmatter has no 'name'")
    else:
        if not NAME_RE.match(str(name)):
            add("error", "name", f"name '{name}' is not kebab-case [a-z0-9-]")
        if len(str(name)) > 64:
            add("error", "name", f"name too long ({len(str(name))} > 64)")
        if name != folder:
            add("error", "name", f"name '{name}' must equal the folder name '{folder}'")

    if not desc:
        add(_by_phase(phase), "description", "no 'description' (what + when) — needed for routing")
    elif len(str(desc)) > 1024:
        add("warn", "description", f"description is {len(str(desc))} chars (> 1024)")

    if not meta:
        add("warn", "metadata", "not skillroy-instrumented — no metadata.skillroy block (phase / tier / version)")
    if phase and phase not in PHASES:
        add("error", "phase", f"phase '{phase}' invalid; choose {list(PHASES)}")
    if meta.get("tier") and meta["tier"] not in TIERS:
        add("error", "tier", f"tier '{meta['tier']}' invalid; choose {list(TIERS)}")

    domain = meta.get("domain")
    if catalog is not None and domain:
        if domain in catalog["tokens"]:
            if catalog["tokens"][domain] == "legacy":
                rb = catalog["legacy"].get(domain)
                add("info", "token", f"domain '{domain}' is a legacy token" + (f"; prefer '{rb}'" if rb else ""))
        elif domain in catalog["aliases"]:
            add(_by_phase(phase), "token",
                f"domain '{domain}' is an alias — use the canonical token '{catalog['aliases'][domain]}'")
        else:
            add(_by_phase(phase), "token",
                f"domain '{domain}' is not in the token catalog — add it (proposed) or fix it; never invent a token")

    body = text.split("---", 2)[2] if text.count("---") >= 2 else ""
    has_scripts = os.path.isdir(os.path.join(skill_dir, "scripts"))
    has_evals = bool(glob.glob(os.path.join(skill_dir, "evals", "*")))
    if has_scripts and "scripts/" not in body and ".py" not in body:
        add(_by_phase(phase), "two-doors", "has scripts/ but the body never tells the agent to run them")
    if SECRET_RE.search(text):
        add("error", "secret", "possible plaintext secret in SKILL.md — reference it, never inline")
    pub = phase == "publish"
    if not has_evals:
        add("error" if pub else "info", "evals", "no evals/ (publish-bar item)")
    elif pub and not glob.glob(os.path.join(skill_dir, "evals", "runs", "*.md")):
        add("warn", "evals-run", "no recorded eval run in evals/runs/ — scaffold with run-evals.py --log (§8)")
    if not data.get("license"):
        add("error" if pub else "info", "license", "no 'license' in frontmatter (publish-bar item)")

    # External resources (§11): a non-meta skill that references clones/URLs/artifacts should have its
    # collection declare them in resources.yaml. We nudge only when the manifest is entirely absent;
    # validate-resources.py does the per-entry check. Meta skills (which act on skills) are exempt —
    # their "git clone"/path mentions are instructional, not dependencies.
    if meta.get("tier") != "meta" and EXTERNAL_REF_RE.search(body):
        if not os.path.isfile(os.path.join(find_collection_root(skill_dir), "resources.yaml")):
            add("warn" if pub else "info", "resources",
                "references external resources (clone/URL/artifact) but the collection has no resources.yaml (§11)")
    return result


def collection_findings(path):
    """Repo/collection-name checks (info): names should be lowercase kebab-case, no redundant suffix."""
    parts = [p for p in os.path.abspath(path).split(os.sep) if p]
    while parts and parts[-1] in SKIP_DIRS:
        parts.pop()
    name = parts[-1] if parts else None
    out = []
    if name and not NAME_RE.match(name):
        out.append(("info", "collection-name",
                    f"collection '{name}' is not lowercase kebab-case (repo names: <tier>-<domain>)"))
    if name and REDUNDANT_SUFFIX_RE.search(name):
        out.append(("info", "collection-name",
                    f"collection '{name}' has a redundant suffix (-tools/-skills/-repo) — the tier conveys that"))

    # External-resources manifest (§11): if present at the collection root, it must be well-formed.
    # Deep per-entry validation is validate-resources.py's job (point the user there).
    manifest = os.path.join(find_collection_root(path), "resources.yaml")
    if os.path.isfile(manifest):
        try:
            import yaml
            rdata = yaml.safe_load(open(manifest, encoding="utf-8"))
            if not isinstance(rdata, dict) or not isinstance(rdata.get("resources"), list):
                out.append(("error", "resources",
                            "resources.yaml malformed (needs version + a 'resources' list) — run resources/validate-resources.py"))
            else:
                out.append(("info", "resources",
                            f"resources.yaml present ({len(rdata['resources'])} resources) — validate fully with resources/validate-resources.py"))
        except ImportError:
            pass  # YAML lib absent; frontmatter path already degrades gracefully
        except Exception as exc:
            out.append(("error", "resources", f"resources.yaml is not valid YAML: {exc}"))
    return name, out


def gitignore_trap_findings(path):
    """The gitignore trap (§10; two real-world strikes): a `.gitignore` ANYWHERE between the skills
    home and the *repo* root that matches the home or a skill file silently loses skills — monorepo
    nesting is exactly where it bites, so every level must be walked, which is what
    `git check-ignore` does. Pattern-only check (`--no-index`): already-tracked files still flag,
    because the trap waits for the next new file. Quiet when there is no enclosing git repo or no
    git binary (best-effort)."""
    home = os.path.abspath(path)
    d, root = home, None
    while True:
        if os.path.exists(os.path.join(d, ".git")):  # dir or file (worktree/submodule)
            root = d
            break
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    if root is None:
        return []
    # Probe only content that MUST be tracked. Runtime/derived dirs (__pycache__, venvs, caches)
    # are legitimately ignored inside skill folders — flagging them would be the false positive.
    DERIVED = {"__pycache__", ".venv", "venv", "node_modules", ".pytest_cache", ".mypy_cache"}

    def _is_source(name):
        return not (name in DERIVED or name.startswith(".") or name.endswith((".pyc", ".pyo")))

    probes = []
    skill_dirs = [home] if os.path.isfile(os.path.join(home, "SKILL.md")) else \
        sorted(os.path.dirname(p) for p in glob.glob(os.path.join(home, "*", "SKILL.md")))
    probes.append(home)
    for sd in skill_dirs:
        probes.append(sd)
        probes.append(os.path.join(sd, "SKILL.md"))
        for child in sorted(filter(_is_source, os.listdir(sd))):
            full = os.path.join(sd, child)
            probes.append(full)
            if os.path.isdir(full):
                for f in sorted(filter(_is_source, os.listdir(full)))[:1]:
                    probes.append(os.path.join(full, f))
    out = []
    try:
        r = subprocess.run(["git", "-C", root, "check-ignore", "-v", "--no-index", "--"] + probes,
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            seen = set()
            for ln in r.stdout.splitlines():
                src, _, rest = ln.partition("\t")
                if not rest or src in seen:
                    continue
                # -v reports the DECIDING pattern, negations included — "!pattern" means the
                # path is re-included (not ignored), which is the safe shape, not a trap.
                m = re.match(r"^(.+?):(\d+):(.*)$", src)
                if m and m.group(3).startswith("!"):
                    continue
                seen.add(src)
                rel = os.path.relpath(rest.strip(), root)
                out.append(("error", "gitignore-trap",
                            f"{src} matches '{rel}' — skills under it would be silently lost from git; "
                            f"use the `.claude/*` + `!.claude/skills/` pattern (CONVENTIONS §10)"))
    except Exception:
        pass
    return out


def lint_path(path, phase_override=None, catalog=None):
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        return [lint_skill(path, phase_override, catalog)]
    dirs = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(path, "*", "SKILL.md")))
    return [lint_skill(d, phase_override, catalog) for d in dirs]


def self_test():
    tmp = tempfile.mkdtemp(prefix="skillroy-lint-")
    try:
        good = os.path.join(tmp, "good-skill")
        os.makedirs(os.path.join(good, "evals"))
        open(os.path.join(good, "SKILL.md"), "w").write(
            '---\nname: good-skill\ndescription: "Does X; use when Y."\n'
            "metadata:\n  skillroy:\n    phase: adhoc\n    tier: dx\n    version: 0.1.0\n"
            "license: Apache-2.0\n---\n# Good\n")
        open(os.path.join(good, "evals", "evals.json"), "w").write("{}\n")
        errs = [f for f in lint_skill(good)["findings"] if f["severity"] == "error"]
        assert not errs, f"good skill flagged errors: {errs}"

        bad = os.path.join(tmp, "bad-folder")
        os.makedirs(bad)
        open(os.path.join(bad, "SKILL.md"), "w").write(
            '---\nname: wrong-name\ndescription: "ok"\n'
            "metadata:\n  skillroy:\n    phase: publish\n    tier: meta\n    version: 0.1.0\n---\n"
            '# Bad\nThe api_key: "AKIA0123456789ABCD" is inline.\n')
        codes = {f["code"] for f in lint_skill(bad)["findings"]}
        assert "name" in codes and "secret" in codes, f"bad skill not fully caught: {codes}"

        colon = os.path.join(tmp, "colon-skill")
        os.makedirs(colon)
        open(os.path.join(colon, "SKILL.md"), "w").write(
            "---\nname: colon-skill\ndescription: TODO: unquoted colon\n---\n# x\n")
        assert any(f["code"] == "frontmatter" for f in lint_skill(colon)["findings"]), "colon missed"

        # Broken YAML must not mask a name/folder mismatch (fallback raw-text check).
        colon2 = os.path.join(tmp, "util")
        os.makedirs(colon2)
        open(os.path.join(colon2, "SKILL.md"), "w").write(
            "---\nname: utils\ndescription: TODO: fill in\n---\n# x\n")
        c2 = {f["code"] for f in lint_skill(colon2)["findings"]}
        assert {"frontmatter", "name"} <= c2, f"broken-YAML name mismatch missed: {c2}"

        # At publish, evals without a recorded run warn (evals-run, §8); a runs/*.md clears it.
        pubsk = os.path.join(tmp, "pubsk")
        os.makedirs(os.path.join(pubsk, "evals"))
        open(os.path.join(pubsk, "SKILL.md"), "w").write(
            '---\nname: pubsk\ndescription: "x"\n'
            "metadata:\n  skillroy:\n    phase: publish\n    tier: dx\n    version: 1.0.0\n"
            "license: Apache-2.0\n---\n# x\n")
        open(os.path.join(pubsk, "evals", "evals.json"), "w").write("{}\n")
        assert any(f["code"] == "evals-run" and f["severity"] == "warn"
                   for f in lint_skill(pubsk)["findings"]), "missing run log not flagged at publish"
        os.makedirs(os.path.join(pubsk, "evals", "runs"))
        open(os.path.join(pubsk, "evals", "runs", "2026-01-01.md"), "w").write("# Eval run\n")
        assert not any(f["code"] == "evals-run" for f in lint_skill(pubsk)["findings"]), \
            "run log present but still flagged"

        assert "skillroy" in provenance(), "provenance stamp missing skillroy version"

        # §11 external-resources: a non-meta skill referencing a clone/artifact with no manifest → nudge;
        # a meta skill with the same body text is exempt; a present resources.yaml clears the nudge.
        coll = os.path.join(tmp, "dx-things", ".claude", "skills")
        dxsk = os.path.join(coll, "fetchy")
        os.makedirs(dxsk)
        body_ext = ("---\nname: fetchy\ndescription: \"x\"\n"
                    "metadata:\n  skillroy:\n    phase: adhoc\n    tier: dx\n    version: 0.1.0\n---\n"
                    "# fetchy\nRun `git clone` of the repo and use BeanstoreServer.war.\n")
        open(os.path.join(dxsk, "SKILL.md"), "w").write(body_ext)
        assert any(f["code"] == "resources" for f in lint_skill(dxsk)["findings"]), "missing-manifest nudge not raised"
        # same body, meta tier → exempt
        metask = os.path.join(tmp, "meta-things", ".claude", "skills", "fetchy")
        os.makedirs(metask)
        open(os.path.join(metask, "SKILL.md"), "w").write(body_ext.replace("tier: dx", "tier: meta"))
        assert not any(f["code"] == "resources" for f in lint_skill(metask)["findings"]), "meta skill should be exempt"
        # add a resources.yaml at the collection root → nudge clears
        open(os.path.join(tmp, "dx-things", "resources.yaml"), "w").write(
            "version: 1\nresources:\n  - id: r\n    type: artifact\n    description: d\n")
        assert not any(f["code"] == "resources" for f in lint_skill(dxsk)["findings"]), "manifest present but still nudged"
        # a broken manifest is an error at collection scope
        open(os.path.join(tmp, "dx-things", "resources.yaml"), "w").write("version: 1\nresources: not-a-list\n")
        _, cf2 = collection_findings(coll)
        assert any(c == "resources" and s == "error" for s, c, _ in cf2), "broken resources.yaml not flagged"

        uninst = os.path.join(tmp, "uninst")
        os.makedirs(uninst)
        open(os.path.join(uninst, "SKILL.md"), "w").write(
            '---\nname: uninst\ndescription: "x"\n---\n# x\n')
        sevs = {f["code"]: f["severity"] for f in lint_skill(uninst)["findings"]}
        assert sevs.get("metadata") == "warn", f"un-instrumented skill should warn: {sevs}"

        _, cf = collection_findings(os.path.join(tmp, "Bad-Name", ".agents", "skills"))
        assert any(c == "collection-name" for _, c, _ in cf), "collection-name check missed"

        catfile = os.path.join(tmp, "cat.json")
        json.dump({"version": 1, "tokens": [
            {"token": "alpha", "name": "Alpha", "status": "confirmed", "aliases": ["AlphaSvc"]},
            {"token": "old-x", "name": "Old", "status": "legacy", "replaced_by": "alpha"}]},
            open(catfile, "w"))
        idx, cerr = load_catalog(catfile)
        assert cerr is None and "alpha" in idx["tokens"], f"catalog load failed: {cerr}"

        def mkskill(nm, dom):
            d = os.path.join(tmp, nm)
            os.makedirs(os.path.join(d, "evals"))
            open(os.path.join(d, "SKILL.md"), "w").write(
                f'---\nname: {nm}\ndescription: "x"\nmetadata:\n  skillroy:\n    phase: adhoc\n'
                f"    tier: ops\n    version: 0.1.0\n    domain: {dom}\nlicense: Apache-2.0\n---\n# x\n")
            open(os.path.join(d, "evals", "e.json"), "w").write("{}")
            return d

        assert not [f for f in lint_skill(mkskill("ok-dom", "alpha"), catalog=idx)["findings"]
                    if f["code"] == "token"], "known token wrongly flagged"
        assert any(f["code"] == "token" for f in lint_skill(mkskill("bad-dom", "frobnicator"),
                   catalog=idx)["findings"]), "unknown domain not flagged"
        assert any(f["code"] == "token" and "alias" in f["message"]
                   for f in lint_skill(mkskill("ali-dom", "AlphaSvc"), catalog=idx)["findings"]), \
            "alias domain not flagged"

        # gitignore-trap (§10): every .gitignore from the skills home up to the REPO root is
        # consulted; a swallow at the collection level AND one at a monorepo parent both flag;
        # the safe `.claude/*` + `!.claude/skills/` pattern clears it. Skipped without git.
        try:
            giroot = os.path.join(tmp, "mono")
            home2 = os.path.join(giroot, "collections", "dx-c", ".claude", "skills", "sk")
            os.makedirs(home2)
            open(os.path.join(home2, "SKILL.md"), "w").write(
                '---\nname: sk\ndescription: "x"\n---\n# x\n')
            subprocess.run(["git", "-C", giroot, "init", "-q"], check=True, timeout=10)
            ghome = os.path.join(giroot, "collections", "dx-c", ".claude", "skills")
            assert not gitignore_trap_findings(ghome), "clean tree wrongly trapped"
            # strike shape 1: collection-level .gitignore swallows .claude/
            open(os.path.join(giroot, "collections", "dx-c", ".gitignore"), "w").write(".claude/\n")
            assert any(c == "gitignore-trap" for _, c, _ in gitignore_trap_findings(ghome)), \
                "collection-level trap missed"
            # safe pattern clears it
            open(os.path.join(giroot, "collections", "dx-c", ".gitignore"), "w").write(
                ".claude/*\n!.claude/skills/\n")
            assert not gitignore_trap_findings(ghome), "safe pattern wrongly trapped"
            # strike shape 2: monorepo parent (repo root) swallows collections/ — nesting bite
            open(os.path.join(giroot, ".gitignore"), "w").write("collections/\n")
            assert any(c == "gitignore-trap" for _, c, _ in gitignore_trap_findings(ghome)), \
                "monorepo-parent trap missed"
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("  (gitignore-trap case skipped: git unavailable)")

        print("self-test OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def provenance(catalog_path=None):
    """Stamp which rules + catalog produced a report (DESIGN §7): skillroy version, catalog digest."""
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
    try:
        ver = subprocess.run(["git", "-C", root, "describe", "--always", "--dirty", "--tags"],
                             capture_output=True, text=True, timeout=5).stdout.strip() or "unversioned"
    except Exception:
        ver = "unversioned"
    out = {"skillroy": ver}
    if catalog_path and os.path.isfile(catalog_path):
        digest = hashlib.sha256(open(catalog_path, "rb").read()).hexdigest()[:12]
        out["catalog"] = f"{os.path.basename(catalog_path)}@{digest}"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint skills against skillroy conventions.")
    ap.add_argument("path", nargs="?", help="a skill folder or a collection directory")
    ap.add_argument("--phase", choices=PHASES, help="override the skill's declared phase")
    ap.add_argument("--tokens", help="token catalog (.yaml/.json) to check metadata.skillroy.domain against")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        self_test()
        return 0
    if not args.path:
        ap.error("path is required (or use --self-test)")

    catalog = None
    tokens_path = args.tokens or os.environ.get("SKILLROY_TOKENS")
    if tokens_path:
        catalog, cerr = load_catalog(tokens_path)
        if cerr:
            print(f"warning: token catalog not used ({cerr})")
        args.tokens = tokens_path
    is_single = os.path.isfile(os.path.join(args.path, "SKILL.md"))
    results = lint_path(args.path, args.phase, catalog)
    gt = gitignore_trap_findings(args.path)
    if is_single and gt and results:
        results[0]["findings"].extend(
            {"severity": s, "code": c, "message": m} for s, c, m in gt)
    if not is_single:
        cname, cf = collection_findings(args.path)
        cf = cf + gt
        if cf:
            results.insert(0, {"skill": f"(collection: {cname})", "path": args.path, "phase": None,
                               "findings": [{"severity": s, "code": c, "message": m} for s, c, m in cf]})

    prov = provenance(args.tokens)
    if args.json:
        print(json.dumps({"provenance": prov, "results": results}, indent=2))
    else:
        for r in results:
            head = r["skill"] + (f" (phase {r['phase']})" if r["phase"] else "")
            print(f"\n== {head} ==")
            if not r["findings"]:
                print("  ok — no findings")
                continue
            for f in sorted(r["findings"], key=lambda x: -SEV_ORDER[x["severity"]]):
                print(f"  [{f['severity']:<5}] {f['code']}: {f['message']}")
        print("\n-- " + " | ".join(f"{k} {v}" for k, v in prov.items()))
    total_errors = sum(1 for r in results for f in r["findings"] if f["severity"] == "error")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
