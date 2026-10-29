# Source review

Status: **FAIL**

Complete responses: 0/1 chunks.
Source coverage: 0/20613 decoded characters.

Suggestions require independent verification; source code and repairs were never executed.

## Coverage

| File | Completed characters | All planned fragments completed |
|---|---:|---|
| mcp_server.py | 0/20613 | False |

## Unverified model suggestions

No suggestions were returned by completed chunks. Unfinished chunks remain unreviewed.

## Scope and limits

- COMPLETE means every scanned source fragment received a complete, valid model response; it does not certify full project understanding, bug freedom, or verified findings.
- Only the explicitly listed source extensions are scanned. Ignored directories, links, binary files, unreadable and oversized files are excluded; scan warnings retain those limits.
- UTF-8 bytes of the complete serialized request are used as a conservative planning token bound, with a protocol margin. This is not an actual model tokenizer or measured token usage, and model context support still requires provider validation.
- Chunks are reviewed independently. Cross-file and cross-chunk reasoning is limited; no claim of a single model simultaneously seeing the entire project is made.
- Compaction deduplicates structured suggestions and indexes existing evidence after review. It never summarizes away unread source and makes no measured token-saving claim.
- Known credentials are located in each complete source before chunking, then masked with equal-length stars while retaining line separators. Original decoded-text hashes and ranges identify the scanned snapshot; a redacted snapshot is not byte-for-byte original source.
- Model suggestions are not executed or independently proven. Hashes detect changes and do not authenticate a producer.

## Scan warnings

