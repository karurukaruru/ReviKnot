# A refund-agent upgrade check

This is a controlled application-boundary example with two tool calls, nested
arguments, Unicode, currency, line items and a human-approval requirement. It
does not connect to customers or payment systems. The deliberate application
bug is not presented as an untested SDK defect.

```sh
python examples/refund-agent/capture.py --output outputs/refund-example
```

The broken candidate loses two tool-call IDs; the reviewed candidate preserves
the original contract; the corrupted candidate silently changes `false` to`0`.
ReviKnot must produce FAIL/PASS/FAIL. This tests preservation of the captured
message contract, not correctness of a refund business policy.

Connect the local MCP server, then ask the coding agent to check these captures
before merging an adapter change. MCP use and trigger guidance: [MCP.md](../../MCP.md).
