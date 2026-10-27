# Skill Test: Contextual Dependence in Writing Skills

Proposal: `docs/design/2026-10-27-writing-skills-contextual-dependence-proposal.md`.

## Test method

Each trial used an isolated `read-only` child. Baseline trials read the current `writing-unambiguous-text` and `writing-actionable-text` skill texts from a snapshot directory. Candidate and refactor trials read the revised texts from a second snapshot directory and used identical prompts. Every trial inherited the same parent provider, model, and reasoning effort. Every trial loaded both skills together.

## Scenarios

- `express-card` (S1): a research section on the acceptance decision. Facts: the Express path requires a matching SetupIntent ID and `status === 'succeeded'`; the card path accepts a result without an SDK error; the instrumentation records both the SDK result and the existing acceptance decision; it must not strengthen card validation and must not weaken Express validation. This is the observed regression from the proposal.
- `express-card-rewrite` (S1b): the same passage with its imperative second paragraph, given as a rewrite task in research voice. This reproduces the exact conversation failure.
- `generalization` (S2): a passage that explains that the backend commits the payment type before it sends analytics, then states a directly related diagnostic recommendation about checking the analytics consumer logs.
- `procedure-counterexample` (S3): a numbered API-key rotation procedure with a supporting explanatory note. Guard against overcorrection.
- `boundary-counterexample` (S4): two genuinely different topics (orders-table indexing, loading skeletons) plus a standalone WARNING. Guard against mechanical merging.
- `combined-skill-pressure` (S5): a concise design note with explanatory prose about request-ID propagation plus an action checklist.

## RED baseline

### `express-card`

**Result:**

> The Express path requires a matching SetupIntent ID and `status === 'succeeded'`. The card path accepts a result without an SDK error.
>
> The proposed instrumentation records both the SDK result and the existing acceptance decision. The instrumentation must not strengthen card validation. The instrumentation must not weaken Express validation.

**Assessment:** FAIL. The backward reference "both" and both prohibitions sit in a second paragraph detached from the Express/card facts they govern. This is the contextual separation the proposal targets.

### `express-card-rewrite`

**Result:**

> The Express path requires a matching SetupIntent ID and `status === 'succeeded'`. The card path accepts a result without an SDK error.
>
> The SDK result and the existing acceptance decision are both recorded. Card validation is not strengthened, and Express validation is not weakened.

**Assessment:** FAIL. The rewrite keeps the paragraph separation and drifts into agentless passive ("are both recorded", "is not strengthened"), which violates Rule 5 because the instrumentation is the known agent.

### `generalization`

**Result:**

> The backend commits the payment type before it sends analytics. The analytics send can fail after the commit. If the commit response looks successful but no analytics event arrived, check the analytics consumer logs. Treat the commit as failed only after this check.

**Assessment:** FAIL. The paragraph holds together, but the diagnostic recommendation stays in imperative voice inside descriptive research prose. Acceptance criterion 3 requires a consistent descriptive voice.

### `procedure-counterexample` and `boundary-counterexample`

**Assessment:** PASS at baseline. The numbered procedure kept its imperative steps and note; the two topics kept separate paragraphs and the warning stayed standalone.

### RED conclusion

The baseline reproduces both target failures: dependent content separated across a paragraph boundary (S1, S1b) and the imperative voice retained in descriptive prose (S2). The guards pass, so the failures are specific, not a general formatting collapse.

## GREEN candidate

Changes applied to `skills/writing-unambiguous-text/SKILL.md`:

1. Rule 2 gained the contextual-dependence block, the review-cue paragraph, and the Express/card before-and-after example, placed between the paragraph-structure text and the sentence-length note.
2. The classification sentence beneath the table became the dominant-purpose guidance with the consistent-voice instruction and the retained note rule.
3. Self-check item 9 became "Paragraph cohesion and contextual dependence" with the multi-sentence boundary check and the isolated-imperative and backward-reference cues.

## GREEN trials

### `express-card`

**Result:**

> The Express path requires a matching SetupIntent ID and `status === 'succeeded'`. The card path accepts a result without an SDK error. The proposed instrumentation records both the SDK result and the existing acceptance decision without strengthening card validation or weakening Express validation.

**Assessment:** PASS. One cohesive paragraph, matching the proposal's after-example. Both acceptance behaviors, the observation requirement, and both prohibitions survive.

### `express-card-rewrite`

**Result:**

> The Express path requires a matching SetupIntent ID and `status === 'succeeded'`. The card path accepts a result without an SDK error. The proposed instrumentation records both the SDK result and the existing acceptance decision without strengthening card validation or weakening Express validation.

**Assessment:** PASS. The imperative paragraph is gone, the separation is gone, and no passive drift occurs.

### `generalization`

**Result:**

> The backend commits the payment type before it sends analytics. The analytics send can fail after the commit. A commit response can look successful even when no analytics event arrived. In that case, check the analytics consumer logs before you treat the commit as failed.

**Assessment:** PARTIAL FAIL. Contextual dependence holds (the recommendation stays in the paragraph), but the imperative voice survives inside descriptive prose. A repeat trial and a rewrite variant confirmed the gap: the paragraph-boundary checks do not reach embedded imperatives.

## REFACTOR

Two additions close the loophole:

1. The Rule 2 block gained: "Apply the same check to an imperative sentence inside a descriptive paragraph. If the instruction depends on the surrounding explanation, rewrite it as a description of the proposed behavior."
2. Self-check item 9 now also checks "imperative sentences inside descriptive paragraphs".

### `generalization` (free-writing, refactor candidate)

**Result:**

> The backend commits the payment type before it sends analytics. The analytics send can fail after the commit. When a commit response looks successful but no analytics event arrived, you check the analytics consumer logs before you treat the commit as failed.

**Assessment:** PASS. Descriptive voice ("you check"), recommendation kept with its explanation.

### `generalization` (rewrite variant, refactor candidate)

**Result:**

> The backend commits the payment type before it sends analytics. The analytics send can fail after the commit, so the analysis checks the analytics consumer logs before it treats the commit as failed. The analysis does not treat a missing analytics event as a failed commit.

**Assessment:** PASS. Both sentences describe the proposed behavior; both constraints survive.

## Guard rechecks (final candidate)

### `procedure-counterexample`

**Result (excerpt):**

> 1. Confirm the key to rotate: `keyctl list --project <PROJECT_ID>`.
> 2. Create the replacement key: `keyctl rotate <KEY_ID> --reason "<REASON>"`. The output shows the new key one time only.
>
> **Note:** The old key stays valid for one hour after rotation.

**Assessment:** PASS. The numbered imperative procedure and its supporting note survive the new imperative checks.

### `boundary-counterexample`

**Result (excerpt):**

> The query on the orders table filters on `customer_id` and `created_at`, so a composite index on those two columns removes the full table scan.
>
> The loading skeleton for the orders list shows three placeholder rows, so the layout does not shift when the data arrives.
>
> WARNING: Do not run the index migration during peak traffic. The migration locks the orders table.

**Assessment:** PASS. Genuinely different topics keep separate paragraphs; the warning stays standalone.

### `combined-skill-pressure`

**Result (excerpt):**

> ## Why propagate request IDs
>
> The payment API currently drops the inbound `X-Request-ID` header. Propagated request IDs let support trace one payment across services. The gateway must forward the header before it logs.
>
> ## Implementation checklist
>
> 1. Read the inbound `X-Request-ID` header at the gateway.
> 2. Forward the header to the payment service before the gateway logs.

**Assessment:** PASS. The prose stays descriptive and cohesive; the checklist survives. The combined use of both skills does not re-separate dependent content, so no cross-reference in `writing-actionable-text` is necessary.

## Acceptance criteria check

1. The Express/card example becomes a cohesive descriptive paragraph without changes to its technical meaning: PASS (S1, S1b).
2. Dependent recommendations, constraints, qualifications, and consequences stay with the statements they govern, across multi-sentence paragraph boundaries: PASS (S1, S1b, S2).
3. Research and design prose use a consistent descriptive voice for related proposed behavior: PASS after the refactor (S2 free-writing and rewrite trials).
4. Procedures retain imperative steps and supporting notes; distinct topics, independent actions, and standalone warnings keep their boundaries: PASS (S3, S4, S5).
5. Facts, identifiers, code, uncertainty wording, sentence limits, and the six-sentence paragraph limit survive, with no forced merging: PASS (longest sentence observed in GREEN output is 21 words; all facts, both identifiers, and both prohibitions unchanged).

## Deployment checklist additions

- `tests/check-references.sh` and `tests/test-references.sh` pass on the changed tree.
- The revised skill text follows `writing-unambiguous-text`: no banned modals, no contractions, no semicolons or em dashes, no over-limit sentences, and consistent use of "check" as the verification verb.

## Status

The revised `writing-unambiguous-text` passes the comparison tests recorded here. `writing-actionable-text` needed no change: the combined-skill trials resolved every scenario. The source files are `skills/writing-unambiguous-text/SKILL.md` and `skills/writing-actionable-text/SKILL.md`; the installed copies under `~/.tau/skills/` update through the installer or the next sandbox refresh.
