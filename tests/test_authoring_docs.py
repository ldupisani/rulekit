"""The authored help and running schemas must stay useful and safely scoped."""

from __future__ import annotations

import asyncio
import json
import re
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="Designer help requires the server extra")
pytest.importorskip("markdown_it", reason="Designer help requires the server extra")

from fastapi import APIRouter, HTTPException
from markdown_it import MarkdownIt
from ruamel.yaml import YAML

from rulekit.data.packs import LoadedPack, load_packs
from rulekit.data.registry import compile_registry
from rulekit.data.schemas import KIND_MODELS, SLOT_TYPES, PackDoc
from rulekit.kernel.engine import solve
from rulekit.server import help as help_module
from rulekit.server.help import (
    DOCUMENTS, document_path, render_document, render_schemas, schema_catalog,
)


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/yaml-reference.md"


def guide_documents():
    for token in MarkdownIt().parse(GUIDE.read_text()):
        if token.type == "fence" and token.info == "yaml":
            data = YAML(typ="safe").load(token.content)
            if "format" in data:
                yield KIND_MODELS[data["format"]].model_validate(data)


def test_guide_format_inventory_tracks_all_document_models():
    formats = set(re.findall(r"`(rulekit/[a-z-]+@\d+)`", GUIDE.read_text()))
    assert formats == set(KIND_MODELS)


def test_complete_yaml_examples_validate_and_rules_round_trip(tmp_path):
    documents = list(guide_documents())
    assert len(documents) >= 8
    # Compile just language packs plus the illustrative rules, avoiding the
    # production arithmetic rules that intentionally already cover this shape.
    pack = LoadedPack(
        "example", tmp_path,
        PackDoc(format="rulekit/pack@1", name="example"),
    )
    pack.rules = [doc for doc in documents if doc.format == "rulekit/rules@1"]
    registry = compile_registry([
        *load_packs([ROOT / "packs/core-english", ROOT / "packs/difg-mined"]),
        pack,
    ])
    result = solve("Aven has 4 apples. How many apples does Aven have?", registry)
    assert result.answer.value == 4


def test_live_schemas_come_from_runtime_and_use_yaml_aliases():
    catalog = schema_catalog()
    assert catalog["slot_types"] == list(SLOT_TYPES)
    for kind, model in KIND_MODELS.items():
        assert catalog["documents"][kind] == model.model_json_schema(by_alias=True)
    conversion = catalog["documents"]["rulekit/conversions@1"]["$defs"]["ConversionDef"]
    assert "from" in conversion["properties"]
    assert "from_" not in conversion["properties"]
    category = catalog["documents"]["rulekit/categories@1"]["$defs"]["CategoryDef"]
    assert "includes" in category["properties"]
    rendered = render_schemas()
    assert 'id="MatchToken"' in rendered
    assert 'id="WherePredicate"' in rendered
    assert 'href="/help/schemas.json"' in rendered


@pytest.mark.parametrize("name", DOCUMENTS)
def test_authored_documents_render_with_valid_internal_links(name):
    path = document_path(name)
    assert path == ROOT / "docs" / DOCUMENTS[name][0]
    source = path.read_text()
    rendered = render_document(name, source)
    anchors = re.findall(r' id="([^"]+)"', rendered)
    assert len(anchors) == len(set(anchors))
    for anchor in re.findall(r'href="#([^"]+)"', rendered):
        assert anchor in anchors, anchor
    assert "<table>" in rendered
    for destination in re.findall(r"\]\(([^)]+)\)", source):
        if destination.startswith("#"):
            continue
        target, _, fragment = destination.partition("#")
        assert (path.parent / target).is_file(), destination
        if fragment:
            key = next(k for k, (f, _) in DOCUMENTS.items() if f == target)
            other = render_document(key, (path.parent / target).read_text())
            assert f'id="{fragment}"' in other


def test_help_is_not_a_filesystem_browser_and_html_is_not_executable():
    for name in ("../../project.yaml", "HANDOFF", "data", "test.parquet", ""):
        with pytest.raises(HTTPException) as caught:
            document_path(name)
        assert caught.value.status_code == 404
    source = (
        '# Example\n\n<script>alert(1)</script>\n\n'
        '[unsafe](javascript:alert(1))\n\n'
        '[dataset](../../projects/gsm8k/data/train.parquet)\n\n'
        '[reference](yaml-reference.md#lexicon)'
    )
    rendered = render_document("architecture", source)
    assert "<script>" not in rendered
    assert 'href="javascript:' not in rendered
    assert 'href="../../projects' not in rendered
    assert 'href="/help/yaml-reference#lexicon"' in rendered


def test_wheel_bundles_single_authored_copies():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    files = config["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    for filename, _ in DOCUMENTS.values():
        assert files[f"docs/{filename}"] == f"rulekit/server/docs/{filename}"


def test_installed_document_resolution_and_missing_resource(tmp_path, monkeypatch):
    installed = tmp_path / "site-packages/rulekit/server"
    installed.mkdir(parents=True)
    module_path = installed / "help.py"
    monkeypatch.setattr(help_module, "__file__", str(module_path))
    with pytest.raises(HTTPException) as caught:
        document_path("yaml-reference")
    assert caught.value.status_code == 503
    docs = installed / "docs"
    docs.mkdir()
    bundled = docs / "yaml-reference.md"
    bundled.write_text("# Bundled guide")
    assert document_path("yaml-reference") == bundled


async def _get(app, path):
    """Tiny ASGI request: no optional httpx dependency, sockets, or server."""
    messages = []
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.Event().wait()

    async def send(message):
        messages.append(message)

    await app({
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": b"",
        "root_path": "", "headers": [], "client": ("127.0.0.1", 1),
        "server": ("localhost", 80),
    }, receive, send)
    start = next(m for m in messages if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return start["status"], dict(start["headers"]), body.decode()


def test_designer_help_routes_and_editor_link(monkeypatch):
    from rulekit.server import app as app_module

    # Exercise the real app integration without loading corpus state;
    # help is independent of the selected project.
    monkeypatch.setattr(app_module, "ServerState", lambda _: object())
    monkeypatch.setattr(app_module, "build_router", lambda _: APIRouter())
    app = app_module.create_app(ROOT / "projects/curated")
    status, _, page = asyncio.run(_get(app, "/"))
    assert status == 200
    assert 'href="/help/yaml-reference" target="_blank" rel="noopener"' in page
    for path in ("/help/yaml-reference", "/help/architecture", "/help/schemas"):
        status, headers, body = asyncio.run(_get(app, path))
        assert status == 200
        assert b"text/html" in headers[b"content-type"]
        assert headers[b"cache-control"] == b"no-cache"
        assert "RuleKit" in body
    status, _, body = asyncio.run(_get(app, "/help/schemas.json"))
    assert status == 200
    assert set(json.loads(body)["documents"]) == set(KIND_MODELS)
    status, _, _ = asyncio.run(_get(app, "/help/project.yaml"))
    assert status == 404
    status, _, css = asyncio.run(_get(app, "/static/help.css"))
    assert status == 200
    assert "@media" in css
