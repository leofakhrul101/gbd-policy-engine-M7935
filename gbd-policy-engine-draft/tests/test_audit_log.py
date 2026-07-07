"""Governance & Provenance Layer tests — GOV-1..5, incl. the version-replay demo (§9 step 5)."""

import copy

import pytest
import sqlite3

from gbd.audit_log import AuditLog
from gbd.engine import evaluate
from gbd.evidence_pack import build_pack
from gbd.policy import bundle_from_dict

TS = "2026-07-06T12:00:00Z"


@pytest.fixture()
def log():
    log = AuditLog(":memory:")
    yield log
    log.close()


def test_retrieve_by_pack_id(log, bundle, slice_records):
    log.register_policy(bundle)
    pack = build_pack(evaluate(slice_records["clean_pass"], bundle), bundle, timestamp=TS)
    log.record_decision(pack)
    assert log.get_pack(pack["pack_id"]) == pack  # GOV-3


def test_append_only(log, bundle, slice_records):
    log.register_policy(bundle)
    pack = build_pack(evaluate(slice_records["clean_pass"], bundle), bundle, timestamp=TS)
    log.record_decision(pack)
    with pytest.raises(sqlite3.DatabaseError):
        log._conn.execute("UPDATE evidence_packs SET pack_json = 'x'")
    with pytest.raises(sqlite3.DatabaseError):
        log._conn.execute("DELETE FROM evidence_packs")
    with pytest.raises(sqlite3.DatabaseError):
        log._conn.execute("UPDATE policy_versions SET bundle_yaml = 'x'")  # GOV-5


def test_policy_version_bump_and_replay(log, bundle, slice_records):
    """§9 demo step 5: bump a threshold, re-run, prior decision still reproducible."""
    log.register_policy(bundle)
    rec = slice_records["judgment_illusion"]
    old_result = evaluate(rec, bundle)
    old_pack = build_pack(old_result, bundle, timestamp=TS)
    log.record_decision(old_pack)

    # v0.2.0: stricter High threshold — same record now bands differently
    data = copy.deepcopy(bundle.raw)
    data["policy_version"] = "0.2.0"
    data["bands"]["high"] = 0.95
    v2 = bundle_from_dict(data)
    log.register_policy(v2)
    new_result = evaluate(rec, v2)
    assert old_result.confidence_band == "High"
    assert new_result.confidence_band == "Medium"

    # GOV-2: the stored pack still references the version in force at decision time
    stored = log.get_pack(old_pack["pack_id"])
    assert stored["policy_version"] == "0.1.0"

    # GOV-4: reconstruct v0.1.0 from the log and replay — identical outcome
    reconstructed = log.reconstruct_policy("0.1.0")
    replayed = evaluate(rec, reconstructed)
    assert replayed == old_result


def test_unknown_lookups_raise(log):
    with pytest.raises(KeyError):
        log.get_pack("nope")
    with pytest.raises(KeyError):
        log.reconstruct_policy("9.9.9")
