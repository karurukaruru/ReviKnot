# ReviKnot compatibility evidence

Run: 6cbec315-d67a-444d-9c0a-7e461f8297b5
Recorded: 2026-10-27T10:41:21.823366+00:00
Mode: recording-check

| Case | Verdict | Evidence |
|---|---|---|
| captured-boundary | FAIL | {'kind': 'User-supplied opt-in BoundaryRecorder transaction; no SDK is executed by this check', 'adapter': 'langchain-nvidia-ai-endpoints/convert_message_to_dict', 'version': '1.4.3', 'request_id': 'sdk-contract-1', 'recording_sha256': 'c7c580577b6ee18772667282aa59b86c87bf6d383097e9c911a760414ad64550', 'timestamps': {'input': '2026-10-27T10:41:21.426175+00:00', 'output': '2026-10-27T10:41:21.426175+00:00'}, 'event_indexes': [0, 1]} |

## Limitations

- Checks a selected captured message pair without executing an SDK or application.
- A saved recording and its checksums do not independently authenticate its producer.
- A future regression gate requires a freshly captured candidate trace or recording.
