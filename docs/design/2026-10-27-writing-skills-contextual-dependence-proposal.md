# Proposal: Keep dependent sentences with their context

Date: 2026-10-27

Status: Proposed for skills-owner implementation and review. No skill files changed for this proposal.

## Requested action

Update `writing-unambiguous-text` to keep context-dependent sentences with the statements they qualify or constrain. Check the interaction with `writing-actionable-text` through isolated before-and-after tests. Apply approved edits in the skills source repository, not only in installed sandbox copies.

## Background and observed failure

The owner applied the paragraph-cohesion changes proposed in `2026-10-27-writing-skills-paragraph-cohesion-proposal.md`. Those changes address consecutive single-sentence paragraphs and distinguish descriptive prose from action lists. The assistant then rewrote the research and proposal documents for #20745, but a contextual separation problem remained.

The rewritten research contains this passage:

```markdown
The Express path requires a matching SetupIntent ID and `status === 'succeeded'`. The card path accepts a result without an SDK error.

Record both the SDK result and the existing acceptance decision. Do not strengthen card validation or weaken Express validation.
```

The second paragraph gives instructions that directly govern the behavior in the first paragraph. Its imperative grammar is complete, with an implied subject of "you". The problem is not a missing grammatical subject. The paragraph boundary separates the recommendation and constraints from their immediate context, while the voice changes from description to instruction.

The assistant explained that it applied the procedural-versus-descriptive distinction too mechanically. It separated the imperative instead of rewriting the related content into a consistent voice. The document review also missed this failure.

## Scope and constraints

The primary edit target is `writing-unambiguous-text/SKILL.md`. The installed copy is `/home/tau/.tau/skills/writing-unambiguous-text/SKILL.md`. The companion skill is `/home/tau/.tau/skills/writing-actionable-text/SKILL.md`. Host-managed copies refresh when the sandbox starts, so source-repository edits are necessary for persistence.

This proposal extends the previous paragraph-cohesion changes rather than replacing them. It preserves sentence limits, the six-sentence paragraph limit, useful lists, numbered procedures, and legitimate short paragraphs. It introduces no minimum paragraph length and no blanket requirement to merge adjacent paragraphs.

This task changes writing guidance and its tests. It does not change the #20745 design, payment behavior, or technical acceptance criteria. Rewriting the #20745 documents again is outside this implementation task.

## Proposed skill changes

### 1. Extend Rule 2 with contextual dependence

Add the following text to the existing paragraph-structure guidance in `writing-unambiguous-text`:

> **Keep dependent sentences with their context.** Keep a recommendation, constraint, qualification, or consequence in the same paragraph as the statement it directly governs. A change in sentence function does not, by itself, justify a paragraph break.
>
> Start a new paragraph only when the topic or purpose changes. Do not isolate a sentence merely because it gives an instruction after an explanation.
>
> Check short paragraphs that begin with verbs such as "Record," "Preserve," "Keep," or "Do not." If the instruction depends on the preceding explanation, integrate it with that explanation. For descriptive documents, rewrite the instruction as a description of the proposed behavior. For procedures, keep the instruction in the relevant step.

These verbs are review cues, not a blacklist. An independent instruction remains valid as a separate step or paragraph. The decision depends on its relationship to the surrounding content, not its opening word.

### 2. Clarify passage classification

Replace this sentence beneath the classification table:

> Do not mix the two in one passage. A note inside a procedure is descriptive: 25-word limit, no imperative.

With:

> Select the dominant purpose of each passage. In descriptive documents, express related recommendations and constraints as descriptions of the proposed behavior. In procedures, use imperative instructions with supporting explanatory notes.
>
> Do not separate related content into different paragraphs solely to avoid mixing descriptive and imperative sentences. First, rewrite the passage into a consistent voice.
>
> A note inside a procedure is descriptive: 25-word limit, no imperative.

This revision preserves the distinction between instruction and explanation. It removes paragraph separation as the default repair for a voice mismatch.

### 3. Replace the paragraph-cohesion self-check

Replace the current self-check item with:

> **Paragraph cohesion and contextual dependence.** Check every paragraph boundary, including boundaries between multi-sentence paragraphs. Does the next paragraph qualify, constrain, explain, or prescribe an action for the preceding statement? If so, keep the related content together unless a distinct topic or purpose requires separation.
>
> Check isolated imperatives and sentences containing backward references such as "both," "this," "these," or "that result." Keep each sentence with the context it needs. Rewrite the voice where necessary instead of inserting a paragraph break.

The existing check focuses on consecutive single-sentence paragraphs. This replacement also covers the observed failure, which separates two multi-sentence paragraphs. A backward reference is a review cue, not an automatic violation.

### 4. Add the regression example

Use the observed Express/card passage as a before-and-after example beside the contextual-dependence guidance. Preserve the existing payment-commit example if both demonstrate distinct failure modes without unnecessary duplication.

Before:

```markdown
The Express path requires a matching SetupIntent ID and `status === 'succeeded'`. The card path accepts a result without an SDK error.

Record both the SDK result and the existing acceptance decision. Do not strengthen card validation or weaken Express validation.
```

After:

```markdown
The Express path requires a matching SetupIntent ID and `status === 'succeeded'`. The card path accepts a result without an SDK error. The proposed instrumentation records both the SDK result and the existing acceptance decision without strengthening card validation or weakening Express validation.
```

The rewrite preserves both acceptance behaviors, both observation requirements, and both prohibitions on changing validation. It describes the proposed behavior in one paragraph instead of switching into a detached instruction.

## Interaction with `writing-actionable-text`

The updated format-selection section already requires cohesive paragraphs in research and design rationale. Treat `writing-unambiguous-text` as the owner of the detailed contextual-dependence rule. Test both skills together before adding duplicate guidance to `writing-actionable-text`.

If combined-skill tests still separate dependent instructions, add a short cross-reference to the contextual-dependence rule in the format-selection section. Do not duplicate the full rule or introduce conflicting paragraph criteria.

## Acceptance criteria

Check the revised skills against these outcomes:

1. The Express/card example becomes a cohesive descriptive paragraph without changes to its technical meaning.
2. Recommendations, constraints, qualifications, and consequences remain with the statements they directly govern, including across multi-sentence paragraph boundaries.
3. Research and design prose use a consistent descriptive voice for related proposed behavior instead of isolated implementation commands.
4. Procedures retain imperative steps and supporting notes. Distinct topics, independent actions, and standalone warnings retain appropriate boundaries.
5. The rewrite preserves facts, uncertainty, identifiers, code, sentence limits, and the six-sentence paragraph limit without forcing unrelated content together.

## Test plan before deployment

Follow the skill-testing workflow for edits. The observed conversation supplies a motivating failure, but it does not replace an isolated failing baseline.

1. Run fixed prompts with the current skills in isolated sessions. Save the exact skill versions, prompts, outputs, and observed failures.
2. Check that a baseline reproduces contextual separation or preserves it during a requested rewrite. If necessary, refine the prompt before editing.
3. Apply the smallest changes that address the reproduced failure.
4. Run the same prompts with the revised skills. Check contextual dependence, consistent voice, source preservation, and legitimate paragraph boundaries.
5. Run the combined-skill scenarios before deployment. Record the results and any further edits for owner review.

Use these scenarios to check both the correction and its limits:

- **Observed regression:** Rewrite the Express/card passage as research prose. Preserve its acceptance differences and instrumentation constraints in one cohesive paragraph.
- **Generalization:** Explain that a backend commit precedes analytics, then state a directly related diagnostic recommendation. Keep the recommendation with its explanation in descriptive voice.
- **Procedural counterexample:** Write a numbered procedure with a supporting explanatory note. Preserve the step structure rather than converting the procedure into descriptive prose.
- **Boundary counterexample:** Write adjacent paragraphs about genuinely different topics, plus an independent warning. Preserve the useful boundaries instead of merging them mechanically.
- **Combined-skill pressure:** Request a concise, scannable design note with explanatory prose and an action checklist. Keep dependent rationale together without removing the checklist.

Review the technical meaning as well as the formatting. Joining paragraphs alone is insufficient if the result retains an unnecessary voice switch or changes a requirement.

## Implementation handoff

Implement the primary changes in the skills source repository after the failing baseline. Check the proposed wording against the current source because the owner already applied the earlier paragraph-cohesion changes. Record the changed files and before-and-after test evidence in the implementation report.

The owner can adjust the wording or example placement while preserving this proposal's acceptance criteria. No production-code changes or #20745 implementation work are necessary. This proposal does not claim that the revised rules prevent recurrence before the tests run.

## Current status

Only this proposal exists for the contextual-dependence correction. No skill edits, isolated comparison tests, or deployment changes occurred for this request.
