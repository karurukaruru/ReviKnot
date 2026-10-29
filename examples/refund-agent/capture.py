"""Capture a controlled refund-agent boundary, without model or network calls.

This deliberately faulty application adapter illustrates a regression; it is
not an allegation about an untested SDK release or a real payment integration.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from patchcourt.recorder import BoundaryRecorder
from patchcourt.evidence import write_json


def messages():
    return [
        {"role": "system", "content": "Prepare a refund draft. Preserve tool IDs, currency, nested policy arguments and approval requirements. Never send money."},
        {"role": "user", "content": "For order R104, draft a refund for the unopened headset. 商品未拆封。"},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "order-R104", "type": "function", "function": {"name": "lookup_order", "arguments": json.dumps({"order_id": "R104", "include": {"line_items": True, "payment_credentials": False}})}},
            {"id": "policy-R104", "type": "function", "function": {"name": "check_return_policy", "arguments": json.dumps({"order_id": "R104", "item": "headset", "condition": {"opened": False}, "reason": "商品未拆封"}, ensure_ascii=False)}},
        ]},
        {"role": "tool", "tool_call_id": "order-R104", "content": json.dumps({"order_id": "R104", "currency": "EUR", "items": [{"sku": "headset", "quantity": 1, "unit_price_cents": 7990}, {"sku": "charger", "quantity": 2, "unit_price_cents": 2500}], "total_paid_cents": 12990})},
        {"role": "tool", "tool_call_id": "policy-R104", "content": json.dumps({"eligible": True, "item": "headset", "requires_human_approval": True})},
        {"role": "assistant", "content": json.dumps({"action": "refund_draft", "order_id": "R104", "currency": "EUR", "amount_cents": 7990, "requires_human_approval": True})},
    ]


def adapter(source, scenario):
    result = deepcopy(source)
    if scenario == "broken":
        result[2].pop("tool_calls")
    elif scenario == "corrupt":
        arguments = json.loads(result[2]["tool_calls"][1]["function"]["arguments"])
        arguments["condition"]["opened"] = 0  # Valid JSON, different semantic type.
        result[2]["tool_calls"][1]["function"]["arguments"] = json.dumps(arguments, ensure_ascii=False)
    elif scenario != "fixed":
        raise ValueError("Unknown controlled scenario")
    return result


def capture(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new output directory; prior evidence is preserved")
    output.mkdir(parents=True)
    source = messages()
    write_json(output / "input.json", source)
    verdicts = {}
    for scenario in ("broken", "fixed", "corrupt"):
        recorder = BoundaryRecorder("refund-application-adapter", "controlled-" + scenario)
        candidate, verdict = recorder.transform(source, lambda value: adapter(value, scenario), request_id="refund-R104")
        recorder.save(output / f"{scenario}.recording.json")
        write_json(output / f"{scenario}.messages.json", candidate)
        verdicts[scenario] = verdict
    assert [verdicts[n]["status"] for n in ("broken", "fixed", "corrupt")] == ["FAIL", "PASS", "FAIL"]
    report = {"kind": "controlled refund-agent application boundary", "scope": "Local synthetic data; no SDK installation, model request, customer data or payment execution.", "provider_requests": 0, "verdicts": verdicts}
    write_json(output / "capture-summary.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = capture(args.output)
    print(json.dumps({"status": "CAPTURED", "scenarios": {n: v["status"] for n, v in report["verdicts"].items()}, "provider_requests": 0}))


if __name__ == "__main__":
    main()
