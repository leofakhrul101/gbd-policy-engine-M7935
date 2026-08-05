"""Plain-English explanation generator (AI Act Art 13; DSA Art 17(4)) — EP-4."""

from __future__ import annotations

from gbd.engine import EvaluationResult
from gbd.policy import PolicyBundle

_OUTCOME_PHRASES = {
    "ALLOW": "This submission was accepted and no restriction was applied.",
    "REVIEW": "This submission has been held for review by a person before anything takes effect.",
    "QUARANTINE": "This submission has been held back from distribution.",
    "REJECT": "This submission was not accepted for distribution.",
}

_FACT_PHRASES = {
    "multiple_ownership_claims": "more than one party claims ownership of this recording",
    "fingerprint_match_partial": "the audio partially matches an existing recording",
    "fingerprint_match_strong": "the audio strongly matches an existing recording",
    "account_age_lt_30d": "the uploading account was created less than 30 days ago",
    "prior_takedowns_present": "the uploading account has previous takedowns",
    "ai_generated_undisclosed": "the track appears to be AI-generated but was not disclosed as such",
}


def plain_english(result: EvaluationResult, bundle: PolicyBundle) -> str:
    parts: list[str] = []
    parts.append(_OUTCOME_PHRASES[result.decision_outcome])
    parts.append(
        f"The decision was made by an automated system using policy version "
        f"{bundle.policy_version}. The system's confidence in the assessment behind it is "
        f"{result.confidence_score:.3f} ({result.confidence_band})."
    )
    if result.facts_relied_on:
        reasons = "; ".join(_FACT_PHRASES.get(f, f.replace("_", " ")) for f in result.facts_relied_on)
        parts.append(f"The assessment relied on the following observations: {reasons}.")
    else:
        parts.append("No risk signals were detected in this submission.")
    if result.human_review_required:
        parts.append(
            f"A person will look at this before it takes effect. You can also contest it "
            f"or ask about it via: {bundle.oversight_pathway}."
        )
    elif result.decision_outcome in bundle.adverse_outcomes:
        parts.append(
            f"This decision was taken by automated means without a person reviewing it "
            f"first. You have the right to ask for a person to look at it, to give your "
            f"side, and to challenge the decision, via: {bundle.oversight_pathway}."
        )
    else:
        parts.append(f"You can contest this outcome via: {bundle.oversight_pathway}.")
    parts.append(
        "This record is a readiness signal produced by compliance-support software. "
        "It is not a legal determination and does not constitute legal advice."
    )
    return " ".join(parts)
