# agdablueprint

Blueprint-style coordination tooling for [Agda](https://agda.readthedocs.io)
formalization projects — the Agda counterpart to
[`leanblueprint`](https://github.com/PatrickMassot/leanblueprint).

A *blueprint* links an informal LaTeX exposition of a mathematical development
to the formal Agda code that realizes it, and renders an interactive
**dependency graph** showing, for each result, whether it has been stated and
proved. It is a coordination tool for large collaborative formalization
projects.

> **Status: early development (v0.0.1).** The plasTeX plugin, Agda declaration
> checker, and the `new`/`web`/`pdf`/`serve`/`all` CLI are in place and covered
> by an end-to-end test against a real agda-stdlib-backed project. See the issue
> tracker for the roadmap (automatic status detection, nixpkgs packaging).

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
agdablueprint new         # scaffold a new blueprint project
agdablueprint web         # build the HTML dependency graph
agdablueprint pdf         # build the PDF blueprint
agdablueprint checkdecls  # verify \agda{...} names in Agda
agdablueprint serve       # serve the built web blueprint
agdablueprint all         # pdf + web + checkdecls
```

## Project layout

`agdablueprint new` scaffolds the blueprint next to your Agda code, mirroring
`leanblueprint`:

```
my-project/
├── my-project.agda-lib      # your Agda library (depend: standard-library, …)
├── src/                     # your Agda modules
├── plastex.cfg              # plasTeX config (plugins = agdablueprint)
└── blueprint/
    ├── agda_decls           # written by `web`; the input to `checkdecls`
    └── src/
        ├── web.tex          # web entry point (plasTeX → dependency graph)
        ├── print.tex        # pdf entry point (latexmk/pdflatex)
        ├── content.tex      # your exposition (shared by web + print)
        ├── agdablueprint.sty
        └── macros/{common,web,print}.tex
```

`agdablueprint web` builds `blueprint/web/`, `agdablueprint pdf` builds
`blueprint/print/`, and `agdablueprint all` runs both and then `checkdecls`
against the project's `.agda-lib`. A worked, stdlib-backed example lives in
[`examples/stdlib`](examples/stdlib).

## Credits

agdablueprint is the Agda counterpart to
[`leanblueprint`](https://github.com/PatrickMassot/leanblueprint) by Patrick
Massot, and adapts its LaTeX macro layer and project layout (Apache-2.0). It
also builds on [`plastexdepgraph`](https://github.com/PatrickMassot/plastexdepgraph)
and [`plasTeX`](https://github.com/plastex/plastex). See [NOTICE](NOTICE).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
