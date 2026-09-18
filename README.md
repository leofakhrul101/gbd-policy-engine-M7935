# gbd-policy-engine

**Governance-by-Design Policy Engine**, the demonstration artefact for M7935
(LLM Law, Technology & Innovation, University of Strathclyde). It turns
obligations under the GDPR, the EU AI Act and the DSA into executable rules, and
writes one regulator-legible record for every decision it makes.

> **Not legal advice.** A readiness signal, not a determination that anyone has
> complied with anything. Synthetic data only. Re-authored clean for this
> dissertation; no code from any prior commercial work.

## Run it

```bash
pip install -e ".[dev,demo]"
pytest                      # 53 tests; each v0.2 test names the legal finding it operationalises
streamlit run demo/app.py   # 6-step supervisor walkthrough
```

**No install needed.** Open `docs/demo.html` in any browser — the engine is ported to
JavaScript and runs locally, with no server and nothing to fetch. Move the signals and the
whole chain re-forms: the six risk dimensions, the accumulated risk, the sealed 14-field
Evidence Pack with its SHA-256 digest, blind-first review, and the Commission export. A
"tamper" control alters one character of the record so you can watch the seal fail.

That port was checked field-for-field and hash-for-hash against this Python implementation
across 1,152 signal combinations; all 1,152 matched, including the digests and the UUIDv5 pack
identifiers. It is the same engine, not an illustration of it.

`docs/walkthrough.html` is the earlier v0.1.0 walkthrough, kept as the *before* exhibit.
`examples/` holds four v0.1.0 packs for the same reason — see `APPENDIX-four-edge-cases.md`.

## What it does, and what it does not

It does not listen to music. It takes what a distributor already knows about a
submission (how many parties claim ownership, how strongly the audio matches an
existing recording, how old the account is, whether it declares AI use), applies
a versioned policy, reaches one of four bounded outcomes, and writes a sealed
Evidence Pack recording how it got there.

Detection is an input assumption, not something this artefact performs. The legal
question begins after the signals arrive.

## Architecture, five layers

| Layer | Where | What |
|---|---|---|
| 1 · Regulatory Norm | `norms/norms.yaml` | OSCOLA-citable records for GDPR Arts 5/22/24, AI Act Arts 13/14, DSA Arts 14/17/20, each with a mechanisability verdict |
| 2 · Policy Translation | `policies/v0.2.0.yaml` (+ JSON Schema) | Versioned rules, each carrying its full Norm-to-Control chain, plus the outcome thresholds, required signals and the controller approval block |
| 3 · Decision Logic | `src/gbd/engine.py` | Pure, deterministic. Produces an outcome and a confidence score |
| 4 · Evidence Pack | `src/gbd/evidence_pack.py` | One 14-field, SHA-256-hashed record per decision |
| 5 · Governance & Provenance | `src/gbd/audit_log.py` | Append-only SQLite log; any prior policy version reconstructable and replayable |

Two modules attach to the sealed record rather than to the decision logic. Both
read a decision; neither can remake one.

| Module | What |
|---|---|
| `src/gbd/review.py` | Blind-first human review. The engine's proposed outcome has no accessor until the reviewer has committed their own; the sealed review record carries reviewer identity, AGREE or OVERRIDE, and time to decision |
| `src/gbd/export.py` | Projection onto the Commission's DSA statement-of-reasons schema. Refuses to export where no ground is present; the ground reference is never null |

## What v0.2 added, and why

Each change answers a finding in the dissertation's legal analysis, and each has
a test that names the finding it operationalises (`tests/test_v02.py`).

- **Sealed norm references.** Every triggered rule carries its `norm_refs` inside
  the hashed payload, so the rule-to-norm link cannot drift from the decision.
  A mapping table written afterwards is compliance by document, which is the
  thing this artefact argues against. DSA Art 17(3)(d)–(e).
- **Two-limb automation record.** `automated_detection` and `automated_decision`
  are recorded separately, as Art 17(3)(c) and the Commission's own schema
  require.
- **Safe state.** A missing required signal routes to REVIEW rather than
  producing a confident ALLOW from absent evidence. AI Act Art 14(4)(e),
  recital 73.
- **Blind-first review.** Withholding the engine's proposal until the reviewer
  commits makes agreement a measurement rather than an assertion — the only
  answer available to SCHUFA's "draws strongly" test and to the rubber-stamping
  literature.
- **Notice-triggered re-entry.** An Art 16 notice re-opens a prior decision,
  including an ALLOW, and the new decision names the one it supersedes.
- **Controller approval.** The policy bundle carries the controller's sign-off,
  which is what keeps the vendor a processor on EDPB 07/2020 para 84.
- **Commission export.** Every required field populates from the sealed pack
  alone, and the ground reference is never null — the field the Transparency
  Database shows as empty in 99.9% of 131 million records.

`docs/CHANGES-v0.2.md` records the four defects closed in v0.2.1 and why each
mattered legally.

## Outcomes and confidence are separate

The engine produces a **bounded workflow outcome**: `ALLOW`, `REVIEW`,
`QUARANTINE` or `REJECT`. It also produces a **confidence score**. These answer
different questions and are deliberately kept apart.

`R` is the sum of triggered risk-rule weights, clamped to 1.0. The outcome comes
from thresholds on `R` set in the policy bundle. The confidence score is
`|1 - 2R|`, which describes how sure the system is about the *assessment*, not
about the outcome. `R = 0` is confidently clean, `R = 1` is confidently
concerning, and `R` near 0.5 is genuine uncertainty.

So a `REJECT` issued at 0.9 confidence is still not a legal determination. The
statement of reasons that accompanies it carries no legal ground, because the
engine cannot supply one. That separation is the boundary thesis.

## Where the human sits

Not in front of every upload, which does not scale. Behind the outcomes that
actually affect someone.

| Outcome | Adverse to the uploader | Solely automated | Intervention |
|---|---|---|---|
| `ALLOW` | no | yes | not engaged, no adverse effect |
| `REVIEW` | yes | no | before the decision takes effect |
| `QUARANTINE` | yes | yes | after the fact, via the oversight pathway |
| `REJECT` | yes | yes | after the fact, via the oversight pathway |

This is GDPR Art 22 read by decision class rather than across the pipeline.
"Solely" attaches to the individual decision, and Art 22(3) requires intervention
to be *obtainable*, not to precede every item. A rule carrying
`forces_human_review` overrides the threshold entirely: contested ownership goes
to a person whatever the score says.

Which outcomes may be reached on automation alone is read from the bundle
(`gated_outcomes`), not hardcoded, because it is a legal question and therefore
has to be a versioned, auditable control.

## Norm-to-Control, two worked examples

**Legal Norm -> Obligation -> Control Objective -> System Rule -> Evidence Output**

### DSA Art 17, statement of reasons

| Stage | Content |
|---|---|
| Norm | Art 17(1): a clear and specific statement of reasons for any restriction |
| Obligation | Art 17(3)(a) to (f): action taken, facts relied on, whether automated means were used, legal or contractual ground with an explanation, redress route |
| Control objective | Every decision emits a structured, automation-disclosing statement of reasons |
| System rule | `RULE_STATEMENT_OF_REASONS` (condition: always) populates the statement block in every pack |
| Evidence output | The statement block inside `regulatory_mapping`, plus the plain-English explanation |

The block carries `quality_flag_17_4`. A pack can satisfy every minimum content
requirement in 17(3) and still fail the 17(4) standard, which asks for a
statement that is clear, easily comprehensible and as precise as reasonably
possible in the circumstances. The engine marks a statement `specific`, `thin` or
`informational` by counting the facts it relied on, which is a structural proxy
for a question about quality. It flags the gap; it cannot close it. That gap is
the dissertation's central argument.

### GDPR Art 22, automated decisions

| Stage | Content |
|---|---|
| Norm | Art 22(1): no decision based solely on automated processing with significant effect. Art 22(3): human intervention obtainable |
| Obligation | Contested-ownership outcomes are significant for the affected artist |
| Control objective | Never let a contested submission reach an outcome on automation alone |
| System rule | `RULE_OWNERSHIP_CONFLICT` adds risk weight **and** forces `REVIEW`; `RULE_HUMAN_REVIEW_ROUTING` records the routing |
| Evidence output | `decision_outcome`, `solely_automated` and `intervention_point` in every pack |

## What the engine deliberately does not do

Each of these is a decision, not a gap.

- **No legal-ground determination** (Art 17(3)(d)). That subparagraph wants the
  ground *and an explanation of why the content is illegal on it*. That is legal
  characterisation, not rule evaluation. The field is left `null` with a note
  rather than filled with something that would read like a legal conclusion.
- **No detection.** No fingerprinting, no audio analysis, no ML. Building it
  would move the argument onto detection quality, which is a different question
  and not the one this project asks.
- **No real data.** Synthetic records only, so no personal data is processed and
  no ethical approval is engaged.
- **SHA-256, not PKI.** Integrity is what the legal argument needs. A hash proves
  the record has not been altered. It does not prove who wrote it, which would
  need signing keys and a key-management story the argument does not turn on.
- **No platform integrations.** Where the engine would sit in a real ingestion
  pipeline is an architecture question, and the controller/processor analysis
  does not turn on the answer.

Where a norm resists mechanisation the code says so, in
`norms.yaml -> mechanisability`. Those are findings, not bugs, and they feed the
critique chapter.

## Repo status

`norms.yaml`: all 8 records carry completed doctrinal analysis, being the
obligation, its application to upload-time triage, a mechanisability verdict and
a critique hook. DSA Arts 14, 17 and 20 and AI Act Art 14 are verified against
the OJ text. GDPR Arts 5, 22 and 24 and AI Act Art 13 are drafted and awaiting
that check.
