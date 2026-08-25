# Minimal Simple-English Rewrites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make simple-English rewrites use the smallest sufficient repair and preserve logical relationships when a split is necessary.

**Architecture:** The skill will define factual fidelity as the first constraint and give the rewriter an ordered repair procedure. Rule 6.1, examples, and the self-check will use the same split policy. Isolated behavior trials will compare the current guidance with the candidate guidance.

**Tech Stack:** Markdown Agent Skill, Tau isolated-subagent `task` tool, Bash installer test

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, simple-english prose.

**Feature spec:** `docs/design/2026-08-25-simple-english-minimal-rewrites-spec.md` (the behavioral contract)

---

## Commands

Run commands from the worktree root.

```bash
# Installer regression test
tests/test-install.sh

# Confirm that the new guidance is present
rg -n 'smallest sufficient|finite clause|explicit logical relationship|one main assertion|split only' skills/simple-english/SKILL.md

# Inspect all changes
git diff --check
git diff -- skills/simple-english/SKILL.md docs/skill-tests/2026-08-25-simple-english-minimal-rewrites.md
```

Behavior verification uses separate Tau `task` calls. Each call contains one `read-only` child. Baseline calls omit the candidate skill. Candidate calls include the complete candidate `SKILL.md`. Each pair inherits the parent provider, model, and reasoning effort without overrides. The scenario text stays identical between the two calls in a pair.

---

### Task 1: Least-change rewrite guidance

**Files:**

- Modify: `skills/simple-english/SKILL.md` — define the repair order, split safeguards, Rule 6.1 boundary, consistent examples, and final checks
- Create: `docs/skill-tests/2026-08-25-simple-english-minimal-rewrites.md` — record scenarios and verbatim baseline and candidate results

**Spec requirement:** Use the smallest sufficient repair; Split only when necessary; Preserve logical relationships; Preserve claims and terminology.

**Interface:**

- Rewrite priority — source claims, logical relationships, and established terminology remain unchanged before vocabulary or structural repairs occur.
- Repair order — replace a noncompliant word or form, convert a phrase to a finite clause, reorder clauses, and split only when earlier repairs cannot satisfy an applicable rule or keep the sentence clear.
- Split boundary — sentence limits, one-instruction rules, safety rules, and unresolved ambiguity can require a split. The presence of a cause, condition, method, purpose, contrast, or result does not require a split by itself.
- Split output — each split states the original logical relationship with an explicit connector. Sentence adjacency is not sufficient.
- Descriptive Rule 6.1 — one main assertion can contain a closely related explanation when the sentence remains within its word limit and satisfies the other rules.
- Self-check — every structural change receives a factual-fidelity check. Every split receives a necessity and logical-relationship check.
- Existing examples — no example can recommend a split when a finite clause gives a compliant and clear sentence. The heading-rewrite example demonstrates the smallest sufficient repair.

**Behavior:**

- Apply the requirements in pragmatic and strict modes.
- Do not weaken Rules 5.1, 5.2, 6.3, or the safety rules.
- Do not add a cause, intention, judgment, mechanism, degree of certainty, or new technical term.
- Use an actor name from the source context when a repair makes the actor explicit.
- Keep a descriptive sentence intact when a finite-clause rewrite meets all applicable rules.
- Split an over-limit sentence when shortening it changes its meaning. Preserve its logical relationship in the resulting sentences.

**Behavior scenarios:**

Each trial asks for only the rewritten passage. Use pragmatic mode unless the scenario says strict mode.

- `test_finite_clause_avoids_unnecessary_split` context: “A rephraser updates headings. In this passage, ‘the rephraser’ names that component.” Source: “Heading rewrites frequently change the meaning by renaming named concepts, frameworks, and terms of art.”
- `test_main_assertion_keeps_related_explanation` source: “The cache rejects duplicate requests because it stores each request key for ten minutes.”
- `test_required_split_keeps_causal_connection` source: “The deployment controller delays the release because it compares the requested image digest with the approved digest before it sends the update to every production cluster.”
- `test_established_actor_name_is_not_replaced` context: “The heading rephraser performs this step.” Source: “During this step, named concepts, frameworks, and terms of art are renamed.” Run this scenario in strict mode.

**Tests must prove:**

- `test_finite_clause_avoids_unnecessary_split` — the rewrite contains one sentence, removes verbal `-ing`, preserves the causal relationship, retains the established terms, and adds no claim such as “invented names.”
- `test_main_assertion_keeps_related_explanation` — the rewrite keeps the source sentence count and preserves the explicit cause.
- `test_required_split_keeps_causal_connection` — the 26-word source becomes multiple sentences and explicitly preserves its causal and temporal relationships.
- `test_established_actor_name_is_not_replaced` — the rewrite makes the known actor explicit as “the heading rephraser” and invents no alternative name.
- `test_skill_examples_follow_repair_order` — each affected example uses a finite clause before a split unless an applicable limit or structural rule requires the split.
- `test_skill_discovery_survives_edit` — the installer regression test passes with the changed skill.

**Check:** Run all commands in the Commands section. Run each isolated behavior scenario without the candidate skill and record the result verbatim. At least one baseline result must violate its named expectation before the skill changes. Run the same scenarios with the complete candidate skill and record the results verbatim. All candidate results must satisfy their named expectations.

- [x] Write the behavior scenarios in the test record. Run isolated baseline trials without the candidate skill. Record each result verbatim and check that at least one result fails for the expected reason.
- [x] Update the skill with the rewrite priority, repair order, Rule 6.1 boundary, split safeguards, consistent examples, and self-check additions.
- [x] Run the same isolated trials with the complete candidate skill. Record each result verbatim and check that all results satisfy their expectations.
- [x] Run `tests/test-install.sh`, the `rg` guidance check, `git diff --check`, and the final diff review.
- [x] Commit: `git add skills/simple-english/SKILL.md docs/skill-tests/2026-08-25-simple-english-minimal-rewrites.md && git commit -m "docs: prefer minimal simple-English rewrites"`

---

## Self-review notes

- Use the smallest sufficient repair → `test_finite_clause_avoids_unnecessary_split`.
- Split only when necessary → `test_main_assertion_keeps_related_explanation` and `test_required_split_keeps_causal_connection`.
- Preserve logical relationships → `test_main_assertion_keeps_related_explanation` and `test_required_split_keeps_causal_connection`.
- Preserve claims and terminology → `test_finite_clause_avoids_unnecessary_split` and `test_established_actor_name_is_not_replaced`.
- Task 1 contains only the skill change and its behavior-test record.
- The plan changes no sentence limit, vocabulary rule, classification rule, or safety rule.
- The RED and GREEN trials use separate isolated calls with identical scenarios and model settings.
- The verification commands contain no placeholders.
