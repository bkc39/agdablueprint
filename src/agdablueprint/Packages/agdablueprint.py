"""plasTeX package: Agda blueprint.

This is the agdablueprint counterpart of leanblueprint's ``blueprint`` package.
It depends on the proof-assistant-agnostic ``plastexdepgraph`` plugin (which
provides ``\\uses``, ``\\proves`` and the dependency-graph machinery) and layers
Agda-specific macros and node coloring on top.

It is loaded from a blueprint document with ``\\usepackage{agdablueprint}`` as
long as the ``agdablueprint`` plugin is active (``plastex --plugins=agdablueprint``,
or the ``plugins`` key in ``plastex.cfg``).

Macros
------
* ``\\agda{decl, ...}``   link a statement to one or more Agda declarations.
* ``\\agdaok``            mark a statement/proof as formalized in Agda.
* ``\\agdanotready``      mark a statement as explicitly not ready to formalize.
* ``\\notready``          alias kept for familiarity with leanblueprint.
* ``\\stdlibok``          the declaration lives upstream (agda-stdlib / a library).
* ``\\discussion{n}``     link to issue ``n`` of the project's GitHub repo.
* ``\\home``/``\\github``/``\\dochome``  project metadata used for links.
* ``\\graphcolor{key}{color}{descr}``  override a dependency-graph color.

Options
-------
Any option not understood here is forwarded to the ``depgraph`` package, so e.g.
``thms=definition+lemma+theorem`` works as documented by plastexdepgraph.
"""

# This module is glue against plasTeX's macro framework, whose type information
# is looser than its runtime contract: `parentNode`/`ownerDocument` are typed
# Optional but are always present while a macro is being digested/invoked, and a
# Command's `invoke` returns `[]` to expand to nothing (matching leanblueprint),
# which plasTeX types as `None`. Confine those framework-interaction overrides
# here rather than relaxing pyright globally.
# pyright: reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportIncompatibleMethodOverride=false

import string
from pathlib import Path

from jinja2 import Template
from plasTeX import Command
from plasTeX.Logging import getLogger
from plasTeX.PackageResource import PackageCss, PackageTemplateDir
from plastexdepgraph.Packages.depgraph import item_kind

log = getLogger()

PKG_DIR = Path(__file__).parent
STATIC_DIR = Path(__file__).parent.parent / "static"


def _discover_project_modules(working_dir: Path) -> set[str]:
    """Find the Agda project near the blueprint and list its module names.

    Walks up from plasTeX's working directory to the nearest ``.agda-lib`` and
    returns that project's modules, so declaration links can be split into the
    ``<module>.html#<name>`` form Agda's ``--html`` output uses. Returns an empty
    set (links fall back to a last-component split) if no project is found.
    """
    from agdablueprint.agda import AgdaProject

    for d in (working_dir, *working_dir.parents):
        if any(d.glob("*.agda-lib")):
            try:
                return AgdaProject.discover(d).modules()
            except OSError:
                return set()
    return set()


def _agda_decl_url(dochome: str, fqn: str, project_modules: set[str]) -> str:
    """Build the URL of ``fqn`` in the Agda ``--html`` docs rooted at ``dochome``.

    Agda renders each module ``M`` to ``M.html`` and anchors every definition by
    its module-relative name, so ``root2.root-prime-irrational1`` lives at
    ``<dochome>/root2.html#root-prime-irrational1``. Empty when ``dochome`` is
    unset (the template then renders plain, unlinked text).
    """
    from agdablueprint.agda import split_module

    if not dochome:
        return ""
    module, local = split_module(fqn, project_modules)
    base = f"{dochome}/{module}.html"
    return f"{base}#{local}" if local else base


# --------------------------------------------------------------------------- #
# Project metadata macros
# --------------------------------------------------------------------------- #
class home(Command):
    r"""\home{url}"""

    args = "url:url"

    def invoke(self, tex):
        Command.invoke(self, tex)
        self.ownerDocument.userdata["project_home"] = self.attributes["url"]
        return []


class github(Command):
    r"""\github{url}"""

    args = "url:url"

    def invoke(self, tex):
        Command.invoke(self, tex)
        self.ownerDocument.userdata["project_github"] = self.attributes[
            "url"
        ].textContent.rstrip("/")
        return []


class dochome(Command):
    r"""\dochome{url}

    Base URL of the project's generated Agda HTML documentation (e.g. the output
    of ``agda --html``). Declaration links in the dependency graph are formed
    relative to it.
    """

    args = "url:url"

    def invoke(self, tex):
        Command.invoke(self, tex)
        self.ownerDocument.userdata["project_dochome"] = self.attributes[
            "url"
        ].textContent.rstrip("/")
        return []


class graphcolor(Command):
    r"""\graphcolor{node_type}{color}{color_descr}"""

    args = "node_type:str color:str color_descr:str"

    def digest(self, tokens):
        Command.digest(self, tokens)
        attrs = self.attributes
        colors = self.ownerDocument.userdata["dep_graph"]["colors"]
        node_type = attrs["node_type"]
        if node_type not in colors:
            log.warning(f"Unknown node type {node_type}")
        colors[node_type] = (
            attrs["color"].strip(),
            attrs["color_descr"].strip(),
        )


# --------------------------------------------------------------------------- #
# Formalization status macros
# --------------------------------------------------------------------------- #
class agdaok(Command):
    r"""\agdaok"""

    def digest(self, tokens):
        Command.digest(self, tokens)
        self.parentNode.userdata["agdaok"] = True


class notready(Command):
    r"""\notready"""

    def digest(self, tokens):
        Command.digest(self, tokens)
        self.parentNode.userdata["notready"] = True


class agdanotready(Command):
    r"""\agdanotready (Agda-flavored alias for \notready)"""

    def digest(self, tokens):
        Command.digest(self, tokens)
        self.parentNode.userdata["notready"] = True


class stdlibok(Command):
    r"""\stdlibok

    The declaration is part of an upstream library (e.g. agda-stdlib or
    agda-unimath). Implies it is formalized.
    """

    def digest(self, tokens):
        Command.digest(self, tokens)
        self.parentNode.userdata["agdaok"] = True
        self.parentNode.userdata["stdlibok"] = True


class agda(Command):
    r"""\agda{decl list}"""

    args = "decls:list:nox"

    def digest(self, tokens):
        Command.digest(self, tokens)
        decls = [dec.strip() for dec in self.attributes["decls"]]
        self.parentNode.setUserData("agdadecls", decls)
        all_decls = self.ownerDocument.userdata.setdefault("agda_decls", [])
        all_decls.extend(decls)


class discussion(Command):
    r"""\discussion{issue_number}"""

    args = "issue:str"

    def digest(self, tokens):
        Command.digest(self, tokens)
        self.parentNode.setUserData(
            "issue", self.attributes["issue"].lstrip("#").strip()
        )


# --------------------------------------------------------------------------- #
# Jinja templates injected into theorem headers and graph modals
# --------------------------------------------------------------------------- #
CHECKMARK_TPL = Template(
    """
    {% if obj.userdata.agdaok and ('proved_by' not in obj.userdata or obj.userdata.proved_by.userdata.agdaok ) %}
    ✓
    {% endif %}
"""
)

AGDA_DECLS_TPL = Template(
    """
    {% if obj.userdata.agdadecls %}
    <button class="modal agda">Agda</button>
    {% call modal('Agda declarations') %}
        <ul class="uses">
          {% for agda, url in obj.userdata.agda_urls %}
          <li>{% if url %}<a href="{{ url }}" class="agda_decl">{{ agda }}</a>{% else %}<span class="agda_decl">{{ agda }}</span>{% endif %}</li>
          {% endfor %}
        </ul>
    {% endcall %}
    {% endif %}
"""
)

GITHUB_ISSUE_TPL = Template(
    """
    {% if obj.userdata.issue %}
    <a class="github_link" href="{{ obj.ownerDocument.userdata.project_github }}/issues/{{ obj.userdata.issue }}">Discussion</a>
    {% endif %}
"""
)

AGDA_LINKS_TPL = Template(
    """
  {% if thm.userdata['agda_urls'] -%}
    {%- if thm.userdata['agda_urls']|length > 1 -%}
  <div class="tooltip">
      <span class="agda_link">Agda</span>
      <ul class="tooltip_list">
        {% for name, url in thm.userdata['agda_urls'] %}
           <li>{% if url %}<a href="{{ url }}" class="agda_decl">{{ name }}</a>{% else %}<span class="agda_decl">{{ name }}</span>{% endif %}</li>
        {% endfor %}
      </ul>
  </div>
    {%- else -%}
    {%- if thm.userdata['agda_urls'][0][1] -%}
    <a class="agda_link agda_decl" href="{{ thm.userdata['agda_urls'][0][1] }}">Agda</a>
    {%- else -%}
    <span class="agda_link agda_decl">Agda</span>
    {%- endif -%}
    {%- endif -%}
    {%- endif -%}
"""
)

GITHUB_LINK_TPL = Template(
    """
  {% if thm.userdata['issue'] -%}
  <a class="issue_link" href="{{ document.userdata['project_github'] }}/issues/{{ thm.userdata['issue'] }}">Discussion</a>
  {%- endif -%}
"""
)


def ProcessOptions(options, document):
    """Called when ``\\usepackage{agdablueprint}`` loads this package."""

    # Ensure the dependency-graph plugin/package is available, then load it.
    plugins = document.config["general"].data["plugins"].value
    if "plastexdepgraph" not in plugins:
        plugins.append("plastexdepgraph")
    document.context.loadPythonPackage(document, "depgraph", options)
    if "showmore" in options:
        if "plastexshowmore" not in plugins:
            plugins.append("plastexshowmore")
        document.context.loadPythonPackage(document, "showmore", {})

    templatedir = PackageTemplateDir(path=PKG_DIR / "renderer_templates")
    document.addPackageResource(templatedir)

    jobname = document.userdata["jobname"]
    outdir = document.config["files"]["directory"]
    outdir = string.Template(outdir).substitute({"jobname": jobname})

    def make_agda_data() -> None:
        """Build URLs and per-node formalization status, and write agda_decls.

        ``agda_decls`` (one declaration name per line) is the input to
        ``agdablueprint checkdecls``, which verifies the names exist in the Agda
        project.
        """
        dochome = document.userdata.get("project_dochome", "")
        working_dir = Path(document.userdata["working-dir"])
        project_modules = _discover_project_modules(working_dir)

        for graph in document.userdata["dep_graph"]["graphs"].values():
            nodes = graph.nodes
            for node in nodes:
                agdadecls = node.userdata.get("agdadecls", [])
                agda_urls = []
                for agdadecl in agdadecls:
                    url = _agda_decl_url(dochome, agdadecl, project_modules)
                    agda_urls.append((agdadecl, url))
                node.userdata["agda_urls"] = agda_urls

                used = node.userdata.get("uses", [])
                node.userdata["can_state"] = all(
                    thm.userdata.get("agdaok") for thm in used
                ) and not node.userdata.get("notready", False)
                proof = node.userdata.get("proved_by")
                if proof:
                    used = list(used) + proof.userdata.get("uses", [])
                    node.userdata["can_prove"] = all(
                        thm.userdata.get("agdaok") for thm in used
                    )
                    node.userdata["proved"] = proof.userdata.get(
                        "agdaok", False
                    )
                else:
                    node.userdata["can_prove"] = False
                    node.userdata["proved"] = False

            for node in nodes:
                node.userdata["fully_proved"] = all(
                    n.userdata.get("proved", False)
                    or item_kind(n) == "definition"
                    for n in graph.ancestors(node).union({node})
                )

        agda_decls_path = (
            Path(document.userdata["working-dir"]).parent / "agda_decls"
        )
        agda_decls_path.write_text(
            "\n".join(document.userdata.get("agda_decls", []))
        )

    document.addPostParseCallbacks(150, make_agda_data)

    document.addPackageResource(
        [PackageCss(path=STATIC_DIR / "agdablueprint.css")]
    )

    colors = document.userdata["dep_graph"]["colors"] = {
        "stdlib": ("darkgreen", "Dark green"),
        "stated": ("green", "Green"),
        "can_state": ("blue", "Blue"),
        "not_ready": ("#FFAA33", "Orange"),
        "proved": ("#9CEC8B", "Green"),
        "can_prove": ("#A3D6FF", "Blue"),
        "defined": ("#B0ECA3", "Light green"),
        "fully_proved": ("#1CAC78", "Dark green"),
    }

    def colorizer(node) -> str:
        data = node.userdata
        color = ""
        if data.get("stdlibok"):
            color = colors["stdlib"][0]
        elif data.get("agdaok"):
            color = colors["stated"][0]
        elif data.get("can_state"):
            color = colors["can_state"][0]
        elif data.get("notready"):
            color = colors["not_ready"][0]
        return color

    def fillcolorizer(node) -> str:
        data = node.userdata
        stated = data.get("agdaok")
        can_state = data.get("can_state")
        can_prove = data.get("can_prove")
        proved = data.get("proved")
        fully_proved = data.get("fully_proved")

        fillcolor = ""
        if proved:
            fillcolor = colors["proved"][0]
        elif can_prove and (can_state or stated):
            fillcolor = colors["can_prove"][0]
        if item_kind(node) == "definition":
            if stated:
                fillcolor = colors["defined"][0]
            elif can_state:
                fillcolor = colors["can_prove"][0]
        elif fully_proved:
            fillcolor = colors["fully_proved"][0]
        return fillcolor

    document.userdata["dep_graph"]["colorizer"] = colorizer
    document.userdata["dep_graph"]["fillcolorizer"] = fillcolorizer

    def make_legend() -> None:
        c = document.userdata["dep_graph"]["colors"]
        document.userdata["dep_graph"]["legend"].extend(
            [
                (
                    f"{c['can_state'][1]} border",
                    "the <em>statement</em> of this result is ready to be formalized; all prerequisites are done",
                ),
                (
                    f"{c['not_ready'][1]} border",
                    "the <em>statement</em> of this result is not ready to be formalized; the blueprint needs more work",
                ),
                (
                    f"{c['can_prove'][1]} background",
                    "the <em>proof</em> of this result is ready to be formalized; all prerequisites are done",
                ),
                (
                    f"{c['proved'][1]} border",
                    "the <em>statement</em> of this result is formalized in Agda",
                ),
                (
                    f"{c['proved'][1]} background",
                    "the <em>proof</em> of this result is formalized in Agda",
                ),
                (
                    f"{c['fully_proved'][1]} background",
                    "the <em>proof</em> of this result and all its ancestors are formalized",
                ),
                (
                    f"{c['stdlib'][1]} border",
                    "this is available in an upstream Agda library",
                ),
            ]
        )

    document.addPostParseCallbacks(150, make_legend)

    document.userdata.setdefault("thm_header_extras_tpl", []).extend(
        [CHECKMARK_TPL]
    )
    document.userdata.setdefault("thm_header_hidden_extras_tpl", []).extend(
        [AGDA_DECLS_TPL, GITHUB_ISSUE_TPL]
    )
    document.userdata["dep_graph"].setdefault(
        "extra_modal_links_tpl", []
    ).extend([AGDA_LINKS_TPL, GITHUB_LINK_TPL])
