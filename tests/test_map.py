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
