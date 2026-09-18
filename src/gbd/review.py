"""Human Review Layer (v0.2) — blind-first review with a sealed review record.

Why this exists. SCHUFA (C-634/21 paras 48, 50) holds that where a human "draws
strongly" on an automated output, the output is the decision; WP29 (WP251rev.01
p 21) requires oversight by someone with "authority and competence to change the
decision", not a token gesture; Binns & Veale (2021) measure rubber-stamping by
whether reviewers are "rarely or never overturning". This module makes the
answer to all three an auditable number rather than an assertion:

  1. Blind-first by construction: `ReviewSession` withholds the engine's
     proposed outcome until the reviewer has committed their own. There is no
     accessor that reveals it earlier (Sterz et al 2024, "reviewing AI output
     after independent judgment"; Goddard et al 2012 mitigators).
  2. Every review commits a sealed, hash-verified review record referencing the
     original Evidence Pack, carrying reviewer identity (pseudonymous),
     agreement/override, and time-to-decision.
  3. `reentry_from_notice` re-opens a prior decision (including an ALLOW) when
     an Article 16 notice arrives — the third-party rightsholder's route into a
     record GDPR Art 22 does not give them.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from gbd.engine import (ALLOW, QUARANTINE, REJECT, REVIEW, RISK_DIMENSIONS,
                        EvaluationResult, evaluate)
from gbd.policy import PolicyBundle

REVIEW_OUTCOMES = (ALLOW, QUARANTINE, REJECT)   # a reviewer must decide; REVIEW is not a decision

REVIEW_FIELDS = [
    "review_id", "pack_id", "policy_version", "reviewer_id", "review_timestamp",
    "blind_first", "signals_shown", "reviewer_outcome", "engine_proposal",
    "agreement", "reason_text", "forwarded_to_provider", "time_to_decision_ms",
    "integrity_hash",
]


def _hash(body: dict[str, Any]) -> str:
    data = {k: v for k, v in body.items() if k != "integrity_hash"}
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ReviewSession:
    """One reviewer, one Evidence Pack. The engine's proposal stays hidden until commit.

    Usage:
        session = ReviewSession(pack, reviewer_id="rev-07")
        session.signals()                  # the six dimensions: what fired and why
        record = session.commit("REJECT", reason_text="...")   # proposal revealed only now
    """

    def __init__(self, pack: dict[str, Any], reviewer_id: str, clock_ms: int | None = None):
        if not reviewer_id:
            raise ValueError("reviewer_id is required: accountability is a condition of "
                             "effective oversight (Goddard et al 2012; AI Act Art 26(2))")
        self._pack = pack
        self._reviewer_id = reviewer_id
        self._proposal = pack["decision_outcome"]
        self._opened_ms = clock_ms if clock_ms is not None else int(
            datetime.now(timezone.utc).timestamp() * 1000)
        self._committed = False

    def signals(self) -> list[dict[str, Any]]:
        """Everything the reviewer may see before deciding.

        All six risk dimensions are shown, each marked fired or not-fired. A
        reviewer who sees only the rules that fired cannot tell whether the
        engine looked at the right things, which is the competence WP29
        (WP251rev.01, 21) requires of meaningful oversight; the dimensions that
        stayed silent are evidence too (audit A2).

        Deliberately NOT included: the engine's proposed outcome.
        """
        fired = {r["rule_id"]: r for r in self._pack["triggered_rules"]}
        out: list[dict[str, Any]] = [
            {"what": f"dimension:{label}",
             "value": {"fired": rule_id in fired,
                       "reason_code": fired.get(rule_id, {}).get("reason_code")}}
            for rule_id, label in RISK_DIMENSIONS
        ]
        out += [
            {"what": "triggered_rules", "value": self._pack["triggered_rules"]},
            {"what": "input_categories", "value": self._pack["input_categories"]},
            {"what": "confidence_band", "value": self._pack["confidence_band"]},
            {"what": "explanation", "value": self._pack["plain_english_explanation"]},
        ]
        return out

    def dimensions_shown(self) -> int:
        """How many risk dimensions the reviewer was shown (fired or not)."""
        return sum(1 for s in self.signals() if s["what"].startswith("dimension:"))

    def commit(self, reviewer_outcome: str, reason_text: str = "",
               forwarded_to_provider: bool = False, clock_ms: int | None = None) -> dict[str, Any]:
        if self._committed:
            raise RuntimeError("review already committed; open a new session to re-review")
        if reviewer_outcome not in REVIEW_OUTCOMES:
            raise ValueError(f"reviewer must decide: one of {REVIEW_OUTCOMES}")
        self._committed = True
        now_ms = clock_ms if clock_ms is not None else int(
            datetime.now(timezone.utc).timestamp() * 1000)
        record: dict[str, Any] = {
            "review_id": str(uuid.uuid4()),
            "pack_id": self._pack["pack_id"],
            "policy_version": self._pack["policy_version"],
            "reviewer_id": self._reviewer_id,
            "review_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "blind_first": True,
            "signals_shown": [s["what"] for s in self.signals()],
            "reviewer_outcome": reviewer_outcome,
            "engine_proposal": self._proposal,          # revealed here, after commitment
            "agreement": "AGREE" if reviewer_outcome == self._proposal else "OVERRIDE",
            "reason_text": reason_text,
            "forwarded_to_provider": forwarded_to_provider,
            "time_to_decision_ms": max(0, now_ms - self._opened_ms),
        }
        record["integrity_hash"] = _hash(record)
        assert list(record.keys()) == REVIEW_FIELDS
        return record


def verify_review(record: dict[str, Any]) -> bool:
    return record.get("integrity_hash") == _hash(record)


def reentry_from_notice(
    original_pack: dict[str, Any],
    record: dict[str, Any],
    bundle: PolicyBundle,
    notice_ref: str,
) -> EvaluationResult:
    """Re-open a prior decision (including an ALLOW) on receipt of an Art 16 notice.

    Re-evaluates the same submission record with trigger_source set to the
    notice, so the fresh statement of reasons carries 17(3)(b) correctly, and
    records the pack_id of the decision being re-opened in supersedes_pack_id.
    Without that link the rightsholder's route produces an orphan decision that
    cannot be tied to the ALLOW it contests (audit A4).
    """
    return evaluate(record, bundle,
                    trigger_source="article_16_notice", notice_ref=notice_ref,
                    supersedes_pack_id=original_pack["pack_id"])


def agreement_rate(records: list[dict[str, Any]]) -> float | None:
    """Share of reviews that AGREE with the engine. The rubber-stamp metric:
    persistently ~1.0 invites the SCHUFA 'draws strongly' characterisation."""
    if not records:
        return None
    agree = sum(1 for r in records if r["agreement"] == "AGREE")
    return round(agree / len(records), 3)
