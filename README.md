# reflectloop

**Reflect only when reflection is predicted to help.**

Most agents reflect on a constant schedule (always) or on a raw confidence
threshold. Both ignore the actual decision: reflection is an intervention
that fixes some failures, breaks some successes, and always costs. reflectloop
fits a **calibrated benefit gate** on labelled history — two logistic models
predicting P(reflection fixes this) and P(reflection breaks this) — and
reflects only when the predicted net benefit clears a cost-chosen threshold.
Calibration method adapted from [pausewise](https://github.com/habib-analyst/pausewise);
the target variable is new: not "am I wrong?" but "will reflecting help?"

Pure Python standard library. No dependencies, no APIs, no cost.

## Measured results

Deterministic scripted testbed, 1,500 held-out tasks across three families,
all policies on identical tasks. Full data: `results.json`; method, bars and
limits: `PAPER.md`, `PREREG.md`.

| Policy | Success | Cost-adjusted success | Reflect rate |
|---|---|---|---|
| Never reflect | 0.533 | 0.383 | 0.00 |
| Always reflect | 0.710 | 0.485 | 1.00 |
| Raw-confidence gate (prior-art trigger) | 0.726 | 0.512 | 0.86 |
| **Benefit gate (reflectloop)** | **0.763** | **0.573** | **0.54** |

The testbed includes a family where reflection is *harmful by construction*
(chained deductions: re-derivation anchors on the agent's own intermediates).
There, always-reflect scores 0.494 against never-reflect's 0.618 — while the
benefit gate scores **0.638**, reflecting on only 19% of those tasks. The
raw-confidence gate still reflects on 65% of them and loses 6 points:
low confidence says "probably wrong", and on compounding tasks that is
exactly where reflection fails.

## Quickstart

```bash
python -m reflectloop        # runs the pre-registered benchmark, writes results.json
python -m pytest tests/ -q   # 8 tests
```

## Library use

```python
from reflectloop import BenefitGate, generate_tasks

calibration = generate_tasks(300, seed=20261028)   # your labelled history
gate = BenefitGate().fit(calibration)              # counterfactual outcomes required

for task in generate_tasks(500, seed=20261029):
    if gate.should_reflect(task):
        ...  # run your reflection pass
```

Fitting needs tasks with both outcomes known (reflect / no-reflect) — in
production that means logged A/B reflection decisions. The gate consumes
only observable features: reported confidence, self-consistency, artefact
size, novelty, and a family check signal.

## Honest limits

- The solver, reflector and fault taxonomy are **designed artefacts**; the
  numbers measure the gate under stated simulation rules, not any real
  LLM. The transferable claim is conditional: *if* reflection's fix/break
  rates vary predictably across tasks, a benefit gate dominates both
  always-reflect and confidence triggers at ~half the reflection spend.
- One reflection per task, binary outcomes, three families.
- Gate calibration is good mid-range, overconfident at the extreme bin.
- Kill-gate analysis against prior art (Reflective Confidence, MV-Debate,
  Reflexion) and sibling projects (loopguard, pausewise): `KILLGATE.md`.

## How it differs from loopguard and pausewise

- **loopguard** detects loops *inside* a run and always reflects when its
  detector fires. reflectloop sits above that: it decides whether
  reflecting is worth it on this task at all.
- **pausewise** gates a *human* pause on calibrated P(error). reflectloop
  gates the agent's *own* revision on predicted benefit of the
  intervention — which flips sign exactly where P(error) does not.
