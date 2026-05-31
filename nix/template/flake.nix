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
          agdablueprint.packages.${system}.default
          pkgs.agda
          pkgs.graphviz
          pkgs.texliveMedium
        ];
      };
    };
}
