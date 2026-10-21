# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 walltime1
# Licensed under the GNU Affero General Public License, version 3 or later; see LICENSE.
import json
import shutil
from pathlib import Path

import pytest

from graphify_map.build import build, render
from graphify_map.cli import main
from graphify_map.config import glob_to_re, guess, load

FIXTURE = Path(__file__).parent / "fixture"


@pytest.fixture
def repo(tmp_path):
    dst = tmp_path / "repo"
    shutil.copytree(FIXTURE, dst)
    return dst


@pytest.mark.parametrize("pat,path,hit", [
    ("app/*.py", "app/a.py", True),
    ("app/*.py", "app/x/a.py", False),
    ("app/**", "app/x/a.py", True),
    ("**/test_*.py", "test_a.py", True),
    ("**/test_*.py", "deep/er/test_a.py", True),
])
def test_glob(pat, path, hit):
    assert bool(glob_to_re(pat).fullmatch(path)) is hit


def test_build_rolls_files_up_to_areas(repo):
    data = build(repo, load(repo / "graphify-map.toml"))
    areas = {a["id"]: a for a in data["areas"]}
    assert set(areas) == {"ui", "core", "tests"}
    assert areas["core"]["lines"] > 0 and areas["core"]["decisions"] >= 3
    assert {"from": "ui", "to": "core"} in [{"from": l["from"], "to": l["to"]} for l in data["links"]]
    assert any(l["from"] == "tests" and l["to"] == "ui" for l in data["links"])
    assert ["app/ui/screen.py", "app/core/store.py"] in [f[:2] for f in data["flinks"]]
    assert areas["ui"]["tests"] == 1
    assert data["totals"]["areas"] == 2


def test_render_inlines_data(repo):
    html = render(build(repo, load(repo / "graphify-map.toml")))
    assert "__DATA__" not in html and "__TITLE__" not in html
    assert "<title>fixture Complexity Map</title>" in html


def test_cli_writes_outputs(repo, capsys):
    assert main([str(repo)]) == 0
    out = repo / "graphify-out" / "map"
    assert json.loads((out / "map.json").read_text())["title"] == "fixture"
    assert (out / "map.html").exists()


def test_guess_without_config(repo):
    (repo / "graphify-map.toml").unlink()
    cfg = guess(repo)
    assert [a.id for a in cfg.lab] == ["tests"]
    assert cfg.area_of("app/ui/screen.py") is not None


def file_entry(data, rel):
    return next(f for a in data["areas"] for f in a["files"] if f["file"] == rel)


def symbols_of(data, rel):
    return file_entry(data, rel)["symbols"]


def test_methods_are_grouped_under_their_class(repo):
    data = build(repo, load(repo / "graphify-map.toml"))
    (repo_class,) = symbols_of(data, "app/core/repo.py")
    assert repo_class["kind"] == "class" and repo_class["name"] == "Repo"
    assert [m["name"] for m in repo_class["methods"]] == ["add", "count"]
    assert repo_class["lines"] == sum(m["lines"] for m in repo_class["methods"])
    assert repo_class["decisions"] == sum(m["decisions"] for m in repo_class["methods"])
    assert [s["name"] for s in symbols_of(data, "app/ui/screen.py")] == ["show", "add_one"]


def test_lab_files_have_no_symbols(repo):
    data = build(repo, load(repo / "graphify-map.toml"))
    assert "symbols" not in file_entry(data, "tests/test_screen.py")


def test_symbol_links_connect_functions_and_methods(repo):
    data = build(repo, load(repo / "graphify-map.toml"))
    sid = {s["name"]: f"{rel}#{s['line']}"
           for rel in ("app/ui/screen.py", "app/core/store.py", "app/core/repo.py")
           for s in symbols_of(data, rel)}
    methods = {m["name"]: f"app/core/repo.py#{m['line']}" for m in symbols_of(data, "app/core/repo.py")[0]["methods"]}
    pairs = {(a, b) for a, b, _ in data["slinks"]}
    assert (sid["show"], sid["save"]) in pairs
    assert (sid["add_one"], sid["Repo"]) in pairs
    assert (methods["add"], methods["count"]) in pairs
    assert not any(a == sid["Repo"] and b in methods.values() for a, b in pairs), "a class does not link to its own methods"
