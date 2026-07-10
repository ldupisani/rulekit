from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import Registry, compile_registry

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def registry() -> Registry:
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic"])
    )
