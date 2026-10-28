"""Deterministic scripted task families for the reflectloop testbed.

Each family generates a concrete artefact (a plan, a ledger, a deduction
chain), runs a scripted solver over it with seeded fault injection, and runs
a scripted reflector whose behaviour depends on the family's fault taxonomy.
Both counterfactual outcomes (no-reflect and reflect) are fixed at generation
time from separate seeded substreams, so policy arms are paired on identical
tasks.

Ground rules of the simulation (stated, not hidden):

- plan_repair: reflection is a checklist re-plan. It reliably repairs local
  slips, rarely repairs misconception faults (the reflector shares the
  solver's wrong constraint model), and rarely breaks a correct plan.
- ledger_check: reflection is a recompute with different grouping. It fixes
  most single-line slips; a printed partial checksum gives an observable
  agreement signal.
- chain_deduction: reflection re-derives the chain but anchors on the
  solver's own recorded intermediates, so early slips survive reflection,
  while re-derivation drift breaks some correct chains. Reflection is
  harmful in this family by construction (PREREG bar B3 checks this).

Observable features never include ground truth, fault type, or outcomes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

FAMILIES = ("plan_repair", "ledger_check", "chain_deduction")


@dataclass
class Task:
    family: str
    features: dict
    first_correct: bool
    reflect_correct: bool
    detail: dict = field(default_factory=dict)


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# --------------------------------------------------------------------------
# plan_repair
# --------------------------------------------------------------------------

def _gen_plan_repair(rng: random.Random) -> Task:
    n_steps = rng.randint(5, 10)
    steps = [f"s{i}" for i in range(n_steps)]
    # precedence constraints over the gold order
    constraints = []
    for _ in range(n_steps):
        a = rng.randrange(n_steps - 1)
        b = rng.randrange(a + 1, n_steps)
        constraints.append((steps[a], steps[b]))
    gold = list(steps)

    fault_roll = rng.random()
    if fault_roll < 0.38:
        fault = "none"
    elif fault_roll < 0.78:
        fault = "slip"
    else:
        fault = "misconception"

    plan = list(gold)
    if fault == "slip":
        i = rng.randrange(n_steps - 1)
        plan[i], plan[i + 1] = plan[i + 1], plan[i]
    elif fault == "misconception":
        # solver optimises for a phantom constraint and drops a real one:
        # rotate a segment, which breaks most precedence constraints it hits
        i = rng.randrange(n_steps - 2)
        plan[i:i + 3] = reversed(plan[i:i + 3])

    def valid(p):
        pos = {s: k for k, s in enumerate(p)}
        return all(pos[a] < pos[b] for a, b in constraints)

    first_correct = valid(plan)

    # reflector: checklist re-plan
    reflect_correct = first_correct
    if not first_correct and fault == "slip":
        reflect_correct = rng.random() < 0.85  # checklist catches local slips
    elif not first_correct and fault == "misconception":
        reflect_correct = rng.random() < 0.10  # shared wrong model
    elif first_correct:
        reflect_correct = rng.random() >= 0.04  # rare over-edit

    # --- observable features ---
    novelty = 1.0 if rng.random() < 0.3 else 0.0
    # solver self-consistency: slips are unstable across resamples,
    # misconceptions are stable (same wrong model), correct plans stable.
    if fault == "slip":
        consistency = rng.uniform(0.3, 0.65)
    elif fault == "misconception":
        consistency = rng.uniform(0.75, 0.98)
    else:
        consistency = rng.uniform(0.8, 1.0)
    difficulty = n_steps / 10.0
    confidence = _clip(0.72 - 0.25 * difficulty
                       - (0.18 if fault == "slip" else 0.05 if fault else 0.0)
                       + rng.uniform(-0.12, 0.12))
    # solver's own quick check flags some violated constraints, imperfectly
    pos = {s: k for k, s in enumerate(plan)}
    violated = sum(1 for a, b in constraints if pos[a] > pos[b])
    flags = violated if rng.random() < 0.7 else max(0, violated - 1)

    features = {
        "confidence": confidence,
        "consistency": consistency,
        "size": difficulty,
        "novelty": novelty,
        "signal": min(1.0, flags / 3.0),  # checklist flags raised by solver
    }
    return Task("plan_repair", features, first_correct, reflect_correct,
                {"fault": fault, "violated": violated})


# --------------------------------------------------------------------------
# ledger_check
# --------------------------------------------------------------------------

def _gen_ledger_check(rng: random.Random) -> Task:
    n_lines = rng.randint(6, 14)
    amounts = [rng.randint(-900, 900) for _ in range(n_lines)]
    true_total = sum(amounts)
    # printed partial checksum: sum of even-index lines mod 9 (observable)
    checksum = sum(amounts[::2]) % 9

    slip_roll = rng.random()
    if slip_roll < 0.34:
        fault = "none"
        slips = []
    elif slip_roll < 0.82:
        fault = "single_slip"
        slips = [rng.randrange(n_lines)]
    else:
        fault = "double_slip"
        slips = rng.sample(range(n_lines), 2)

    reported = list(amounts)
    for i in slips:
        reported[i] += rng.choice([-1, 1]) * rng.randint(3, 60)
    solver_total = sum(reported)
    first_correct = solver_total == true_total
    solver_checksum = sum(reported[::2]) % 9
    checksum_agree = 1.0 if solver_checksum == checksum else 0.0

    # reflector: recompute with different grouping
    reflect_correct = first_correct
    if not first_correct:
        p_fix = 0.88 if fault == "single_slip" else 0.55
        reflect_correct = rng.random() < p_fix
    elif first_correct:
        reflect_correct = rng.random() >= 0.05  # rare fresh slip

    novelty = 1.0 if rng.random() < 0.3 else 0.0
    if fault == "none":
        consistency = rng.uniform(0.85, 1.0)
    elif fault == "single_slip":
        consistency = rng.uniform(0.55, 0.85)
    else:
        consistency = rng.uniform(0.35, 0.65)
    difficulty = n_lines / 14.0
    confidence = _clip(0.74 - 0.22 * difficulty
                       - (0.10 if fault else 0.0)
                       + rng.uniform(-0.12, 0.12))
    features = {
        "confidence": confidence,
        "consistency": consistency,
        "size": difficulty,
        "novelty": novelty,
        "signal": checksum_agree,  # printed checksum matches solver subtotal
    }
    return Task("ledger_check", features, first_correct, reflect_correct,
                {"fault": fault})


# --------------------------------------------------------------------------
# chain_deduction (reflection harmful by construction)
# --------------------------------------------------------------------------

def _gen_chain_deduction(rng: random.Random) -> Task:
    n_steps = rng.randint(5, 9)
    x = rng.randint(2, 20)
    true_val = x
    ops = []
    for _ in range(n_steps):
        op = rng.choice(["+a", "*2", "-b", "+c"])
        val = rng.randint(1, 9)
        ops.append((op, val))
        if op == "+a" or op == "+c":
            true_val += val
        elif op == "*2":
            true_val *= 2
        else:
            true_val -= val

    # solver executes; an early slip compounds through later steps
    slip_at = -1
    if rng.random() < 0.36:
        slip_at = rng.randrange(max(1, n_steps - 2))  # early/mid slip
    solver_val = x
    for k, (op, val) in enumerate(ops):
        if op == "+a" or op == "+c":
            solver_val += val
        elif op == "*2":
            solver_val *= 2
        else:
            solver_val -= val
        if k == slip_at:
            solver_val += rng.choice([-1, 1]) * rng.randint(2, 7)
    first_correct = solver_val == true_val

    # reflector anchors on the solver's recorded intermediates: an existing
    # slip survives; a clean chain can be broken by re-derivation drift.
    reflect_correct = first_correct
    if not first_correct:
        reflect_correct = rng.random() < 0.10  # anchoring: rarely fixed
    else:
        reflect_correct = rng.random() >= 0.24  # drift breaks ~1 in 4

    novelty = 1.0 if rng.random() < 0.3 else 0.0
    # step agreement between two solver passes: slips are localised, so most
    # intermediates still agree even on failed chains (weak signal)
    if first_correct:
        consistency = rng.uniform(0.85, 1.0)
    else:
        consistency = rng.uniform(0.6, 0.9)
    difficulty = n_steps / 9.0
    confidence = _clip(0.76 - 0.2 * difficulty
                       - (0.06 if not first_correct else 0.0)
                       + rng.uniform(-0.12, 0.12))
    # the only cheap check in this family is re-deriving the final step from
    # the recorded intermediate; slips are early, so it passes either way and
    # is nearly uninformative -- which is the honest situation here.
    last_step_ok = (slip_at != n_steps - 1)
    signal = 1.0 if (rng.random() < (0.9 if last_step_ok else 0.3)) else 0.0
    features = {
        "confidence": confidence,
        "consistency": consistency,
        "size": difficulty,
        "novelty": novelty,
        "signal": signal,  # final-step spot re-check (weak; no verifier)
    }
    return Task("chain_deduction", features, first_correct, reflect_correct,
                {"fault": "slip" if slip_at >= 0 else "none",
                 "slip_at": slip_at})


_GENERATORS = {
    "plan_repair": _gen_plan_repair,
    "ledger_check": _gen_ledger_check,
    "chain_deduction": _gen_chain_deduction,
}


def generate_tasks(n_per_family: int, seed: int) -> list:
    """Generate a balanced, deterministic task set."""
    tasks = []
    for fam in FAMILIES:
        rng = random.Random(f"{seed}:{fam}")
        for _ in range(n_per_family):
            tasks.append(_GENERATORS[fam](rng))
    rng = random.Random(f"{seed}:shuffle")
    rng.shuffle(tasks)
    return tasks
