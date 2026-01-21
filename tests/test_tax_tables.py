from pathlib import Path

import pytest

from payroll.tax_tables import TaxTableRepository


def build_repo() -> TaxTableRepository:
    return TaxTableRepository(Path(__file__).resolve().parent.parent / "data" / "tax_tables")


def test_available_versions_lists_known_tables():
    repo = build_repo()

    versions = repo.available_versions()

    assert "2024_v1" in versions
    assert versions == sorted(versions)


def test_allowance_for_unknown_state_defaults_zero():
    repo = build_repo()
    table = repo.load("2024_v1")

    assert table.allowance_for("state", "XX") == 0.0


def test_brackets_for_unknown_state_raises():
    repo = build_repo()
    table = repo.load("2024_v1")

    with pytest.raises(KeyError):
        table.brackets_for("state", "single", state="XX")


def test_load_missing_table_version_raises(tmp_path):
    repo = TaxTableRepository(tmp_path)

    with pytest.raises(FileNotFoundError):
        repo.load("missing")
