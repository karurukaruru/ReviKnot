"""Independent malformed-response checks; all transports are synthetic."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from patchcourt import providers
from patchcourt.budget import RequestBudget
from patchcourt.evidence import read_json
from patchcourt.live_workflow import run_live_workflow
from patchcourt.reasoning import run_reasoning
from tests.test_patchcourt_provider_workflows import NEMOTRON, model_replies


def valid_replies():
    values = model_replies(providers.DEEPSEEK_MODEL)
    for value in values:
        choice = value["response"]["choices"][0]
        choice["message"].setdefault("role", "assistant")
        choice["finish_reason"] = "tool_calls" if choice["message"].get("tool_calls") else "stop"
    return values


class ProviderContractReviewTests(unittest.TestCase):
    def test_reasoning_large_output_is_explicit_and_is_not_silently_clamped(self):
        proposal = {"hypothesis": "synthetic", "test_cases": [], "repair_proposals": [], "citations": []}
        for provider, model, credential in (("deepseek", providers.DEEPSEEK_MODEL, "DEEPSEEK_API_KEY"),
                                            ("nebius", NEMOTRON, "NEBIUS_API_KEY")):
            response = {"status": "PASS", "provenance": "synthetic", "response": {
                "model": model, "choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps(proposal)}}]}}
            for maximum in (None, 65536):
                with self.subTest(provider=provider, maximum=maximum), patch.dict(
                        "os.environ", {credential: "synthetic-key"}, clear=True), patch.object(
                        providers, "request", return_value=response) as request:
                    kwargs = {} if maximum is None else {"max_output_tokens": maximum}
                    result = run_reasoning("full boundary source", {}, provider=provider, model=model, **kwargs)
                expected = 8192 if maximum is None else maximum
                self.assertEqual(request.call_args.args[1]["max_tokens"], expected)
                inputs = json.loads(request.call_args.args[1]["messages"][1]["content"])
                self.assertEqual(inputs["source"], "full boundary source")
                self.assertFalse(result["source_scope"]["truncated"])
                self.assertEqual(result["limits"]["max_output_tokens"], expected)

    def test_large_boundary_source_or_invalid_output_stops_before_any_paid_request(self):
        with patch.dict("os.environ", {"NEBIUS_API_KEY": "synthetic-key", "TAVILY_API_KEY": "synthetic-key"}, clear=True), patch.object(
                providers, "request") as inference, patch.object(providers, "search_docs") as search, patch.object(
                providers, "discover_models") as discovery:
            for source, evidence in (("a" * 16001, {}), ("中" * 12000, {}), ("short", {"evidence": "x" * 32000})):
                with self.subTest(characters=len(source)):
                    result = run_reasoning(source, evidence, use_tavily=True)
                    self.assertEqual(result["status"], "BLOCKED")
                    self.assertIn("review-source", result["reason"])
                    self.assertFalse(result["source_scope"]["truncated"])
                    self.assertEqual(result["source_scope"]["included_source_characters"], 0)
            for maximum in (0, True, 65537, "8192"):
                with self.subTest(maximum=maximum), self.assertRaises(ValueError):
                    run_reasoning("small boundary", {}, max_output_tokens=maximum)
            inference.assert_not_called()
            search.assert_not_called()
            discovery.assert_not_called()

    def test_more_output_headroom_does_not_turn_a_truncated_reply_into_success(self):
        response = {"status": "PASS", "provenance": "synthetic", "response": {
            "model": providers.DEEPSEEK_MODEL, "choices": [{"finish_reason": "length", "message": {
                "role": "assistant", "content": '{"hypothesis":"incomplete"'}}]}}
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "synthetic-key"}, clear=True), patch.object(
                providers, "request", return_value=response) as request:
            result = run_reasoning("boundary", {}, provider="deepseek", max_output_tokens=65536)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("Incomplete model response", result["reason"])

    def test_workflow_rejects_role_refusal_and_inconsistent_tool_finish(self):
        for mutation in ("role", "refusal", "tool-stop", "final-tool-finish"):
            values = valid_replies()
            if mutation == "role": values[-1]["response"]["choices"][0]["message"]["role"] = "user"
            if mutation == "refusal": values[-1]["response"]["choices"][0]["message"]["refusal"] = "refused"
            if mutation == "tool-stop": values[1]["response"]["choices"][0]["finish_reason"] = "stop"
            if mutation == "final-tool-finish": values[-1]["response"]["choices"][0]["finish_reason"] = "tool_calls"
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder, patch.object(
                providers, "request", side_effect=values):
                root = Path(folder) / "run"
                result = run_live_workflow(root, provider="deepseek")
                self.assertEqual(result["status"], "INCONCLUSIVE")
                self.assertTrue((root / "manifest.json").exists())

    def test_malformed_usage_never_prevents_final_report_and_manifest(self):
        for usage in ("not-an-object", {"total_tokens": None}, {"total_tokens": True}):
            values = valid_replies()
            values[0]["usage"] = usage
            with self.subTest(usage=usage), tempfile.TemporaryDirectory() as folder, patch.object(
                providers, "request", side_effect=values):
                root = Path(folder) / "run"
                result = run_live_workflow(root, provider="deepseek")
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["total_reported_tokens"], 20)
                self.assertEqual(result["requests_missing_token_usage"], 1)
                self.assertTrue((root / "manifest.json").exists())

    def test_budget_exhaustion_is_a_preserved_failed_attempt_without_retry(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(providers, "request", side_effect=valid_replies()) as transport:
            root = Path(folder) / "run"
            with RequestBudget(Path(folder) / "budget.json", model_calls=1).applied():
                result = run_live_workflow(root, provider="deepseek")
            self.assertEqual(result["status"], "INCONCLUSIVE")
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(len(result["requests"]), 2)
            self.assertEqual(result["requests"][-1]["status"], "FAIL")
            failed = read_json(root / result["requests"][-1]["evidence_file"])
            self.assertIn("budget exhausted", failed["reason"])

    def test_nebius_schema_rejection_is_retained_without_fallback_or_retry(self):
        failed = {"status": "FAIL", "provenance": "synthetic HTTP attempt", "http_status": 400,
            "reason": "Provider HTTP error", "raw_response": '{"error":"json_schema unsupported"}'}
        with patch.dict("os.environ", {"NEBIUS_API_KEY": "synthetic-key"}, clear=True), patch.object(
            providers, "request", return_value=failed) as request:
            result = run_reasoning("adapter source", {}, provider="nebius", model=NEMOTRON)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["inference"], failed)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[1]["response_format"]["type"], "json_schema")

    def test_provider_reasoning_echo_cannot_mutate_the_verified_boundary_evidence(self):
        from patchcourt.semantic import compare_messages
        values, sent = valid_replies(), []
        values[1]["response"]["choices"][0]["message"]["reasoning_content"] = "synthetic provider-only metadata"
        def request(provider, payload):
            sent.append(deepcopy(payload))
            return values[len(sent) - 1]
        with tempfile.TemporaryDirectory() as folder, patch.object(providers, "request", side_effect=request):
            root = Path(folder) / "run"
            result = run_live_workflow(root, provider="deepseek")
            self.assertEqual(result["status"], "PASS")
            boundary = result["live_boundaries"][0]
            self.assertEqual(compare_messages(boundary["input"], boundary["repaired"])["status"], boundary["after"]["status"])
            self.assertNotIn("reasoning_content", boundary["repaired"][0])
            self.assertEqual(sent[-1]["messages"][-3]["reasoning_content"], "synthetic provider-only metadata")
            self.assertEqual(read_json(root / "task-turn-1.json")["response"]["choices"][0]["message"]["reasoning_content"],
                             "synthetic provider-only metadata")

    def test_reasoning_does_not_accept_a_proposal_with_tool_calls_or_wrong_role(self):
        proposal = {"hypothesis": "synthetic", "test_cases": [{"name": "control", "baseline": [],
            "candidate": [], "expected_status": "PASS"}], "repair_proposals": [], "citations": []}
        for field in ({"role": "user"}, {"tool_calls": [{"id": "unexpected"}]}, {"refusal": "refused"}):
            response = {"status": "PASS", "provenance": "synthetic", "response": {
                "model": providers.DEEPSEEK_MODEL, "choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps(proposal), **deepcopy(field)}}]}}
            with self.subTest(field=field), patch.dict("os.environ", {"DEEPSEEK_API_KEY": "synthetic-key"}, clear=True), patch.object(
                providers, "request", return_value=response):
                result = run_reasoning("source", {}, provider="deepseek")
            self.assertEqual(result["status"], "FAIL")

    def test_reasoning_wrapper_failure_returns_record_instead_of_losing_attempt(self):
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "synthetic-key"}, clear=True), patch.object(
            providers, "request", side_effect=ValueError("Experiment model_calls budget exhausted")) as request:
            result = run_reasoning("source", {}, provider="deepseek")
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("budget exhausted", result["inference"]["reason"])


if __name__ == "__main__":
    unittest.main()
