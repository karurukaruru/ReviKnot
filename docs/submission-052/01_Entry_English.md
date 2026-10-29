# PatchCourt — English entry copy

**Review draft, 26 October 2026. Not submitted.** This is the description supported by the current development evidence. It deliberately does not claim completed Nebius/NVIDIA inference. Before entering the competition, replace the platform paragraph with the verified final result and complete the separate link/field worksheet. The current 0.5.2 revision is local; earlier public 0.5.1 links do not publish it.

The copy below starts at “Project name” and ends at “Built With”. These headings are editorial sections, not a claim that the authenticated Devpost form has exactly these fields or accepts these lengths.

---

**Project name:** PatchCourt — AI Agent Compatibility Guardian

**Tagline:** Turn silent agent regressions into evidence and reusable CI tests.

**Track:** Coding and Agentic Engineering

## Inspiration

The tools ran. The next model request forgot them.

An SDK adapter can silently drop tool-call identifiers, arguments or images while producing valid Python and valid JSON. A successful installation does not tell an agent developer whether the next step still means the same thing. PatchCourt makes that hidden message contract visible, then asks a proposed repair to prove itself.

## What it does

PatchCourt helps developers investigate changes at an agent-to-SDK message boundary. It compares the original messages with the actual serialized candidate, shows the missing meaning and produces an evidence report. It distinguishes preserved behavior, detected defects, unsupported input and cases requiring review.

Its practical workflow continues after diagnosis. A developer can explicitly capture an adapter transaction and export a standalone CI gate for that same input. The saved broken candidate fails the gate; a later captured candidate must preserve the frozen input and adapter identity. The generated test includes the reviewed checker source and license and runs with Python’s standard library. It checks supplied captured data; it does not secretly execute or authenticate a future SDK.

The repair workflow asks a model for a bounded field mapping. Independent checks test the mapping, a deliberate corruption must be rejected, and a real development-model conversation uses two fixed local inventory tools. The saved successful development workflow recovers the checked result **21**. Model-generated Python is never executed.

## How we built it

The product combines a Python semantic comparator, opt-in transaction recording, a local HTML workbench, portable regression exports and source/environment-scoped evidence. A reused repair must pass verification again. A persistent request ledger reserves attempts before transport, so failed requests remain visible in the budget and evidence trail.

The examples reproduce credited historical defects in LangChain NVIDIA tool-call serialization and CrewAI/Gemini image formatting. Separately executed upgrade runs use two real installed NVIDIA SDK releases with shared dependency pins. Each output is checked against the original input: two identically broken releases produce **NEEDS_REVIEW**, not a compatibility pass.

Version 0.5.2 was exercised with actual **DeepSeek Flash** requests and **Tavily** retrieval of allowlisted official documentation. The initial workflow passed with three model requests and 4,094 reported tokens. An exact-match reuse run skipped the proposal request, revalidated all eight checks, rejected the corrupted repair and completed the tool task again: two model requests and 655 reported tokens. Those are two observed runs, not a general savings estimate. Their reports are retained under `evidence/development-052`.

The separate evaluation retained a **PARTIAL** outcome because the second original-ACV baseline response was incomplete. The direct-model and Tavily-assisted arms each matched 18 of 24 scheduled case outcomes across two repetitions of the same 12 developer-authored cases. This did not demonstrate a retrieval improvement, and it is not an independent held-out benchmark. Earlier GLM experiments and unsuccessful attempts retain their original labels. These development runs do not establish competition-required platform use.

The subsequent v2 protocol clarifies the OpenAI/LangChain normalization contract and decision order, retains the same frozen cases and labels, and makes the output budget configurable. Those code changes do not imply a measured v2 live result; the recorded v1 PARTIAL remains intact.

The intended competition path uses an NVIDIA Nemotron model served by **Nebius Token Factory** to propose the bounded repair and participate in the real tool conversation. At this review checkpoint, that final inference has not executed because usable Nebius access is still pending. Discovery, SDK execution and another provider’s completion are separate evidence categories.

## Challenges and accomplishments

The hardest part was defining what deserves a pass. Equal outputs can share a defect. Redacted evidence can hide a difference. A plausible repair can be wrong. An HTTP success code cannot establish that a tool-call contract survived.

PatchCourt therefore preserves failed attempts, source and environment identity, request records, independent controls and explicit scope. The captured-input gate makes a discovered problem reusable in a developer’s own CI. Connection recovery in the workbench retrieves the existing run state instead of prompting an accidental second inference request.

## Who it is for and why it matters

The intended users are agent developers evaluating an SDK upgrade or investigating a failed tool conversation. They need a small reproducible contract, an inspectable explanation and a regression test they can keep. PatchCourt demonstrates that workflow on reviewed adapters and a controlled application capture. It does not claim production adoption, universal framework coverage or a measured reduction in incidents.

## What we learned and what comes next

Compatibility is a contract about meaning, not just matching package outputs. Model assistance becomes more useful when a separate verifier can reject it and the rejected attempts remain inspectable.

The next work is final Nebius/NVIDIA execution and broader reviewed application boundaries. Arbitrary repository instrumentation, automatic production patching and a general vision-task guarantee are outside this build. Preserving image bytes demonstrates serialization behavior, not a successful live vision task.

## Existing work and attribution

PatchCourt builds on Agent Code Validator v0.2.0, which predates the competition. Its original scanner, bounded read-only tools, CLI and MIT license are retained. Competition-period additions include semantic boundary checks, historical reproductions, installed-SDK comparisons, bounded repair verification, actual development-model tool workflows, transaction capture, portable CI gates and the evidence workbench. `COMPETITION_CHANGELOG.md` in the source archive records the changes.

The historical defects are credited to LangChain NVIDIA issue #387 and CrewAI issue #8434. We do not present them as new discoveries. Upstream source and attribution are retained under their applicable licenses.

## Built With

Python; HTML/CSS/JavaScript; Agent Code Validator; LangChain NVIDIA AI Endpoints; CrewAI; Google GenAI types; DeepSeek Flash development inference; Tavily official-document retrieval; GLM 5.3 Flash historical development evidence; ASM-derived evidence and revalidation conventions.

---

## Finalization notes — do not paste as completed claims

1. After a real verified run, replace the pending-platform paragraph with the **exact NVIDIA model ID**, Nebius Token Factory’s actual role, the completed result and the evidence location. Add those technologies to Built With only after execution.
2. Current development facts were checked against the saved 0.5.2 initial/reuse reports and evaluation `benchmark.json`. Preserve the PARTIAL evaluation and original records if a later run follows; do not silently relabel it as success.
3. Review the final public source/test-build links, YouTube URL, feedback and actual field limits using `05_Form_Fields_表单填写.md`.
4. The exact published revision, free judge-access arrangement and final video are still open. No remote update or video production is authorized by this document.
5. The separate `review-source` workflow has passed local acceptance: complete scanned-source planning, per-chunk coverage, deterministic result compaction, an 8192 default answer ceiling and configurable application limits. A credential-free real development test covered 63833 characters in two responses; final redaction safeguards were subsequently verified offline. The older `acv agent` and `acv review` modes retain their original bounded behavior. See SOURCE_REVIEW.md and RELEASE_REVIEW_052_ZH.md; do not claim 100000 actual input tokens were measured.
