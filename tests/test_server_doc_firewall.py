"""The designer's /api/doc boundary — a FIREWALL, not a convenience check.

`resolve_editable_doc` used to admit any path under a pack root OR under the
PROJECT root. The second disjunct is the whole project directory, which holds
`data/` (the DEV/TEST parquet) and `snapshots/` — so the designer could READ
TEST items and OVERWRITE datasets and baselines over HTTP. That defeats the
DEV/TEST firewall `docs/methodology.md` is built around, and it put silent
corruption of a baseline one request away.

The boundary is a PURE function precisely so this file can exercise it with no
HTTP stack and no optional dependency. A security check that only runs when
`httpx` happens to be installed is the "gate that never executes" this repo
already has a name for.
"""

from pathlib import Path

import pytest

from rulekit.server.api import pack_documents, resolve_editable_doc


class _Pack:
    def __init__(self, name, root):
        self.name, self.root = name, root


class _Project:
    """The two attributes the boundary reads. Faked rather than compiled: the
    check is about PATHS, and a real registry would only add a way for this
    test to fail for an unrelated reason."""

    def __init__(self, root, packs):
        self.root, self.packs = root, packs


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    pack = root / "packs" / "p"
    pack.mkdir(parents=True)
    (pack / "pack.yaml").write_text("format: rulekit/pack@1\nname: p\n")
    (pack / "lex.yaml").write_text("format: rulekit/lexicon@1\nentries: {}\n")
    (root / "project.yaml").write_text("format: rulekit/project@1\nname: proj\n")
    (root / "data").mkdir()
    (root / "data" / "test.parquet").write_text("TEST GOLDS — must never be readable")
    (root / "snapshots").mkdir()
    (root / "snapshots" / "baseline.json").write_text('{"baseline": true}')
    return _Project(root, [_Pack("p", pack)])


# --- what must still work --------------------------------------------------


def test_a_listed_pack_document_resolves(project):
    doc = project.packs[0].root / "lex.yaml"
    assert resolve_editable_doc(str(doc), project) == doc.resolve()


def test_the_allowlist_is_exactly_what_the_UI_is_offered(project):
    # the listing and the boundary share ONE definition, so the UI can never be
    # handed a path the boundary then refuses
    listed = [d["path"] for d in pack_documents(project)]
    assert listed, "fixture should offer documents"
    for path in listed:
        assert resolve_editable_doc(path, project) is not None


# --- what must be refused --------------------------------------------------


@pytest.mark.parametrize("rel", ["data/test.parquet", "snapshots/baseline.json", "project.yaml"])
def test_project_files_outside_the_packs_are_refused(project, rel):
    # THE regression. Every one of these sits under the project root, which the
    # old containment check admitted for both read and write.
    assert resolve_editable_doc(str(project.root / rel), project) is None


def test_traversal_out_of_the_project_is_refused(project, tmp_path):
    outside = tmp_path / "outside.yaml"
    outside.write_text("secret")
    assert resolve_editable_doc(str(outside), project) is None
    sneaky = project.packs[0].root / ".." / ".." / ".." / "outside.yaml"
    assert resolve_editable_doc(str(sneaky), project) is None


def test_a_symlink_pointing_out_of_the_tree_is_refused(project, tmp_path):
    # membership on RESOLVED paths is what makes this work: the link lives
    # inside a pack, but resolves to something not on the list. A containment
    # check on the unresolved path would have admitted it.
    secret = tmp_path / "secret.yaml"
    secret.write_text("secret")
    link = project.packs[0].root / "link.yaml"
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):  # pragma: no cover
        pytest.skip("symlinks unavailable")
    assert resolve_editable_doc(str(link), project) is None


def test_a_new_file_cannot_be_created(project):
    # the allowlist is EXISTING documents, so a write cannot conjure a path
    assert resolve_editable_doc(str(project.packs[0].root / "new.yaml"), project) is None


def test_a_non_yaml_file_inside_a_pack_is_refused(project):
    sneaky = project.packs[0].root / "notes.txt"
    sneaky.write_text("plain")
    assert resolve_editable_doc(str(sneaky), project) is None


def test_the_allowlist_is_not_cached_across_a_reload(project):
    # `ServerState.reload()` can change the pack set; an allowlist computed once
    # would be a stale authority. Adding a document must make it editable.
    fresh = project.packs[0].root / "added.yaml"
    assert resolve_editable_doc(str(fresh), project) is None
    fresh.write_text("format: rulekit/lexicon@1\nentries: {}\n")
    assert resolve_editable_doc(str(fresh), project) is not None
