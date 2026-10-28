import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reflectloop import BenefitGate, generate_tasks  # noqa: E402
from reflectloop.gate import BASE_FEATURES, feature_vector  # noqa: E402
from reflectloop.benchmark import run_benchmark  # noqa: E402
from reflectloop.tasks import FAMILIES  # noqa: E402


def test_generation_is_deterministic():
    a = generate_tasks(20, seed=123)
    b = generate_tasks(20, seed=123)
    assert len(a) == len(b) == 60
    for ta, tb in zip(a, b):
        assert ta.family == tb.family
        assert ta.features == tb.features
        assert ta.first_correct == tb.first_correct
        assert ta.reflect_correct == tb.reflect_correct


def test_balanced_families():
    tasks = generate_tasks(10, seed=7)
    for fam in FAMILIES:
        assert sum(1 for t in tasks if t.family == fam) == 10


def test_features_are_observables_only():
    for t in generate_tasks(5, seed=3):
        assert set(t.features.keys()) == set(BASE_FEATURES)
        for v in t.features.values():
            assert 0.0 <= v <= 1.0


def test_feature_vector_shape():
    t = generate_tasks(1, seed=3)[0]
    v = feature_vector(t)
    assert len(v) == 1 + len(BASE_FEATURES) + len(FAMILIES) - 1


def test_chain_family_reflection_is_harmful_on_average():
    tasks = [t for t in generate_tasks(200, seed=99)
             if t.family == "chain_deduction"]
    never = sum(t.first_correct for t in tasks) / len(tasks)
    always = sum(t.reflect_correct for t in tasks) / len(tasks)
    assert always < never


def test_plan_family_reflection_helps_on_average():
    tasks = [t for t in generate_tasks(200, seed=99)
             if t.family == "plan_repair"]
    never = sum(t.first_correct for t in tasks) / len(tasks)
    always = sum(t.reflect_correct for t in tasks) / len(tasks)
    assert always > never


def test_gate_fits_and_decides():
    calib = generate_tasks(50, seed=11)
    gate = BenefitGate().fit(calib)
    assert 0.0 <= gate.threshold <= 0.30
    for t in generate_tasks(5, seed=12):
        assert isinstance(gate.should_reflect(t), bool)
        assert -1.0 <= gate.delta_hat(t) <= 1.0


def test_benchmark_small_run_structure():
    res = run_benchmark(calib_n=40, test_n=60, calib_seed=5, test_seed=6)
    for arm in ("never", "always", "gated", "rawconf"):
        assert arm in res["arms"]
        assert 0.0 <= res["arms"][arm]["success"] <= 1.0
    assert res["arms"]["never"]["reflect_rate"] == 0.0
    assert res["arms"]["always"]["reflect_rate"] == 1.0
    assert set(res["prereg_bars"].keys()) == {
        "B1_gated_cas_beats_always_by_0.02",
        "B2_gated_success_beats_never_by_0.05",
        "B3a_chain_always_worse_than_never",
        "B3b_chain_gated_not_worse_than_never",
        "B4a_chain_gated_reflect_rate_le_0.25",
        "B4b_plan_gated_reflect_rate_ge_0.40",
    }
