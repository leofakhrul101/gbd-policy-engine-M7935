"""Plain-English explanation generator (AI Act Art 13; DSA Art 17(4)) — EP-4.

Two registers, one decision. The sealed pack and the Commission export carry machine
references — a policy version, a scheme identifier, a confidence score — because an
auditor needs to resolve them. The recipient needs none of that: Art 17(4) asks for a
statement that is 'clear and easily comprehensible' and precise enough to let them
'effectively exercise the possibilities for redress'. So the identifiers are gathered
into one clearly-labelled reference line at the end, and the sentences above it say what
happened, why, and what the artist can do, in words an artist uses.
"""

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


def _route(bundle: PolicyBundle) -> str:
    """How to reach redress, in words. Falls back to the machine reference if a bundle
    predates the label — a wrong-register sentence beats a missing one."""
    return bundle.oversight_pathway_label or bundle.oversight_pathway


def plain_english(result: EvaluationResult, bundle: PolicyBundle) -> str:
    parts: list[str] = []
    parts.append(_OUTCOME_PHRASES[result.decision_outcome])
    parts.append("This decision was made by automated means — software applying our "
                 "published rules — and no person had looked at it when it was made.")
    missing = list(result.statement_of_reasons.get("missing_signals", []))
    if result.facts_relied_on:
        reasons = "; ".join(_FACT_PHRASES.get(f, f.replace("_", " ")) for f in result.facts_relied_on)
        parts.append(f"The assessment relied on the following observations: {reasons}.")
    elif missing:
        # Safe state (AI Act Art 14(4)(e)). Saying "nothing was detected" here would be
        # false: the checks did not run. DSA Art 17(4) requires the statement to be
        # specific enough for the recipient to act on, and "we could not check" is a
        # different thing to act on than "we checked and found nothing".
        parts.append("The automated checks did not run on this submission, because the "
                     "information they need was not available. Nothing has been found "
                     "against your release.")
    else:
        parts.append("No risk signals were detected in this submission.")
    if result.human_review_required:
        parts.append(
            f"A person will look at this before anything takes effect. You can also tell us "
            f"why you think it is wrong, using {_route(bundle)}."
        )
    elif result.decision_outcome in bundle.adverse_outcomes:
        parts.append(
            f"No person reviewed this before it took effect. You can ask for a person to look "
            f"at it, give your side, and challenge it, using {_route(bundle)}."
        )
    else:
        parts.append(f"If you think this is wrong, you can tell us using {_route(bundle)}.")
    parts.append(
        "This is a check on how your release was handled. It is not a legal determination that "
        "anything is illegal, and it is not legal advice."
    )
    parts.append(
        f"Reference, if you contact us or if this decision is audited: policy version "
        f"{bundle.policy_version}, "
        + ("assessment confidence not established — checks incomplete"
           if missing else
           f"assessment confidence {result.confidence_score:.3f} ({result.confidence_band})")
        + f", redress scheme {bundle.oversight_pathway}."
    )
    return " ".join(parts)
