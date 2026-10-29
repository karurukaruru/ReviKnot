"""Synthetic evidence exercises configurable export limits, never inference."""
import pytest

from tests.test_submission_check import checker, update_report, workflow


def renamed_final_turn(tmp_path):
    folder, report = workflow(tmp_path)
    row = next(r for r in report["requests"] if r["name"] == "task-turn-2")
    (folder / "task-turn-2.json").rename(folder / "task-turn-5.json")
    row.update(name="task-turn-5", evidence_file="task-turn-5.json")
    return folder, report


def test_export_honors_declared_tool_turn_limit(tmp_path):
    folder, report = renamed_final_turn(tmp_path)
    report["limits"] = {"max_model_requests": 16, "max_proposal_attempts": 3, "max_tool_turns": 8}
    update_report(folder, report)
    checker.verify_workflow(tmp_path, "evidence/workflow/report.json", competition=True)


def test_export_retains_legacy_bound_without_an_explicit_configuration(tmp_path):
    folder, report = renamed_final_turn(tmp_path)
    update_report(folder, report)
    with pytest.raises(ValueError, match="request evidence name"):
        checker.verify_workflow(tmp_path, "evidence/workflow/report.json", competition=True)


@pytest.mark.parametrize("value", [True, 0, -1, 10001, "16"])
def test_export_rejects_invalid_declared_request_limits(tmp_path, value):
    folder, report = workflow(tmp_path)
    report["limits"] = {"max_model_requests": value}
    update_report(folder, report)
    with pytest.raises(ValueError, match="invalid request limits"):
        checker.verify_workflow(tmp_path, "evidence/workflow/report.json", competition=True)
