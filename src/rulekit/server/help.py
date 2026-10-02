"""Read-only authoring help; never a general filesystem document endpoint."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from markdown_it import MarkdownIt

from rulekit.data.schemas import KIND_MODELS, SLOT_TYPES


DOCUMENTS = {
    "yaml-reference": ("yaml-reference.md", "YAML reference"),
    "architecture": ("architecture.md", "Architecture"),
}


def document_path(name: str) -> Path:
    """Resolve only bundled, explicitly named help documents."""
    if name not in DOCUMENTS:
        raise HTTPException(404, "Unknown help document")
    filename = DOCUMENTS[name][0]
    packaged = Path(__file__).parent / "docs" / filename
    if packaged.is_file():
        return packaged
    # Editable/source checkout: the Markdown under docs/ is the authored copy.
    root = Path(__file__).resolve().parents[3]
    if (root / "src/rulekit/server/help.py").resolve() == Path(__file__).resolve():
        source = root / "docs" / filename
        if source.is_file():
            return source
    raise HTTPException(503, "Help document is missing from this installation")


def _page(title: str, body: str, navigation: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · RuleKit</title>
<link rel="stylesheet" href="/static/help.css"></head>
<body><header><strong>RuleKit authoring help</strong><nav aria-label="Help">
<a href="/help/yaml-reference">YAML reference</a>
<a href="/help/schemas">Live schemas</a>
<a href="/help/architecture">Architecture</a>
</nav></header><div class="help-layout">
<aside aria-label="On this page">{navigation}</aside>
<main id="content">{body}</main></div></body></html>"""


def render_document(name: str, source: str) -> str:
    """Render trusted local prose with raw HTML and unsafe URLs disabled."""
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = md.parse(source)
    toc = []
    used: dict[str, int] = {}
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            label = tokens[index + 1].content
            base = re.sub(r"[^\w\- ]", "", label.lower()).replace(" ", "-")
            number = used.get(base, 0)
            used[base] = number + 1
            anchor = f"{base}-{number}" if number else base
            token.attrSet("id", anchor)
            if token.tag in {"h2", "h3"}:
                toc.append(
                    f'<a class="{token.tag}" href="#{anchor}">'
                    f"{html.escape(label)}</a>"
                )
        # Repo-relative links must not turn into a filesystem-serving route.
        for child in token.children or []:
            if child.type != "link_open":
                continue
            href = child.attrGet("href") or ""
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = next(
                (key for key, (file, _) in DOCUMENTS.items() if parsed.path == file),
                None,
            )
            if target:
                child.attrSet("href", f"/help/{target}" + (
                    f"#{parsed.fragment}" if parsed.fragment else ""
                ))
            else:
                # Keep checkout-only references legible, without dead links.
                child.attrs.pop("href", None)
                child.attrSet("title", f"Repository reference: {href}")
                child.attrSet("class", "checkout-reference")
    return _page(
        DOCUMENTS[name][1], md.renderer.render(tokens, md.options, {}),
        '<p class="hint">Find text with Ctrl/Cmd + F.</p>' + "".join(toc),
    )


def schema_catalog() -> dict:
    return {
        "slot_types": list(SLOT_TYPES),
        "documents": {
            kind: model.model_json_schema(by_alias=True)
            for kind, model in sorted(KIND_MODELS.items())
        },
    }


def render_schemas() -> str:
    catalog = schema_catalog()
    models = {}
    for schema in catalog["documents"].values():
        models[schema["title"]] = {k: v for k, v in schema.items() if k != "$defs"}
        models.update(schema.get("$defs", {}))
    navigation = []
    sections = []
    for name, schema in sorted(models.items()):
        escaped = html.escape(name)
        navigation.append(f'<a href="#{escaped}">{escaped}</a>')
        required = set(schema.get("required", []))
        rows = []
        for field, contract in schema.get("properties", {}).items():
            rows.append(
                f"<tr><th scope=row><code>{html.escape(field)}</code>"
                f'<br><small>{"required" if field in required else "optional"}</small></th>'
                f"<td><pre>{html.escape(json.dumps(contract, indent=2))}</pre></td></tr>"
            )
        extra = schema.get("additionalProperties", True)
        sections.append(
            f'<section id="{escaped}"><h2>{escaped}</h2>'
            f'<p>{html.escape(schema.get("description", ""))}</p>'
            f'<p>Additional properties: <code>{html.escape(str(extra))}</code></p>'
            '<table><thead><tr><th>YAML field</th><th>JSON Schema contract</th></tr>'
            f'</thead><tbody>{"".join(rows)}</tbody></table></section>'
        )
    body = (
        "<h1>Live YAML schemas</h1>"
        "<p>Generated from the running Pydantic models, not a copied field list. "
        "References such as <code>#/$defs/MatchToken</code> name the corresponding "
        "model section below. Python validators, registry checks and runtime "
        "restrictions still apply; schema acceptance alone is not execution support.</p>"
        '<p><a href="/help/schemas.json">Download JSON schemas</a></p>'
        '<h2 id="slot-types">Built-in slot types</h2><p><code>'
        + html.escape(", ".join(catalog["slot_types"])) + "</code></p>"
        + "".join(sections)
    )
    return _page("Live YAML schemas", body, "".join(navigation))


def build_help_router() -> APIRouter:
    router = APIRouter()

    @router.get("/help/schemas", response_class=HTMLResponse)
    def schemas():
        return render_schemas()

    @router.get("/help/schemas.json")
    def schemas_json():
        return schema_catalog()

    @router.get("/help/{name}", response_class=HTMLResponse)
    def document(name: str):
        return render_document(name, document_path(name).read_text(encoding="utf-8"))

    return router
