# When Should an Agent Reflect? A Calibrated Benefit Gate, Measured

**reflectloop** — Agentic 12 Programme, P10. Habib Ur Rehman, 2026-10-28.
Status: pre-registered benchmark, all bars passed (PREREG.md, results.json).
Testbed is deterministic and scripted; no LLM was called. Read the limits
section before citing anything.

## The question

Reflection is usually wired into agents as a constant: always critique and
revise (Reflexion, Self-Refine), or trigger on a raw confidence threshold
(Reflective Confidence, arXiv:2512.18605). Both skip the actual decision
problem. Reflection is an *intervention* with a cost and two-sided effects:
it fixes some failures and breaks some successes (Kamoi et al., TACL 2024;
Huang et al., ICLR 2024). The deployable question is not "is the agent
probably wrong?" but "**will reflecting on this task help, in expectation,
by more than it costs?**"

reflectloop answers that with the calibration method from pausewise —
fit on labelled history, choose the operating point by explicit cost —
pointed at a different target variable: the net benefit of reflection
itself, Δ = P(reflect fixes it) − P(reflect breaks it), predicted from
observables available before reflecting.

## Testbed

Three deterministic scripted task families (900 calibration / 1,500 test
tasks, disjoint seeds; both counterfactual outcomes fixed per task from
separate seeded substreams, so arms are paired):

| Family | Reflection mechanism | Design expectation |
|---|---|---|
| plan_repair | checklist re-plan | helps: local slips detectable, correct plans rarely broken |
| ledger_check | recompute, different grouping | helps moderately; printed checksum is an observable signal |
| chain_deduction | re-derive, anchored on own intermediates | **harms**: slips survive anchoring, drift breaks correct chains |

Observables (the only gate inputs): solver-reported confidence,
self-consistency across resamples, artefact size, novelty flag, and a
family check signal (solver checklist flags / checksum agreement /
final-step spot re-check). Fault type and outcomes are never features.

## Arms

never-reflect; always-reflect (once); the calibrated benefit gate (two
logistic models for P(fix) and P(break) fit on calibration counterfactuals,
threshold on Δ̂ chosen on calibration to maximise cost-adjusted success);
and a report-only raw-confidence gate — the Reflective Confidence trigger
transplanted to this testbed, threshold also tuned on calibration.

Cost model: first pass 1.0 units, reflection +0.5. Cost-adjusted success
(CAS) = success − 0.15 × cost per task, averaged.

## Results (test split, n = 1,500)

| Arm | Success | CAS | Reflect rate |
|---|---|---|---|
| never | 0.533 | 0.383 | 0.00 |
| always | 0.710 | 0.485 | 1.00 |
| raw-confidence gate | 0.726 | 0.512 | 0.86 |
| **benefit gate** | **0.763** | **0.573** | **0.54** |

Per family (success, never / always / gated):

| Family | never | always | gated | gated reflect rate |
|---|---|---|---|---|
| plan_repair | 0.680 | 0.788 | **0.804** | 0.42 |
| ledger_check | 0.302 | 0.848 | **0.848** | 1.00 |
| chain_deduction | 0.618 | 0.494 | **0.638** | 0.19 |

Pre-registered bars: **all pass.** B1: gated CAS beats always by +0.088
(bar +0.02). B2: gated success beats never by +0.230 (bar +0.05). B3: on
chain_deduction always-reflect is 12.4 points *worse* than never (the
harm is real), while the gate is 2.0 points *better* than never — it
reflects on only 19% of chain tasks and still finds the fixable minority.
B4: gate reflect rates discriminate by family (0.19 chain vs 0.42 plan;
the plan bar of ≥ 0.40 passed narrowly, by 2 points).

Gate quality: Δ̂ predicts realised benefit with AUC 0.907 and harm with
AUC 0.846; mean |Δ̂ − Δ| = 0.29. Predicted-vs-realised Δ by bin is
monotone through the mid-range (bin −0.2 → −0.23 realised; bin 0.6 →
+0.77) and overconfident at the extreme bin (Δ̂ ≈ 1.0, n = 18, realised
+0.50).

## The contrast that matters

The raw-confidence gate is not useless — it beats always-reflect on CAS
(0.512 vs 0.485) by skipping some hopeless reflections. But it reflects on
65% of chain_deduction tasks and loses 6 points there against
never-reflecting (0.558 vs 0.618), because low confidence identifies
"probably wrong", and on compounding chains "probably wrong" is exactly
where reflection anchors and fails, while "probably right" is where it
drifts and breaks. A benefit model separates those cases; a confidence
threshold cannot, because the sign of reflection's effect is not a
function of confidence alone.

## Limits — read before citing

1. **Scripted simulation.** The solver, reflector, and fault taxonomy are
   designed artefacts with stated ground rules (tasks.py docstring). The
   numbers measure the *gate's* behaviour under those rules, not any real
   LLM's reflection behaviour. The claim that transfers is narrow: when
   reflection's fix/break rates vary by task type and are predictable from
   observables, a calibrated benefit gate dominates both always-reflect and
   confidence triggers, at roughly half the reflection spend. Whether real
   LLM reflection has this predictable structure is an empirical question
   this testbed does not answer.
2. **Counterfactual labels are free here and expensive in production.**
   Fitting the gate needs labelled reflect/no-reflect outcomes. In a real
   deployment those come from logged A/B reflection decisions, which this
   study assumes away.
3. **One reflection, binary outcome, three families.** No iterated
   reflection, no partial credit, no open-ended tasks.
4. Calibration is good in the mid-range and overconfident at the extreme
   bin (small n). The threshold choice (Δ̂ > 0.02) came from the
   calibration split per protocol; no test-split tuning was done.

## Relation to prior work

Reflexion / Self-Refine: always-reflect arms of this study. Reflective
Confidence (arXiv:2512.18605): the raw-confidence arm; it gates on
P(wrong)-adjacent signal during decoding, without a benefit model or a
help/hurt comparison. MV-Debate (arXiv:2508.05557): Δ-score gating inside
one debate pipeline. loopguard (sibling project): detection/recovery
inside a loop — it always reflects when its detector fires; reflectloop is
the policy layer that decides whether reflecting is worth it at all.
pausewise (sibling project): the same calibration method gating a human
pause on P(error); reflectloop gates self-reflection on predicted benefit
of the intervention, which flips sign exactly where P(error) does not.
Full gate analysis: KILLGATE.md.
