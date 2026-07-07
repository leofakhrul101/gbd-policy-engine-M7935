"""Decision Logic Layer — pure, deterministic confidence-scoring evaluator (DEC-1..5).

Semantics (documented in README §3 and the policy bundle header):
  R                 = sum of confidence_weight over triggered risk rules, clamped to 1.0
  risk_direction    = "concerns_identified" if R >= 0.5 else "no_concerns_identified"
  confidence_score  = |1 - 2R|   — confidence in the assessment, not a verdict
  confidence_band   = from policy thresholds (High / Medium / Low / Human-Review-Required)

There is no Allow/Reject anywhere. A confident concern is still evidence for a
human or downstream deployer decision, never an adjudication (the boundary thesis).

Pure function: no I/O, no clock, no randomness, no database (DEC-5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gbd.policy import PolicyBundle

HUMAN_REVIEW = "Human-Review-Required"
BAND_ORDER = [("high", "High"), ("medium", "Medium"), ("low", "Low")]


def _get_field(record: dict[str, Any], dotted: str) -> Any:
    """Resolve 'behavioural_signals.account_age_days' against a record dict.

    Derived virtual field: ai_generated_undisclosed = ai_generated and not ai_disclosed.
    """
    if dotted == "ai_generated_undisclosed":
        return bool(record.get("ai_generated")) and not bool(record.get("ai_disclosed"))
    cur: Any = record
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _condition_met(cond: dict[str, Any], subject: dict[str, Any]) -> bool:
    ctype = cond["type"]
    if ctype == "always":
        return True
    value = _get_field(subject, cond["field"])
    op, target = cond["op"], cond.get("value")
    if op == "count_gt":
        return value is not None and len(value) > target
    if value is None:
        return False
    if op == "eq":
        return value == target
    if op == "neq":
        return value != target
    if op == "lt":
        return value < target
    if op == "lte":
        return value <= target
    if op == "gt":
        return value > target
    if op == "gte":
        return value >= target
    if op == "between":  # inclusive low, exclusive high
        lo, hi = target
        return lo <= value < hi
    raise ValueError(f"unknown op: {op}")


def band_for(score: float, bands: dict[str, float]) -> str:
    """Map a confidence score to a band. Inclusive lower bounds, checked high→low."""
    for key, label in BAND_ORDER:
        if score >= bands[key]:
            return label
    return HUMAN_REVIEW


_CATEGORY_RULES: dict[str, str] = {
    "RULE_OWNERSHIP_CONFLICT": "multiple_ownership_claims",
    "RULE_FINGERPRINT_PARTIAL": "fingerprint_match_partial",
    "RULE_FINGERPRINT_STRONG": "fingerprint_match_strong",
    "RULE_NEW_ACCOUNT": "account_age_lt_30d",
    "RULE_TAKEDOWN_HISTORY": "prior_takedowns_present",
    "RULE_AI_DISCLOSURE_MISSING": "ai_generated_undisclosed",
}


@dataclass(frozen=True)
class EvaluationResult:
    confidence_score: float
    confidence_band: str
    risk_direction: str
    human_review_required: bool
    triggered_rules: list[dict[str, str]]
    input_categories: list[str]           # categorical only — no raw personal data
    facts_relied_on: list[str]            # DSA Art 17(3)(b)
    regulatory_mapping: dict[str, Any]
    statement_of_reasons: dict[str, Any] = field(default_factory=dict)


def evaluate(record: dict[str, Any], bundle: PolicyBundle) -> EvaluationResult:
    """Evaluate one submission record against a policy bundle. Pure and replayable."""
    risk_rules = [r for r in bundle.rules if r["confidence_weight"] > 0]
    disclosure_rules = [r for r in bundle.rules if r["confidence_weight"] == 0]

    # Phase 1 — risk rules, in bundle order (deterministic, DEC-2)
    triggered: list[dict[str, str]] = []
    facts: list[str] = []
    risk = 0.0
    forces_review = False
    for rule in risk_rules:
        if _condition_met(rule["condition"], record):
            risk += rule["confidence_weight"]
            triggered.append({"rule_id": rule["rule_id"], "description": rule["description"]})
            if rule["rule_id"] in _CATEGORY_RULES:
                facts.append(_CATEGORY_RULES[rule["rule_id"]])
            forces_review = forces_review or bool(rule.get("forces_human_review"))

    risk = min(risk, 1.0)
    direction = "concerns_identified" if risk >= 0.5 else "no_concerns_identified"
    score = round(abs(1.0 - 2.0 * risk), 3)
    band = band_for(score, bundle.bands)
    human_review = forces_review or band == HUMAN_REVIEW
    if human_review:
        band = HUMAN_REVIEW

    # Phase 2 — disclosure rules (weight 0) against the outcome
    outcome = {"human_review_required": human_review, "band": band, "risk_direction": direction}
    regulatory_mapping: dict[str, Any] = {}
    for rule in disclosure_rules:
        subject = outcome if rule["condition"]["type"] == "outcome" else record
        if _condition_met(rule["condition"], subject):
            triggered.append({"rule_id": rule["rule_id"], "description": rule["description"]})
            for article in rule["articles"]:
                regulatory_mapping[article] = {"rule_id": rule["rule_id"], "status": "evidenced"}
    for rule in risk_rules:  # risk rules that fired also evidence their articles
        if any(t["rule_id"] == rule["rule_id"] for t in triggered):
            for article in rule["articles"]:
                regulatory_mapping.setdefault(article, {"rule_id": rule["rule_id"], "status": "evidenced"})

    # Statement of reasons (DSA Art 17(3)) with the 17(1) quality flag
    concerns = direction == "concerns_identified" or human_review
    quality = "informational" if not concerns else ("specific" if len(facts) >= 2 else "thin")
    statement = {
        "action_context": (
            "routed_to_human_review" if human_review
            else ("flagged_with_concerns" if concerns else "no_restriction_indicated")
        ),                                                    # 17(3)(a) context
        "facts_relied_on": list(facts),                       # 17(3)(b)
        "automated_means_used": True,                         # 17(3)(c) — unconditional
        "legal_ground": None,                                 # 17(3)(d) — requires legal characterisation; deliberately not mechanised
        "contractual_ground": "distributor terms: metadata, ownership and originality requirements",  # 17(3)(e)
        "redress": bundle.oversight_pathway,                  # 17(3)(f)
        "quality_flag_17_1": quality,                         # form vs sufficiency (boundary thesis)
    }

    # Input categories (EP schema: categorical descriptors, never raw data)
    categories = list(facts)
    if record.get("metadata_complete") is False:
        categories.append("metadata_incomplete")
    if not categories:
        categories.append("no_risk_signals_detected")

    return EvaluationResult(
        confidence_score=score,
        confidence_band=band,
        risk_direction=direction,
        human_review_required=human_review,
        triggered_rules=triggered,
        input_categories=categories,
        facts_relied_on=facts,
        regulatory_mapping=regulatory_mapping,
        statement_of_reasons=statement,
    )
