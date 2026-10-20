# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 walltime1
# Licensed under the GNU Affero General Public License, version 3 or later; see LICENSE.
"""Roll graphify's file-level graph up into a map of areas.

Size is non-blank code lines (lizard nloc). Tangle is decision points
(cyclomatic complexity minus one, summed over functions) per 100 code lines.
Connections are graphify edges between files in different areas.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import lizard

from .config import SKIP_DIRS, Config

IGNORED_RELATIONS = {"contains", "rationale_for", "method"}


def collect(root: Path, cfg: Config) -> dict[str, str]:
    """Map each code file graphify and lizard can both read to its area id."""
    from graphify.extract import collect_files

    out = {}
    for p in collect_files(root, root=root):
        rel = p.resolve().relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in rel.split("/")) or lizard.get_reader_for(rel) is None:
            continue
        area = cfg.area_of(rel)
        if area:
            out[rel] = area.id
    return out


def extract_graph(root: Path, files: list[str]) -> tuple[list[dict], list[dict]]:
    from graphify.extract import extract

    res = extract([root / f for f in files], root=root)
    return res["nodes"], res["edges"]


def load_graph(path: Path) -> tuple[list[dict], list[dict]]:
    """Read an existing graphify-out/graph.json. Arc order is the edge direction."""
    data = json.loads(path.read_text())
    edges = data.get("links", data.get("edges", []))
    for e in edges:
        e["source"], e["target"] = e.get("_src", e["source"]), e.get("_tgt", e["target"])
    return data["nodes"], edges


def file_metrics(root: Path, rel: str) -> tuple[int, int]:
    try:
        r = lizard.analyze_file(str(root / rel))
    except Exception:
        return 0, 0
    return r.nloc, sum(max(f.cyclomatic_complexity - 1, 0) for f in r.function_list)


def build(root: Path, cfg: Config, graph: Path | None = None) -> dict:
    root = root.resolve()
    file_area = collect(root, cfg)
    if not any(a for a in file_area.values() if not cfg_area(cfg, a).lab):
        raise SystemExit("no source files matched any area; check the config patterns")
    nodes, edges = load_graph(graph) if graph else extract_graph(root, sorted(file_area))

    metrics = {f: file_metrics(root, f) for f in file_area}
    areas = []
    for a in cfg.areas:
        files = [f for f, aid in file_area.items() if aid == a.id]
        per_file = sorted(({"file": f, "lines": metrics[f][0], "decisions": metrics[f][1]} for f in files),
                          key=lambda x: -x["lines"])
        lines = sum(x["lines"] for x in per_file)
        decisions = sum(x["decisions"] for x in per_file)
        areas.append({
            "id": a.id, "name": a.name, "layer": a.layer, "blurb": a.blurb, "lab": a.lab,
            "lines": lines, "decisions": decisions,
            "tangle": round(100 * decisions / lines, 1) if lines else 0,
            # lab areas can be large; the panel only lists the biggest files
            "files": per_file[:12] if a.lab else per_file,
            "nfiles": len(per_file),
        })
    areas = [a for a in areas if a["nfiles"]]
    present = {a["id"] for a in areas}
    lab_ids = {a.id for a in cfg.lab}
    test_ids = {a.id for a in cfg.lab if a.tests}

    node_file = {n["id"]: n.get("source_file") for n in nodes}
    links = defaultdict(lambda: {"count": 0, "solid": 0, "kinds": defaultdict(int)})
    flinks = defaultdict(int)
    tested_by = defaultdict(set)
    for e in edges:
        if e.get("relation") in IGNORED_RELATIONS:
            continue
        sf, tf = node_file.get(e["source"]), node_file.get(e["target"])
        s, t = file_area.get(sf), file_area.get(tf)
        if not s or not t or sf == tf or t in lab_ids:
            continue
        if s not in lab_ids:
            flinks[(sf, tf)] += 1
        if s in test_ids:
            tested_by[t].add(sf)
        if s == t:
            continue
        d = links[(s, t)]
        d["count"] += 1
        d["kinds"][e.get("relation", "uses")] += 1
        if e.get("confidence") == "EXTRACTED":
            d["solid"] += 1

    for a in areas:
        a["tests"] = len(tested_by.get(a["id"], ()))
    ship = [a for a in areas if not a["lab"]]
    total = sum(a["lines"] for a in ship)
    top = sorted(ship, key=lambda a: -a["lines"])[: cfg.top]
    used_layers = {a["layer"] for a in areas}
    return {
        "title": cfg.title,
        "layers": [{"id": i, "name": n} for i, n in cfg.layers if i in used_layers]
                  + [{"id": "lab", "name": "Lab only, never ships"}],
        "areas": areas,
        "links": [{"from": s, "to": t, "count": d["count"], "solid": d["solid"], "kinds": dict(d["kinds"])}
                  for (s, t), d in sorted(links.items()) if s in present and t in present],
        "flinks": [[a, b, n] for (a, b), n in sorted(flinks.items())],
        "totals": {
            "shipped": total,
            "tests": sum(a["lines"] for a in areas if a["id"] in test_ids),
            "areas": len(ship),
            "top3": [a["id"] for a in top],
            "top3share": round(100 * sum(a["lines"] for a in top) / total) if total else 0,
        },
    }


def cfg_area(cfg: Config, aid: str):
    return next(a for a in cfg.areas if a.id == aid)


def render(data: dict) -> str:
    template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    title = data["title"].replace("&", "&amp;").replace("<", "&lt;")
    return template.replace("__TITLE__", title).replace("__DATA__", blob)
