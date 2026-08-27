from src.evaluation.cases_task1 import build_task1_cases
from src.evaluation.cases_task2 import build_task2_cases
from src.evaluation.runner import run_evaluation


def test_task1_cases_have_minimum_five_plus_adversarial():
    cases = build_task1_cases()
    assert len(cases) >= 6
    assert any("adversarial" in c["id"] for c in cases)


def test_task2_cases_have_minimum_five_plus_adversarial():
    cases = build_task2_cases()
    assert len(cases) >= 6
    assert any("adversarial" in c["id"] for c in cases)


def test_full_evaluation_run_produces_scored_report():
    report = run_evaluation()
    assert 0.0 <= report["task1"]["aggregate_score"] <= 1.0
    assert 0.0 <= report["task2"]["aggregate_score"] <= 1.0
    assert 0.0 <= report["overall_score"] <= 1.0
    assert report["task1"]["total_count"] == len(build_task1_cases())
    assert report["task2"]["total_count"] == len(build_task2_cases())
    # No case is silently hidden -- every case has a pass/fail state.
    for case in report["task1"]["cases"] + report["task2"]["cases"]:
        assert "passed" in case
        assert "score" in case
