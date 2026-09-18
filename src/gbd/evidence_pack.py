"""Evidence Pack Layer — one regulator-legible record per decision (EP-1..6).

Schema — exactly these 14 fields:
  pack_id, submission_ref, decision_timestamp, policy_version, decision_outcome, confidence_score,
  confidence_band, triggered_rules, input_categories, regulatory_mapping,
  plain_english_explanation, oversight_pathway, retention_reference, integrity_hash

decision_outcome carries the bounded workflow step named in the approved project
outline (ALLOW / REVIEW / QUARANTINE / REJECT). It sits next to, not instead of,
the confidence band: the outcome is what happens, the band is how sure the system
is about the assessment underneath it.

The DSA Art 17 statement-of-reasons block lives inside regulatory_mapping so the
top-level schema stays exact.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from gbd.engine import EvaluationResult
from gbd.explainer import plain_english
from gbd.policy import PolicyBundle

PACK_FIELDS = [
    "pack_id", "submission_ref", "decision_timestamp", "policy_version", "decision_outcome",
    "confidence_score", "confidence_band", "triggered_rules", "input_categories",
    "regulatory_mapping", "plain_english_explanation", "oversight_pathway",
    "retention_reference", "integrity_hash",
]

_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # RFC 4122 namespace


def _canonical(pack: dict[str, Any]) -> bytes:
    body = {k: v for k, v in pack.items() if k != "integrity_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def compute_hash(pack: dict[str, Any]) -> str:
    """SHA-256 over canonical pack contents, excluding the hash field itself (EP-3)."""
    return hashlib.sha256(_canonical(pack)).hexdigest()


def build_pack(
    result: EvaluationResult,
    bundle: PolicyBundle,
    timestamp: str | None = None,
    pack_id: str | None = None,
) -> dict[str, Any]:
    """Assemble the Evidence Pack. Deterministic when timestamp is supplied."""
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    regulatory = dict(result.regulatory_mapping)
    regulatory["DSA Art 17 — statement of reasons"] = result.statement_of_reasons
    regulatory.setdefault("GDPR Art 22 — automated decision-making", {
        "decision_outcome": result.decision_outcome,
        "adverse": result.decision_outcome in bundle.adverse_outcomes,
        "solely_automated": result.solely_automated,
        "intervention_point": result.intervention_point,
        "status": "evidenced",
    })
    pack: dict[str, Any] = {
        "pack_id": pack_id or str(uuid.uuid5(_NAMESPACE, ts + bundle.policy_version
            + result.submission_ref
            + json.dumps([t["rule_id"] for t in result.triggered_rules])
            + str(result.confidence_score))),
        "submission_ref": result.submission_ref,
        "decision_timestamp": ts,
        "policy_version": bundle.policy_version,
        "decision_outcome": result.decision_outcome,
        "confidence_score": result.confidence_score,
        "confidence_band": result.confidence_band,
        "triggered_rules": result.triggered_rules,
        "input_categories": result.input_categories,
        "regulatory_mapping": regulatory,
        "plain_english_explanation": plain_english(result, bundle),
        "oversight_pathway": bundle.oversight_pathway,
        "retention_reference": bundle.retention_reference,
    }
    pack["integrity_hash"] = compute_hash(pack)
    assert list(pack.keys()) == PACK_FIELDS
    return pack


def verify_integrity(pack: dict[str, Any]) -> bool:
    """Recompute the hash and compare (demo step 4)."""
    return pack.get("integrity_hash") == compute_hash(pack)


def to_json(pack: dict[str, Any]) -> str:
    """EP-6 — export as JSON."""
    return json.dumps(pack, indent=2)
