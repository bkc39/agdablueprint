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
            "--prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.agda pkgs.graphviz ]}"
          ];
        };
        default = agdablueprint;
      });

      devShells = forAllSystems ({ pkgs, ... }: {
        default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps: (pyDeps ps) ++ [ ps.pytest ps.hatchling ]))
            pkgs.agda
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
