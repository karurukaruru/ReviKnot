# PatchCourt compatibility evidence

Run: a8110f44-e3cc-4d33-b043-583cfdb2601d
Recorded: 2026-10-26T08:38:01.836274+00:00
Mode: recording-check

| Case | Verdict | Evidence |
|---|---|---|
| captured-boundary | FAIL | {'kind': 'User-supplied opt-in BoundaryRecorder transaction; no SDK is executed by this check', 'adapter': 'langchain-nvidia-ai-endpoints/convert_message_to_dict', 'version': '1.4.3', 'request_id': 'sdk-contract-1', 'recording_sha256': 'dabd7e4b775952db376fc55e233c289b8accf54b2707fd5e2fc2550dd8f03615', 'timestamps': {'input': '2026-10-26T08:38:01.485102+00:00', 'output': '2026-10-26T08:38:01.485102+00:00'}, 'event_indexes': [0, 1]} |

## Limitations

- Checks a selected captured message pair without executing an SDK or application.
- A saved recording and its checksums do not independently authenticate its producer.
- A future regression gate requires a freshly captured candidate trace or recording.
