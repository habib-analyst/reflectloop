# PREREG — reflectloop benchmark (locked before any benchmark run)

Locked: 2026-10-28, before the benchmark in `reflectloop.benchmark` was run at
full size. Smoke tests of mechanics (tiny n, checking the code executes) are
not measurements and do not count as runs.

## Design

- **Testbed.** Deterministic scripted tasks, pure Python stdlib, seeded RNG.
  Three task families, each generating concrete artefacts (plans, ledgers,
  deduction chains) that a scripted solver attempts and a scripted reflector
  revises. Fault injection is seeded; ground truth is checked against the
  artefact, never asserted.
  - `plan_repair` — multi-step plans checked against constraints. Reflection
    is a checklist re-plan. Expected: reflection mostly helps (local slips
    are detectable; correct plans are rarely broken).
  - `ledger_check` — multi-line ledgers with a partial checksum. Reflection
    is a recompute with different grouping. Expected: reflection helps
    moderately; a checksum-agreement signal is observable.
  - `chain_deduction` — chained deductions where each step conditions on the
    previous one. Reflection re-derives the chain but anchors on its own
    first-pass intermediates (self-agreement) and drifts. Expected:
    **reflection is harmful here by construction** — it rarely fixes wrong
    chains and often breaks right ones.
- **Observable features** (the only inputs any gate may use): self-reported
  confidence emitted by the solver (noisy), self-consistency between two
  cheap first-pass samples, artefact size (steps/lines), novelty flag,
  checksum/verifier-agreement flag where the family has one, family-internal
  difficulty proxy. Ground truth, fault type, and counterfactual outcomes are
  never features.
- **Counterfactual labelling.** Every task carries two seeded substreams so
  the no-reflect outcome and the reflect outcome are both well-defined for
  the same task instance. Arms are paired on identical tasks.
- **Calibration / test split.** Calibration: 900 tasks (300 per family),
  seed 20261028. Test: 1,500 tasks (500 per family), seed 20261029. The gate
  is fit on calibration only; all headline numbers are test-split.
- **Gate.** Two logistic models fit by full-batch gradient descent on
  calibration counterfactuals: P(reflection changes outcome fail→success)
  and P(reflection changes outcome success→fail). Predicted net benefit
  Δ̂ = P̂(fix) − P̂(break). Reflect iff Δ̂ > λ·(reflection cost), with the
  cost weight λ and the decision offset chosen on the calibration split to
  maximise calibration cost-adjusted success. No test-split tuning.

## Arms

1. `never` — never reflect.
2. `always` — reflect exactly once on every task.
3. `gated` — the calibrated benefit gate above.
4. `rawconf` (report-only baseline) — reflect iff solver self-reported
   confidence < threshold, threshold tuned on calibration. This is the
   Reflective Confidence (arXiv:2512.18605) trigger transplanted to the
   testbed; it is a comparison point, not a bar-bearing arm.

## Metrics

- **Cost**: first pass = 1.0 units; each reflection = +0.5 units.
- **Cost-adjusted success (CAS)** = mean over tasks of
  (1[final success] − 0.15 × total cost). The base cost is common to all
  arms, so arm differences come from success and reflection spend.
- **Raw success** = mean 1[final success].
- Reflection rate, per-family success/CAS, gate benefit-prediction AUC and
  calibration error on test (predicted Δ̂ vs realised Δ) are reported
  diagnostics.

## Pre-registered bars

- **B1 (primary, vs always-reflect):** CAS(gated) ≥ CAS(always) + 0.02.
- **B2 (primary, vs never-reflect):** raw success(gated) ≥ raw
  success(never) + 0.05.
- **B3 (harmful-family validity + guard):** on `chain_deduction`,
  success(always) < success(never) (the family really is reflection-harmful)
  AND success(gated) ≥ success(never) − 0.01 (the gate avoids the harm).
- **B4 (gate behaviour):** gate reflection rate on `chain_deduction` ≤ 0.25,
  while gate reflection rate on `plan_repair` ≥ 0.40 (the gate discriminates
  between families rather than collapsing to a single global rate).

If B1 or B2 fails, the headline claim fails and the paper reports the
negative result with the same prominence. B3's first clause failing means
the harmful family was mis-designed, which is also reported as-is.
