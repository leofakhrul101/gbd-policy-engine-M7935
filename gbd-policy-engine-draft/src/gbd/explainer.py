"""Plain-English explanation generator (AI Act Art 13; DSA Art 17(1)) — EP-4."""

from __future__ import annotations

from gbd.engine import EvaluationResult
from gbd.policy import PolicyBundle

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
    parts.append(
        f"This submission was assessed by an automated system using policy version "
        f"{bundle.policy_version}. The system's confidence in its assessment is "
        f"{result.confidence_score:.3f} ({result.confidence_band})."
    )
    if result.facts_relied_on:
        reasons = "; ".join(_FACT_PHRASES.get(f, f.replace("_", " ")) for f in result.facts_relied_on)
        parts.append(f"The assessment relied on the following observations: {reasons}.")
    else:
        parts.append("No risk signals were detected in this submission.")
    if result.human_review_required:
        parts.append(
            f"This outcome has been routed to a human reviewer and no automated "
            f"restriction takes effect on its own. You can contest or ask about this "
            f"outcome via: {bundle.oversight_pathway}."
        )
    else:
        parts.append(f"You can contest this outcome via: {bundle.oversight_pathway}.")
    parts.append(
        "This record is a readiness signal produced by compliance-support software. "
        "It is not a legal determination and does not constitute legal advice."
    )
    return " ".join(parts)
