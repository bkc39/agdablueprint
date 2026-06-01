{
  description = "agdablueprint — blueprint-style coordination tooling for Agda formalization projects";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f {
        inherit system;
        pkgs = import nixpkgs { inherit system; };
      });

      # The Python runtime dependencies, kept in one place so the package and
      # the devShell agree.
      pyDeps = ps: with ps; [ plasTeX plastexdepgraph pygraphviz click ];

      # agdablueprint as an importable Python *library*. Needed so it can be put
      # into a python.withPackages environment alongside plasTeX, which is what
      # makes `plastex --plugins=agdablueprint` work (the plugin must be
      # importable by the very python that runs plastex).
      mkLib = pkgs: pkgs.python3Packages.buildPythonPackage {
        pname = "agdablueprint";
        version = "0.0.1";
        pyproject = true;
        src = ./.;
        build-system = [ pkgs.python3Packages.hatchling ];
        dependencies = pyDeps pkgs.python3Packages;
        nativeCheckInputs = [ pkgs.python3Packages.pytestCheckHook ];
      };

      # A ready-to-run blueprint toolchain: a single python env exposing both the
      # `agdablueprint` CLI and the `plastex` it drives, with the plugin
      # importable. Deliberately does NOT bundle agda — consumers put their own
      # `agda.withPackages [ … ]` (with the libraries their blueprint references)
      # on PATH, so `checkdecls`/`agda --html` resolve against the right project.
      mkBlueprintEnv = pkgs: pkgs.python3.withPackages (ps: [ (mkLib pkgs) ]);

      # Agda with the standard library available so blueprints whose .agda-lib
      # `depend:`s on standard-library type-check (and so `checkdecls` can
      # resolve stdlib imports). This is the `agda.withPackages [standard-library]`
      # wrinkle from the end-to-end test (issue #3).
      agdaWithStdlib = pkgs: pkgs.agda.withPackages (p: [ p.standard-library ]);
    in
    {
      packages = forAllSystems ({ pkgs, ... }: rec {
        agdablueprint = pkgs.python3Packages.buildPythonApplication {
          pname = "agdablueprint";
          version = "0.0.1";
          pyproject = true;
          src = ./.;
          build-system = [ pkgs.python3Packages.hatchling ];
          dependencies = pyDeps pkgs.python3Packages;
          nativeCheckInputs = [ pkgs.python3Packages.pytestCheckHook ];
          # Agda + graphviz are runtime tools invoked by the CLI, exposed via PATH.
          makeWrapperArgs = [
            "--prefix PATH : ${pkgs.lib.makeBinPath [ (agdaWithStdlib pkgs) pkgs.graphviz ]}"
          ];
        };
        # Python env with `agdablueprint` + `plastex` (plugin importable) for
        # consumers/CI that supply their own agda; see `mkBlueprintEnv`.
        blueprintEnv = mkBlueprintEnv pkgs;
        default = agdablueprint;
      });

      devShells = forAllSystems ({ pkgs, ... }: {
        default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps: (pyDeps ps) ++ [ ps.pytest ps.hatchling ]))
            pkgs.black
            pkgs.pyright
            (agdaWithStdlib pkgs)
            pkgs.graphviz
            # texlive scheme used for the `pdf` build path; medium keeps the
            # closure reasonable while covering the AMS/blueprint preamble.
            (pkgs.texliveMedium)
          ];
          shellHook = ''
            echo "agdablueprint devShell — python $(python3 --version 2>&1 | cut -d' ' -f2), agda $(agda --version 2>&1 | head -1)"
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };
      });

      # `nix flake init -t .#blueprint` scaffolds a new Agda blueprint project.
      templates.blueprint = {
        path = ./nix/template;
        description = "A new Agda blueprint project";
      };
      templates.default = self.templates.blueprint;
    };
}
