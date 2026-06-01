"""Tests for declaration-name splitting and Agda --html URL construction."""

from agdablueprint.agda import split_module
from agdablueprint.Packages.agdablueprint import _agda_decl_url


def test_split_module_top_level():
    assert split_module("root2.root-prime-irrational1", {"root2"}) == (
        "root2",
        "root-prime-irrational1",
    )


def test_split_module_record_field():
    # A field stays under its module; the local part keeps the dotted remainder.
    assert split_module("root2.Rational.i", {"root2"}) == (
        "root2",
        "Rational.i",
    )


def test_split_module_prefers_longest_known_module():
    assert split_module("A.B.c", {"A", "A.B"}) == ("A.B", "c")


def test_split_module_library_fallback():
    # Unknown locally: everything but the last component is taken as the module.
    assert split_module("Data.Nat._+_", set()) == ("Data.Nat", "_+_")


def test_split_module_bare_name():
    assert split_module("Foo", set()) == ("Foo", "")


def test_agda_decl_url_matches_agda_html_scheme():
    url = _agda_decl_url("agda", "root2.root-prime-irrational1", {"root2"})
    assert url == "agda/root2.html#root-prime-irrational1"


def test_agda_decl_url_empty_dochome_is_unlinked():
    assert _agda_decl_url("", "root2.gcd", {"root2"}) == ""


def test_agda_decl_url_module_only_has_no_anchor():
    assert _agda_decl_url("https://x/docs", "root2", {"root2"}) == (
        "https://x/docs/root2.html"
    )
