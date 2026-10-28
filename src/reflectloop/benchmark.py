"""Benchmark: never / always / calibrated-gated / raw-confidence reflection
on identical scripted tasks. Writes results.json; checks PREREG bars."""

from __future__ import annotations

import json

from .gate import (BenefitGate, RawConfidenceGate, COST_FIRST, COST_REFLECT,
                   CAS_WEIGHT)
from .tasks import FAMILIES, generate_tasks

CALIB_N = 300        # per family (PREREG)
TEST_N = 500         # per family (PREREG)
CALIB_SEED = 20261028
TEST_SEED = 20261029


def _run_arm(tasks, decide):
    """decide(task) -> bool: reflect? Returns (success, cas, reflect_rate)."""
    succ = 0.0
    cas = 0.0
    refs = 0
    for t in tasks:
        reflect = decide(t)
        ok = t.reflect_correct if reflect else t.first_correct
        cost = COST_FIRST + (COST_REFLECT if reflect else 0.0)
        succ += 1.0 if ok else 0.0
        cas += (1.0 if ok else 0.0) - CAS_WEIGHT * cost
        refs += 1 if reflect else 0
    n = len(tasks)
    return succ / n, cas / n, refs / n


def _auc(scores, labels):
    """Rank AUC with tie handling; labels are 0/1."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for p in pos:
        for q in neg:
            if p > q:
                wins += 1.0
            elif p == q:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def run_benchmark(calib_n=CALIB_N, test_n=TEST_N,
                    calib_seed=CALIB_SEED, test_seed=TEST_SEED) -> dict:
    calib = generate_tasks(calib_n, calib_seed)
    test = generate_tasks(test_n, test_seed)

    gate = BenefitGate().fit(calib)
    raw = RawConfidenceGate().fit(calib)

    arms = {
        "never": lambda t: False,
        "always": lambda t: True,
        "gated": gate.should_reflect,
        "rawconf": raw.should_reflect,
    }

    results = {
        "protocol": {
            "calib_n_per_family": calib_n,
            "test_n_per_family": test_n,
            "calib_seed": calib_seed,
            "test_seed": test_seed,
            "cost_first": COST_FIRST,
            "cost_reflect": COST_REFLECT,
            "cas_weight": CAS_WEIGHT,
            "gate_threshold_on_delta_hat": gate.threshold,
            "rawconf_threshold_on_confidence": raw.threshold,
        },
        "arms": {},
        "per_family": {},
        "gate_diagnostics": {},
    }

    for name, decide in arms.items():
        s, c, r = _run_arm(test, decide)
        results["arms"][name] = {
            "success": round(s, 4),
            "cas": round(c, 4),
            "reflect_rate": round(r, 4),
        }
        fam_out = {}
        for fam in FAMILIES:
            sub = [t for t in test if t.family == fam]
            fs, fc, fr = _run_arm(sub, decide)
            fam_out[fam] = {
                "success": round(fs, 4),
                "cas": round(fc, 4),
                "reflect_rate": round(fr, 4),
            }
        results["per_family"][name] = fam_out

    # gate diagnostics: does delta_hat predict the realised benefit?
    deltas = [gate.delta_hat(t) for t in test]
    realised = [
        (1 if t.reflect_correct else 0) - (1 if t.first_correct else 0)
        for t in test
    ]
    benefit_label = [1 if d > 0 else 0 for d in realised]
    harm_label = [1 if d < 0 else 0 for d in realised]
    # calibration of delta_hat: mean realised delta within prediction bins
    bins = {}
    for dh, rd in zip(deltas, realised):
        b = round(dh * 5) / 5
        bins.setdefault(b, []).append(rd)
    cal_curve = {
        str(b): {"n": len(v), "mean_realised_delta": round(sum(v) / len(v), 4)}
        for b, v in sorted(bins.items())
    }
    results["gate_diagnostics"] = {
        "auc_benefit": round(_auc(deltas, benefit_label), 4),
        "auc_harm_avoidance": round(_auc([-d for d in deltas], harm_label), 4),
        "mean_abs_delta_error": round(
            sum(abs(dh - rd) for dh, rd in zip(deltas, realised)) / len(test),
            4),
        "delta_calibration_bins": cal_curve,
    }

    a = results["arms"]
    pf = results["per_family"]
    bars = {
        "B1_gated_cas_beats_always_by_0.02":
            a["gated"]["cas"] >= a["always"]["cas"] + 0.02,
        "B2_gated_success_beats_never_by_0.05":
            a["gated"]["success"] >= a["never"]["success"] + 0.05,
        "B3a_chain_always_worse_than_never":
            pf["always"]["chain_deduction"]["success"]
            < pf["never"]["chain_deduction"]["success"],
        "B3b_chain_gated_not_worse_than_never":
            pf["gated"]["chain_deduction"]["success"]
            >= pf["never"]["chain_deduction"]["success"] - 0.01,
        "B4a_chain_gated_reflect_rate_le_0.25":
            pf["gated"]["chain_deduction"]["reflect_rate"] <= 0.25,
        "B4b_plan_gated_reflect_rate_ge_0.40":
            pf["gated"]["plan_repair"]["reflect_rate"] >= 0.40,
    }
    results["prereg_bars"] = bars
    results["prereg_all_pass"] = all(bars.values())
    return results


def main():
    results = run_benchmark()
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
