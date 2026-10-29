# Source review

Status: **COMPLETE**

Complete responses: 2/2 chunks.
Source coverage: 63833/63833 decoded characters.

Suggestions require independent verification; source code and repairs were never executed.

## Coverage

| File | Completed characters | All planned fragments completed |
|---|---:|---|
| long_source_fixture.py | 63833/63833 | True |

## Unverified model suggestions

- MEDIUM — long_source_fixture.py:2902-2904
  mean_price divides by len(prices) without guarding against an empty list, causing ZeroDivisionError.
  Calling mean_price([]) raises ZeroDivisionError at runtime; the inline comment explicitly acknowledges the unsafe empty-list case, so any caller passing an empty collection will crash.
  Suggested change: Validate the input and raise a clear ValueError (or return None/0.0 per contract) when prices is empty, e.g. `if not prices: raise ValueError('prices must be non-empty')`.
- LOW — long_source_fixture.py:2696-2899
  A large hardcoded literal dictionary of ~200+ sku_XXXXX entries with cycling values is embedded directly in the module.
  This bulk data inflates the source file, is hard to review or diff, and mixes data with logic; any change requires editing code rather than a data file, and it obscures the actual functions in the module.
  Suggested change: Move the SKU data to an external data file (JSON/CSV) or generate it programmatically, and load it at runtime; keep the module focused on logic.
- LOW — long_source_fixture.py:2902-2904
  mean_price accepts any iterable but relies on sum() and len(), which fails for generators or one-shot iterators.
  If a caller passes a generator, len() raises TypeError; the function's implicit contract (a sized sequence) is undocumented, leading to surprising failures.
  Suggested change: Either document that a sized sequence is required, or materialize the input once (e.g. `prices = list(prices)`) before computing sum and length.
- INFO — long_source_fixture.py:2902-2904
  mean_price lacks a docstring and type hints, and the inline comment describes test intent rather than behavior.
  Without a documented contract (input type, empty-input behavior, return type), callers cannot know how to use it safely, and the comment referencing 'a review suggestion' is noise in production code.
  Suggested change: Add a docstring and type hints (e.g. `def mean_price(prices: Sequence[float]) -> float:`), and remove or replace the meta-comment with a description of the actual behavior.

## Scope and limits

- COMPLETE means every scanned source fragment received a complete, valid model response; it does not certify full project understanding, bug freedom, or verified findings.
- Only the explicitly listed source extensions are scanned. Ignored directories, links, binary files, unreadable and oversized files are excluded; scan warnings retain those limits.
- UTF-8 bytes of the complete serialized request are used as a conservative planning token bound, with a protocol margin. This is not an actual model tokenizer or measured token usage, and model context support still requires provider validation.
- Chunks are reviewed independently. Cross-file and cross-chunk reasoning is limited; no claim of a single model simultaneously seeing the entire project is made.
- Compaction deduplicates structured suggestions and indexes existing evidence after review. It never summarizes away unread source and makes no measured token-saving claim.
- Known credentials are redacted before transport. Original decoded-text hashes and ranges identify the scanned snapshot; a redacted snapshot is not byte-for-byte original source.
- Model suggestions are not executed or independently proven. Hashes detect changes and do not authenticate a producer.

## Scan warnings

