"""Auto-marks every test by its directory (unit/integration/e2e/architecture)
so ``pytest -m unit`` etc. (used by the Makefile targets) works without each
test file remembering to add ``pytestmark`` itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_MARKER_BY_DIR = {
    "unit": "unit",
    "integration": "integration",
    "e2e": "e2e",
    "architecture": "architecture",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        relative = Path(item.fspath).relative_to(Path(__file__).parent)
        top_level = relative.parts[0]
        marker = _MARKER_BY_DIR.get(top_level)
        if marker:
            item.add_marker(getattr(pytest.mark, marker))
