"""Streamlit demo — the 6-step supervisor walkthrough (REQUIREMENTS §9).

Run:  streamlit run demo/app.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
import yaml

from gbd.audit_log import AuditLog
from gbd.engine import evaluate
from gbd.evidence_pack import build_pack, to_json, verify_integrity
from gbd.policy import bundle_from_dict, load_bundle

st.set_page_config(page_title="GBD Policy Engine", layout="wide")
st.title("Governance-by-Design Policy Engine — demo")
st.caption(
    "M7935 dissertation artefact. Not legal advice: a readiness signal, not a "
    "determination of compliance. Synthetic data only."
)

BUNDLE_PATH = ROOT / "policies" / "v0.1.0.yaml"


@st.cache_resource
def _log() -> AuditLog:
    log = AuditLog(":memory:")
    log.register_policy(load_bundle(BUNDLE_PATH))
    return log


bundle = load_bundle(BUNDLE_PATH)
slice_data = yaml.safe_load((ROOT / "data" / "synthetic" / "slice.yaml").read_text())
records = {r["record_id"]: r for r in slice_data["records"]}
log = _log()

steps = st.tabs([
    "1 · Trace a rule to its Article",
    "2 · Clean pass",
    "3 · Edge case → human review",
    "4 · Retrieve + verify hash",
    "5 · Version bump + replay",
    "6 · Plain-English explainer",
])

with steps[0]:
    st.subheader("Norm-to-Control chain, live from the policy YAML")
    rule_id = st.selectbox("Rule", [r["rule_id"] for r in bundle.rules])
    rule = bundle.rule(rule_id)
    st.markdown(f"**Articles:** {', '.join(rule['articles'])}")
    for stage in ("obligation", "control_objective", "system_rule", "evidence_output"):
        st.markdown(f"**{stage.replace('_', ' ').title()}:**")
        st.write(rule[stage])

with steps[1]:
    st.subheader("Clean pass — high confidence, disclosure still emitted")
    result = evaluate(records["clean_pass"], bundle)
    pack = build_pack(result, bundle)
    log.record_decision(pack)
    st.metric("Confidence", f"{result.confidence_score:.3f}", result.confidence_band)
    st.json(pack)
    st.session_state["pack_id"] = pack["pack_id"]

with steps[2]:
    st.subheader("Ambiguous record — lower confidence, human-review flag")
    result = evaluate(records["ambiguous_review"], bundle)
    pack = build_pack(result, bundle)
    log.record_decision(pack)
    st.metric("Confidence", f"{result.confidence_score:.3f}", result.confidence_band)
    st.warning(f"human_review_required = {result.human_review_required} → {bundle.oversight_pathway}")
    st.json(pack["regulatory_mapping"]["DSA Art 17 — statement of reasons"])

with steps[3]:
    st.subheader("Retrieve a prior decision by Evidence Pack ID; verify integrity")
    pid = st.text_input("Pack ID", st.session_state.get("pack_id", ""))
    if pid:
        try:
            stored = log.get_pack(pid)
            st.success(f"Integrity hash verifies: {verify_integrity(stored)}")
            st.json(stored)
        except KeyError:
            st.error("No Evidence Pack with that ID (run steps 2–3 first).")

with steps[4]:
    st.subheader("Change a threshold → bump version → prior decision unchanged")
    new_high = st.slider("High-band threshold (v0.2.0)", 0.80, 0.99, 0.95)
    data = copy.deepcopy(bundle.raw)
    data["policy_version"] = "0.2.0"
    data["bands"]["high"] = new_high
    v2 = bundle_from_dict(data)
    rec = records["judgment_illusion"]
    old, new = evaluate(rec, bundle), evaluate(rec, v2)
    col1, col2 = st.columns(2)
    col1.metric("v0.1.0", f"{old.confidence_score:.3f}", old.confidence_band)
    col2.metric("v0.2.0", f"{new.confidence_score:.3f}", new.confidence_band)
    st.info("Prior Evidence Packs still reference v0.1.0 and replay identically (GOV-2/4).")

with steps[5]:
    st.subheader("Plain-English explanation (AI Act Art 13)")
    rid = st.selectbox("Record", list(records))
    st.write(evaluate(records[rid], bundle))
    st.markdown(f"> {build_pack(evaluate(records[rid], bundle), bundle)['plain_english_explanation']}")
