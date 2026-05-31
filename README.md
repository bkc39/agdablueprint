# agdablueprint

Blueprint-style coordination tooling for [Agda](https://agda.readthedocs.io)
formalization projects — the Agda counterpart to
[`leanblueprint`](https://github.com/PatrickMassot/leanblueprint).

A *blueprint* links an informal LaTeX exposition of a mathematical development
to the formal Agda code that realizes it, and renders an interactive
**dependency graph** showing, for each result, whether it has been stated and
proved. It is a coordination tool for large collaborative formalization
projects.

> **Status: early development (v0.0.1).** Phase 1 (project skeleton) is in
> place; the plasTeX plugin, Agda declaration checker, and CLI are being built
> out. See `docs`/the issue tracker for the roadmap.

## How it works

agdablueprint stands on the proof-assistant-agnostic
[`plastexdepgraph`](https://github.com/PatrickMassot/plastexdepgraph) plugin,
which already turns `\uses{...}` / `\label{...}` annotations in a LaTeX document
into an interactive HTML dependency graph. agdablueprint adds a thin
Agda-flavored layer on top:

| Macro            | Meaning                                                            |
| ---------------- | ----------------------------------------------------------------- |
| `\agda{Mod.name}`| Link a LaTeX statement to an Agda declaration.                    |
| `\agdaok`        | Mark a statement/proof as formalized in Agda (turns the node green). |
| `\agdanotready`  | Mark a statement as explicitly not yet started.                   |

On the web side, `\uses`, `\proves`, and `\label` are handled by
`plastexdepgraph`. agdablueprint's LaTeX macro files (`macros/common.tex`,
`macros/print.tex`, `agdablueprint.sty`) are **adapted from
[`leanblueprint`](https://github.com/PatrickMassot/leanblueprint)'s templates**
(Apache-2.0): the `\uses` / `\proves` print definitions, the package stub, and
the theorem-environment block are reused largely verbatim, with leanblueprint's
Lean-named status macros replaced by the Agda ones above. agdablueprint does not
depend on `leanblueprint` at runtime.

The `agdablueprint checkdecls` command verifies that every declaration named in
an `\agda{...}` macro actually exists and type-checks in your Agda project.

## Installation

### Nix (recommended, reproducible)

```sh
nix develop          # dev shell with python + agda + graphviz + texlive
nix build .#agdablueprint
```

Scaffold a new blueprint project:

```sh
nix flake init -t github:bkc39/agdablueprint#blueprint
```

### pip

```sh
pip install agdablueprint
```

This requires `agda`, `graphviz` (with its development headers, for
`pygraphviz`), and a TeX distribution to be installed on your system — the same
external prerequisites `leanblueprint` assumes for Lean.

## CLI

```
agdablueprint new         # scaffold a new blueprint project   (Phase 4)
agdablueprint web         # build the HTML dependency graph     (Phase 4)
agdablueprint pdf         # build the PDF blueprint             (Phase 4)
agdablueprint checkdecls  # verify \agda{...} names in Agda     (Phase 3)
agdablueprint serve       # serve the built web blueprint       (Phase 4)
agdablueprint all         # pdf + web + checkdecls              (Phase 4)
```

## Credits

agdablueprint is the Agda counterpart to
[`leanblueprint`](https://github.com/PatrickMassot/leanblueprint) by Patrick
Massot, and adapts its LaTeX macro layer and project layout (Apache-2.0). It
also builds on [`plastexdepgraph`](https://github.com/PatrickMassot/plastexdepgraph)
and [`plasTeX`](https://github.com/plastex/plastex). See [NOTICE](NOTICE).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
