"""agdablueprint — blueprint-style coordination tooling for Agda projects.

This package is two things:

* A **plasTeX plugin**. Loaded via ``plastex --plugins=agdablueprint``, it makes
  the plasTeX package :mod:`agdablueprint.Packages.agdablueprint` available so a
  blueprint document can ``\\usepackage{agdablueprint}``. That package defines
  the Agda-flavored macros (``\\agda``, ``\\agdaok``, ``\\agdanotready`` …) and
  styles the dependency graph built by the proof-assistant-agnostic
  ``plastexdepgraph`` plugin.

* A **command-line tool** (:mod:`agdablueprint.cli`) that scaffolds, builds,
  serves, and checks blueprint projects.

plasTeX discovers a plugin by importing this package and looking for a
``Packages`` subdirectory, so the macro/rendering logic deliberately lives in
:mod:`agdablueprint.Packages.agdablueprint`, not here (mirroring how leanblueprint
keeps an empty top-level ``__init__``).
"""

__version__ = "0.0.1"
