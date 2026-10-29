# Source review

Status: **COMPLETE**

Complete responses: 1/1 chunks.
Source coverage: 20613/20613 decoded characters.

Suggestions require independent verification; source code and repairs were never executed.

## Coverage

| File | Completed characters | All planned fragments completed |
|---|---:|---|
| mcp_server.py | 20613/20613 | True |

## Unverified model suggestions

- HIGH — mcp_server.py:173-176
  The method inspect_boundary compares the original input with itself (compare_messages(original, original)), which always yields a PASS status and discards the actual validation result, leading to incorrect verification of captured boundaries.
  This logic error can cause the server to accept invalid outputs as valid, undermining the safety guarantee of boundary verification.
  Suggested change: Replace the self‑comparison with a comparison against the baseline or expected input, e.g., compare_messages(original, baseline_original) where baseline is provided, or remove the unused variable and directly use the candidate comparison.
- HIGH — mcp_server.py:210-215
  In compare_recordings, the condition `if compare_messages(baseline["original_input"], baseline["original_input"])["status"] != "PASS":` always evaluates to false because a message compared with itself always passes, making the block that handles an unhealthy baseline dead code.
  The dead code masks potential errors in the baseline recording, preventing proper error reporting and leading to silent acceptance of an unhealthy baseline.
  Suggested change: Replace the self‑comparison with a check against a known unhealthy state or remove the condition; alternatively, pass the baseline's validation result from elsewhere and act on it.
- MEDIUM — mcp_server.py:25-38
  The _public_payload function only checks a limited set of credential patterns via regular expressions and may miss newly introduced or obfuscated credential formats, potentially allowing sensitive data to be processed.
  If a credential pattern bypasses detection, the WorkspaceError may not be raised, leading to accidental exposure of credentials in JSON payloads.
  Suggested change: Broaden credential detection to include additional common patterns (e.g., AWS session tokens, GCP metadata tokens) and consider using a more comprehensive secret‑detection library; also make the regex configurable.
- LOW — mcp_server.py:95-105
  Workspace.verdict performs a deepcopy of the entire JSON payload before mutating it, which can be expensive for large files and may cause high memory usage during processing.
  Repeated deepcopy operations on large payloads can degrade performance and increase GC pressure, especially when processing many recordings.
  Suggested change: Modify the function to work on a shallow copy or mutate a structured representation directly, only copying when necessary; or stream the JSON to avoid full in‑memory duplication.
- LOW — mcp_server.py:61-70
  Workspace.read catches generic OSError, UnicodeError, ValueError and re‑raises a generic WorkspaceError, losing the original exception context and making debugging of file‑related failures harder.
  Suppressing the original traceback can hinder root‑cause analysis in production environments.
  Suggested change: Re‑raise the original exception or include the original error message and traceback in the WorkspaceError to preserve debugging information.
- LOW — mcp_server.py:260-265
  The export_regression_gate method calls self.path(output_dir, new_directory=True) twice, overwriting the result and making the code harder to read; also the first call's return value is unused.
  Redundant calls reduce readability and may indicate a copy‑paste error; they also add unnecessary computation.
  Suggested change: Store the result of the first call in a variable and reuse it, or call the method once and assign the directory path directly.

## Scope and limits

- COMPLETE means every scanned source fragment received a complete, valid model response; it does not certify full project understanding, bug freedom, or verified findings.
- Only the explicitly listed source extensions are scanned. Ignored directories, links, binary files, unreadable and oversized files are excluded; scan warnings retain those limits.
- UTF-8 bytes of the complete serialized request are used as a conservative planning token bound, with a protocol margin. This is not an actual model tokenizer or measured token usage, and model context support still requires provider validation.
- Chunks are reviewed independently. Cross-file and cross-chunk reasoning is limited; no claim of a single model simultaneously seeing the entire project is made.
- Compaction deduplicates structured suggestions and indexes existing evidence after review. It never summarizes away unread source and makes no measured token-saving claim.
- Known credentials are located in each complete source before chunking, then masked with equal-length stars while retaining line separators. Original decoded-text hashes and ranges identify the scanned snapshot; a redacted snapshot is not byte-for-byte original source.
- Model suggestions are not executed or independently proven. Hashes detect changes and do not authenticate a producer.

## Scan warnings

