# graphify-map

A complexity map of a codebase. It shows which parts are big, which are tangled, and which lean on each other.

It is built on [graphify](https://github.com/Graphify-Labs/graphify) (`graphifyy` on PyPI). graphify reads the code and finds the calls, imports and references between files. graphify-map rolls those up into areas you name, adds size and complexity from [lizard](https://github.com/terryyin/lizard), and writes one self-contained HTML page.

> **Note:** this project is vibe-coded. It was written with an AI coding assistant (Claude), guided by prompts and by running the result, not by line-by-line human authorship. It has a small test suite and has been run on one real codebase (graphify itself). Treat the numbers as a rough guide, check anything you plan to rely on, and expect rough edges.

## Install

```bash
pip install git+https://github.com/walltime1/graphify-map
```

This installs `graphifyy` and `lizard` as dependencies.

## Use

```bash
graphify-map path/to/repo                     # writes path/to/repo/graphify-out/map/map.html
graphify-map . -c graphify-map.toml           # use an area config
graphify-map . -g graphify-out/graph.json     # reuse a graph graphify already built
```

Without a config, each top-level folder becomes an area, and folders named `test`, `tests` or `spec` become lab-only. A config gives better results, because areas should match how people talk about the product, not just the folder layout.

## Area config

Put `graphify-map.toml` at the repo root, or pass it with `-c`.

```toml
title = "my app"

[[layers]]                 # top to bottom on the map
id = "ui"
name = "What you see"

[[areas]]
id = "chat"
name = "Chat screen"
layer = "ui"
blurb = "The main conversation view."
files = ["app/chat/**", "app/shared/chat_*.swift"]

[[lab]]                    # never ships: tests, tools, experiments
id = "tests"
name = "Test suite"
files = ["tests/**"]
tests = true               # count references from here as tests
```

A file goes to the first area whose `files` globs match it. `*` stays inside one folder and `**` crosses folders. Files that match nothing are left off the map.

[`examples/graphify.toml`](examples/graphify.toml) maps graphify itself.

## What the page shows

- **Overview**: areas in layers. Shade boxes by size, tangle or connections. Arrows mean "uses". Click an area for its files, what it uses and what uses it.
- **Two trees**: the same files grouped by folder and by area. Hover or click to see file-level arcs for what a file uses and what uses it.
- **Functions and classes**: open any file in either tree to see its classes, methods and functions, each with size and tangle. Select one to see which other functions or classes it uses and which use it.
- **Heaviest** and **Shared building blocks**: ranked lists. Heaviest also ranks the biggest and most branching functions.
- **Ask the map**: precomputed answers, such as what is most tangled or which areas depend on each other both ways.

## How it measures

- **Size**: code lines from lizard, without blanks or comments.
- **Tangle**: decision points per 100 code lines. That is cyclomatic complexity minus one, summed over functions.
- **Links**: graphify edges between files in different areas, excluding structural edges such as `contains`.
- **Functions and classes**: lizard measures each function and method. Graphify says which methods belong to which class, and a class is the sum of its methods. Function-level links are graphify's call and reference edges between them. Code outside any function counts toward the file only.
- **Tests per area**: how many lab files marked `tests = true` reference the area. This is not line coverage.

Only files that both graphify and lizard can read are counted.

## Develop

```bash
pip install -e '.[test]'
pytest
```

## Acknowledgements

- The idea came from two screenshots seen on X (formerly Twitter) of codebase maps. This project is an independent attempt at the same kind of view. It is not affiliated with their authors and uses none of their code or assets.
- [graphify](https://github.com/Graphify-Labs/graphify) (Apache-2.0) builds the code graph this tool rolls up.
- [lizard](https://github.com/terryyin/lizard) (MIT) measures code lines and complexity.
- The page is set in [mononoki](https://github.com/madmalik/mononoki) (SIL OFL 1.1) when it is installed on the viewer's machine, and falls back to the system monospace font otherwise. The font is not bundled and the page makes no network requests.

## License

graphify-map is licensed under the [GNU Affero General Public License, version 3 or later](https://www.gnu.org/licenses/agpl-3.0.html) (`AGPL-3.0-or-later`). See [LICENSE](LICENSE) for the full text.

The AGPL's network clause applies if you run a modified graphify-map as a service that other people interact with over a network: those users must be offered the source of your modified version. Running the CLI locally to map your own repository does not affect the license of that repository.

**Additional permission for generated maps.** Under section 7 of the AGPL, the copyright holder grants this extra permission: the HTML pages that graphify-map generates, including the viewer code embedded in them, may be used, shared and hosted under any terms you choose. The permission covers the generated pages only. The graphify-map source, including `template.html` in this repository, stays under the AGPL.

graphify itself stays under its own permissive license; graphify-map depends on it, and permissive code can be used inside an AGPL work.
