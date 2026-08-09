"""One isolated, on-demand Designer runner for a mining candidate.

The central server never imports candidate code. It resolves an exact Git
worktree and commit, starts that worktree's own installed ``rulekit`` process
on loopback, and proxies only an explicit review allowlist. Benchmark, TEST,
impact, baseline, and review-ledger endpoints are deliberately absent here.
"""

from __future__ import annotations

import json
import socket
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class CandidateRunnerError(RuntimeError):
    """The requested candidate cannot be run or safely proxied."""


@dataclass(frozen=True)
class GitWorktree:
    path: Path
    head: str
    branch: str | None


def parse_worktree_porcelain(raw: str) -> tuple[GitWorktree, ...]:
    """Parse ``git worktree list --porcelain`` without shell interpolation."""

    rows = []
    current: dict[str, str] = {}
    for line in [*raw.splitlines(), ""]:
        if not line:
            if current:
                path = current.get("worktree")
                head = current.get("HEAD")
                if path and head:
                    rows.append(
                        GitWorktree(
                            path=Path(path).resolve(),
                            head=head,
                            branch=current.get("branch"),
                        )
                    )
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return tuple(rows)


@dataclass
class ActiveCandidateRunner:
    candidate_id: str
    branch: str
    commit: str
    registry_fingerprint: str
    worktree: Path
    project_root: Path
    port: int
    process: subprocess.Popen[str]
    log: TextIO


@dataclass(frozen=True)
class PromotionRuntime:
    """One clean checkout and its own executables for the fixed M4 gate."""

    root: Path
    commit: str
    python: Path
    rulekit: Path


class CandidateRunnerManager:
    """Own at most one candidate subprocess and its narrow HTTP proxy."""

    def __init__(self, central_project_root: Path):
        self.central_project_root = central_project_root.resolve()
        self._lock = threading.RLock()
        self._active: ActiveCandidateRunner | None = None

    @staticmethod
    def _git(cwd: Path, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(cwd), *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (
            OSError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise CandidateRunnerError(
                f"git {' '.join(args)} failed: {detail}"
            ) from exc
        # Porcelain status uses a leading space as its first status column for
        # an unstaged worktree change (`` M path``).  Stripping the left edge
        # corrupts the first record and makes an allowlisted evidence path look
        # like ``rojects/...``.  Git's other machine-readable outputs do not
        # need leading whitespace removed, so preserve it and trim only the
        # trailing record separator.
        return result.stdout.rstrip()

    def _repo_layout(self) -> tuple[Path, Path]:
        repo = Path(
            self._git(self.central_project_root, "rev-parse", "--show-toplevel")
        ).resolve()
        try:
            relative_project = self.central_project_root.relative_to(repo)
        except ValueError as exc:
            raise CandidateRunnerError(
                "the served project is not inside its Git repository"
            ) from exc
        return repo, relative_project

    def _resolve_worktree(self, manifest: dict[str, Any]) -> tuple[Path, Path, str]:
        repo, relative_project = self._repo_layout()
        raw = self._git(repo, "worktree", "list", "--porcelain")
        branch_ref = f"refs/heads/{manifest['branch']}"
        matches = [
            worktree
            for worktree in parse_worktree_porcelain(raw)
            if worktree.branch == branch_ref
        ]
        if len(matches) != 1:
            raise CandidateRunnerError(
                f"candidate branch {manifest['branch']!r} must have exactly one "
                f"registered worktree; found {len(matches)}"
            )
        worktree = matches[0]
        if worktree.path == repo:
            raise CandidateRunnerError(
                "candidate review refuses to execute the main checkout"
            )
        expected_commit = self._git(
            repo,
            "rev-parse",
            f"{manifest['commit']}^{{commit}}",
        )
        if worktree.head != expected_commit:
            raise CandidateRunnerError(
                f"candidate worktree is at {worktree.head[:12]}, expected "
                f"{expected_commit[:12]}"
            )
        if self._git(worktree.path, "status", "--porcelain"):
            raise CandidateRunnerError(
                "candidate worktree has uncommitted changes; publish a fresh "
                "commit and manifest before review"
            )
        candidate_project = (worktree.path / relative_project).resolve()
        if not candidate_project.is_relative_to(worktree.path):
            raise CandidateRunnerError("candidate project escaped its worktree")
        if not (candidate_project / "project.yaml").is_file():
            raise CandidateRunnerError(
                f"candidate project is missing {relative_project}/project.yaml"
            )
        executable = (worktree.path / ".venv" / "bin" / "rulekit").resolve()
        if not executable.is_relative_to(worktree.path) or not executable.is_file():
            raise CandidateRunnerError(
                "candidate worktree needs its own .venv/bin/rulekit; never share "
                "the main editable environment"
            )
        return worktree.path, candidate_project, str(executable)

    @staticmethod
    def _free_loopback_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _log_tail(log: TextIO, limit: int = 2000) -> str:
        try:
            log.flush()
            log.seek(0)
            return log.read()[-limit:]
        except OSError:
            return ""

    @staticmethod
    def _validate_project_metadata(
        runner: ActiveCandidateRunner,
        project: dict[str, Any],
    ) -> None:
        """Keep every proxied authoring path inside the exact worktree."""

        documents = project.get("docs")
        sources = project.get("sources")
        if not isinstance(documents, list) or not isinstance(sources, dict):
            raise CandidateRunnerError(
                "candidate project metadata lacks the review path allowlist"
            )
        allowed_documents: set[Path] = set()
        for document in documents:
            if not isinstance(document, dict) or not isinstance(
                document.get("path"), str
            ):
                raise CandidateRunnerError(
                    "candidate project returned an invalid document path"
                )
            path = Path(document["path"]).resolve()
            if not path.is_relative_to(runner.worktree):
                raise CandidateRunnerError(
                    "candidate project exposed a document outside its worktree"
                )
            allowed_documents.add(path)
        for source in sources.values():
            if not isinstance(source, dict) or not isinstance(
                source.get("path"), str
            ):
                raise CandidateRunnerError(
                    "candidate project returned an invalid source path"
                )
            if Path(source["path"]).resolve() not in allowed_documents:
                raise CandidateRunnerError(
                    "candidate project exposed a source outside its editable documents"
                )

    @staticmethod
    def _request_at(
        port: int,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        timeout: float = 30,
    ) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{port}{path}",
            data=data,
            method=method,
            headers=(
                {"Content-Type": "application/json"}
                if body is not None
                else {}
            ),
        )
        try:
            # S310 is safe here: the URL is constructed from a numeric port
            # and a private fixed-path allowlist on 127.0.0.1.
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(payload).get("detail", payload)
            except json.JSONDecodeError:
                detail = payload
            raise CandidateRunnerError(
                f"candidate runner rejected {method} {path}: {detail}"
            ) from exc
        except (OSError, URLError) as exc:
            raise CandidateRunnerError(
                f"candidate runner is unavailable for {method} {path}: {exc}"
            ) from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise CandidateRunnerError(
                f"candidate runner returned non-JSON for {method} {path}"
            ) from exc

    def start(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Start or reuse the exact candidate described by ``manifest``."""

        with self._lock:
            active = self._live_active()
            if (
                active is not None
                and active.candidate_id == manifest["candidate_id"]
                and active.commit == manifest["commit"]
                and active.registry_fingerprint == manifest["registry_fingerprint"]
            ):
                return self._status(active, include_project=True)
            worktree, candidate_project, executable = self._resolve_worktree(manifest)
            # Resolve every immutable boundary before replacing a healthy
            # runner. A malformed or dirty second candidate must not evict
            # the candidate a reviewer is already inspecting.
            self._stop_locked()
            port = self._free_loopback_port()
            log = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
            try:
                process = subprocess.Popen(
                    [
                        executable,
                        "--project",
                        str(candidate_project),
                        "serve",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                    ],
                    cwd=worktree,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except OSError as exc:
                log.close()
                raise CandidateRunnerError(
                    f"could not start candidate runner: {exc}"
                ) from exc
            runner = ActiveCandidateRunner(
                candidate_id=manifest["candidate_id"],
                branch=manifest["branch"],
                commit=manifest["commit"],
                registry_fingerprint=manifest["registry_fingerprint"],
                worktree=worktree,
                project_root=candidate_project,
                port=port,
                process=process,
                log=log,
            )
            deadline = time.monotonic() + 30
            project = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    detail = self._log_tail(log)
                    log.close()
                    raise CandidateRunnerError(
                        "candidate runner exited during startup"
                        + (f": {detail}" if detail else "")
                    )
                try:
                    project = self._request_at(port, "GET", "/api/project", timeout=1)
                    break
                except CandidateRunnerError:
                    time.sleep(0.1)
            if project is None:
                self._terminate(runner)
                raise CandidateRunnerError(
                    "candidate runner did not become ready in 30s"
                )
            try:
                self._validate_project_metadata(runner, project)
            except CandidateRunnerError:
                self._terminate(runner)
                raise
            fingerprint = project.get("registry_fingerprint")
            if fingerprint != manifest["registry_fingerprint"]:
                self._terminate(runner)
                raise CandidateRunnerError(
                    "candidate runtime fingerprint does not match its manifest"
                )
            self._active = runner
            return self._status(runner, project=project)

    def _live_active(self) -> ActiveCandidateRunner | None:
        active = self._active
        if active is not None and active.process.poll() is not None:
            active.log.close()
            self._active = None
            return None
        return active

    @staticmethod
    def _terminate(runner: ActiveCandidateRunner) -> None:
        if runner.process.poll() is None:
            runner.process.terminate()
            try:
                runner.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                runner.process.kill()
                runner.process.wait(timeout=5)
        runner.log.close()

    def _stop_locked(self) -> bool:
        active = self._active
        self._active = None
        if active is None:
            return False
        self._terminate(active)
        return True

    def stop(self) -> bool:
        """Stop only the isolated candidate process, never the central server."""

        with self._lock:
            return self._stop_locked()

    close = stop

    def _require(self, candidate_id: str) -> ActiveCandidateRunner:
        active = self._live_active()
        if active is None or active.candidate_id != candidate_id:
            raise CandidateRunnerError(
                f"candidate {candidate_id!r} is not the active isolated runner"
            )
        return active

    def _status(
        self,
        runner: ActiveCandidateRunner,
        *,
        project: dict[str, Any] | None = None,
        include_project: bool = False,
    ) -> dict[str, Any]:
        if include_project and project is None:
            project = self._request_at(runner.port, "GET", "/api/project")
        if project is not None:
            self._validate_project_metadata(runner, project)
        return {
            "active": True,
            "candidate_id": runner.candidate_id,
            "branch": runner.branch,
            "commit": runner.commit,
            "registry_fingerprint": runner.registry_fingerprint,
            "pid": runner.process.pid,
            "project": project,
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            active = self._live_active()
            return (
                {"active": False}
                if active is None
                else self._status(active, include_project=True)
            )

    def project(self, candidate_id: str) -> dict[str, Any]:
        with self._lock:
            runner = self._require(candidate_id)
            project = self._request_at(runner.port, "GET", "/api/project")
            self._validate_project_metadata(runner, project)
            return project

    def trace(self, candidate_id: str, body: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            runner = self._require(candidate_id)
            return self._request_at(runner.port, "POST", "/api/trace", body)

    def read_doc(self, candidate_id: str, path: str) -> dict[str, Any]:
        with self._lock:
            runner = self._require(candidate_id)
            return self._request_at(
                runner.port,
                "GET",
                f"/api/doc?path={quote(path, safe='')}",
            )

    def write_doc(
        self,
        candidate_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            runner = self._require(candidate_id)
            return self._request_at(runner.port, "PUT", "/api/doc", body)

    def retest(self, candidate_id: str, body: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            runner = self._require(candidate_id)
            return self._request_at(
                runner.port,
                "POST",
                "/api/generation/retest",
                body,
            )

    def approval_blocker(
        self,
        candidate_id: str,
        commit: str,
        registry_fingerprint: str,
    ) -> str | None:
        """Why an active reviewed runtime cannot approve its manifest."""

        with self._lock:
            active = self._live_active()
            if active is None or active.candidate_id != candidate_id:
                return None
            if active.commit != commit:
                return "active candidate commit differs from the review manifest"
            if self._git(active.worktree, "status", "--porcelain"):
                return (
                    "candidate worktree has uncommitted review edits; commit, gate, "
                    "and publish a new manifest before approval"
                )
            expected_commit = self._git(
                active.worktree,
                "rev-parse",
                f"{commit}^{{commit}}",
            )
            current_commit = self._git(active.worktree, "rev-parse", "HEAD")
            if current_commit != expected_commit:
                return (
                    "candidate worktree commit differs from the review manifest; "
                    "publish a new manifest before approval"
                )
            project = self._request_at(active.port, "GET", "/api/project")
            self._validate_project_metadata(active, project)
            if project.get("registry_fingerprint") != registry_fingerprint:
                return (
                    "candidate runtime fingerprint differs from the review manifest; "
                    "publish a new manifest before approval"
                )
            return None

    @staticmethod
    def _promotion_runtime(root: Path, commit: str) -> PromotionRuntime:
        environment = (root / ".venv").resolve()
        python = root / ".venv" / "bin" / "python"
        rulekit = root / ".venv" / "bin" / "rulekit"
        if (
            not environment.is_relative_to(root)
            or not python.is_file()
            or not rulekit.resolve().is_relative_to(root)
            or not rulekit.is_file()
        ):
            raise CandidateRunnerError(
                "promotion gate requires each checkout's own .venv executables"
            )
        return PromotionRuntime(
            root=root,
            commit=commit,
            python=python,
            rulekit=rulekit,
        )

    def _central_code_changes(self, repo: Path) -> list[str]:
        """Ignore only the served project's non-runtime evidence ledgers."""

        status = self._git(repo, "status", "--porcelain")
        if not status:
            return []
        _, relative_project = self._repo_layout()
        evidence_root = (relative_project / "generation").as_posix().rstrip("/") + "/"
        changed = []
        for line in status.splitlines():
            raw = line[3:] if len(line) >= 4 else line
            # A rename has both an old and a new path. Neither is legitimate
            # campaign evidence unless both stay below the fixed evidence root.
            paths = [item.strip(' "') for item in raw.split(" -> ")]
            if not paths or any(not path.startswith(evidence_root) for path in paths):
                changed.append(raw)
        return changed

    def promotion_runtimes(
        self,
        candidate_id: str,
    ) -> tuple[PromotionRuntime, PromotionRuntime]:
        """Return clean central baseline and exact active candidate contexts."""

        with self._lock:
            active = self._require(candidate_id)
            baseline_root, _ = self._repo_layout()
            if self._central_code_changes(baseline_root):
                raise CandidateRunnerError(
                    "central baseline checkout has uncommitted code changes"
                )
            if self._git(active.worktree, "status", "--porcelain"):
                raise CandidateRunnerError(
                    "candidate worktree has uncommitted changes"
                )
            baseline_commit = self._git(baseline_root, "rev-parse", "HEAD")
            candidate_commit = self._git(active.worktree, "rev-parse", "HEAD")
            expected_commit = self._git(
                active.worktree,
                "rev-parse",
                f"{active.commit}^{{commit}}",
            )
            if candidate_commit != expected_commit:
                raise CandidateRunnerError(
                    "candidate worktree commit differs from its active manifest"
                )
            return (
                self._promotion_runtime(baseline_root, baseline_commit),
                self._promotion_runtime(active.worktree, active.commit),
            )

    @contextmanager
    def promotion_session(
        self,
        candidate_id: str,
    ):
        """Freeze proxy mutations and revalidate both exact checkouts."""

        with self._lock:
            before = self.promotion_runtimes(candidate_id)
            yield before
            after = self.promotion_runtimes(candidate_id)
            if before != after:
                raise CandidateRunnerError(
                    "promotion checkout identity changed while the gate was running"
                )
