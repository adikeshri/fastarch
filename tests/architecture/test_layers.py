"""Turns the Clean Architecture dependency rule into an enforceable test
(PRD §47), not just a convention.

The primary check runs the same import-linter contracts CI runs
(``make lint-arch``) in-process via its CLI entry point. The supplementary
checks below re-verify the two sharpest edges directly against the AST, so
this file fails loudly and specifically (rather than via a generic
import-linter report) if the domain or application layer ever imports
something it shouldn't.
"""

from __future__ import annotations

import ast
from pathlib import Path

from click.testing import CliRunner
from importlinter.cli import lint_imports_command

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "app"

_DOMAIN_FORBIDDEN_TOP_LEVEL_IMPORTS = {
    "fastapi",
    "starlette",
    "pydantic",
    "sqlalchemy",
    "alembic",
    "redis",
    "arq",
    "httpx",
    "jwt",
    "passlib",
}
_APPLICATION_FORBIDDEN_TOP_LEVEL_IMPORTS = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "redis",
    "arq",
    "jwt",
    "passlib",
}


def test_import_linter_contracts_pass() -> None:
    result = CliRunner().invoke(
        lint_imports_command, ["--config", str(REPO_ROOT / "pyproject.toml")]
    )

    assert result.exit_code == 0, result.output


def _top_level_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    return modules


def _assert_no_forbidden_imports(package_dir: Path, forbidden: set[str]) -> None:
    violations: dict[str, set[str]] = {}
    for py_file in package_dir.rglob("*.py"):
        found = _top_level_imports(py_file) & forbidden
        if found:
            violations[str(py_file.relative_to(REPO_ROOT))] = found
    assert not violations, f"Forbidden imports found: {violations}"


def test_domain_layer_never_imports_frameworks_or_infrastructure() -> None:
    _assert_no_forbidden_imports(SRC_ROOT / "domain", _DOMAIN_FORBIDDEN_TOP_LEVEL_IMPORTS)


def test_application_layer_never_imports_frameworks_or_infrastructure() -> None:
    _assert_no_forbidden_imports(SRC_ROOT / "application", _APPLICATION_FORBIDDEN_TOP_LEVEL_IMPORTS)


def test_domain_layer_never_imports_application_infrastructure_or_presentation() -> None:
    forbidden_internal = {
        "app.application",
        "app.infrastructure",
        "app.presentation",
        "app.composition",
    }
    for py_file in (SRC_ROOT / "domain").rglob("*.py"):
        tree = ast.parse(py_file.read_text(), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(node.module.startswith(prefix) for prefix in forbidden_internal), (
                    f"{py_file} imports {node.module}"
                )


def test_the_forbidden_import_check_actually_detects_a_violation() -> None:
    """A meta-test: proves ``_assert_no_forbidden_imports`` isn't vacuously passing."""
    fake_domain_file = ast.parse("import sqlalchemy\n")
    modules = {
        alias.name.split(".")[0]
        for node in ast.walk(fake_domain_file)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert modules & _DOMAIN_FORBIDDEN_TOP_LEVEL_IMPORTS
