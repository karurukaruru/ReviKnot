"""CLI integration keeps full-source planning free and real requests budgeted."""
import io
import json
from unittest.mock import patch

from patchcourt import providers
from patchcourt.cli import main


def test_source_cli_dry_run_and_explicit_large_output_use_the_same_budget_path(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    source = tmp_path / "small.py"
    source.write_text("def total(items):\n    return sum(items)\n", encoding="utf-8")
    credential = tmp_path / "local.env"
    credential.write_text("DEEPSEEK_API_KEY=synthetic-source-cli-key\n", encoding="utf-8")
    ledger = tmp_path / "budget.json"
    common = ["review-source", str(source), "--context-tokens", "100000", "--max-output-tokens", "65536"]
    with patch.object(providers, "_transport") as transport, patch("sys.stdout", new_callable=io.StringIO):
        assert main(common + ["--dry-run", "--output", str(tmp_path / "plan")]) == 0
        transport.assert_not_called()
    assert not ledger.exists()
    assert json.loads((tmp_path / "plan/report.json").read_text("utf-8"))["status"] == "PLANNED"

    body = {"model": "deepseek-flash", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": "[]"}}], "usage": {"total_tokens": 20}}
    with patch.dict("os.environ", {}, clear=True), patch.object(providers, "_transport", return_value=(
            200, {}, json.dumps(body))) as transport, patch("sys.stdout", new_callable=io.StringIO) as output:
        assert main(["--env-file", str(credential)] + common + ["--budget", str(ledger),
                    "--output", str(tmp_path / "review")]) == 0
        assert transport.call_count == 1
        assert transport.call_args.args[2]["max_tokens"] == 65536
    state = json.loads(ledger.read_text("utf-8"))
    assert len(state["reservations"]) == 1
    assert state["reservations"][0]["max_tokens"] == 65536
    report = json.loads((tmp_path / "review/report.json").read_text("utf-8"))
    assert report["status"] == "COMPLETE" and report["all_scanned_fragments_completed"]
    assert "synthetic-source-cli-key" not in output.getvalue()


def test_source_cli_refuses_unbudgeted_requests_before_creating_output(tmp_path):
    source = tmp_path / "small.py"
    source.write_text("print('data only')\n", encoding="utf-8")
    output = tmp_path / "unbudgeted"
    with patch.object(providers, "request") as request, patch("sys.stderr", new_callable=io.StringIO) as error:
        assert main(["review-source", str(source), "--output", str(output)]) == 2
        request.assert_not_called()
    assert "--budget" in error.getvalue()
    assert not output.exists()
