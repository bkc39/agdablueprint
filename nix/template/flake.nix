{
  description = "An Agda blueprint project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    agdablueprint.url = "github:bkc39/agdablueprint";
  };

  outputs = { self, nixpkgs, agdablueprint }:
    let
      system = builtins.currentSystem or "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          # `agdablueprint` + `plastex` (plugin importable) — runs web/pdf/all.
          agdablueprint.packages.${system}.blueprintEnv
          # Agda with the standard library; add the libraries your .agda-lib
          # `depend:`s on here, e.g. (p: [ p.standard-library p.cubical ]).
          (pkgs.agda.withPackages (p: [ p.standard-library ]))
          pkgs.graphviz
          pkgs.texliveMedium
        ];
      };
    };
}
