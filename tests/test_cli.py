import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from payroll import cli
from payroll.models import Employee
from payroll.storage import DataStore


def test_list_employees_sorts_and_formats(capsys, tmp_path, monkeypatch):
    data_path = tmp_path / "store.json"
    store = DataStore(data_path)
    store.add_employee(Employee(id="b", name="Zelda Ops", department="Ops", pto_balance_hours=4))
    store.add_employee(
        Employee(id="a", name="anna dev", department="Engineering", pto_balance_hours=12)
    )
    store.save()

    monkeypatch.setattr(cli, "DEFAULT_DATA_PATH", data_path)

    cli.main(["list-employees"])

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured[0].startswith("a anna dev")
    assert "dept: Engineering" in captured[0]
    assert "PTO balance: 12" in captured[0]
    assert captured[1].startswith("b Zelda Ops")
