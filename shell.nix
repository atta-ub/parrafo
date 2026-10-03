# Development shell with Python and the libraries parrafo needs.
# Use `nix-shell`, then `python -m parrafo`, or just run ./parrafo-run.
{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (p: [ p.rich p.typer p.requests p.pytest ]))
  ];
}
