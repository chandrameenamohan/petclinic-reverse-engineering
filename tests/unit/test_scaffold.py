"""Verify the per-service directory scaffold is in place."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SERVICE_DIRS = [
    "customers_service",
    "vets_service",
    "visits_service",
    "api_gateway",
    "genai_service",
    "config_server",
    "discovery_server",
    "admin_server",
]

EXTRA_DIRS = [
    "shared",
    "config",
    "docker",
    "tests/unit",
    "tests/integration",
    "tests/e2e",
]


def test_service_directories_exist() -> None:
    for name in SERVICE_DIRS:
        d = PROJECT_ROOT / name
        assert d.is_dir(), f"Missing service directory: {name}/"


def test_service_init_files_exist() -> None:
    for name in SERVICE_DIRS:
        init = PROJECT_ROOT / name / "__init__.py"
        assert init.is_file(), f"Missing {name}/__init__.py"


def test_shared_has_init() -> None:
    assert (PROJECT_ROOT / "shared" / "__init__.py").is_file()


def test_extra_directories_exist() -> None:
    for name in EXTRA_DIRS:
        d = PROJECT_ROOT / name
        assert d.is_dir(), f"Missing directory: {name}/"


def test_test_subdirs_have_init() -> None:
    for sub in ["unit", "integration", "e2e"]:
        init = PROJECT_ROOT / "tests" / sub / "__init__.py"
        assert init.is_file(), f"Missing tests/{sub}/__init__.py"
