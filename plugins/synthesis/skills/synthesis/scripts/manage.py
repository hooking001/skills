#!/usr/bin/env python3
"""Create standalone RTL projects, verify library assets, or install this skill."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from rtl_flow import identifier

ROOT = Path(__file__).resolve().parent.parent
PDKS = ("asap7", "nangate45")
DEFAULT_PDK = "asap7"
# Without these, dfflibmap picks the large Q-output flops for every register;
# QN x1 flops plus inverters are smaller. Edit project.json to change it.
ASAP7_DONT_USE = ["DFFHQx4_ASAP7_75t_R", "DFFLQx4_ASAP7_75t_R"]

TEMPLATE_GROUP = re.compile(r"^[ \t]*(?:lu_table_template|power_lut_template)\s*\(\s*(\w+)\s*\)\s*\{", re.M)
CELL_START = re.compile(r"^[ \t]*cell\s*\(", re.M)
CELL_NAME = re.compile(r"^[ \t]*cell\s*\(\s*\"?([^\s\")]+)\"?\s*\)", re.M)


def lib_dir():
    """Shared download cache for bundled libraries, outside the (versioned) plugin copy."""
    override = os.environ.get("SYNTHESIS_LIB_DIR")
    if override:
        return Path(override).expanduser().resolve()
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache).expanduser().resolve() / "synthesis" / "lib"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(name):
    return json.loads((ROOT / "resources" / name).read_text())


def fetch(url, target, sha256):
    # Curl uses the OS certificate store on both supported platforms.
    subprocess.run(["curl", "--fail", "--location", "--show-error", "--silent",
                    "--retry", "2", "--connect-timeout", "15", "--max-time", "180",
                    url, "--output", str(target)], check=True)
    if digest(target) != sha256:
        raise ValueError("Checksum mismatch for " + url)
    return target


def group_end(text, start):
    """Return the index just past the brace that closes the group opened after start."""
    depth = 0
    for match in re.finditer(r"[{}]", text[start:]):
        depth += 1 if match.group() == "{" else -1
        if depth == 0:
            return start + match.end()
    raise ValueError("Unbalanced braces in Liberty group")


def split_liberty(path):
    """Split one cell library into its header, its cell groups and its table templates."""
    data = path.read_bytes()
    text = (gzip.decompress(data) if path.name.endswith(".gz") else data).decode("ascii")
    library = re.search(r"^library\s*\(", text, re.M)
    first = CELL_START.search(text)
    body = text.rstrip()
    if not library or not first or not body.endswith("}"):
        raise ValueError("Not a single-library Liberty file: " + path.name)
    header = text[:first.start()]
    templates = {m.group(1): header[m.start():group_end(header, m.start())]
                 for m in TEMPLATE_GROUP.finditer(header)}
    return header, body[first.start():-1].rstrip() + "\n", templates


def merge_asap7_liberties(components, name="asap7sc7p5t_28_RVT_TT"):
    """Deterministically merge the ASAP7 NLDM category files into one Liberty library.

    The first component supplies the license comment and library attributes. Table
    templates that only later components define are appended, so every reference
    in the merged cells resolves; same-named templates must have identical bodies.
    """
    parts = [split_liberty(path) for path in components]
    header, _, templates = parts[0]
    header = re.sub(r"^library\s*\([^)]*\)", "library (" + name + ")", header, count=1, flags=re.M)
    extra = []
    for _, _, more in parts[1:]:
        for key, group in more.items():
            if key not in templates:
                templates[key] = group
                extra.append(group)
            elif templates[key].split() != group.split():
                raise ValueError("Conflicting Liberty template: " + key)
    cells, seen = [], set()
    for _, chunk, _ in parts:
        for cell in CELL_NAME.findall(chunk):
            if cell in seen:
                raise ValueError("Duplicate Liberty cell: " + cell)
            seen.add(cell)
        cells.append(chunk)
    merged = header.rstrip() + "\n" + "".join(g + "\n" for g in extra) + "".join(cells) + "}\n"
    return merged.encode("ascii")


def download_nangate45(destination):
    data = manifest("library.json")
    destination.mkdir(parents=True, exist_ok=True)
    for item in data["files"]:
        target = destination / Path(item["path"]).name
        if target.exists():
            if digest(target) != item["sha256"]:
                raise ValueError("Checksum mismatch; existing file preserved: " + str(target))
            print("Verified " + str(target))
            continue
        url = data["base_url"] + "/" + data["revision"] + "/flow/platforms/nangate45/" + item["path"]
        with tempfile.TemporaryDirectory(prefix=".download-", dir=str(destination)) as temp:
            fetch(url, Path(temp) / target.name, item["sha256"]).replace(target)
        print("Downloaded and verified " + str(target))


def download_asap7(destination, data=None):
    data = data or manifest("library_asap7.json")
    destination.mkdir(parents=True, exist_ok=True)
    merged = destination / data["merged"]["filename"]
    libs = [item for item in data["files"] if item["path"].startswith("lib/")]
    others = {destination / Path(item["path"]).name: item
              for item in data["files"] if not item["path"].startswith("lib/")}
    missing = []
    # Check every existing file first; a mismatched file is never overwritten.
    for target, sha256 in [(merged, data["merged"]["sha256"])] + [(t, i["sha256"]) for t, i in others.items()]:
        if not target.exists():
            missing.append(target)
        elif digest(target) != sha256:
            raise ValueError("Checksum mismatch; existing file preserved: " + str(target))
        else:
            print("Verified " + str(target))
    if not missing:
        return
    base = data["base_url"] + "/" + data["revision"] + "/flow/platforms/asap7/"
    with tempfile.TemporaryDirectory(prefix=".download-", dir=str(destination)) as temp:
        staged = {}
        for target in missing:
            if target in others:
                item = others[target]
                staged[target] = fetch(base + item["path"], Path(temp) / target.name, item["sha256"])
        if merged in missing:
            parts = [fetch(base + item["path"], Path(temp) / Path(item["path"]).name, item["sha256"])
                     for item in libs]
            candidate = Path(temp) / ("merged-" + merged.name)
            candidate.write_bytes(merge_asap7_liberties(parts))
            if digest(candidate) != data["merged"]["sha256"]:
                raise ValueError("Checksum mismatch for assembled " + merged.name)
            staged[merged] = candidate
        # Publish only after every download and the merge have been verified.
        for target, candidate in staged.items():
            candidate.replace(target)
            print("Downloaded and verified " + str(target))


def download(destination, pdk="all"):
    if pdk in ("asap7", "all"):
        download_asap7(destination)
    if pdk in ("nangate45", "all"):
        download_nangate45(destination)


def pdk_assets(pdk):
    """Bundled files a new project copies, default Liberty first, plus the license."""
    if pdk == "asap7":
        data = manifest("library_asap7.json")
        names = [data["merged"]["filename"]] + [Path(item["path"]).name for item in data["files"]
                                                 if not item["path"].startswith("lib/")]
        return names, "ASAP7-LICENSE"
    return [Path(item["path"]).name for item in manifest("library.json")["files"]], "NANGATE-LICENSE"


def wrapper(path, command, runtime='"${SCRIPT_DIR}/rtl_flow.py"', project='"${SCRIPT_DIR}/.."'):
    path.write_text('''#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 %s --project %s %s "$@"
''' % (runtime, project, command))
    path.chmod(0o755)


def setup(args):
    name = identifier(args.name)
    top = identifier(args.top or name)
    base = Path(args.directory).resolve()
    target = base / name
    if target.exists() or target.is_symlink():
        raise ValueError("Project already exists; refusing to overwrite: " + str(target))
    liberty = Path(args.liberty).resolve(strict=True) if args.liberty else None
    if liberty and not liberty.is_file():
        raise ValueError("Liberty must be a file")
    pdk = "custom" if liberty else args.pdk
    if not liberty:
        # Downloads missing files once and verifies every file before copying it.
        download(lib_dir(), pdk=pdk)
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rtl-project-", dir=str(base)) as temp:
        project = Path(temp) / name
        for directory in ("rtl", "tb", "lib", "script", "synth", "dump"):
            (project / directory).mkdir(parents=True)
        config = {"pdk": pdk, "top": top, "tb_top": top + "_tb"}
        if liberty:
            shutil.copy2(str(liberty), str(project / "lib" / liberty.name))
            config["liberty"] = "lib/" + liberty.name
        else:
            names, license_name = pdk_assets(pdk)
            for filename in names + [license_name]:
                source = (lib_dir() if filename in names else ROOT / "resources") / filename
                shutil.copy2(str(source), str(project / "lib" / filename))
            config["liberty"] = "lib/" + names[0]
            if pdk == "asap7":
                config["dont_use"] = list(ASAP7_DONT_USE)
        (project / "project.json").write_text(json.dumps(config, indent=2) + "\n")
        for kind, suffix in (("rtl", ".v"), ("tb", "_tb.v")):
            template = (ROOT / "assets" / (kind + ".v.template")).read_text()
            (project / kind / (top + suffix)).write_text(template.replace("@TOP@", top))
            (project / "script" / (kind + ".f")).write_text("../" + kind + "/" + top + suffix + "\n")
        shutil.copy2(str(ROOT / "scripts/rtl_flow.py"), str(project / "script/rtl_flow.py"))
        for filename, command in (("run_synth.sh", "synth"), ("run_tb.sh", "tb"), ("clean.sh", "clean")):
            wrapper(project / "script" / filename, command)
        wrapper(project / "clean.sh", "clean", '"${SCRIPT_DIR}/script/rtl_flow.py"', '"${SCRIPT_DIR}"')
        (project / ".gitignore").write_text("synth/\ndump/\n.rtl-flow-outputs.json\n__pycache__/\n")
        project.rename(target)
    print("Created standalone {} project: {}".format(pdk, target))


def install(args):
    if args.destination:
        parent = Path(args.destination).expanduser().resolve()
    else:
        home = Path.home()
        parent = {"codex": Path(os.environ.get("CODEX_HOME", str(home / ".codex"))) / "skills",
                  "claude": home / ".claude/skills",
                  "antigravity": home / ".gemini/config/skills"}[args.target]
        parent = parent.resolve()
    target = parent / "synthesis"
    if target == ROOT or ROOT in target.parents or target in ROOT.parents:
        raise ValueError("Install destination must be outside the source skill")
    if target.exists() or target.is_symlink():
        raise ValueError("Destination already exists; refusing to overwrite: " + str(target))
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".synthesis-install-", dir=str(parent)) as temp:
        staging = Path(temp) / target.name
        shutil.copytree(str(ROOT), str(staging), symlinks=False,
                        ignore=shutil.ignore_patterns(".git", ".serena", ".agents", ".codex",
                                                     "__pycache__", "*.pyc", ".DS_Store",
                                                     ".rtl-flow-outputs.json", "synth", "dump"))
        staging.rename(target)
    print("Installed " + str(target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("setup")
    create.add_argument("name")
    create.add_argument("directory", nargs="?", default=".")
    create.add_argument("--top")
    create.add_argument("--pdk", choices=PDKS, default=DEFAULT_PDK,
                        help="Bundled library (default: %(default)s)")
    create.add_argument("--liberty", help="Copy a local Liberty file instead of a bundled library")
    fetch_cmd = sub.add_parser("download")
    fetch_cmd.add_argument("--pdk", choices=PDKS + ("all",), default="all",
                           help="Which bundled library to verify or restore (default: %(default)s)")
    fetch_cmd.add_argument("directory", nargs="?",
                           help="Target directory (default: $SYNTHESIS_LIB_DIR or ~/.cache/synthesis/lib)")
    add = sub.add_parser("install")
    add.add_argument("--target", choices=("codex", "claude", "antigravity"), default="codex")
    add.add_argument("--destination", help="Custom parent skills directory")
    args = parser.parse_args()
    try:
        if args.command == "setup":
            setup(args)
        elif args.command == "download":
            download(Path(args.directory).resolve() if args.directory else lib_dir(), pdk=args.pdk)
        else:
            install(args)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
