# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 walltime1
# Licensed under the GNU Affero General Public License, version 3 or later; see LICENSE.
"""graphify-map command line."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .build import build, render
from .config import guess, load


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="graphify-map", description="Build a complexity map of a codebase with graphify.")
    ap.add_argument("root", nargs="?", default=".", type=Path, help="repository to map (default: current folder)")
    ap.add_argument("-c", "--config", type=Path, help="area config TOML (default: <root>/graphify-map.toml, else one area per top-level folder)")
    ap.add_argument("-g", "--graph", type=Path, help="reuse an existing graphify graph.json instead of extracting")
    ap.add_argument("-o", "--out", type=Path, default=Path("graphify-out/map"), help="output folder (default: graphify-out/map)")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    root = args.root.resolve()
    cfg_path = args.config or (root / "graphify-map.toml")
    cfg = load(cfg_path) if cfg_path.exists() else guess(root)
    data = build(root, cfg, args.graph)

    out = args.out if args.out.is_absolute() else root / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "map.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    (out / "map.html").write_text(render(data), encoding="utf-8")
    t = data["totals"]
    print(f"{t['areas']} areas, {t['shipped']} lines shipped, {len(data['links'])} links -> {out / 'map.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
