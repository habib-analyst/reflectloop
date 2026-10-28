# KILLGATE — reflectloop (Agentic 12 Programme, P10)

**Verdict: PASS for the narrow re-scope only.** A generic reflection/self-critique
loop library would be a me-too and is killed by this gate. What survives is a
*measured study + reference implementation of calibrated benefit-gated
reflection*: reflect only when a benefit model, fit on a calibration split,
predicts reflection will help — evaluated against always-reflect and
never-reflect on deterministic scripted agent tasks, including one task family
where reflection is known-harmful.

Gate run: 2026-10-28. Searches: web + arXiv + PyPI (see below).

## Closest prior art, and why each does not occupy the narrow scope

1. **Reflective Confidence** (Zeng et al., arXiv:2512.18605, Dec 2025) — the
   closest hit. It triggers reflection *during decoding* when the model's raw
   intrinsic confidence (token probabilities) drops below a hand-set threshold,
   on single-chain math reasoning (AIME). Differences: (a) the trigger is raw
   confidence, not a calibrated prediction of reflection *benefit* — low
   confidence says the answer may be wrong, not that reflection will fix it or
   break it; (b) no always-reflect / never-reflect policy comparison and no
   cost-adjusted success metric; (c) no agent task loop and no task family
   where reflection is harmful. reflectloop's gate is fit on labelled
   counterfactual outcomes (reflect vs. not, on calibration tasks) and is
   evaluated exactly on those missing axes.

2. **MV-Debate** (arXiv:2508.05557) — "dynamic reflection gating" inside a
   multi-agent debate for multimodal harmful-content detection. The gate is a
   Top-k Δ-score rule over debate rounds (reflect when the observed score
   improvement is large), inside one task-specific pipeline. Not a calibrated
   pre-reflection benefit prediction, not a general agent reflection policy,
   no help/hurt analysis, no never-reflect arm.

3. **Reflexion** (Shinn et al., 2023), **Self-Refine** (Madaan et al., 2023),
   **CRITIC** (Gou et al., 2024) — always-reflect frameworks (on failure or
   unconditionally). No gating decision at all.

4. **Agent-Reflex** (arXiv:2610.17953), **Agent-R** — *training* frameworks
   that teach models to reflect. Different layer; no inference-time policy for
   when reflection is worth its cost.

5. **Kamoi et al.** (TACL 2024) and **Huang et al.** (ICLR 2024) — evidence
   that self-correction often *hurts* without external feedback. Motivation
   for this study, not a gating tool or a help/hurt policy evaluation.

6. **PyPI shelf**: `langgraph-reflection` (always-reflect critique loop),
   `ai-agentreflect` (learns AGENTS.md rules from failures), `reflective`
   (unrelated data library). No calibrated gating package exists.

## Differentiation from Habib's own assets (required by the brief)

- **loopguard** (habib-analyst/loopguard): *detection/recovery inside* a ReAct
  loop — semantic revisit detection, a cost-justified step budget, and forced
  dissimilar reflections once a loop is detected. loopguard always reflects
  when its detector fires; it never asks whether reflecting is a good idea on
  this task. reflectloop is the policy layer *above* that machinery: it
  decides, before any reflection happens, whether the expected benefit of
  reflecting on this task instance is positive. Complementary, not competing.

- **pausewise** (habib-analyst/pausewise): calibrated gating of a *human*
  pause — an error scorer predicts P(agent is wrong) and a cost-chosen
  threshold decides whether to interrupt a person. reflectloop borrows the
  calibration *method* (fit on labelled history, choose the operating point by
  explicit cost minimisation on the calibration split) but changes both the
  target variable and the intervention: the gate predicts the *net benefit of
  the reflection intervention itself* — P(reflect fixes it) − P(reflect breaks
  it) — and the intervention is the agent's own revision pass, not a human
  review. Predicting "am I wrong?" and predicting "will reflecting help?" are
  different questions; in the error-compounding family they give opposite
  answers, which is precisely what the benchmark measures.

## Scope that survives the gate

- A deterministic, scripted, stdlib-only testbed (no LLM calls): three task
  families, one of them designed so reflection is known-harmful (error
  compounding with self-anchoring).
- Three policy arms on identical tasks: never-reflect, always-reflect, and
  calibrated benefit-gated reflection; plus a report-only raw-confidence gate
  (the Reflective Confidence trigger) as the closest-prior-art baseline.
- Primary metric: cost-adjusted success. Secondary: raw success, reflection
  rate, per-family breakdowns, gate calibration quality.

If the pre-registered bars in PREREG.md fail, the honest negative result is
the deliverable — the build does not get re-scoped mid-flight to pass.
