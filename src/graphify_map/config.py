# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 walltime1
# Licensed under the GNU Affero General Public License, version 3 or later; see LICENSE.
"""Area config: which files belong to which area, and how areas are layered.

A config is a TOML file:

    title = "graphify"
    top = 3                      # how many heaviest areas the summary names

    [[layers]]
    id = "run"
    name = "How you run it"

    [[areas]]
    id = "cli"
    name = "Command line"
    layer = "run"
    blurb = "The graphify command and its subcommands."
    files = ["graphify/cli.py", "graphify/__main__.py"]

    [[lab]]                      # code that never ships: tests, tools
    id = "tests"
    name = "Test suite"
    files = ["tests/**"]
    tests = true                 # count these files as tests

Patterns are globs on the repo-relative path, where ``*`` stays inside one
folder and ``**`` crosses folders. A file goes to the first area that matches.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

TEST_DIRS = {"test", "tests", "spec", "specs", "__tests__"}
SKIP_DIRS = {".git", "node_modules", "graphify-out", "dist", "build", "venv", ".venv", "__pycache__"}


@dataclass
class Area:
    id: str
    name: str
    layer: str
    files: list[str]
    blurb: str = ""
    lab: bool = False
    tests: bool = False
    _res: list[re.Pattern] = field(default_factory=list, repr=False)

    def __post_init__(self):
        self._res = [glob_to_re(p) for p in self.files]

    def matches(self, rel: str) -> bool:
        return any(r.fullmatch(rel) for r in self._res)


@dataclass
class Config:
    title: str
    layers: list[tuple[str, str]]
    areas: list[Area]
    top: int = 3

    @property
    def shipped(self) -> list[Area]:
        return [a for a in self.areas if not a.lab]

    @property
    def lab(self) -> list[Area]:
        return [a for a in self.areas if a.lab]

    def area_of(self, rel: str) -> Area | None:
        for a in self.areas:
            if a.matches(rel):
                return a
        return None


def glob_to_re(pat: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif pat.startswith("**", i):
            out += ".*"; i += 2
        elif pat[i] == "*":
            out += "[^/]*"; i += 1
        elif pat[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pat[i]); i += 1
    return re.compile(out)


def load(path: Path) -> Config:
    data = tomllib.loads(path.read_text())
    layers = [(l["id"], l["name"]) for l in data.get("layers", [])]
    if not layers:
        layers = [("code", "Code")]
    known = {l for l, _ in layers}
    areas = []
    for a in data.get("areas", []):
        layer = a.get("layer", layers[0][0])
        if layer not in known:
            raise ValueError(f"area {a['id']!r} uses unknown layer {layer!r}")
        areas.append(Area(a["id"], a["name"], layer, a["files"], a.get("blurb", "")))
    for a in data.get("lab", []):
        areas.append(Area(a["id"], a["name"], "lab", a["files"], a.get("blurb", ""), lab=True, tests=a.get("tests", False)))
    ids = [a.id for a in areas]
    if len(ids) != len(set(ids)):
        raise ValueError("area ids must be unique")
    return Config(data.get("title", path.stem), layers, areas, data.get("top", 3))


def guess(root: Path) -> Config:
    """No config given: one area per top-level folder, test folders go to the lab."""
    areas, lab = [], []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name.startswith(".") or d.name in SKIP_DIRS:
            continue
        target = lab if d.name.lower() in TEST_DIRS else areas
        target.append(d.name)
    shipped = []
    for name in areas:
        subs = sorted(p.name for p in (root / name).iterdir() if p.is_dir() and not p.name.startswith((".", "_")))
        # a single package folder (src/, or the project's own package) is split one level down
        if len(areas) <= 2 and len(subs) >= 3:
            shipped += [Area(f"{name}/{s}", f"{name}/{s}", "code", [f"{name}/{s}/**"]) for s in subs]
            shipped.append(Area(name, f"{name} (top level)", "code", [f"{name}/*"]))
        else:
            shipped.append(Area(name, name, "code", [f"{name}/**"]))
    shipped.append(Area("root", "Top-level files", "code", ["*"]))
    tests = [Area(n, n, "lab", [f"{n}/**"], lab=True, tests=True) for n in lab]
    return Config(root.resolve().name, [("code", "Code")], shipped + tests)
