"""Commission export (v0.2) — map an Evidence Pack to the DSA Transparency
Database Statement-of-Reasons schema (Art 24(5) DSA).

This is the dissertation's falsifiable test made executable: every field the
Commission's schema requires must populate from the sealed certificate alone.
Field names follow the Commission's published API documentation
(transparency.dsa.ec.europa.eu/page/api-documentation, accessed 21 Aug 2026).

Art 24(5): "the information submitted shall not contain personal data". The
pack carries only categorical descriptors (input_categories), so the export is
a projection, never an enrichment.
"""

from __future__ import annotations

from typing import Any

_OUTCOME_TO_VISIBILITY = {
    "REJECT": ["DECISION_VISIBILITY_CONTENT_REMOVED"],
    "QUARANTINE": ["DECISION_VISIBILITY_CONTENT_DISABLED"],
    "REVIEW": ["DECISION_VISIBILITY_OTHER"],
    "ALLOW": [],
}

_TRIGGER_TO_SOURCE = {
    "article_16_notice": "SOURCE_ARTICLE_16",
    "trusted_flagger_notice": "SOURCE_TRUSTED_FLAGGER",
    "other_notification": "SOURCE_TYPE_OTHER_NOTIFICATION",
    "own_initiative_upload_screening": "SOURCE_VOLUNTARY",
}

_DECISION_MAP = {
    "fully_automated": "AUTOMATED_DECISION_FULLY",
    "not_fully_automated": "AUTOMATED_DECISION_PARTIALLY",
}


def commission_sor(pack: dict[str, Any]) -> dict[str, Any]:
    """Project a sealed Evidence Pack onto the Commission SoR schema.

    Raises KeyError if the pack lacks the statement-of-reasons block, and
    ValueError if a required Commission field cannot be populated — an
    exportability failure IS the finding (the certificate fell one step short).
    """
    sor = pack["regulatory_mapping"]["DSA Art 17 — statement of reasons"]

    contractual = sor.get("contractual_ground")
    legal = sor.get("legal_ground")
    if not contractual and not legal:
        raise ValueError("neither contractual nor legal ground present: "
                         "decision_ground cannot be populated (Art 17(3)(d)/(e))")

    # Norm references travel inside the pack per triggered rule; surface the
    # union as the ground reference (the field the database shows as NULL 99.9%
    # of the time — Kaushal et al, FAccT '24).
    norm_refs = sorted({ref for rule in pack["triggered_rules"] for ref in rule.get("norm_refs", [])})

    out: dict[str, Any] = {
        "puid": pack["pack_id"],
        "decision_visibility": _OUTCOME_TO_VISIBILITY[pack["decision_outcome"]],
        "decision_ground": ("DECISION_GROUND_ILLEGAL_CONTENT" if legal
                            else "DECISION_GROUND_INCOMPATIBLE_CONTENT"),
        "incompatible_content_ground": contractual,
        "incompatible_content_explanation": pack["plain_english_explanation"][:2000],
        "decision_facts": "; ".join(sor["facts_relied_on"]) or "no risk signals detected",
        "decision_ground_reference": norm_refs,          # never NULL by construction
        "source_type": _TRIGGER_TO_SOURCE[sor["trigger_source"]],
        "source_identity": None,                          # never exported (Art 24(5))
        "automated_detection": "Yes" if sor["automated_detection"] else "No",
        "automated_decision": _DECISION_MAP[sor["automated_decision"]],
        "application_date": pack["decision_timestamp"][:10],
        "territorial_scope": [],                          # submission-level; no territorial restriction set
    }

    # Personal-data guard: only categorical values may leave the system.
    for key in ("decision_facts", "incompatible_content_explanation"):
        if any(tok in str(out[key]).lower() for tok in ("@", "email", "name:")):
            raise ValueError(f"possible personal data in export field {key}")
    return out
