# ReviKnot compatibility evidence

Run: 79b4e41e-4294-41ad-8b2d-511ec721f9c4
Recorded: 2026-10-28T04:42:06.731014+00:00
Mode: recording-check

| Case | Verdict | Evidence |
|---|---|---|
| captured-boundary | FAIL | {'kind': 'User-supplied opt-in BoundaryRecorder transaction; no SDK is executed by this check', 'adapter': 'langchain-nvidia-ai-endpoints/convert_message_to_dict', 'version': '1.4.3', 'request_id': 'sdk-contract-1', 'recording_sha256': '2f18ab6a3759c7c1e129e08c7c2889c7af29a28e5e0d0389eb72a264437b895e', 'timestamps': {'input': '2026-10-28T04:42:06.387102+00:00', 'output': '2026-10-28T04:42:06.387102+00:00'}, 'event_indexes': [0, 1]} |

## Limitations

- Checks a selected captured message pair without executing an SDK or application.
- A saved recording and its checksums do not independently authenticate its producer.
- A future regression gate requires a freshly captured candidate trace or recording.
