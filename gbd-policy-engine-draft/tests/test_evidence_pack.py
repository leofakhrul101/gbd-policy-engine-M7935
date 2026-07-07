"""Evidence Pack Layer tests — EP-1..6."""

import json

from gbd.engine import evaluate
from gbd.evidence_pack import PACK_FIELDS, build_pack, compute_hash, to_json, verify_integrity

TS = "2026-07-06T12:00:00Z"


def test_schema_exact_fields(bundle, slice_records):
    pack = build_pack(evaluate(slice_records["clean_pass"], bundle), bundle, timestamp=TS)
    assert list(pack.keys()) == PACK_FIELDS  # EP-2: exactly the §6 schema


def test_hash_verifies_and_detects_tampering(bundle, slice_records):
    pack = build_pack(evaluate(slice_records["ambiguous_review"], bundle), bundle, timestamp=TS)
    assert verify_integrity(pack)  # EP-3
    tampered = dict(pack)
    tampered["confidence_score"] = 0.999
    assert not verify_integrity(tampered)


def test_hash_excludes_itself(bundle, slice_records):
    pack = build_pack(evaluate(slice_records["clean_pass"], bundle), bundle, timestamp=TS)
    assert pack["integrity_hash"] == compute_hash(pack)


def test_plain_english_explanation(bundle, slice_records):
    pack = build_pack(evaluate(slice_records["ambiguous_review"], bundle), bundle, timestamp=TS)
    text = pack["plain_english_explanation"]  # EP-4 (AI Act Art 13)
    assert "automated" in text.lower()
    assert "not a legal determination" in text
    assert bundle.oversight_pathway in text


def test_oversight_pathway_referenced(bundle, slice_records):
    pack = build_pack(evaluate(slice_records["ambiguous_review"], bundle), bundle, timestamp=TS)
    assert pack["oversight_pathway"] == bundle.oversight_pathway  # EP-5 (DSA 17, 20)


def test_statement_of_reasons_block(bundle, slice_records):
    pack = build_pack(evaluate(slice_records["thin_reasons"], bundle), bundle, timestamp=TS)
    sor = pack["regulatory_mapping"]["DSA Art 17 — statement of reasons"]
    for key in ("action_context", "facts_relied_on", "automated_means_used", "redress", "quality_flag_17_1"):
        assert key in sor  # 17(3) structural completeness
    assert sor["automated_means_used"] is True  # 17(3)(c)


def test_json_export_round_trip(bundle, slice_records):
    pack = build_pack(evaluate(slice_records["clean_pass"], bundle), bundle, timestamp=TS)
    assert json.loads(to_json(pack)) == pack  # EP-6


def test_deterministic_with_fixed_timestamp(bundle, slice_records):
    a = build_pack(evaluate(slice_records["clean_pass"], bundle), bundle, timestamp=TS)
    b = build_pack(evaluate(slice_records["clean_pass"], bundle), bundle, timestamp=TS)
    assert a == b  # replayable end to end
