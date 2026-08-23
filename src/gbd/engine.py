"""Decision Logic Layer — pure, deterministic evaluator (DEC-1..5).

Semantics (documented in README and the policy bundle header):
  R                 = sum of confidence_weight over triggered risk rules, clamped to 1.0
  risk_direction    = "concerns_identified" if R >= 0.5 else "no_concerns_identified"
  confidence_score  = |1 - 2R|   — confidence in the assessment, not in the outcome
  confidence_band   = from policy thresholds (High / Medium / Low / Human-Review-Required)
  decision_outcome  = ALLOW / REVIEW / QUARANTINE / REJECT, from policy thresholds on R

Outcome and confidence are separate axes. The outcome is the bounded workflow
step; the confidence score is how sure the system is about the assessment behind
it. A REJECT at 0.95 confidence is still not a legal determination — the
statement of reasons carries no legal_ground, and that is the boundary thesis.

Which outcomes may be reached on automation alone is not decided here. It is read
from the bundle (`gated_outcomes`), because it is a legal question under GDPR Art
22 and therefore has to be a versioned, auditable control rather than a constant
in code.

Pure function: no I/O, no clock, no randomness, no database (DEC-5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gbd.policy import PolicyBundle

HUMAN_REVIEW = "Human-Review-Required"
BAND_ORDER = [("high", "High"), ("medium", "Medium"), ("low", "Low")]

ALLOW, REVIEW, QUARANTINE, REJECT = "ALLOW", "REVIEW", "QUARANTINE", "REJECT"
OUTCOME_ORDER = [("reject", REJECT), ("quarantine", QUARANTINE), ("review", REVIEW)]

# Where the human sits relative to the decision taking effect. This is the
# operative distinction under GDPR Art 22: 22(1) bites on decisions taken solely
# by automated means, while 22(3) is satisfied by intervention obtainable after
# the fact. See norms.yaml -> GDPR_22.
INTERVENTION = {
    ALLOW: "none_no_adverse_effect",
    REVIEW: "before_decision_takes_effect",
    QUARANTINE: "after_decision_via_oversight_pathway",
    REJECT: "after_decision_via_oversight_pathway",
}


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


def outcome_for(risk: float, outcomes: dict[str, float]) -> str:
    """Map accumulated risk to a bounded workflow outcome (proposal §2).

    Thresholds live in the policy bundle, not here, so that a change of outcome
    boundary is a versioned policy event with an effective date.
    """
    for key, label in OUTCOME_ORDER:
        if risk >= outcomes[key]:
            return label
    return ALLOW


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
    decision_outcome: str                 # ALLOW / REVIEW / QUARANTINE / REJECT
    risk_direction: str
    human_review_required: bool
    solely_automated: bool                # GDPR Art 22(1)
    intervention_point: str               # GDPR Art 22(3)
    triggered_rules: list[dict[str, Any]]
    input_categories: list[str]           # categorical only — no raw personal data
    facts_relied_on: list[str]            # DSA Art 17(3)(b)
    regulatory_mapping: dict[str, Any]
    statement_of_reasons: dict[str, Any] = field(default_factory=dict)


def evaluate(
    record: dict[str, Any],
    bundle: PolicyBundle,
    trigger_source: str = "own_initiative_upload_screening",
    notice_ref: str | None = None,
) -> EvaluationResult:
    """Evaluate one submission record against a policy bundle. Pure and replayable.

    v0.2: `trigger_source` distinguishes own-initiative screening from an Art 16
    notice (DSA Art 17(3)(b)); a notice against a prior ALLOW re-enters here with
    trigger_source="article_16_notice" and the notice reference. `notice_ref` is
    recorded in the statement of reasons, never evaluated as a signal.
    """
    risk_rules = [r for r in bundle.rules if r["confidence_weight"] > 0]
    disclosure_rules = [r for r in bundle.rules if r["confidence_weight"] == 0]

    # Phase 0 (v0.2) — safe state. If a required input signal is absent, the
    # engine must not decide on partial evidence: silence would under-count risk
    # and produce a confident ALLOW from missing data. Route to REVIEW instead
    # (AI Act Art 14(4)(e), recital 73: in-built operational constraints).
    missing_signals = [s for s in bundle.required_signals if _get_field(record, s) is None]
    safe_state = bool(missing_signals)

    # Phase 1 — risk rules, in bundle order (deterministic, DEC-2)
    triggered: list[dict[str, Any]] = []
    facts: list[str] = []
    risk = 0.0
    forces_review = False
    for rule in risk_rules:
        if _condition_met(rule["condition"], record):
            risk += rule["confidence_weight"]
            triggered.append({
                "rule_id": rule["rule_id"],
                "description": rule["description"],
                "reason_code": rule.get("reason_code"),
                # v0.2 — the rule-to-norm link travels inside the sealed record
                # (DSA Art 17(3)(d)/(e); a side mapping table would be
                # compliance by document, which this artefact argues against).
                "norm_refs": list(rule.get("norm_refs", [])),
                "articles": list(rule.get("articles", [])),
            })
            if rule["rule_id"] in _CATEGORY_RULES:
                facts.append(_CATEGORY_RULES[rule["rule_id"]])
            forces_review = forces_review or bool(rule.get("forces_human_review"))

    risk = min(risk, 1.0)
    direction = "concerns_identified" if risk >= 0.5 else "no_concerns_identified"
    score = round(abs(1.0 - 2.0 * risk), 3)
    band = band_for(score, bundle.bands)

    # Phase 1b — bounded workflow outcome. A rule carrying forces_human_review
    # overrides the threshold and routes to REVIEW whatever the score says:
    # contested ownership is significant for the affected artist regardless of
    # how confident the system happens to be (norms.yaml -> GDPR_22).
    # v0.2: a missing required signal likewise forces REVIEW (safe state).
    decision_outcome = REVIEW if (forces_review or safe_state) else outcome_for(risk, bundle.outcomes)
    human_review = decision_outcome in bundle.gated_outcomes
    if human_review:
        band = HUMAN_REVIEW
    intervention_point = INTERVENTION[decision_outcome]

    # Phase 2 — disclosure rules (weight 0) against the outcome
    outcome = {
        "human_review_required": human_review,
        "band": band,
        "risk_direction": direction,
        "decision_outcome": decision_outcome,
    }
    regulatory_mapping: dict[str, Any] = {}
    for rule in disclosure_rules:
        subject = outcome if rule["condition"]["type"] == "outcome" else record
        if _condition_met(rule["condition"], subject):
            triggered.append({
                "rule_id": rule["rule_id"],
                "description": rule["description"],
                "reason_code": rule.get("reason_code"),
                "norm_refs": list(rule.get("norm_refs", [])),
                "articles": list(rule.get("articles", [])),
            })
            for article in rule["articles"]:
                regulatory_mapping[article] = {"rule_id": rule["rule_id"], "status": "evidenced"}
    for rule in risk_rules:  # risk rules that fired also evidence their articles
        if any(t["rule_id"] == rule["rule_id"] for t in triggered):
            for article in rule["articles"]:
                regulatory_mapping.setdefault(article, {"rule_id": rule["rule_id"], "status": "evidenced"})

    # Statement of reasons (DSA Art 17(3)) with the 17(4) quality flag
    concerns = direction == "concerns_identified" or human_review
    quality = "informational" if not concerns else ("specific" if len(facts) >= 2 else "thin")
    statement = {
        "action_taken": decision_outcome,                     # 17(3)(a)
        "action_scope": "submission-level; no duration set by this system",   # 17(3)(a)
        "facts_relied_on": list(facts),                       # 17(3)(b)
        "trigger_source": trigger_source,                     # 17(3)(b) — notice vs own-initiative
        "notice_ref": notice_ref,                             # 17(3)(b) — Art 16 notice reference, if any
        "automated_means_used": True,                         # 17(3)(c) — unconditional
        # v0.2 — 17(3)(c) names two facts, and the Commission schema separates
        # them (automated_detection / automated_decision). Detection here means
        # the upstream signals (fingerprint scores etc), which this artefact
        # takes as automated inputs; the decision is the engine's own step.
        "automated_detection": True,                          # 17(3)(c), first limb
        "automated_decision": "not_fully_automated" if human_review else "fully_automated",  # 17(3)(c), second limb
        "safe_state": safe_state,                             # AI Act Art 14(4)(e)
        "missing_signals": list(missing_signals),
        "solely_automated": not human_review,                 # 17(3)(c) / GDPR Art 22(1)
        "intervention_point": intervention_point,             # GDPR Art 22(3)
        "legal_ground": None,                                 # 17(3)(d) — requires a legal characterisation AND an explanation of why the content is illegal on that ground; deliberately not mechanised
        "contractual_ground": "distributor terms: metadata, ownership and originality requirements",  # 17(3)(e)
        "redress": bundle.oversight_pathway,                  # 17(3)(f)
        "quality_flag_17_4": quality,                         # form vs sufficiency (boundary thesis)
    }

    # Input categories (EP schema: categorical descriptors, never raw data)
    categories = list(facts)
    if record.get("metadata_complete") is False:
        categories.append("metadata_incomplete")
    for s in missing_signals:                       # v0.2 — safe state is a recorded fact
        categories.append(f"signal_unavailable:{s}")
    if not categories:
        categories.append("no_risk_signals_detected")

    return EvaluationResult(
        confidence_score=score,
        confidence_band=band,
        decision_outcome=decision_outcome,
        risk_direction=direction,
        human_review_required=human_review,
        solely_automated=not human_review,
        intervention_point=intervention_point,
        triggered_rules=triggered,
        input_categories=categories,
        facts_relied_on=facts,
        regulatory_mapping=regulatory_mapping,
        statement_of_reasons=statement,
    )
