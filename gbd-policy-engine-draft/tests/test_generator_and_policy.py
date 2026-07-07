"""Synthetic data (SD-1..5) and policy validation (POL-1..4) tests."""

import copy

import pytest
from jsonschema import ValidationError

from gbd.data_generator import DISTRIBUTION, generate
from gbd.engine import evaluate
from gbd.policy import bundle_from_dict


# ── Generator ────────────────────────────────────────────────────────────────

def test_generator_deterministic():
    assert generate(100, seed=1742) == generate(100, seed=1742)  # SD-5
    assert generate(100, seed=1742) != generate(100, seed=1)


def test_generator_volume_and_distribution():
    records = generate(100, seed=1742)
    assert len(records) >= 100  # SD-4
    counts = {}
    for r in records:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    assert set(counts) == set(DISTRIBUTION)
    assert counts["clean_pass"] == 40


def test_generator_synthetic_only():
    for r in generate(100, seed=1742):
        assert r["title"].startswith("Synthetic")
        assert r["artist"].startswith("Test Artist")
        assert r["isrc"].startswith("SYN")  # SD-3


def test_engine_runs_end_to_end_on_100(bundle):
    """Acceptance: engine runs end-to-end on >=100 synthetic records."""
    for rec in generate(100, seed=1742):
        result = evaluate(rec, bundle)
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.confidence_band in ("High", "Medium", "Low", "Human-Review-Required")


def test_generator_stresses_not_confirms(bundle):
    """The set must produce a spread of bands, not a happy-path monoculture."""
    bands = {evaluate(r, bundle).confidence_band for r in generate(100, seed=1742)}
    assert len(bands) >= 3


# ── Policy bundle validation ────────────────────────────────────────────────

def test_bundle_valid(bundle):
    assert len(bundle.rules) >= 6  # POL-4
    for rule in bundle.rules:
        assert rule["norm_refs"]                     # POL-1
        for part in ("obligation", "control_objective", "system_rule", "evidence_output"):
            assert rule[part]                        # POL-2 full chain


def test_bad_bundle_rejected(bundle):
    data = copy.deepcopy(bundle.raw)
    del data["rules"][0]["control_objective"]        # break the chain
    with pytest.raises(ValidationError):
        bundle_from_dict(data)


def test_bad_version_rejected(bundle):
    data = copy.deepcopy(bundle.raw)
    data["policy_version"] = "not-semver"
    with pytest.raises(ValidationError):
        bundle_from_dict(data)
