"""Calibrated benefit gating for reflection.

The gate predicts the *net benefit of reflecting* on a task instance:

    delta_hat(x) = P_hat(reflect changes fail -> success | x)
                 - P_hat(reflect changes success -> fail | x)

Two logistic models are fit on calibration counterfactuals (both outcomes
are known for calibration tasks by construction of the testbed). The
decision threshold on delta_hat is chosen on the calibration split to
maximise calibration cost-adjusted success. This is the pausewise
calibration method (fit on labelled history; operating point chosen by
explicit cost) with a different target: not P(agent is wrong), but the
expected effect of the reflection intervention itself.

Pure stdlib; full-batch gradient descent; fully deterministic.
"""

from __future__ import annotations

import math

from .tasks import FAMILIES

BASE_FEATURES = ("confidence", "consistency", "size", "novelty", "signal")
COST_FIRST = 1.0
COST_REFLECT = 0.5
CAS_WEIGHT = 0.15


def feature_vector(task) -> list:
    feats = [1.0]  # intercept
    feats.extend(task.features[k] for k in BASE_FEATURES)
    for fam in FAMILIES[1:]:  # one-hot, first family is the reference
        feats.append(1.0 if task.family == fam else 0.0)
    return feats


def _sigmoid(z: float) -> float:
    if z < -35:
        return 0.0
    if z > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


class LogisticModel:
    """Minimal deterministic logistic regression (full-batch GD)."""

    def __init__(self, n_features: int):
        self.w = [0.0] * n_features
        self.mean = [0.0] * n_features
        self.std = [1.0] * n_features

    def fit(self, X: list, y: list, iters: int = 2000, lr: float = 0.1,
            l2: float = 1e-3):
        n = len(X)
        d = len(X[0])
        for j in range(1, d):  # standardise non-intercept columns
            col = [row[j] for row in X]
            m = sum(col) / n
            var = sum((c - m) ** 2 for c in col) / n
            self.mean[j] = m
            self.std[j] = math.sqrt(var) if var > 1e-12 else 1.0
        Xs = [[row[0]] + [(row[j] - self.mean[j]) / self.std[j]
                          for j in range(1, d)] for row in X]
        w = [0.0] * d
        for _ in range(iters):
            grad = [0.0] * d
            for row, yi in zip(Xs, y):
                p = _sigmoid(sum(wj * xj for wj, xj in zip(w, row)))
                err = p - yi
                for j in range(d):
                    grad[j] += err * row[j]
            for j in range(d):
                w[j] -= lr * (grad[j] / n + l2 * w[j])
        self.w = w
        return self

    def predict(self, x: list) -> float:
        xs = [x[0]] + [(x[j] - self.mean[j]) / self.std[j]
                       for j in range(1, len(x))]
        return _sigmoid(sum(wj * xj for wj, xj in zip(self.w, xs)))


class BenefitGate:
    """Reflect iff predicted net benefit of reflecting clears a threshold
    chosen on the calibration split by cost-adjusted success."""

    def __init__(self):
        self.fix_model = None
        self.break_model = None
        self.threshold = 0.0

    def fit(self, calib_tasks: list):
        X = [feature_vector(t) for t in calib_tasks]
        y_fix = [1 if (not t.first_correct and t.reflect_correct) else 0
                 for t in calib_tasks]
        y_break = [1 if (t.first_correct and not t.reflect_correct) else 0
                   for t in calib_tasks]
        d = len(X[0])
        self.fix_model = LogisticModel(d).fit(X, y_fix)
        self.break_model = LogisticModel(d).fit(X, y_break)
        # choose the operating point on calibration CAS (PREREG protocol)
        best_tau, best_cas = 0.0, float("-inf")
        for k in range(0, 31):
            tau = k * 0.01
            cas = self._cas(calib_tasks, tau)
            if cas > best_cas:
                best_cas, best_tau = cas, tau
        self.threshold = best_tau
        return self

    def delta_hat(self, task) -> float:
        x = feature_vector(task)
        return self.fix_model.predict(x) - self.break_model.predict(x)

    def should_reflect(self, task) -> bool:
        return self.delta_hat(task) > self.threshold

    def _cas(self, tasks, tau) -> float:
        total = 0.0
        for t in tasks:
            reflect = self.delta_hat(t) > tau
            success = t.reflect_correct if reflect else t.first_correct
            cost = COST_FIRST + (COST_REFLECT if reflect else 0.0)
            total += (1.0 if success else 0.0) - CAS_WEIGHT * cost
        return total / len(tasks)


class RawConfidenceGate:
    """Report-only baseline: reflect iff self-reported confidence is below
    a threshold tuned on calibration (the Reflective Confidence trigger,
    arXiv:2512.18605, transplanted to this testbed)."""

    def __init__(self):
        self.threshold = 1.0

    def fit(self, calib_tasks: list):
        best_tau, best_cas = 1.0, float("-inf")
        for k in range(40, 101, 2):
            tau = k * 0.01
            total = 0.0
            for t in calib_tasks:
                reflect = t.features["confidence"] < tau
                success = t.reflect_correct if reflect else t.first_correct
                cost = COST_FIRST + (COST_REFLECT if reflect else 0.0)
                total += (1.0 if success else 0.0) - CAS_WEIGHT * cost
            cas = total / len(calib_tasks)
            if cas > best_cas:
                best_cas, best_tau = cas, tau
        self.threshold = best_tau
        return self

    def should_reflect(self, task) -> bool:
        return task.features["confidence"] < self.threshold
