"""The designer's API: project browse, doc edit with validation + lint,
trace (the decision stream the stepper replays), and the impact panel.

State model: one Project loaded per server. A doc save re-loads packs from
disk and re-compiles; a compile error is REPORTED and the previous good
registry stays live (a broken registry never serves traces).
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..data.packs import PackError
from ..data.project import Project, load_project
from ..data.registry import CompileError, Registry
from ..harness.bench import run_suite
from ..harness.snapshot import diff as snapshot_diff
from ..kernel.engine import solve
from ..kernel.model import PATTERN, Unit, _jsonable
from ..kernel.patterns import match_ask
from ..lint.checks import lint_checks
from ..lint.overlap import lint_overlaps


# module-level (not nested in build_router): `from __future__ import
# annotations` stringifies hints and FastAPI resolves them against module
# globals — a locally-scoped model silently degrades to a query param
class DocBody(BaseModel):
    path: str
    content: str


class TraceBody(BaseModel):
    text: str


class ImpactBody(BaseModel):
    target: str = "suite"  # suite | dev-train | dev-holdout | test
    spend_test_look: bool = False


class ServerState:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.project: Project = load_project(project_root)
        self.baselines: dict[str, dict] = {}  # target -> snapshot
        import threading

        # one bench run at a time — a second tab must not race the first
        # (and two concurrent TEST looks would double-spend the ledger)
        self.run_lock = threading.Lock()

    @property
    def registry(self) -> Registry:
        return self.project.registry

    def reload(self) -> str | None:
        """Re-load from disk; returns an error string (old registry kept)."""
        try:
            self.project = load_project(self.project_root)
            return None
        except (PackError, CompileError, Exception) as exc:  # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"


def _unit_json(unit: Unit) -> dict[str, Any]:
    f = unit.features
    return {
        "uid": unit.uid,
        "surface": unit.surface,
        "senses": f.get("senses", []),
        "lemma": f.get("lemma"),
        "number": f.get("number"),
        "value": f.get("value"),
        "value_kind": f.get("value_kind"),
        "attributes": f.get("attributes", []),
        "unknown": bool(f.get("unknown")),
        "ambiguous": bool(f.get("ambiguous")),
        "pattern_consumed": bool(f.get("pattern_consumed")),
        "obligations": [
            {
                "role": ob.role,
                "need": ob.need,
                "met": ob.met,
                "optional": ob.optional,
                "target": (
                    "<pattern>" if ob.target is PATTERN
                    else ob.target.surface if isinstance(ob.target, Unit)
                    else None
                ),
            }
            for ob in unit.obligations()
        ],
    }


def _fact_json(fact) -> dict[str, Any]:
    fields = {
        k: _jsonable(v)
        for k, v in fact.__dict__.items()
        if k != "provenance" and v is not None
    }
    return {
        "type": type(fact).__name__,
        "fields": fields,
        "source": fact.provenance.source,
        "sentence": fact.provenance.sentence,
    }


def _observation_json(obs) -> dict[str, Any]:
    """One deictic resolution: who asked, from where, over what, and what happened.

    This is the channel that records what the engine THREW AWAY. A decline mutates
    nothing, so it is invisible to the Decision trace — but the declines are where all
    the information is.
    """
    return {
        "source": obs.source,  # shares vocabulary with fact.source AND decision.kind
        "dimension": obs.dimension,
        "metric": obs.metric,
        "round": obs.round,
        "attempts": obs.attempts,
        "origo": {
            "sentence": obs.origo.sentence,
            "span": list(obs.origo.span) if obs.origo.span else None,
            "moment": obs.origo.moment,  # always null — the temporal origo is unbuilt
            "locus": obs.origo.locus,  # always null — the spatial origo is unbuilt
        },
        "filters": list(obs.filters),
        "candidates": [
            {
                "key": c.key,
                "dimension": c.dimension,
                # null whenever the candidate genuinely has no coordinate. Most sites
                # resolve over bare measure/entity strings; the viewer must draw those
                # unanchored rather than invent a position for them.
                "sentence": c.sentence,
                "span": list(c.span) if c.span else None,
                "ref": f"unit:{c.uid}" if c.uid is not None else None,
                "data_uid": (
                    f"{c.sentence}:{c.uid}"
                    if c.uid is not None and c.sentence is not None
                    else None
                ),
                "distance": c.distance,
                "eliminated_by": c.eliminated_by,
            }
            for c in obs.candidates
        ],
        "outcome": obs.outcome,
        "winner": obs.winner,
        "arbitration": obs.arbitration,
        "reason": obs.reason,
    }


def _field_json(result) -> dict[str, Any]:
    """The deictic field itself: what coordinates EXIST, per dimension.

    A pure projection of the Result — no kernel machinery. Each axis reports its own
    degeneracy honestly, because three of the four are degenerate and a viewer that
    hid that would be drawing a field the engine does not have.
    """
    readings = result.premises + ([result.question] if result.question else [])
    quantities = [
        f for f in result.store.facts if type(f).__name__ == "Quantity"
    ]

    # PERSON — the only axis with true positional coordinates. This is also where the
    # capitalisation heuristic dumps any capitalised mid-sentence word that is not
    # timeperiod-exempt, so a month can appear here as a rival person (deixis.md §4).
    person = [
        {
            "key": u.features.get("lemma", u.features.get("fold")),
            "surface": u.surface,
            "uid": u.uid,
            "sentence": r.sentence_index,
            "span": list(u.span),
            "data_uid": f"{r.sentence_index}:{u.uid}",
        }
        for r in readings
        for u in r.units
        if u.sense() == "name"
    ]

    # DISCOURSE — measures and entities are bare strings. Their ONLY coordinate is the
    # sentence their facts came from, so they render as sentence BANDS, never spans.
    def _bands(attr: str) -> list[dict[str, Any]]:
        bands: dict[str, set[int]] = {}
        for q in quantities:
            key = getattr(q, attr, None)
            if key is None:
                continue
            bands.setdefault(str(key), set()).add(q.provenance.sentence)
        return [
            {"key": k, "sentences": sorted(v)} for k, v in sorted(bands.items())
        ]

    # TIME — labels exist; ORDER DOES NOT. Quantity.time is an opaque surface string
    # that is never parsed or normalised, and whose only use anywhere is equality, and
    # only ever to REFUSE to combine facts. `Before` is a registered fact class nothing
    # constructs. So we hand the viewer the labels and an explicit "ordered: false",
    # and it must not draw an axis through them.
    time_labels = sorted({q.time for q in quantities if getattr(q, "time", None)})

    return {
        "narrative": [
            {
                "sentence": r.sentence_index,
                "is_question": result.question is r,
                "text": r.text,
            }
            for r in readings
        ],
        "person": {"candidates": person},
        "discourse": {
            "measures": _bands("measure"),
            "entities": _bands("entity"),
        },
        "time": {
            "labels": time_labels,
            "ordered": False,
            "note": (
                "time is an opaque label: never parsed, never ordered. Its only use is "
                "equality, and only to REFUSE to combine facts. No ask can name a "
                "point in time (docs/deixis.md §1.3, §4)."
            ),
        },
        "place": {
            "loci": [],
            "note": (
                "the spatial origo is unbuilt: prepositions are matched and discarded, "
                "and a container is an entity string indistinguishable from a person "
                "(docs/deixis.md §1.4, phase 4)."
            ),
        },
    }


def pack_documents(project) -> list[dict]:
    """THE editable document set — the one definition the UI listing and the
    read/write allowlist both use.

    Never cached: `ServerState.reload()` can change the pack set, and an
    allowlist that outlived a reload would be a stale authority.
    """
    docs = []
    for pack in project.packs:
        root = pack.root.resolve()
        for path in sorted(pack.root.rglob("*.yaml")):
            # A SYMLINK OUT OF THE PACK IS NOT A PACK DOCUMENT. `rglob` happily
            # lists one, and because the request side resolves too, both would
            # resolve to the same target and membership would pass — so
            # resolve-and-compare alone does NOT contain the tree. A link
            # planted in a pack (deliberately or as a convenience) pointing at
            # `../../data/test.parquet` would otherwise expose TEST golds
            # through an allowlisted name.
            #
            # Membership guards the REQUEST; containment guards the LIST. Both,
            # and each does a job the other cannot.
            if not path.resolve().is_relative_to(root):
                continue
            docs.append({
                "pack": pack.name,
                "path": str(path),
                "name": str(path.relative_to(pack.root)),
            })
    return docs


def resolve_editable_doc(raw: str, project) -> Path | None:
    """The editable path for `raw`, or None if it is out of bounds.

    ⚠ THIS IS A FIREWALL BOUNDARY, not a convenience check, and it is a pure
    function so it can be tested without an HTTP stack — an unrunnable check on
    a boundary is no check.

    The previous version admitted anything under a pack root OR under the
    PROJECT root, and that second disjunct is the whole project directory —
    including `data/` (the DEV/TEST parquet) and `snapshots/`. The designer
    could therefore READ TEST items and OVERWRITE datasets and baselines over
    HTTP, defeating the DEV/TEST firewall `docs/methodology.md` is built around
    and putting silent corruption of a baseline one request away.

    Now it is an ALLOWLIST of exactly the pack YAML documents the UI is offered,
    compared on RESOLVED paths so a symlink out of the tree resolves to
    something not on the list. MEMBERSHIP, not containment: `..` traversal, a
    dataset, a snapshot, `project.yaml`, a non-YAML file inside a pack, and any
    not-yet-existing path all fail it.

    This costs the UI nothing: `app.js` only ever opens a path handed to it by
    `/api/project`, which is this same set.
    """
    path = Path(raw).resolve()
    allowed = {Path(d["path"]).resolve() for d in pack_documents(project)}
    return path if path in allowed else None


def build_router(state: ServerState) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/project")
    def project_info():
        docs = pack_documents(state.project)
        return {
            "name": state.project.doc.name,
            "packs": [p.name for p in state.project.packs],
            "fingerprint": state.registry.fingerprint[:16],
            "docs": docs,
            "has_suite": bool(state.project.doc.suite),
            "has_datasets": bool(state.project.doc.datasets),
            "impact_targets": (
                (["suite"] if state.project.doc.suite else [])
                + (["dev-train", "dev-holdout", "test"]
                   if state.project.doc.datasets else [])
            ),
            "rules": [r.id for r in state.registry.rules],
            "asks": [a.id for a in state.registry.asks],
        }

    def _resolve_doc_path(raw: str) -> Path:
        path = resolve_editable_doc(raw, state.project)
        if path is None:
            raise HTTPException(403, "not an editable pack document")
        return path

    @router.get("/doc")
    def read_doc(path: str):
        p = _resolve_doc_path(path)
        if not p.exists():
            raise HTTPException(404, f"{path} not found")
        return {"path": path, "content": p.read_text()}

    @router.put("/doc")
    def write_doc(body: DocBody):
        p = _resolve_doc_path(body.path)
        previous = p.read_text() if p.exists() else None
        p.write_text(body.content)
        error = state.reload()
        if error is not None:
            # roll back the file so the on-disk state matches the live registry
            if previous is not None:
                p.write_text(previous)
            else:
                p.unlink(missing_ok=True)
            state.reload()
            return {"ok": False, "error": error, "lint": []}
        findings = lint_overlaps(state.registry) + lint_checks(state.registry)
        return {
            "ok": True,
            "error": None,
            "fingerprint": state.registry.fingerprint[:16],
            "lint": [
                {"level": f.level, "code": f.code, "message": f.message}
                for f in findings
                if f.level != "info"
            ],
        }

    @router.post("/trace")
    def trace(body: TraceBody):
        try:
            result = solve(body.text, state.registry)
        except Exception as exc:  # noqa: BLE001 — surface, don't 500
            return {"error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc()[-2000:]}
        readings = result.premises + ([result.question] if result.question else [])
        ask = match_ask(result.question, state.registry) if result.question else None
        return {
            "error": None,
            "answer": {
                "kind": result.answer.kind,
                "value": result.answer.value,
                "reason": result.answer.reason,
            },
            "rounds": result.document.rounds if result.document else 1,
            "ask": (
                {"id": ask[0].id, "query": ask[1]} if ask is not None else None
            ),
            "sentences": [
                {
                    "index": r.sentence_index,
                    "text": r.text,
                    "is_question": result.question is r,
                    "units": [_unit_json(u) for u in r.units],
                    "decisions": [d.to_json() for d in r.decisions],
                }
                for r in readings
            ],
            "facts": [_fact_json(f) for f in result.store.facts],
            "collisions": [
                {"key": _jsonable(list(c.key)), "a": c.a_source, "b": c.b_source,
                 "a_value": _jsonable(c.a_value), "b_value": _jsonable(c.b_value)}
                for c in result.store.collisions
            ],
            "gaps": (
                [g.describe() for g in result.document.gaps]
                if result.document else []
            ),
            "deficiencies": result.deficiencies(),
            "deixis": {
                "observations": (
                    [_observation_json(o) for o in result.log.journal.observations]
                    if result.log.journal is not None else []
                ),
                "field": _field_json(result),
            },
        }

    def _target_items(target: str) -> list[dict] | None:
        if target == "suite":
            return state.project.suite_items() or None
        if state.project.doc.datasets:
            return state.project.dataset_items(target)
        return None

    @router.post("/impact")
    def impact(body: ImpactBody):
        """The firewall, enforced in the tool itself:
        - suite / dev-train: fully inspectable (per-item outcomes returned)
        - dev-holdout: a DELTA GATE — bucket counts + opaque item ids only
        - test: aggregates only, requires spend_test_look, lands in the ledger
        """
        target = body.target
        if target == "test" and not body.spend_test_look:
            return {"error": "TEST is one-look and aggregate-only — tick "
                             "'spend the TEST look' to spend it (ledgered)"}
        try:
            items = _target_items(target)
        except ValueError as exc:
            return {"error": str(exc)}
        if not items:
            return {"error": f"no items for target {target!r}"}

        if not state.run_lock.acquire(blocking=False):
            return {"error": "a bench run is already in progress — wait for it to finish"}
        try:
            report = run_suite(items, state.registry)
        finally:
            state.run_lock.release()
        snapshot = report.to_snapshot()
        inspectable = target in ("suite", "dev-train")

        if target == "test":
            from ..harness.firewall import record_test_look

            record_test_look(
                state.project.snapshots_dir / "test-ledger.jsonl",
                state.registry.fingerprint, report.aggregates(),
            )
            return {
                "error": None, "target": target,
                "aggregates": report.aggregates(),
                "items": None, "diff": None,
                "note": "TEST look SPENT and recorded in snapshots/test-ledger.jsonl "
                        "— a precision drop vs your last look means REVERT",
            }

        d = None
        baseline = state.baselines.get(target)
        if baseline is not None:
            dd = snapshot_diff(baseline, snapshot)
            d = {
                "solved": dd.solved, "broke": dd.broke,
                "decl_to_wrong": dd.decl_to_wrong, "wrong_to_decl": dd.wrong_to_decl,
                "verdict": dd.verdict(),
            }
        return {
            "error": None,
            "target": target,
            "aggregates": report.aggregates(),
            "items": (
                {
                    r.id: {"outcome": r.outcome, "expected": _jsonable(r.expected),
                           "got": _jsonable(r.got), "reason": r.reason[:120]}
                    for r in report.results
                    if r.outcome in ("wrong", "errored") or target == "suite"
                }
                if inspectable else None
            ),
            "diff": d,
            "has_baseline": baseline is not None,
            "note": None if inspectable else
                    "dev-holdout is a delta gate: buckets only, ids are opaque "
                    "— diagnose classes on dev-train, never tune to these items",
        }

    @router.post("/baseline")
    def set_baseline(body: ImpactBody):
        if body.target == "test":
            return {"error": "TEST has no baseline — the ledger is its history"}
        try:
            items = _target_items(body.target)
        except ValueError as exc:
            return {"error": str(exc)}
        if not items:
            return {"error": f"no items for target {body.target!r}"}
        if not state.run_lock.acquire(blocking=False):
            return {"error": "a bench run is already in progress — wait for it to finish"}
        try:
            report = run_suite(items, state.registry)
        finally:
            state.run_lock.release()
        state.baselines[body.target] = report.to_snapshot()
        return {"error": None, "target": body.target, "aggregates": report.aggregates()}

    @router.get("/lint")
    def lint():
        findings = lint_overlaps(state.registry) + lint_checks(state.registry)
        return [
            {"level": f.level, "code": f.code, "message": f.message}
            for f in findings
        ]

    return router
