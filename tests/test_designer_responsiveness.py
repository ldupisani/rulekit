"""Designer reads stay independent of expensive catalogs and review replay."""

import asyncio
import json
from copy import deepcopy
from threading import Event
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from rulekit.generation.exploration import (
    GenerationError,
    exploration_failure_path,
    exploration_path,
    read_exploration_events,
    read_exploration_failures,
)
from rulekit.generation.reviews import _raw_reviews, review_path
from rulekit.server.read_worker import ReadWorker


async def get(application, url):
    path = urlsplit(url)
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

    await application({
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": path.path, "raw_path": path.path.encode(),
        "query_string": path.query.encode(), "root_path": "", "headers": [],
        "client": ("127.0.0.1", 1), "server": ("localhost", 80),
    }, receive, send)
    assert messages[0]["status"] == 200
    return json.loads(b"".join(m.get("body", b"") for m in messages))


def test_recorded_inbox_and_ask_selector_skip_replay(monkeypatch, tmp_path):
    pytest.importorskip("fastapi", reason="Designer API requires the server extra")
    pytest.importorskip("markdown_it", reason="Designer help requires the server extra")
    from rulekit.server import api, app

    project = SimpleNamespace(source_index=None)
    monkeypatch.setattr(app, "ServerState", lambda _: SimpleNamespace(project=project))
    rows = [{"id": "recorded", "verdict": "invalid"}, {"id": "current", "verdict": "valid"}]
    monkeypatch.setattr(api, "read_review_history", lambda *args: [dict(row) for row in rows])
    calls = []

    def evidence(_):
        calls.append("evidence")
        return {"groups": [], "summary": {}, "targets": {}}

    def replay(_, review):
        calls.append(review["id"])
        return {"status": "regressed", "detail": "changed"}

    monkeypatch.setattr(api, "ask_review_evidence", evidence)
    monkeypatch.setattr(api, "premise_review_evidence", evidence)
    monkeypatch.setattr(api, "review_replay", replay)
    monkeypatch.setattr(api, "list_ask_availability", lambda _: [])
    rule = {
        "id": "rule", "generation": "premise", "supported": True,
        "status": "reviewed", "generated_count": 1, "failed_count": 0,
        "reviewed_count": 1, "validated_count": 0, "structural_covered": 1,
        "structural_total": 2, "signature_counts": {"surface:base": 1},
        "profile": {"phenomena": [], "categories": ["noun"], "fact_types": [], "slot_types": []},
    }
    exploration = {
        "rules": [rule, {**rule, "id": "other"}],
        "fillers": [{"identity": "object", "compatible_rules": ["other"]}],
    }
    monkeypatch.setattr(api, "exploration_status", lambda *args, **kwargs: deepcopy(exploration))
    application = app.create_app(tmp_path)

    async def check():
        assert (await get(application, "/api/generation/asks?include_evidence=false"))["asks"] == []
        recorded = await get(application, "/api/generation/recorded-history?view=attention")
        assert [row["id"] for row in recorded["reviews"]] == ["recorded"]
        assert calls == []
        verified = await get(application, "/api/generation/history?view=attention")
        assert [row["id"] for row in verified["reviews"]] == ["recorded", "current"]
        assert calls == ["evidence", "evidence", "current"]
        assert await get(application, "/api/generation/exploration") == exploration
        workbench = await get(application, "/api/generation/exploration?view=workbench")
        assert "signature_counts" not in workbench["rules"][0]
        assert workbench["rules"][0]["profile"]["categories"] == ["noun"]
        assert workbench["fillers"] == [{"identity": "object", "compatible_rule_indices": [1]}]

    asyncio.run(check())


def test_cancelled_read_keeps_its_lane_until_worker_finishes():
    async def check():
        release = Event()
        started = asyncio.Event()
        loop = asyncio.get_running_loop()
        completed = []

        @ReadWorker().wrap
        def endpoint(value):
            if value == 1:
                loop.call_soon_threadsafe(started.set)
                assert release.wait(2)
            completed.append(value)
            return value

        first = asyncio.create_task(endpoint(1))
        try:
            await asyncio.wait_for(started.wait(), 2)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            second = asyncio.create_task(endpoint(2))
            await asyncio.sleep(0)
            assert not second.done()
            assert completed == []
        finally:
            release.set()
        assert await asyncio.wait_for(second, 2) == 2
        assert completed == [1, 2]

    asyncio.run(check())


def test_incomplete_review_append_does_not_hide_complete_rows(tmp_path):
    project = SimpleNamespace(root=tmp_path)
    path = review_path(project)
    path.parent.mkdir()
    path.write_bytes(b'{"id":"complete"}\n{"id":"unfinished')
    assert _raw_reviews(project) == [{"id": "complete"}]


@pytest.mark.parametrize(("ledger_path", "read"), [
    (exploration_path, read_exploration_events),
    (exploration_failure_path, read_exploration_failures),
])
def test_exploration_read_can_overlap_an_append(tmp_path, ledger_path, read):
    project = SimpleNamespace(root=tmp_path)
    path = ledger_path(project)
    path.parent.mkdir()
    path.write_bytes(b'{"id":"unfinished')
    assert read(project) == []
    path.write_bytes(b'{"id":"corrupt\n')
    with pytest.raises(GenerationError, match="invalid exploration"):
        read(project)
