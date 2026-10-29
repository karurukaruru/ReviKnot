"""Model-content recovery must match live acceptance; HTTP envelopes stay strict."""
import json

import pytest

from tests.test_submission_check import checker, update_report, workflow, write


def replace_content(folder, report, name, transform):
    path = folder / (name + ".json")
    record = checker.read_json(path)
    message = record["response"]["choices"][0]["message"]
    message["content"] = transform(message["content"])
    record["raw_response"] = json.dumps(record["response"])
    write(path, record)
    next(row for row in report["requests"] if row["name"] == name)["evidence_sha256"] = checker.digest(record)
    update_report(folder, report)


@pytest.mark.parametrize("name", ["repair-proposal-1", "task-turn-2"])
@pytest.mark.parametrize("wrapper", [lambda value: "```json\n" + value + "\n```",
                                     lambda value: "The complete result is:\n" + value + "\nDone."])
def test_export_accepts_same_single_wrapped_model_json_as_live(tmp_path, name, wrapper):
    folder, report = workflow(tmp_path)
    replace_content(folder, report, name, wrapper)
    checker.verify_workflow(tmp_path, "evidence/workflow/report.json", competition=True)


@pytest.mark.parametrize("name", ["repair-proposal-1", "task-turn-2"])
@pytest.mark.parametrize("bad", [lambda value: value + "\n{}",
                                 lambda value: '{"bad":' + value,
                                 lambda value: value[:-1] + ',"sku":"duplicate","sku":"duplicate"}'])
def test_export_rejects_ambiguous_or_malformed_model_containers(tmp_path, name, bad):
    folder, report = workflow(tmp_path)
    replace_content(folder, report, name, bad)
    with pytest.raises(ValueError):
        checker.verify_workflow(tmp_path, "evidence/workflow/report.json", competition=True)


def test_http_envelope_does_not_gain_model_wrapper_recovery(tmp_path):
    folder, report = workflow(tmp_path)
    path = folder / "repair-proposal-1.json"
    record = checker.read_json(path)
    record["raw_response"] = "```json\n" + record["raw_response"] + "\n```"
    write(path, record)
    report["requests"][0]["evidence_sha256"] = checker.digest(record)
    update_report(folder, report)
    with pytest.raises(ValueError):
        checker.verify_workflow(tmp_path, "evidence/workflow/report.json", competition=True)
