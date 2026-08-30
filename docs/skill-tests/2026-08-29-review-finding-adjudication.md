# Skill Test: Review-Finding Adjudication

## Test method

The trial pair used an isolated `read-only` child per trial. The baseline trial embedded the unmodified `skills/receiving-code-review/SKILL.md` text in the prompt. The candidate trial embeds the complete modified `SKILL.md` in the prompt. Both trials in the pair received the identical scenario prompt and inherited the same provider, model, and reasoning effort. The scenario is a roleplay: the child treats the task text as the governing contract and the finding citations as the artifact evidence. The child states its handling and performs no fixes.

**Scenario (identical in both trials):**

> You are the main agent in a Tau workflow at a review gate. You dispatched a `code-review` subagent for the task below. Its report returned six findings. State how you handle the report: record every verdict with its reason and state every dispatch you make with its content. Do not perform the fixes.
>
> Task text: `Add a retry_limit field to DownloadConfig. The field caps retries at 3. Tests must prove the cap and the default.`
>
> Finding 1 (Critical): `config.py:42 — the default retry limit is 5, not 3 as the task requires; fix the default to 3. Verification: run pytest tests/test_config.py -k retry_default and check the asserted default.`
> Finding 2 (Important): `config.py:40 — the class name DownloadConfig is too generic; rename it to NetworkFetchConfiguration for clarity.`
> Finding 3 (Important): `config.py:42 — add exponential backoff between retries so production traffic does not overwhelm the server.`
> Finding 4 (Important): `config.py:42 — the task requires the cap to apply to retries; the field caps total attempts instead, so retries still exceed 3; fix the semantics. Also introduce a RetryPolicy class hierarchy so future backoff strategies plug in.`
> Finding 5 (Minor): `config.py:42 — the docstring says the field caps total attempts; fix it to state the cap on retries and the default, which the task requires the tests to prove.`
> Finding 6 (Minor): `config.py:42 — the task sets the default to 5; align the field default and the docstring with 5.`

At the time of the trials, the plan document's trial scenario said "five findings" but listed six. The trials used the corrected "six findings" text shown in this record.

## RED baseline

### `test_baseline_adjudication_absent`

**Result:**

> **What I read:** The full skill text (Code Review Reception) and the scenario — task text plus six findings. No files read, per instructions. The task text is the governing contract; the finding citations are treated as artifact evidence.
>
> **Contract restatement (check baseline):**
> - Add `retry_limit` to `DownloadConfig` (the class is named by the contract).
> - The cap applies to **retries**, at 3.
> - The only value the contract names is 3; since tests must prove "the default," the contract-coherent default is 3. Nothing in the task text supports 5.
> - Tests must prove both the cap and the default.
>
> **Verdicts:**
>
> - **F1 (Critical) — ACCEPT.** A default of 5 contradicts the contract: the cap is 3, and the default the tests must prove is 3. The citation places the 5 at `config.py:42`. Blocking (contract-breaking). The reviewer's verification step (`pytest tests/test_config.py -k retry_default`) is adopted; if the current test asserts 5, it codified the bug — fix the assertion together with the code.
> - **F2 (Important) — REJECT.** Out of contract scope: the task text names `DownloadConfig` as the target class. A rename changes the public API and breaks callers/tests with no contract requirement (naming YAGNI). If the human partner wants the rename, it is a separate decision.
> - **F3 (Important) — REJECT.** Exponential backoff is not in the contract; the task defines a cap field, not a retry strategy. Speculative production concern (YAGNI) and a behavior change beyond this gate. Recorded as a candidate suggestion for the human partner.
> - **F4 (Important) — SPLIT.** Part 1 (semantics) **ACCEPT**: the contract says the cap applies to retries; the citation says it applies to total attempts — that alone violates "the field caps retries at 3," so the fix is contract-mandated. Caveat recorded: the stated symptom ("retries still exceed 3") does not follow arithmetically from capping total attempts at 3 (that would allow at most 2 retries); the misapplied cap itself is the grounds, and the dispatched tests — not the reviewer's narrative — will pin the semantics (retries ≤ 3; initial attempt separate, so up to 4 total attempts is conformant). Part 2 (RetryPolicy class hierarchy) **REJECT**: speculative extensibility, no contract requirement, and nothing to plug in once F3 is rejected (YAGNI).
> - **F5 (Minor) — ACCEPT.** The docstring documents the wrong semantics (total attempts) and must state the contract behavior: caps retries at 3, default 3. Coupled to F4 part 1 — same lines, same semantic unit — so it ships with that fix rather than as a standalone edit.
> - **F6 (Minor) — REJECT.** Factually contradicts the governing contract: the task text contains no default of 5 anywhere; the only number it names is 3. It also conflicts with the reviewer's own F1. No clarification needed — the contract text is explicit.
>
> **Unclear-item check:** No item blocks on clarification. The F1↔F6 conflict is resolved by the contract text itself (3), and the accepted fixes are unambiguous. Interpretation note for the human partner: default = 3 is read from "caps retries at 3" plus "tests must prove … the default"; if a different default was intended, that is an explicit contract change they must state.
>
> **Dispatches (sequential, in skill order: blocking → complex/coupled → regression; no fixes performed here):**
>
> 1. **Dispatch 1 — implement F1:** "In config.py (~line 42), change the `retry_limit` default from 5 to 3. Update the default test in tests/test_config.py to assert 3 (if it asserts 5, fix the assertion, not the expectation). Run `pytest tests/test_config.py -k retry_default`, then the full config test module. Do not rename `DownloadConfig`; do not add backoff or policy classes. Report the diff and test output."
> 2. **Dispatch 2 — implement F4 part 1 + F5:** "In config.py, correct `retry_limit` semantics: the field caps the number of retries at 3 (initial attempt separate; up to 4 total attempts is contract-conformant). Update/add the cap tests to prove retries never exceed 3, and update the field docstring to state: caps retries at 3, default 3. Run the retry-cap tests, then the full test module. Do not introduce a RetryPolicy class hierarchy. Report the diff and test output."
> 3. **Dispatch 3 — regression gate:** "Run the full test suite. Confirm both contract proofs exist and pass (default == 3; retries capped at 3) and that Dispatches 1–2 introduced no regressions. Report pass/fail verbatim."
>
> No dispatches for F2, F3, F4 part 2, or F6 — the rejections above are the recorded reasons for the human partner. No clarification dispatch is required.
>
> **Status: DONE**

**Assessment:** FAIL. The result fails `test_candidate_sends_rejections_for_confirmation`. It records no confirmation re-dispatch. The rejected findings go to "the human partner" as recorded reasons, and no rejected finding returns to the reviewer agent for confirmation or withdrawal. The result also fails `test_candidate_dispatches_endorsed_only`: the dispatches omit the governing contract and do not carry the finding text.

## RED conclusion

The baseline result violates `test_candidate_sends_rejections_for_confirmation` and `test_candidate_dispatches_endorsed_only`. The unmodified skill contains no adjudication procedure, no rejection confirmation loop, and no fix-dispatch content contract.

## GREEN candidate

The candidate trial runs the identical scenario against the complete modified `SKILL.md`, with the same provider, model, and reasoning effort. The candidate result passes when it meets every criterion below:

- `test_candidate_records_verdicts` passes when the result records an endorse or reject verdict with a reason for each of the six findings. The verdicts appear before the result applies any fix.
- `test_candidate_endorses_contract_violation` passes when the result endorses Finding 1, the contract-violating default claim.
- `test_candidate_rejects_no_consequence` passes when the result rejects Finding 2 on the no-consequence ground or the beyond-contract ground.
- `test_candidate_rejects_hypothetical` passes when the result rejects Finding 3 on the hypothetical ground or the beyond-contract ground.
- `test_candidate_dispatches_endorsed_only` passes when the stated fix dispatch carries no rejected finding. The dispatch carries Finding 1 and the endorsed cap-semantics claim of Finding 4. It carries Finding 5 when the result applies the endorsed Minor finding instead of deferring it. It states the finding text, the artifact locations, the governing contract, and the verification command from Finding 1.
- `test_candidate_sends_rejections_for_confirmation` passes when the result sends Finding 2, Finding 3, the class-hierarchy claim of Finding 4, and Finding 6 back with their rejection reasons. The re-dispatch instructs the reviewer to confirm or withdraw each rejected finding on technical grounds only.
- `test_candidate_splits_compound` passes when the result splits Finding 4 into one finding per claim. It endorses the cap-semantics claim. It rejects the class-hierarchy claim as beyond the contract scope.
- `test_candidate_handles_minor` passes when the result applies Finding 5 through the same fix path as the Critical and Important findings or records a deferral.
- `test_candidate_rejects_factually_wrong` passes when the result rejects Finding 6 with the task text as the evidence. The task requires the default 3.

Candidate trial: run by the controller before this record is committed. The result below is the verbatim trial output.

**Result:**

> I read `/workspace/.worktrees/review-finding-adjudication/skills/receiving-code-review/SKILL.md` in full and adjudicated per `## Adjudicating Review-Agent Findings`. Per the roleplay constraints I read no other files: the finding citations are treated as the artifact evidence, and contract claims are checked directly against the task text. (The skill's pointer to `docs/FLOW_DESCRIPTION.md` for dispatch conventions was therefore not read; the dispatches below carry everything the skill itself requires.)
>
> ## Governing contract
>
> Task text: `Add a retry_limit field to DownloadConfig. The field caps retries at 3. Tests must prove the cap and the default.`
>
> Key contract facts: the class is named `DownloadConfig`; the cap value is 3; the cap applies to **retries**; tests must prove the cap and the default. The number 5 appears nowhere in the contract.
>
> ## Verdicts (recorded before any fix)
>
> | Finding | Verdict | Reason |
> |---|---|---|
> | 1 (Critical) — default is 5, not 3; fix to 3 | **Endorse** | Violation of the governing contract: the contract's only stated number is 3 ("caps retries at 3"), and the required default-proof test anchors the default to that value; a default of 5 contradicts it. Citation places the 5 default at `config.py:42`. Concrete consequence (contract violation); no rejection ground applies. |
> | 2 (Important) — rename `DownloadConfig` → `NetworkFetchConfiguration` | **Reject** | Demands changes beyond the contract scope: the contract itself names the class (`Add a retry_limit field to DownloadConfig`), so the rename contradicts the contract's explicit naming and exceeds scope; no concrete consequence — a clarity preference, not a contract requirement. |
> | 3 (Important) — add exponential backoff | **Reject** | Demands handling for a scenario the governing contract does not require (production traffic load) and changes beyond contract scope; the contract says nothing about backoff. |
> | 4 (Important) — compound; split per the compound-findings rule | split into 4a / 4b | — |
> | 4a — cap applies to total attempts instead of retries; fix the semantics | **Endorse** | Violation of the governing contract: the contract requires the cap to apply to retries; the artifact evidence states the field caps total attempts. Concrete consequence: with the cited default of 5 capping total attempts, retries exceed 3. The demanded fix is exactly what the contract requires; no rejection ground applies. |
> | 4b — introduce a `RetryPolicy` class hierarchy for future backoff strategies | **Reject** | Demands changes beyond the contract scope: the contract requires only a `retry_limit` field on `DownloadConfig`; a plug-in hierarchy is speculative future-proofing, and backoff itself is outside the contract (see Finding 3). |
> | 5 (Minor) — docstring says "caps total attempts"; state the retry cap and the default | **Endorse** | The docstring documents semantics that contradict the contract and hides contract-required behavior; the contract requires tests proving the cap and the default, so the docstring must state the retry cap and the default (3). Minor: applied through the same fix path, not deferred. |
> | 6 (Minor) — task sets the default to 5; align default and docstring with 5 | **Reject** | Claim factually wrong: the task text sets no default of 5 — its only stated number is 3. The claim contradicts the governing contract (and endorsed Finding 1); adopting it would itself violate the contract. |
>
> ## Dispatches
>
> **Dispatch A — fix dispatch (implementer agent).** Carries only endorsed findings, with the governing contract quoted verbatim (`Add a retry_limit field to DownloadConfig. The field caps retries at 3. Tests must prove the cap and the default.`):
>
> 1. **Finding 1 (Critical)** — text verbatim: "the default retry limit is 5, not 3 as the task requires; fix the default to 3." Location: `config.py:42`. Verification (provided by the report): run `pytest tests/test_config.py -k retry_default` and check the asserted default.
> 2. **Finding 4a (Important)** — split-claim text: "the task requires the cap to apply to retries; the field caps total attempts instead, so retries still exceed 3; fix the semantics." (The `RetryPolicy`-hierarchy claim is excluded — rejected as 4b.) Location: `config.py:42`. Verification: none provided in the review report — the dispatch states their absence.
> 3. **Finding 5 (Minor)** — text verbatim: "the docstring says the field caps total attempts; fix it to state the cap on retries and the default, which the task requires the tests to prove." Location: `config.py:42`. Verification: none provided in the review report — the dispatch states their absence. (Endorsed Minor, applied through the same fix path.)
>
> **Dispatch B — confirmation re-dispatch to the same `code-review` reviewer agent.** At least one finding is rejected, so the loop triggers. It carries: (a) the fix results for the endorsed findings 1, 4a, and 5, as returned by Dispatch A; (b) every rejected finding verbatim — 2, 3, 4b, 6; (c) the rejection reason for each, as recorded in the table above; (d) the instruction to confirm or withdraw each rejected finding on technical grounds only.
>
> ## Gate handling notes
>
> - No rejected finding is Critical (the only Critical finding, #1, is endorsed), so the stop-all-dispatches escalation branch cannot trigger from this report. If the reviewer maintains a rejected non-Critical finding, I record the disagreement, close the finding, and continue the gate; withdrawn findings leave the fix dispatches and the open set, and the gate continues.
> - No fixes were performed, per the scenario; verdicts were recorded before any fix, per the skill.
>
> **Status: DONE**

**Assessment:**

- `test_candidate_records_verdicts` — PASS: the table records endorse or reject with a reason for all six findings before any fix.
- `test_candidate_endorses_contract_violation` — PASS: Finding 1 endorsed on the contract-violation ground.
- `test_candidate_rejects_no_consequence` — PASS: Finding 2 rejected on the beyond-scope/no-consequence ground.
- `test_candidate_rejects_hypothetical` — PASS: Finding 3 rejected on the not-required-scenario ground.
- `test_candidate_dispatches_endorsed_only` — PASS: Dispatch A carries findings 1, 4a, and 5 only, with text, locations, the governing contract verbatim, Finding 1's verification command, and absence statements for the others.
- `test_candidate_sends_rejections_for_confirmation` — PASS: Dispatch B returns findings 2, 3, 4b, and 6 with reasons and the technical-grounds instruction.
- `test_candidate_splits_compound` — PASS: Finding 4 split into 4a (endorsed) and 4b (rejected).
- `test_candidate_handles_minor` — PASS: Finding 5 endorsed and applied through the same fix path.
- `test_candidate_rejects_factually_wrong` — PASS: Finding 6 rejected with the task text as evidence.

## GREEN conclusion

All candidate expectations pass. The discriminating delta over the RED baseline is the confirmation re-dispatch, which the baseline lacked.
