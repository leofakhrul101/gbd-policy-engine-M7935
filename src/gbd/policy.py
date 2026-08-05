"""Policy Translation Layer — load and validate versioned policy bundles (POL-1..4, GOV-1)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validate as _js_validate

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "policies" / "policy_bundle.schema.json"


@dataclass(frozen=True)
class PolicyBundle:
    policy_version: str
    effective_date: str
    description: str
    oversight_pathway: str
    retention_reference: str
    bands: dict[str, float]
    outcomes: dict[str, float]
    adverse_outcomes: list[str]
    gated_outcomes: list[str]
    rules: list[dict[str, Any]]
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def rule(self, rule_id: str) -> dict[str, Any]:
        for r in self.rules:
            if r["rule_id"] == rule_id:
                return r
        raise KeyError(rule_id)


def validate_bundle(data: dict[str, Any], schema_path: Path | None = None) -> None:
    """Raise jsonschema.ValidationError if the bundle is malformed (POL-3)."""
    schema = json.loads((schema_path or _SCHEMA_PATH).read_text())
    _js_validate(instance=data, schema=schema)


def bundle_from_dict(data: dict[str, Any]) -> PolicyBundle:
    validate_bundle(data)
    return PolicyBundle(
        policy_version=data["policy_version"],
        effective_date=str(data["effective_date"]),
        description=data["description"],
        oversight_pathway=data["oversight_pathway"],
        retention_reference=data["retention_reference"],
        bands=dict(data["bands"]),
        outcomes=dict(data["outcomes"]),
        adverse_outcomes=list(data["adverse_outcomes"]),
        gated_outcomes=list(data["gated_outcomes"]),
        rules=list(data["rules"]),
        raw=data,
    )


def load_bundle(path: str | Path) -> PolicyBundle:
    data = yaml.safe_load(Path(path).read_text())
    # YAML parses effective_date as datetime.date; normalise for schema format check
    data["effective_date"] = str(data["effective_date"])
    return bundle_from_dict(data)


def bundle_to_yaml(bundle: PolicyBundle) -> str:
    """Serialise the exact bundle for provenance storage (GOV-4)."""
    return yaml.safe_dump(bundle.raw, sort_keys=False)
