"""The M2 candidate runner is an exact-worktree, narrow-proxy boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from rulekit.server.api import ServerState, build_router
from rulekit.server.candidate_runner import (
    CandidateRunnerError,
    CandidateRunnerManager,
    parse_worktree_porcelain,
)


COMMIT = "a" * 40
FINGERPRINT = "registry-abcdef0123456789"


def _manifest() -> dict:
    return {
        "candidate_id": "holder-question",
        "branch": "mining/cand-holder-question",
        "commit": COMMIT[:12],
        "registry_fingerprint": FINGERPRINT,
    }


def _layout(tmp_path: Path) -> tuple[Path, Path, Path, CandidateRunnerManager]:
    repo = tmp_path / "repo"
    worktree = tmp_path / "candidate"
    central_project = repo / "projects" / "gsm8k"
    candidate_project = worktree / "projects" / "gsm8k"
    central_project.mkdir(parents=True)
    candidate_project.mkdir(parents=True)
    (candidate_project / "project.yaml").write_text("name: candidate\n")
    executable = worktree / ".venv" / "bin" / "rulekit"
    executable.parent.mkdir(parents=True)
    executable.write_text("candidate executable\n")
    return repo, worktree, candidate_project, CandidateRunnerManager(central_project)


def _fake_git(repo: Path, worktree: Path, *, dirty: bool = False):
    porcelain = (
        f"worktree {repo}\n"
        f"HEAD {'b' * 40}\n"
        "branch refs/heads/main\n\n"
        f"worktree {worktree}\n"
        f"HEAD {COMMIT}\n"
        "branch refs/heads/mining/cand-holder-question\n"
    )

    def run(cwd: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo)
        if args == ("worktree", "list", "--porcelain"):
            return porcelain
        if args == ("rev-parse", f"{COMMIT[:12]}^{{commit}}"):
            return COMMIT
        if args == ("status", "--porcelain") and cwd.resolve() == worktree.resolve():
            return " M packs/arithmetic/rules.yaml" if dirty else ""
        raise AssertionError((cwd, args))

    return run


def test_worktree_porcelain_preserves_exact_branch_and_detached_state() -> None:
    worktrees = parse_worktree_porcelain(
        "/repo\n"  # ignored because the required key is deliberately absent
        "\n"
        "worktree /repo\n"
        f"HEAD {COMMIT}\n"
        "branch refs/heads/main\n"
        "\n"
        "worktree /tmp/candidate\n"
        f"HEAD {'b' * 40}\n"
        "detached\n"
    )

    assert len(worktrees) == 2
    assert worktrees[0].branch == "refs/heads/main"
    assert worktrees[1].branch is None
    assert worktrees[1].path == Path("/tmp/candidate").resolve()


def test_candidate_resolution_requires_clean_exact_registered_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, worktree, candidate_project, manager = _layout(tmp_path)
    monkeypatch.setattr(manager, "_git", _fake_git(repo, worktree))

    resolved_worktree, resolved_project, executable = manager._resolve_worktree(
        _manifest()
    )

    assert resolved_worktree == worktree.resolve()
    assert resolved_project == candidate_project.resolve()
    assert executable == str((worktree / ".venv" / "bin" / "rulekit").resolve())


def test_candidate_resolution_rejects_dirty_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, worktree, _, manager = _layout(tmp_path)
    monkeypatch.setattr(manager, "_git", _fake_git(repo, worktree, dirty=True))

    with pytest.raises(CandidateRunnerError, match="uncommitted changes"):
        manager._resolve_worktree(_manifest())


def test_candidate_resolution_never_uses_main_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _, manager = _layout(tmp_path)
    porcelain = (
        f"worktree {repo}\n"
        f"HEAD {COMMIT}\n"
        "branch refs/heads/mining/cand-holder-question\n"
    )

    def fake_git(cwd: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo)
        if args == ("worktree", "list", "--porcelain"):
            return porcelain
        raise AssertionError((cwd, args))

    monkeypatch.setattr(manager, "_git", fake_git)
    with pytest.raises(CandidateRunnerError, match="main checkout"):
        manager._resolve_worktree(_manifest())


def test_candidate_resolution_requires_its_own_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, worktree, _, manager = _layout(tmp_path)
    (worktree / ".venv" / "bin" / "rulekit").unlink()
    monkeypatch.setattr(manager, "_git", _fake_git(repo, worktree))

    with pytest.raises(CandidateRunnerError, match="own .venv/bin/rulekit"):
        manager._resolve_worktree(_manifest())


def test_git_preserves_the_leading_porcelain_status_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Result:
        stdout = " M projects/curated/generation/exploration.jsonl\n"

    monkeypatch.setattr(
        "rulekit.server.candidate_runner.subprocess.run",
        lambda *args, **kwargs: Result(),
    )

    assert CandidateRunnerManager._git(tmp_path, "status", "--porcelain") == (
        " M projects/curated/generation/exploration.jsonl"
    )


def test_promotion_runtime_accepts_a_normal_venv_python_symlink(
    tmp_path: Path,
) -> None:
    root = tmp_path / "candidate"
    bin_dir = root / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").symlink_to(Path("/bin/sh"))
    (bin_dir / "rulekit").write_text("candidate executable\n")

    runtime = CandidateRunnerManager._promotion_runtime(root.resolve(), COMMIT[:12])

    assert runtime.python == root.resolve() / ".venv" / "bin" / "python"
    assert runtime.commit == COMMIT[:12]


def test_central_cleanliness_ignores_only_fixed_generation_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, worktree, _, manager = _layout(tmp_path)

    def evidence_git(cwd: Path, *args: str) -> str:
        if args == ("status", "--porcelain"):
            return " M projects/gsm8k/generation/campaign/gates.jsonl"
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo)
        raise AssertionError((cwd, args))

    monkeypatch.setattr(manager, "_git", evidence_git)
    assert manager._central_code_changes(repo) == []

    monkeypatch.setattr(
        manager,
        "_git",
        lambda cwd, *args: (
            str(repo)
            if args == ("rev-parse", "--show-toplevel")
            else " M packs/arithmetic/rules.core.yaml"
        ),
    )
    assert manager._central_code_changes(repo) == [
        "packs/arithmetic/rules.core.yaml"
    ]


class _FakeProcess:
    def __init__(self) -> None:
        self.pid = 8421
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout: int | None = None) -> int:
        del timeout
        return int(self.returncode or 0)

    def kill(self) -> None:
        self.returncode = -9


def test_runner_owns_one_child_and_exposes_only_review_operations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, worktree, candidate_project, manager = _layout(tmp_path)
    executable = worktree / ".venv" / "bin" / "rulekit"
    process = _FakeProcess()
    calls = []
    monkeypatch.setattr(
        manager,
        "_resolve_worktree",
        lambda manifest: (worktree, candidate_project, str(executable)),
    )
    monkeypatch.setattr(manager, "_free_loopback_port", lambda: 18421)
    monkeypatch.setattr(
        "rulekit.server.candidate_runner.subprocess.Popen",
        lambda *args, **kwargs: process,
    )

    project = {
        "name": "candidate",
        "fingerprint": FINGERPRINT[:16],
        "registry_fingerprint": FINGERPRINT,
        "docs": [],
        "sources": {},
    }

    def request(port, method, path, body=None, **kwargs):
        calls.append((port, method, path, body, kwargs))
        if path == "/api/project":
            return project
        return {"ok": True, "path": path, "body": body}

    monkeypatch.setattr(manager, "_request_at", request)

    status = manager.start(_manifest())
    assert status["active"] is True
    assert status["project"] == project
    assert manager.trace("holder-question", {"text": "A sentence."})["ok"]
    assert manager.read_doc("holder-question", "/candidate/rules.yaml")["ok"]
    assert manager.write_doc(
        "holder-question",
        {"path": "/candidate/rules.yaml", "content": "rules: []"},
    )["ok"]
    assert manager.retest("holder-question", {"rule_id": "x"})["ok"]
    assert manager.stop() is True
    assert process.terminated is True
    assert manager.status() == {"active": False}

    proxied_paths = {call[2].split("?", 1)[0] for call in calls}
    assert proxied_paths == {
        "/api/project",
        "/api/trace",
        "/api/doc",
        "/api/generation/retest",
    }
    assert not hasattr(manager, "proxy")


def test_invalid_replacement_does_not_evict_active_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, worktree, candidate_project, manager = _layout(tmp_path)
    executable = worktree / ".venv" / "bin" / "rulekit"
    process = _FakeProcess()
    monkeypatch.setattr(
        manager,
        "_resolve_worktree",
        lambda manifest: (worktree, candidate_project, str(executable)),
    )
    monkeypatch.setattr(manager, "_free_loopback_port", lambda: 18421)
    monkeypatch.setattr(
        "rulekit.server.candidate_runner.subprocess.Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        manager,
        "_request_at",
        lambda *args, **kwargs: {
            "name": "candidate",
            "fingerprint": FINGERPRINT[:16],
            "registry_fingerprint": FINGERPRINT,
            "docs": [],
            "sources": {},
        },
    )
    manager.start(_manifest())

    def reject_replacement(manifest):
        if manifest["candidate_id"] == "other-candidate":
            raise CandidateRunnerError("replacement is dirty")
        return worktree, candidate_project, str(executable)

    monkeypatch.setattr(manager, "_resolve_worktree", reject_replacement)
    replacement = {
        **_manifest(),
        "candidate_id": "other-candidate",
        "branch": "mining/cand-other-candidate",
    }
    with pytest.raises(CandidateRunnerError, match="replacement is dirty"):
        manager.start(replacement)

    assert manager.status()["candidate_id"] == "holder-question"
    assert process.terminated is False
    manager.stop()


def test_runner_rejects_project_documents_outside_candidate_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, worktree, candidate_project, manager = _layout(tmp_path)
    executable = worktree / ".venv" / "bin" / "rulekit"
    process = _FakeProcess()
    monkeypatch.setattr(
        manager,
        "_resolve_worktree",
        lambda manifest: (worktree, candidate_project, str(executable)),
    )
    monkeypatch.setattr(manager, "_free_loopback_port", lambda: 18421)
    monkeypatch.setattr(
        "rulekit.server.candidate_runner.subprocess.Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        manager,
        "_request_at",
        lambda *args, **kwargs: {
            "name": "candidate",
            "fingerprint": FINGERPRINT[:16],
            "registry_fingerprint": FINGERPRINT,
            "docs": [{"path": str(tmp_path / "central" / "rules.yaml")}],
            "sources": {},
        },
    )

    with pytest.raises(CandidateRunnerError, match="outside its worktree"):
        manager.start(_manifest())

    assert process.terminated is True
    assert manager.status() == {"active": False}


def test_approval_is_blocked_after_live_candidate_edit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, worktree, candidate_project, manager = _layout(tmp_path)
    executable = worktree / ".venv" / "bin" / "rulekit"
    process = _FakeProcess()
    monkeypatch.setattr(
        manager,
        "_resolve_worktree",
        lambda manifest: (worktree, candidate_project, str(executable)),
    )
    monkeypatch.setattr(manager, "_free_loopback_port", lambda: 18421)
    monkeypatch.setattr(
        "rulekit.server.candidate_runner.subprocess.Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        manager,
        "_request_at",
        lambda *args, **kwargs: {
            "name": "candidate",
            "fingerprint": FINGERPRINT[:16],
            "registry_fingerprint": FINGERPRINT,
            "docs": [],
            "sources": {},
        },
    )
    manager.start(_manifest())
    monkeypatch.setattr(manager, "_git", lambda cwd, *args: " M rules.yaml")

    blocker = manager.approval_blocker(
        "holder-question",
        COMMIT[:12],
        FINGERPRINT,
    )

    assert blocker is not None
    assert "uncommitted review edits" in blocker
    manager.stop()


def test_approval_is_blocked_after_worktree_advances_to_another_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, worktree, candidate_project, manager = _layout(tmp_path)
    executable = worktree / ".venv" / "bin" / "rulekit"
    process = _FakeProcess()
    monkeypatch.setattr(
        manager,
        "_resolve_worktree",
        lambda manifest: (worktree, candidate_project, str(executable)),
    )
    monkeypatch.setattr(manager, "_free_loopback_port", lambda: 18421)
    monkeypatch.setattr(
        "rulekit.server.candidate_runner.subprocess.Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        manager,
        "_request_at",
        lambda *args, **kwargs: {
            "name": "candidate",
            "fingerprint": FINGERPRINT[:16],
            "registry_fingerprint": FINGERPRINT,
            "docs": [],
            "sources": {},
        },
    )
    manager.start(_manifest())

    def advanced_git(cwd: Path, *args: str) -> str:
        del cwd
        if args == ("status", "--porcelain"):
            return ""
        if args == ("rev-parse", f"{COMMIT[:12]}^{{commit}}"):
            return COMMIT
        if args == ("rev-parse", "HEAD"):
            return "c" * 40
        raise AssertionError(args)

    monkeypatch.setattr(manager, "_git", advanced_git)

    blocker = manager.approval_blocker(
        "holder-question",
        COMMIT[:12],
        FINGERPRINT,
    )

    assert blocker is not None
    assert "commit differs" in blocker
    manager.stop()


def test_runner_routes_exclude_benchmarks_and_review_ledger() -> None:
    router = build_router(ServerState(Path("projects/curated")))
    paths = {route.path for route in router.routes}

    assert {
        "/api/campaign/runner",
        "/api/campaign/runner/{candidate_id}/start",
        "/api/campaign/runner/stop",
        "/api/campaign/runner/{candidate_id}/project",
        "/api/campaign/runner/{candidate_id}/trace",
        "/api/campaign/runner/{candidate_id}/doc",
        "/api/campaign/runner/{candidate_id}/retest",
    } <= paths
    assert not any("benchmark" in path for path in paths if "/campaign/runner" in path)
    assert not any("review" in path for path in paths if "/campaign/runner" in path)


def test_designer_wires_isolated_read_edit_retest_and_stop() -> None:
    static = Path("src/rulekit/server/static")
    js = (static / "app.js").read_text()
    css = (static / "style.css").read_text()

    assert "Start isolated review" in js
    assert "Stop isolated runner" in js
    assert 'campaignRunnerPath("/trace")' in js
    assert 'campaignRunnerPath("/doc")' in js
    assert '"/api/generation/retest"' in js
    assert "campaign-runner-controls" in css
    assert "campaign-retest-result" in css
