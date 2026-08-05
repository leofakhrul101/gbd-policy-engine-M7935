# gbd-policy-engine

**Governance-by-Design Policy Engine** — academic demonstration artefact for M7935
(LLM Law, Technology & Innovation, University of Strathclyde). Translates GDPR /
EU AI Act / DSA obligations into executable rules with regulator-legible evidence
output.

> **Not legal advice.** A readiness signal, not a determination of compliance.
> Synthetic data only. Re-authored clean for this dissertation; no code from any
> prior commercial work.

## Run it

```bash
pip install -e ".[dev,demo]"
pytest                      # full suite incl. threshold-boundary tests
streamlit run demo/app.py   # 6-step supervisor walkthrough
```

## Architecture — five layers

| Layer | Where | What |
|---|---|---|
| 1 · Regulatory Norm | `norms/norms.yaml` | OSCOLA-citable records for GDPR Arts 5/22/24, AI Act Arts 13/14, DSA Arts 14/17/20 |
| 2 · Policy Translation | `policies/v0.1.0.yaml` (+ JSON Schema) | Versioned rules, each carrying its full Norm-to-Control chain |
| 3 · Decision Logic | `src/gbd/engine.py` | Pure, deterministic confidence scoring — **no Allow/Reject exists** |
| 4 · Evidence Pack | `src/gbd/evidence_pack.py` | One 12-field, SHA-256-hashed, regulator-legible record per decision |
| 5 · Governance & Provenance | `src/gbd/audit_log.py` | Append-only SQLite log; any prior policy version reconstructable and replayable |

## Scoring semantics

`R` = sum of triggered risk-rule weights (clamped to 1.0).
`confidence_score = |1 − 2R|` — the system's confidence **in its own assessment**,
not a verdict. `R = 0` → confidently clean; `R = 1` → confidently concerning;
`R ≈ 0.5` → genuinely uncertain → **Human-Review-Required**. Bands come from
policy-defined thresholds; contested ownership forces human review regardless of
score (GDPR Art 22).

This shape is deliberate: the engine can be *confident* and still never
*adjudicate*. Confidence describes evidence quality; judgment stays human
(the boundary thesis).

## Norm-to-Control — two worked examples

The methodology this artefact demonstrates:
**Legal Norm → Obligation → Control Objective → System Rule → Evidence Output**

### Example 1 — DSA Art 17 (statement of reasons)

| Stage | Content |
|---|---|
| Norm | DSA Art 17: clear and specific statement of reasons for any restriction |
| Obligation | State action taken, facts relied on, automated means used, redress route (17(3)(a)–(f)) |
| Control objective | Every decision emits a structured, automation-disclosing statement of reasons |
| System rule | `RULE_STATEMENT_OF_REASONS` (condition: always) populates the statement block in every pack |
| Evidence output | `regulatory_mapping["DSA Art 17 — statement of reasons"]` + plain-English explanation |

The block also carries `quality_flag_17_1`: a pack can satisfy every structural
field of 17(3) and still be **thin** against 17(1)'s clear-and-specific standard.
The engine flags this; it cannot resolve it. That gap is the dissertation's
central argument.

### Example 2 — GDPR Art 22 (automated decisions)

| Stage | Content |
|---|---|
| Norm | GDPR Art 22: no solely automated decision with significant effect; human intervention available |
| Obligation | Contested-ownership outcomes are significant for the affected artist |
| Control objective | Never let a contested submission pass on automation alone |
| System rule | `RULE_OWNERSHIP_CONFLICT` adds risk weight **and** forces human review; `RULE_HUMAN_REVIEW_ROUTING` records the routing |
| Evidence output | `human_review_required` flag + `oversight_pathway` in every affected pack |

## What the engine deliberately does not do

- No Allow / Review / Quarantine / Reject. Ever.
- No legal-ground determination (DSA 17(3)(d)) — that is legal characterisation,
  left `null` with a note, by design.
- No real data, no ML, no PKI (SHA-256 only), no platform integrations.

Where a norm resists mechanisation, the code says so (`norms.yaml →
mechanisability`) — those honest failures feed the dissertation's critique
chapter; they are findings, not bugs.

## Repo status

`norms.yaml`: all 8 records carry completed doctrinal analysis — obligation,
applicability to upload-time triage, mechanisability verdict (what the code can
and cannot do), and a critique hook. DSA Art 17 is verified against the OJ text;
the other 7 are `drafted` pending that re-verification.
