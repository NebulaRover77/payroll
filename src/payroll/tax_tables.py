from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class TaxBracket:
    up_to: float
    rate: float


class TaxTable:
    def __init__(self, version: str, federal: dict, states: dict, employer_taxes: dict):
        self.version = version
        self.federal = federal
        self.states = states
        self.employer_taxes = employer_taxes

    def brackets_for(self, level: str, filing_status: str, state: Optional[str] = None) -> List[TaxBracket]:
        if level == "federal":
            tables = self.federal
        else:
            if state is None or state not in self.states:
                raise KeyError(f"State {state} not configured in tax table {self.version}")
            tables = self.states[state]
        bracket_rows = tables.get(filing_status) or tables.get("single")
        return [TaxBracket(up_to=row["up_to"], rate=row["rate"]) for row in bracket_rows]

    def allowance_for(self, level: str, state: Optional[str] = None) -> float:
        if level == "federal":
            return float(self.federal.get("allowance", 0))
        if state is None or state not in self.states:
            return 0.0
        return float(self.states[state].get("allowance", 0))


class TaxTableRepository:
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def available_versions(self) -> List[str]:
        return sorted([p.stem for p in self.base_path.glob("*.json")])

    def load(self, version: str) -> TaxTable:
        file_path = self.base_path / f"{version}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Tax table version {version} not found at {file_path}")
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return TaxTable(
            version=data["version"],
            federal=data["federal"],
            states=data.get("states", {}),
            employer_taxes=data.get("employer_taxes", {}),
        )
