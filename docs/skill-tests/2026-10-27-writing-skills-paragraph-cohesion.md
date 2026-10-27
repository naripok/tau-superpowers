# Skill Test: Paragraph Cohesion in Writing Skills

Proposal: `docs/design/2026-10-27-writing-skills-paragraph-cohesion-proposal.md`.

## Test method

Each trial used an isolated `read-only` child. Baseline trials embedded the complete current `writing-unambiguous-text` and `writing-actionable-text` skill texts in the prompt. Candidate trials embedded the complete revised skill texts and the identical scenario. Every trial inherited the same parent provider, model, and reasoning effort.

## Scenarios

- `payment-save-section`: one section of a research document, "Why a payment save can appear to fail". Facts: external Stripe change, local commit, later analytics failure, error response without lost save, unknown outcome when the response never arrived. This is the representative #20745 input required by the proposal.
- `payment-save-note`: the same fact set expanded to eight interlinked findings with explicit causal links and uncertainty wording, written as a full wiki note.
- `analytics-cache-doc`: mixed document with explanatory prose, a numbered procedure, a standalone warning, and two alternatives with trade-offs.

## RED baseline

### `payment-save-section`

**Result:**

> ## Why a payment save can appear to fail
>
> An error response does not prove that the local save failed.
>
> ### Order of operations
>
> An external Stripe change can alter the payment state before the local save runs. The backend commits the payment record to the local database. After the commit, the backend sends an analytics event. The analytics send can fail after the commit.
>
> ### The error response
>
> When the analytics send fails, the caller receives an error response. An error response does not prove that the local save failed, because the commit already happened.
>
> ### Unknown outcome
>
> In some recorded cases, the HTTP response never reached the caller, so the outcome of the save is unknown.

**Assessment:** PARTIAL FAIL. The conclusion opens as an isolated single-sentence paragraph detached from its evidence. The error-response reasoning and the unknown-outcome statement sit in separate sections although they develop one chain.

### `payment-save-note`

**Result (excerpt):**

> **When a ticket reports "save failed", query the payment record in the local database first.**
>
> ## The operation order
>
> The operations happen in this order:
>
> 1. An external Stripe change can alter the payment state before the local save runs.
> 2. The backend commits the payment record to the local database.
> 3. After the commit, the backend sends an analytics event, and the send can fail.
> 4. When the analytics send fails, the caller receives an error response.
> 5. The commit already happened when the error response goes out.

**Assessment:** FAIL. The connected temporal and causal reasoning became a numbered list of facts. An action line from `writing-actionable-text` Rule 1 fronts a descriptive note. The conclusion about the missing response is again stranded from the error-response reasoning.

### `analytics-cache-doc`

**Assessment:** PASS at baseline. Explanation stayed in one paragraph, the procedure kept numbered steps, the warning stayed standalone, and the alternatives kept their trade-offs. This trial guards acceptance criterion 2: the change must not break correct procedural formatting.

## RED conclusion

The baseline fragments connected reasoning in two forms: isolated single-sentence paragraphs for claims that develop the same point as adjacent sentences, and connected reasoning converted into a list. It does not produce wholesale one-sentence-per-paragraph prose in these scenarios; the mixed-document scenario never fragments. The proposal's smallest changes target exactly the two observed forms.

## GREEN candidate

Changes applied to `skills/writing-unambiguous-text/SKILL.md`:

1. Rule 2 gained the paragraph-structure text and the before-and-after example from the proposal, verbatim.
2. The self-check gained item 9, "Paragraph cohesion". The item title adds the "(Rule 2)" citation marker that every other self-check item carries; the proposal text did not include it.
3. "Run these eight checks" became "Run these nine checks".

Change applied to `skills/writing-actionable-text/SKILL.md`:

4. The section "Match the format to the content" was added before "## Rules", verbatim.

## GREEN trials

### `payment-save-section`

**Result:**

> ## Why a payment save can appear to fail
>
> An external Stripe change can alter the payment state before the local save runs. The backend commits the payment record to the local database. After the commit, the backend sends an analytics event, and the analytics send can fail after the commit. When the analytics send fails, the caller receives an error response. An error response does not prove that the local save failed, because the commit already happened.
>
> In some recorded cases, the HTTP response never reached the caller, so the outcome of the save is unknown.

**Assessment:** PASS. The full chain now sits in one cohesive paragraph. The unknown-outcome sentence keeps its own paragraph because its topic differs. Every fact, the operation order, and the uncertainty wording survive. The longest new sentence is 18 words.

### `payment-save-note`

**Result (excerpt):**

> ## The order of operations
>
> An external Stripe change can alter the payment state before the local save runs. The backend commits the payment record to the local database. After the commit, the backend sends an analytics event. This send can fail. When the analytics send fails, the caller receives an error response. The commit already happened when the error response goes out.

**Assessment:** PASS. The operation order is now a paragraph, not a list. Each causal link ("As a result", "so", "when") and each degree of certainty ("can", "in some recorded cases", "cannot yet") is preserved. No action line fronts the descriptive note.

### `analytics-cache-doc`

**Result (excerpt):**

> ## Refresh procedure
>
> WARNING: Do not run the refresh during peak traffic. The refresh doubles the database load and can slow dashboards for all teams.
>
> 1. Run `analytics-cache refresh --window 24h`. The command rebuilds the cache from the database.
> 2. Check a dashboard to see the new data.

**Assessment:** PASS. The numbered procedure and the standalone warning survive. The alternatives keep their trade-offs as labeled paragraphs. The response-level lead ("If a dashboard shows stale data, run ... now.") and the closing next action remain, matching the new format-selection section. Minor note: the explanation is split across two short headed paragraphs. Each carries a distinct topic, so the revised rules permit it; the density is at the boundary the owner review question three asks about.

## Acceptance criteria check

1. Research and design explanations group related claims, evidence, and qualifications into paragraphs: PASS (both payment-save trials).
2. Procedures retain numbered steps, and independent alternatives or criteria retain lists: PASS (analytics-cache trial).
3. Standalone warnings and conclusions can remain single-sentence paragraphs: PASS (warning in the mixed document; unknown-outcome paragraph in the section trial).
4. Sentence limits, technical facts, identifiers, and explicit causal relationships remain intact: PASS (longest sentence observed in GREEN output is 18 words; `analytics-cache refresh --window 24h` and all facts unchanged).
5. No rule imposes a minimum paragraph length or treats every short paragraph as an error: PASS (the added text validates single-sentence warnings, conclusions, and transitions).

## Status

The revised skills pass the comparison tests recorded here. Deployment follows the skills-owner review of the proposal; the source files are `skills/writing-unambiguous-text/SKILL.md` and `skills/writing-actionable-text/SKILL.md`, and the installed copies under `~/.tau/skills/` update through the installer.
