# Proposal: Preserve paragraph cohesion in writing skills

Date: 2026-10-27

Status: Proposed for skills-owner review. No skill files changed.

## Requested decision

Approve or revise the proposed guidance for `writing-unambiguous-text` and `writing-actionable-text`. The change makes cohesive paragraphs the default for descriptive prose while preserving concise instructions and useful lists.

## Problem

The research document for issue #20745 uses consecutive single-sentence paragraphs throughout its descriptive sections. Related claims, evidence, and qualifications appear as isolated statements instead of cohesive paragraphs. The resulting document requires excessive vertical scanning and obscures the connections between sentences.

The current skills do not require this format. `writing-unambiguous-text` permits descriptive paragraphs of up to six sentences. But its sentence-length rules and the scannability guidance in `writing-actionable-text` lack an explicit safeguard against paragraph fragmentation. The assistant applied sentence boundaries as paragraph boundaries.

## Scope

This proposal changes guidance in two existing skills. It does not create a new skill, relax sentence-length limits, or change technical facts. It also does not impose a minimum sentence count per paragraph or require a rewrite of existing documents.

The installed files are `/home/tau/.tau/skills/writing-unambiguous-text/SKILL.md` and `/home/tau/.tau/skills/writing-actionable-text/SKILL.md`. Apply approved changes in the skills owner's source repository, not only in the sandbox copies. Host-managed skill files refresh when the sandbox starts.

## Proposed changes

### 1. Define paragraph structure in `writing-unambiguous-text`

Expand Rule 2 with the following text. Keep its existing distinction between procedural and descriptive writing.

> **Paragraph structure.** Group related descriptive sentences into cohesive paragraphs. Keep a claim, its supporting evidence, and its immediate qualification together. Start a new paragraph when the topic or purpose changes, not whenever a sentence ends.
>
> Sentence-length limits do not require paragraph breaks. A single-sentence paragraph is valid for a standalone warning, conclusion, or transition. Do not use single-sentence paragraphs as the default for explanations or long documents.
>
> Use lists for actual steps, alternatives, criteria, or independently useful items. Do not turn connected reasoning into a list merely to shorten its appearance.

This addition preserves the current one-topic rule and six-sentence paragraph limit. It clarifies how to group sentences without replacing the existing sentence rules.

### 2. Clarify format selection in `writing-actionable-text`

Add the following section before the numbered rules.

> ## Match the format to the content
>
> For immediate actions, use concise instructions and numbered steps. For research, explanations, and design rationale, use cohesive paragraphs with descriptive headings.
>
> Scannability does not mean one sentence per paragraph. Keep related reasoning together. Do not force descriptive sections into action lists or isolated statements.
>
> Apply "lead with the next action" and "end with one concrete next action" to the response as a whole. Do not apply them to every section of a document.

This section separates response-level action guidance from the internal structure of a long document. Existing rules for warnings, steps, and list length remain unchanged.

### 3. Add a paragraph-cohesion self-check

Add the following item to the self-check in `writing-unambiguous-text`.

> **Paragraph cohesion.** Check consecutive single-sentence paragraphs. If they develop the same point, combine them. Keep separate paragraphs only when their topics or purposes differ.

This check targets the observed failure without banning short paragraphs. It does not require an automated sentence-count threshold.

### 4. Include one before-and-after example

Place this example beside the paragraph guidance in `writing-unambiguous-text`.

Avoid:

```markdown
The backend commits the payment type.

It then sends analytics.

Analytics can fail after the commit.

An error response does not prove that the save failed.
```

Prefer:

```markdown
The backend commits the payment type before it sends analytics. Analytics can fail after the commit, so an error response does not prove that the save failed.
```

The preferred version preserves the operation order, failure possibility, and conclusion. It groups the reasoning into one paragraph without increasing sentence length beyond the current descriptive limit.

## Acceptance criteria

The revised guidance must produce cohesive descriptive prose without replacing useful structure with dense text. Check these outcomes:

1. Research and design explanations group related claims, evidence, and qualifications into paragraphs.
2. Procedures retain numbered steps, and independent alternatives or criteria retain lists.
3. Standalone warnings and conclusions can remain single-sentence paragraphs.
4. Sentence limits, technical facts, identifiers, and explicit causal relationships remain intact.
5. No rule imposes a minimum paragraph length or treats every short paragraph as an error.

## Test plan before deployment

Use the skill-testing workflow for edits. This proposal does not constitute a completed skill test or authorization to skip the failing baseline.

1. Run a fixed research-writing prompt in an isolated session with the current skills. Save the exact prompt and output.
2. Check whether the baseline fragments connected reasoning into consecutive single-sentence paragraphs. If it does not, refine the scenario before editing.
3. Apply the smallest proposed changes that address the observed failure.
4. Run the same prompt with the revised skills. Check paragraph cohesion, preservation of facts, and compliance with existing sentence rules.
5. Repeat the comparison with a mixed document containing explanatory prose, a numbered procedure, alternatives, and a standalone warning.

Use the #20745 payment-save explanation as one representative input. Include the external Stripe changes, local database commit, later analytics failure, and lost-response uncertainty. The output must preserve those distinctions without placing each sentence in a separate paragraph.

Record before-and-after outputs for owner review. Do not claim that this proposal prevents recurrence until the revised skills pass these checks.

## Review questions

The owner review covers the following decisions:

- Does the paragraph guidance belong in Rule 2, or in a separate paragraph-structure section?
- Does the format-selection section resolve the interaction between action-oriented responses and descriptive documents?
- Do the example and self-check prevent fragmentation without encouraging dense paragraphs?

## Current status

Only this proposal exists. No skill edits, isolated comparison tests, or deployment changes occurred for this request.
