"""v0.2 tests — safe state, norm_refs in the sealed payload, blind-first review,
notice-triggered re-entry, controller approval, Commission export.

Each test names the legal finding it operationalises. See docs/CHANGES-v0.2.md.
"""

from pathlib import Path

import pytest

from gbd.audit_log import AuditLog
from gbd.engine import ALLOW, QUARANTINE, REJECT, REVIEW, RISK_DIMENSIONS, evaluate
from gbd.evidence_pack import build_pack, verify_integrity
from gbd.export import commission_sor
from gbd.policy import load_bundle
from gbd.review import ReviewSession, agreement_rate, reentry_from_notice, verify_review

ROOT = Path(__file__).resolve().parents[1]
TS = "2026-08-22T12:00:00Z"


@pytest.fixture(scope="module")
def v02():
    return load_bundle(ROOT / "policies" / "v0.2.0.yaml")


@pytest.fixture()
def clean_record():
    return {
        "record_id": "t1", "ownership_claims": ["artist-a"],
        "fingerprint_match_score": 0.05,
        "behavioural_signals": {"account_age_days": 400, "takedown_history": 0},
        "ai_generated": False, "ai_disclosed": False, "metadata_complete": True,
    }


@pytest.fixture()
def risky_record():
    return {
        "record_id": "t2", "ownership_claims": ["a", "b"],
        "fingerprint_match_score": 0.9,
        "behavioural_signals": {"account_age_days": 5, "takedown_history": 2},
        "ai_generated": True, "ai_disclosed": False, "metadata_complete": True,
    }


# 1 — backward compatibility: v0.1.0 bundle still loads, evaluates, seals, verifies.
def test_v010_still_replayable(clean_record):
    old = load_bundle(ROOT / "policies" / "v0.1.0.yaml")
    pack = build_pack(evaluate(clean_record, old), old, timestamp=TS)
    assert verify_integrity(pack)
    assert old.required_signals == [] and old.approval is None


# 2 — every triggered rule carries its norm_refs inside the sealed payload
#     (DSA Art 17(3)(d)/(e); Husovec p 255 'previously disclosed legal basis').
def test_norm_refs_sealed_in_payload(v02, risky_record):
    pack = build_pack(evaluate(risky_record, v02), v02, timestamp=TS)
    assert pack["triggered_rules"], "risky record must trigger rules"
    for rule in pack["triggered_rules"]:
        assert rule["norm_refs"], f"{rule['rule_id']} has no norm_refs in the sealed record"
        assert rule["articles"]
    assert verify_integrity(pack)  # the refs are under the hash


# 3 — explanation is always present and non-empty (DSA Art 17(4)).
def test_explanation_required(v02, clean_record, risky_record):
    for rec in (clean_record, risky_record):
        pack = build_pack(evaluate(rec, v02), v02, timestamp=TS)
        assert pack["plain_english_explanation"].strip()


# 4 — safe state: a missing required signal must route to REVIEW, never a
#     confident ALLOW from absent evidence (AI Act Art 14(4)(e), recital 73).
def test_safe_state_on_missing_signal(v02, clean_record):
    broken = dict(clean_record)
    del broken["fingerprint_match_score"]
    r = evaluate(broken, v02)
    assert r.decision_outcome == REVIEW
    assert r.statement_of_reasons["safe_state"] is True
    assert "signal_unavailable:fingerprint_match_score" in r.input_categories
    # and the same record with the signal present is an ALLOW:
    assert evaluate(clean_record, v02).decision_outcome == ALLOW


# 5 — 17(3)(c) two limbs: automated detection and automated decision are
#     recorded separately (Commission schema: automated_detection / automated_decision).
def test_automation_two_limbs(v02, clean_record, risky_record):
    allow = evaluate(clean_record, v02).statement_of_reasons
    review = evaluate(risky_record, v02).statement_of_reasons  # forces_human_review
    assert allow["automated_detection"] is True
    assert allow["automated_decision"] == "fully_automated"
    assert review["automated_decision"] == "not_fully_automated"


# 6 — blind-first review: the engine's proposal is not readable before commit;
#     the sealed review record carries reviewer identity and agreement
#     (SCHUFA C-634/21 para 48; WP29 p 21; Sterz et al 2024; Goddard et al 2012).
def test_blind_first_review(v02, risky_record):
    pack = build_pack(evaluate(risky_record, v02), v02, timestamp=TS)
    session = ReviewSession(pack, reviewer_id="rev-07", clock_ms=1000)
    shown = {s["what"] for s in session.signals()}
    assert "triggered_rules" in shown and "explanation" in shown
    # every risk dimension is shown, fired or not — not only the ones that fired
    assert session.dimensions_shown() == len(RISK_DIMENSIONS) == 6
    dims = [s for s in session.signals() if s["what"].startswith("dimension:")]
    assert any(d["value"]["fired"] for d in dims)
    assert any(not d["value"]["fired"] for d in dims)
    assert not any("proposal" in s["what"] or "outcome" in s["what"] for s in session.signals())
    record = session.commit(REJECT, reason_text="strong match + conflict", clock_ms=61000)
    assert record["blind_first"] is True
    assert record["reviewer_id"] == "rev-07"
    assert record["agreement"] in ("AGREE", "OVERRIDE")
    assert record["time_to_decision_ms"] == 60000
    assert verify_review(record)
    with pytest.raises(RuntimeError):
        session.commit(REJECT)  # one commitment per session
    with pytest.raises(ValueError):
        ReviewSession(pack, reviewer_id="")  # anonymous review refused


# 7 — reviewer must decide: REVIEW is not a permissible reviewer outcome.
def test_reviewer_must_decide(v02, risky_record):
    pack = build_pack(evaluate(risky_record, v02), v02, timestamp=TS)
    with pytest.raises(ValueError):
        ReviewSession(pack, reviewer_id="rev-07").commit(REVIEW)


# 8 — notice-triggered re-entry: an Art 16 notice re-opens a prior ALLOW with
#     trigger_source recorded (DSA Art 17(3)(b); the rightsholder's route).
def test_reentry_from_notice(v02, clean_record):
    original = build_pack(evaluate(clean_record, v02), v02, timestamp=TS)
    assert original["decision_outcome"] == ALLOW
    r2 = reentry_from_notice(original, clean_record, v02, notice_ref="NOTICE-2026-0042")
    sor = r2.statement_of_reasons
    assert sor["trigger_source"] == "article_16_notice"
    assert sor["notice_ref"] == "NOTICE-2026-0042"
    # the re-entry names the decision it re-opens (audit A4)
    assert sor["supersedes_pack_id"] == original["pack_id"]


# 9 — review events are append-only and the agreement rate is computable
#     (Binns & Veale: rubber-stamping is 'rarely or never overturning').
def test_review_audit_and_agreement_rate(v02, risky_record):
    import sqlite3
    log = AuditLog()
    log.register_policy(v02)
    pack = build_pack(evaluate(risky_record, v02), v02, timestamp=TS)
    log.record_decision(pack)
    rec = ReviewSession(pack, reviewer_id="rev-07", clock_ms=0).commit(REJECT, clock_ms=1)
    log.record_review(rec)
    stored = log.reviews_for(pack["pack_id"])
    assert len(stored) == 1 and verify_review(stored[0])
    assert agreement_rate(stored) in (0.0, 1.0)
    with pytest.raises(sqlite3.DatabaseError):
        log._conn.execute("DELETE FROM review_events")


# 10 — controller approval travels with the bundle (EDPB 07/2020 para 84).
def test_approval_block(v02):
    assert v02.approval and v02.approval["approved_by"] == "distributor-demo"


# 11 — Commission export: every required SoR field populates from the sealed
#     pack alone, and the ground reference is never NULL (Kaushal et al 2024).
def test_commission_export(v02, risky_record, clean_record):
    pack = build_pack(evaluate(risky_record, v02), v02, timestamp=TS)
    out = commission_sor(pack)
    assert out["decision_ground"] == "DECISION_GROUND_INCOMPATIBLE_CONTENT"
    assert out["decision_ground_reference"], "ground reference must never be NULL"
    assert out["source_type"] == "SOURCE_VOLUNTARY"
    assert out["automated_detection"] == "Yes"
    assert out["automated_decision"] == "AUTOMATED_DECISION_PARTIALLY"
    assert out["source_identity"] is None
    # notice-triggered decision exports SOURCE_ARTICLE_16
    r2 = reentry_from_notice(pack, clean_record, v02, notice_ref="N-1")
    pack2 = build_pack(r2, v02, timestamp=TS)
    assert commission_sor(pack2)["source_type"] == "SOURCE_ARTICLE_16"


# 12 — every pack names the submission it decides, pseudonymously; two different
#      submissions with an identical signal profile in the same second remain
#      distinct records and both persist (audit A1; DSA Art 17(1), Art 24(5)).
def test_pack_identifies_its_submission(v02, clean_record):
    import sqlite3
    a = dict(clean_record, record_id="track-AAA")
    b = dict(clean_record, record_id="track-ZZZ")
    pa = build_pack(evaluate(a, v02), v02, timestamp=TS)
    pb = build_pack(evaluate(b, v02), v02, timestamp=TS)
    assert pa["submission_ref"] and pa["submission_ref"] != pb["submission_ref"]
    assert "track-AAA" not in str(pa), "the raw identifier must never enter the pack"
    assert pa["pack_id"] != pb["pack_id"]
    assert verify_integrity(pa) and verify_integrity(pb)
    log = AuditLog()
    log.register_policy(v02)
    log.record_decision(pa)
    log.record_decision(pb)          # would raise IntegrityError before v0.2.1
    assert len(log.list_decisions()) == 2
    # and the reference is stable: the same submission always resolves the same way
    assert build_pack(evaluate(a, v02), v02, timestamp=TS)["submission_ref"] == pa["submission_ref"]


# 13 — the 17(4) sufficiency flag actually reaches 'thin': a decision that is
#      structurally complete under 17(3) yet rests on a single named fact.
#      This is the boundary thesis under test, not merely asserted (audit A3).
def test_thin_statement_is_reachable_and_flagged(v02, clean_record):
    lone_signal = dict(clean_record, fingerprint_match_score=0.9)
    r = evaluate(lone_signal, v02)
    assert r.decision_outcome == QUARANTINE
    assert len(r.facts_relied_on) == 1
    assert r.statement_of_reasons["quality_flag_17_4"] == "thin"
    # structurally complete all the same: every 17(3) field is populated
    for field_name in ("action_taken", "facts_relied_on", "automated_means_used",
                       "contractual_ground", "redress"):
        assert r.statement_of_reasons[field_name] not in (None, "", [])


# 14 — the Commission export carries the submission reference forward, so a
#      database row can be traced back to one sealed decision.
def test_export_carries_submission_reference(v02, risky_record):
    pack = build_pack(evaluate(risky_record, v02), v02, timestamp=TS)
    out = commission_sor(pack)
    assert out["puid"] == pack["pack_id"]
    assert pack["submission_ref"] not in str(out), \
        "the submission reference stays internal; only the pack id is exported"


# 15 — the safe state tells the recipient the truth. A submission routed to REVIEW
#      because a required signal was unavailable must not be described to the artist
#      as one where nothing was detected, and must not carry a confidence figure:
#      DSA Art 17(4) requires the statement to be specific enough to act on, and
#      "we could not check" is a different thing to act on than "we checked and
#      found nothing". AI Act Art 13(1) on interpretable output points the same way.
def test_safe_state_is_not_reported_as_a_clean_result(v02, clean_record):
    blind = {k: v for k, v in clean_record.items() if k not in v02.required_signals}
    r = evaluate(blind, v02)
    assert r.decision_outcome == REVIEW
    assert r.statement_of_reasons["safe_state"] is True
    assert not r.facts_relied_on

    text = build_pack(r, v02, timestamp=TS)["plain_english_explanation"]
    assert "No risk signals were detected" not in text, \
        "the checks did not run; saying nothing was detected asserts a result never reached"
    assert "did not run" in text
    assert f"{r.confidence_score:.3f}" not in text, \
        "a confidence figure on an assessment that never completed reads as certainty"

    # the clean path is untouched: there, the same sentence is true
    clean = build_pack(evaluate(clean_record, v02), v02, timestamp=TS)
    assert "No risk signals were detected" in clean["plain_english_explanation"]
    assert f"{evaluate(clean_record, v02).confidence_score:.3f}" in \
        clean["plain_english_explanation"]
