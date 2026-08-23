"""Decision Logic Layer tests — DEC-1..5, incl. threshold boundaries (NFR-3)."""

import pytest

from gbd.engine import evaluate, band_for, HUMAN_REVIEW


# ── The four demonstration records (the dissertation's edge cases) ──────────

def test_clean_pass(bundle, slice_records):
    r = evaluate(slice_records["clean_pass"], bundle)
    assert r.confidence_band == "High"
    assert r.risk_direction == "no_concerns_identified"
    assert not r.human_review_required
    assert r.confidence_score == 1.0
    # 17(3)(c): automation disclosed even on a clean pass
    assert r.statement_of_reasons["automated_means_used"] is True


def test_ambiguous_routes_to_human(bundle, slice_records):
    r = evaluate(slice_records["ambiguous_review"], bundle)
    assert r.confidence_band == HUMAN_REVIEW
    assert r.human_review_required
    assert "multiple_ownership_claims" in r.facts_relied_on
    assert any(t["rule_id"] == "RULE_HUMAN_REVIEW_ROUTING" for t in r.triggered_rules)


def test_thin_reasons_flagged(bundle, slice_records):
    r = evaluate(slice_records["thin_reasons"], bundle)
    assert r.confidence_band == "Medium"
    assert r.statement_of_reasons["quality_flag_17_4"] in ("thin", "informational")
    # exactly one weak signal -> structurally complete but thin against 17(1)
    assert len(r.facts_relied_on) == 1


def test_judgment_illusion_confident_concern(bundle, slice_records):
    r = evaluate(slice_records["judgment_illusion"], bundle)
    assert r.confidence_band == "High"
    assert r.risk_direction == "concerns_identified"
    assert not r.human_review_required
    # the pack is confident, but it is still evidence, not adjudication:
    assert r.statement_of_reasons["legal_ground"] is None


# ── No categorical output anywhere (DEC-4) ──────────────────────────────────

def test_no_categorical_decision(bundle, slice_records):
    for rec in slice_records.values():
        r = evaluate(rec, bundle)
        for forbidden in ("Allow", "Reject", "Quarantine"):
            assert r.confidence_band != forbidden
            assert forbidden.lower() not in r.risk_direction.lower()


# ── Threshold boundaries (DEC-3) ────────────────────────────────────────────

@pytest.mark.parametrize("score,expected", [
    (0.199, HUMAN_REVIEW), (0.200, "Low"),
    (0.499, "Low"), (0.500, "Medium"),
    (0.799, "Medium"), (0.800, "High"),
    (0.0, HUMAN_REVIEW), (1.0, "High"),
])
def test_band_boundaries(bundle, score, expected):
    assert band_for(score, bundle.bands) == expected


# ── Determinism (DEC-2, DEC-5) ──────────────────────────────────────────────

def test_determinism_on_slice(bundle, slice_records):
    for rec in slice_records.values():
        a, b = evaluate(rec, bundle), evaluate(rec, bundle)
        assert a == b


def test_rule_order_is_bundle_order(bundle, slice_records):
    r = evaluate(slice_records["ambiguous_review"], bundle)
    ids = [t["rule_id"] for t in r.triggered_rules]
    bundle_order = [ru["rule_id"] for ru in bundle.rules if ru["rule_id"] in ids]
    assert ids == bundle_order


# ── Rules fire when they should, stay silent when they shouldn't ───────────

def test_ai_disclosure_rule(bundle, slice_records):
    rec = dict(slice_records["clean_pass"])
    rec.update(ai_generated=True, ai_disclosed=False)
    r = evaluate(rec, bundle)
    assert "ai_generated_undisclosed" in r.facts_relied_on
    rec.update(ai_disclosed=True)
    r2 = evaluate(rec, bundle)
    assert "ai_generated_undisclosed" not in r2.facts_relied_on


def test_fingerprint_band_edges(bundle, slice_records):
    rec = dict(slice_records["clean_pass"])
    for score, cat in [(0.29, None), (0.30, "fingerprint_match_partial"),
                       (0.74, "fingerprint_match_partial"), (0.75, "fingerprint_match_strong")]:
        rec["fingerprint_match_score"] = score
        r = evaluate(rec, bundle)
        if cat is None:
            assert not any("fingerprint" in f for f in r.facts_relied_on)
        else:
            assert cat in r.facts_relied_on


def test_input_categories_contain_no_raw_data(bundle, slice_records):
    for rec in slice_records.values():
        r = evaluate(rec, bundle)
        joined = " ".join(r.input_categories)
        assert rec["artist"] not in joined
        assert rec["isrc"] not in joined
