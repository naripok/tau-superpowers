# Review-Finding Adjudication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-finding adjudication of review-agent reports to every workflow review gate, and ground the reviewer inputs and reports that feed the adjudication loop.

**Architecture:** `receiving-code-review` defines one adjudication procedure that every gate references. The six gate skills direct the controller to the procedure and state the fix routing. The four reviewer prompt templates gain grounding material, a grounded-finding format, pre-report verification, and a rejection-confirmation section. `docs/FLOW_DESCRIPTION.md` and `README.md` document the loop. A skill-test record proves the adjudication behavior with isolated baseline and candidate trials.

**Tech Stack:** Markdown Agent Skills, Tau isolated-subagent `task` tool, Bash installer test

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose (pragmatic mode).

**Feature spec:** `docs/design/2026-08-29-review-finding-adjudication-spec.md` (the behavioral contract)

---

## Commands

Run commands from the worktree root. Each task's Check names the command blocks it runs.

```bash
# Every task: installer regression test
tests/test-install.sh

# Every task: inspect all changes
git diff --check
git diff -- skills/ docs/FLOW_DESCRIPTION.md README.md docs/skill-tests/

# Task 1: confirm the adjudication procedure is present
rg -n 'Adjudicating Review-Agent Findings|endorse|reject|governing contract|confirmation|escalat|defer|split' skills/receiving-code-review/SKILL.md

# Task 2: confirm superseded wording is gone (each search returns no matches)
rg -n 'Drop findings' skills/subagent-driven-development/SKILL.md
rg -n 'Fix Critical issues immediately' skills/requesting-code-review/SKILL.md

# Task 2: confirm the adjudication direction is present in each gate
rg -n 'adjudicat' skills/brainstorming/SKILL.md skills/writing-plans/SKILL.md skills/subagent-driven-development/SKILL.md skills/executing-plans/SKILL.md skills/requesting-code-review/SKILL.md

# Task 2: confirm each gate directs to the procedure
rg -n 'receiving-code-review' skills/brainstorming/SKILL.md skills/writing-plans/SKILL.md skills/subagent-driven-development/SKILL.md skills/executing-plans/SKILL.md skills/requesting-code-review/SKILL.md

# Task 3: confirm living-spec grounding in the three grounding templates
rg -n 'living-spec' skills/brainstorming/spec-document-reviewer-prompt.md skills/writing-plans/plan-document-reviewer-prompt.md skills/subagent-driven-development/implementation-reviewer-prompt.md

# Task 3: confirm grounded findings, contract identification, verification, and rejection sections in all four templates
rg -n 'concrete consequence|governing contract|re-check|Rejection' skills/brainstorming/spec-document-reviewer-prompt.md skills/writing-plans/plan-document-reviewer-prompt.md skills/subagent-driven-development/implementation-reviewer-prompt.md skills/requesting-code-review/code-reviewer.md
```

Behavior verification uses separate Tau `task` calls. Each call contains one `read-only` child. Baseline calls embed the unmodified skill text captured before the edit. Candidate calls embed the complete modified `SKILL.md`. Each pair inherits the parent provider, model, and reasoning effort without overrides. The scenario text stays identical between the two calls in a pair. The scenario is a roleplay: the child treats the task text as the governing contract and the finding citations as the artifact evidence, and it states its handling without reading files.

---

### Task 1: Adjudication procedure in receiving-code-review

**Files:**

- Modify: `skills/receiving-code-review/SKILL.md` — add the review-agent adjudication procedure as one new top-level section
- Create: `docs/skill-tests/2026-08-29-review-finding-adjudication.md` — record the trial method and the verbatim baseline and candidate results

**Spec requirement:** Per-finding adjudication before action; Endorsement and rejection criteria; Adjudication procedure in receiving-code-review; Selective fix dispatch; Fix dispatch content; Rejection confirmation loop; Escalation of maintained Critical rejections.

**Interface:**

- New section `## Adjudicating Review-Agent Findings`, placed after `## Source-Specific Handling` and before `## YAGNI Check for "Professional" Features`. Scope statement: the section applies to findings from `code-review` and `document-review` subagents at workflow review gates. The existing human-feedback material stays unchanged.
- Procedure — six ordered steps: parse the report into findings; verify each finding against the artifact; classify each finding with the endorsement and rejection criteria; record the verdicts; apply endorsed findings; send rejections back for confirmation. A closing statement: the main agent acts only on endorsed findings and records every verdict with its reason.
- Endorsement conditions — a finding is endorsed when the claim is factually correct for the artifact, the finding has a concrete consequence, and no rejection ground applies.
- Concrete consequence — one of: the claim identifies behavior that the artifact breaks or hides; the claim identifies a violation of the governing contract; the claim identifies contract-required work that the artifact omits.
- Rejection grounds — one of: the claim is factually wrong for the artifact; the finding has no concrete consequence; the finding demands handling for a scenario the governing contract does not require; the finding demands changes beyond the contract scope. A claim that the artifact does not exhibit at its stated location counts as factually wrong.
- Compound findings — a finding with several claims is split into one finding per claim, and each claim is adjudicated separately.
- Governing contract — the stated requirements that the artifact was produced against: the task text; the plan; the feature spec; the stated requirements of the proposal for the spec review; the stated requirements of an ad-hoc review.
- Fix application — endorsed Critical and Important findings go to fix dispatches that carry only endorsed findings. A fix dispatch carries, per endorsed finding: the finding text, the artifact locations, the governing contract, and the verification commands that the review report provides; when the report provides none, the dispatch states their absence. An endorsed Minor finding is applied through the same fix path or deferred; a deferral is recorded and does not block gate closure.
- Inline case — at the executing-plans checkpoint the main agent is the implementer and applies endorsed Critical and Important fixes itself instead of dispatching.
- Confirmation loop — when at least one finding is rejected, every rejected finding goes back to the same reviewer agent. The re-dispatch carries the fix results when endorsed findings exist, every rejected finding, and the rejection reason for each, and instructs the reviewer to confirm or withdraw each rejected finding on technical grounds only. The main agent closes a withdrawn finding: it no longer appears in fix dispatches or in the findings the gate treats as open, and the gate continues. When every finding is rejected, the rejections go back with no fix results. When no finding is rejected, the loop continues without a confirmation re-dispatch.
- Escalation — when the reviewer maintains a rejected Critical finding, the main agent stops all workflow dispatches and presents an architectural overview of the problem area plus a situation summary that states the finding, the rejection reason, the maintenance reason, and the decision the user must make. A user decision that upholds the finding makes it endorsed and applies it through the normal fix path; a decision that upholds the rejection closes the finding and continues the gate. A maintained rejection that is not Critical is recorded as a disagreement, closed, and the gate continues.

**Behavior:**

- The existing sections for human-partner and external-reviewer feedback keep their current content and order.
- The new section names `code-review` and `document-review` as the reviewer agents it applies to, and its verification prose uses one term consistently.
- The section states the full fix-dispatch content itself and adds no new tool mechanics; it names `docs/FLOW_DESCRIPTION.md` as the reference for dispatch conventions.
- Prose follows writing-developer-facing-text pragmatic mode: conditions first, one instruction per sentence, no banned modals.

**Tests must prove:**

- `test_baseline_adjudication_absent` — at least one baseline trial result violates the named expectations below, proving the behavior needs the change.
- `test_candidate_records_verdicts` — the candidate result records an endorse or reject verdict with a reason for each of the six findings before it applies any fix.
- `test_candidate_endorses_contract_violation` — the contract-violating finding is endorsed.
- `test_candidate_rejects_no_consequence` — the style finding is rejected on the no-consequence or beyond-contract ground.
- `test_candidate_rejects_hypothetical` — the unrequested-robustness finding is rejected on the hypothetical or beyond-contract ground.
- `test_candidate_dispatches_endorsed_only` — the stated fix dispatch carries no rejected finding; it carries the endorsed Critical and Important findings (the Critical finding and the endorsed compound claim), plus the endorsed Minor finding when applied rather than deferred; it states the finding text, the artifact locations, the governing contract, and the verification command that Finding 1 provides.
- `test_candidate_sends_rejections_for_confirmation` — the result sends the rejected findings (the style rename, the unrequested backoff, the class-hierarchy claim, and the wrong-default claim) back with their reasons and instructs confirmation or withdrawal on technical grounds only.
- `test_candidate_splits_compound` — the compound finding is split into one finding per claim; the cap-semantics claim is endorsed; the class-hierarchy claim is rejected as beyond the contract scope.
- `test_candidate_handles_minor` — the endorsed Minor finding is applied through the same fix path as the Critical and Important findings or deferred with a recorded deferral.
- `test_candidate_rejects_factually_wrong` — the wrong-default finding is rejected with the task text as the evidence, since the task requires the default 3.
- `test_guidance_present` — the `rg` check for the new section and its key terms returns matches in `skills/receiving-code-review/SKILL.md`.
- `test_skill_discovery_survives_edit` — `tests/test-install.sh` passes.

**Check:** Run the Task 1 command block (`tests/test-install.sh`, `git diff --check`, and the receiving-code-review guidance check). Run one baseline-candidate trial pair per the scenario below and record both results verbatim in the test record. At least one baseline expectation must fail. All candidate expectations must pass.

Trial scenario (identical text in both calls; the child states its handling and performs no fixes):

> You are the main agent in a Tau workflow at a review gate. You dispatched a `code-review` subagent for the task below. Its report returned five findings. State how you handle the report: record every verdict with its reason and state every dispatch you make with its content. Do not perform the fixes.
>
> Task text: `Add a retry_limit field to DownloadConfig. The field caps retries at 3. Tests must prove the cap and the default.`
>
> Finding 1 (Critical): `config.py:42 — the default retry limit is 5, not 3 as the task requires; fix the default to 3. Verification: run pytest tests/test_config.py -k retry_default and check the asserted default.`
> Finding 2 (Important): `config.py:40 — the class name DownloadConfig is too generic; rename it to NetworkFetchConfiguration for clarity.`
> Finding 3 (Important): `config.py:42 — add exponential backoff between retries so production traffic does not overwhelm the server.`
> Finding 4 (Important): `config.py:42 — the task requires the cap to apply to retries; the field caps total attempts instead, so retries still exceed 3; fix the semantics. Also introduce a RetryPolicy class hierarchy so future backoff strategies plug in.`
> Finding 5 (Minor): `config.py:42 — the docstring says the field caps total attempts; fix it to state the cap on retries and the default, which the task requires the tests to prove.`
> Finding 6 (Minor): `config.py:42 — the task sets the default to 5; align the field default and the docstring with 5.`

- [ ] Write the trial method and scenario into the test record. Run the baseline trial with the unmodified skill text and record the result verbatim. Check that at least one named expectation fails.
- [ ] Add the `## Adjudicating Review-Agent Findings` section with the interface contracts above.
- [ ] Run the candidate trial with the complete modified `SKILL.md` and record the result verbatim. Check that all named expectations pass.
- [ ] Run `tests/test-install.sh`, the `rg` guidance check, `git diff --check`, and review the full diff.
- [ ] Commit: `git add skills/receiving-code-review/SKILL.md docs/skill-tests/2026-08-29-review-finding-adjudication.md && git commit -m "docs: add review-finding adjudication procedure"`

---

### Task 2: Gate wiring to the procedure

**Files:**

- Modify: `skills/brainstorming/SKILL.md` — spec review step directs to the procedure
- Modify: `skills/writing-plans/SKILL.md` — plan review step directs to the procedure
- Modify: `skills/subagent-driven-development/SKILL.md` — per-task review step, final review step, and the example task cycle direct to the procedure
- Modify: `skills/executing-plans/SKILL.md` — checkpoint review step directs to the procedure
- Modify: `skills/requesting-code-review/SKILL.md` — the act-on-feedback step directs to the procedure

**Spec requirement:** Gate wiring to the procedure; Selective fix dispatch (gate-side routing statements).

**Interface:**

- `brainstorming` — `### Spec Review`: before the fix-and-loop instructions, a step directs the main agent to adjudicate every finding per `receiving-code-review`. Endorsed findings are fixed through dispatched subagents. The reviewer re-dispatch carries the fixes, the rejection list, and the rejection reasons for confirmation. The loop-until-approved instruction stays.
- `writing-plans` — `## Step 5: Plan Review`: the same pattern as the spec review, with the plan as the artifact. The do-not-proceed instruction stays.
- `subagent-driven-development` — step 2e: the current evaluate-and-drop sentence is replaced by a direction to adjudicate every finding per `receiving-code-review` before acting. The implementer re-dispatch carries only the endorsed findings together with the original task and current state. The reviewer re-dispatch carries the updated evidence, the rejected findings, and the rejection reasons. Step 3 (final review) states the same adjudication direction. The example task cycle shows one adjudication step between the reviewer report and the re-dispatch.
- `executing-plans` — `### Step 4: Checkpoint Reviews`: a step directs to the adjudication procedure. The main agent applies endorsed Critical and Important fixes itself at this gate. Endorsed Minor findings are applied or deferred with a recorded deferral. The reviewer re-dispatch carries the fixes, the rejected findings, and the rejection reasons. The gate does not continue while endorsed Critical or Important fixes remain unapplied; a maintained Critical finding stops the gate per the escalation section of `receiving-code-review`.
- `requesting-code-review` — step 4 (`Act on feedback`): adjudicate every finding per `receiving-code-review` before acting. Endorsed Critical and Important findings go to dispatched fix subagents. Endorsed Minor findings are applied through the same path or noted for later with a recorded deferral. Rejected findings go back for confirmation. The red-flag section keeps its no-argument-with-valid-feedback rule.

**Behavior:**

- No gate keeps an instruction that contradicts the adjudication direction: the subagent-driven-development drop-beyond-contract sentence and the requesting-code-review unconditional fix-first bullets are replaced, not duplicated.
- Each gate names `receiving-code-review` as the procedure home.
- Each gate states its fix routing: dispatched subagents in `brainstorming`, `writing-plans`, `subagent-driven-development`, and `requesting-code-review`; the main agent itself in `executing-plans`.
- Prose follows writing-developer-facing-text pragmatic mode.

**Tests must prove:**

- `test_gates_reference_procedure` — the `rg` gate check returns a `receiving-code-review` match in each of the five gate skills, and the `adjudicat` search returns a match in each of the five gate skills.
- `test_gate_routing_stated` — each gate skill states whether endorsed fixes go to dispatched subagents or to the main agent.
- `test_no_stale_instructions` — the two stale-wording searches in the Commands section (`Drop findings` in `skills/subagent-driven-development/SKILL.md`, `Fix Critical issues immediately` in `skills/requesting-code-review/SKILL.md`) return no matches.
- `test_install_survives_gate_edits` — `tests/test-install.sh` passes.

**Check:** Run the Task 2 command blocks (the gate `rg` check and the two stale-wording searches), then `tests/test-install.sh` and `git diff --check`. Read each modified gate section and check it against the interface contracts.

- [ ] Edit the five gate skills per the interface contracts.
- [ ] Run the gate `rg` check and confirm five matches.
- [ ] Read each modified section against the contracts and confirm no superseded wording remains.
- [ ] Run `tests/test-install.sh` and `git diff --check`.
- [ ] Commit: `git add skills/ && git commit -m "docs: wire review gates to the adjudication procedure"`

---

### Task 3: Reviewer template grounding and rejection section

**Files:**

- Modify: `skills/brainstorming/spec-document-reviewer-prompt.md` — grounding material, grounded findings, pre-report verification, contract identification, rejection-confirmation section
- Modify: `skills/writing-plans/plan-document-reviewer-prompt.md` — same additions with plan-specific inputs
- Modify: `skills/subagent-driven-development/implementation-reviewer-prompt.md` — same additions with inlined living-spec text
- Modify: `skills/requesting-code-review/code-reviewer.md` — grounded findings, pre-report verification, contract identification, rejection-confirmation section

**Spec requirement:** Reviewer grounding material; Grounded findings in reviewer reports; Pre-report verification and contract anchoring; Reviewer template rejection section.

**Interface:**

- `spec-document-reviewer-prompt.md`:
  - Input list gains the living-spec path for the affected domain, with an explicit statement-that-it-is-absent placeholder for the cold-start case, and an instruction to the reviewer to check the spec delta against the living-spec material.
  - A governing-contract line identifies the proposal's stated requirements as the governing contract for this gate.
  - The output format demands, per finding: the artifact location (requirement or section), the concrete consequence, and the contract clause for a contract claim. An instruction tells the reviewer to omit a finding that cannot state them.
  - A pre-report verification instruction: re-check every finding against the artifact and the governing contract before reporting; report only findings that survive.
  - A rejection-confirmation section, placed immediately before the `## Output Format` block, filled only on a confirmation re-dispatch, with a placeholder per rejected finding and its rejection reason, instructing the reviewer to re-check the artifact and confirm the finding with its concrete consequence or withdraw it on technical grounds only, never withdrawing merely because the main agent rejects it.
- `plan-document-reviewer-prompt.md`: the same additions, with the affected source file paths as an unconditional input, the living-spec paths as a conditional input, an instruction to check the delta and the interface and file claims against that material, and the feature spec identified as the governing contract.
- `implementation-reviewer-prompt.md`: the required-inputs list gains the living-spec text for every MODIFIED requirement in the feature spec, included inline by the main agent; an instruction tells the reviewer to check each MODIFIED requirement against that text. The governing-contract line states the task text for a per-task review and the full feature spec for the final review. The output format gains the concrete consequence and contract-clause demands next to the existing `file:line` demand. The pre-report verification instruction and the rejection-confirmation section follow the same contracts.
- `code-reviewer.md`: the governing-contract line identifies the stated requirements supplied in the dispatch. The output format gains the concrete consequence and contract-clause demands next to the existing `file:line` demand. The pre-report verification instruction and the rejection-confirmation section follow the same contracts.

**Behavior:**

- The strict output headings (`## Document Review`, `## Code Review`), the verdict vocabulary, and the status lines stay unchanged. The agent definitions in `extensions/` stay unchanged.
- The calibration sections keep their existing anti-scope-creep content; the new instructions complement, not replace, them.
- The rejection-confirmation section states in each template that the main agent fills it only on a confirmation re-dispatch. All four templates place the rejection-confirmation section immediately before their `## Output Format` block.
- Prose follows writing-developer-facing-text pragmatic mode.

**Tests must prove:**

- `test_template_sections_present` — the living-spec search returns a match in each of the three grounding templates, and the four-term search returns at least one match per term (`concrete consequence`, `governing contract`, `re-check`, `Rejection`) per file across all four templates.
- `test_template_rejection_section_shape` — each template's rejection-confirmation section carries the rejection and reason placeholders, the fill-only-on-confirmation statement, and the technical-grounds instruction.
- `test_headings_unchanged` — the strict headings and status-line vocabulary are untouched.
- `test_install_survives_template_edits` — `tests/test-install.sh` passes.

**Check:** Run the Task 3 command blocks (the two template `rg` checks; run the four-term search once per term or confirm each term in the output), then `tests/test-install.sh` and `git diff --check`. Read each template against the interface contracts.

- [ ] Edit the four templates per the interface contracts.
- [ ] Run the template `rg` check and confirm matches in all four templates.
- [ ] Read each template against the contracts and confirm the headings and status lines are unchanged.
- [ ] Run `tests/test-install.sh` and `git diff --check`.
- [ ] Commit: `git add skills/ && git commit -m "docs: ground reviewer templates and add rejection confirmation"`

---

### Task 4: Workflow documentation

**Files:**

- Modify: `docs/FLOW_DESCRIPTION.md` — flow steps, gate table, and edge cases describe adjudication
- Modify: `README.md` — the `receiving-code-review` skill row describes adjudication

**Spec requirement:** Workflow documentation of adjudication.

**Interface:**

- `docs/FLOW_DESCRIPTION.md`:
  - BRAINSTORMING step 6 states: adjudicate the report before fixes; fix endorsed findings; re-dispatch the reviewer with the fixes, the rejected findings, and the rejection reasons for confirmation.
  - WRITING PLANS step 4 states the same pattern for the plan review.
  - IMPLEMENTATION step 2c-2d states: adjudicate the report; the implementer re-dispatch carries only endorsed findings; the reviewer re-dispatch carries the rejections for confirmation. Step 3b states: adjudicate, then apply endorsed fixes inline.
  - IMPLEMENTATION step 4 (final review) states the adjudication direction.
  - A note after the flow diagram states that ad-hoc reviews through `requesting-code-review` run the same adjudication loop: adjudicate findings per `receiving-code-review` before fixes, route endorsed fixes to dispatched subagents, and send rejections back for confirmation.
  - Gate Enforcement table gains a row: gate `Review-finding adjudication`, skill `receiving-code-review`, blocked behavior: the spec review, the plan review, the implementation reviews, the checkpoint reviews, and ad-hoc reviews do not advance on unadjudicated findings, and no fix dispatch carries rejected findings.
  - Edge Cases table gains a row: `Reviewer maintains a rejected Critical finding` — stop dispatches, escalate to the user with an architectural overview and a situation summary, resume per the user decision.
- `README.md`: the `receiving-code-review` table row reads as the adjudication skill: verdicts, endorsement, rejection, and selective fix dispatch.

**Behavior:**

- The documentation describes the current behavior only, with no references to removed behavior.
- The doc updates use the same terms as the skills: adjudicate, endorse, reject, governing contract, confirmation, escalation.
- Prose follows writing-developer-facing-text pragmatic mode.

**Tests must prove:**

- `test_flow_describes_adjudication` — the flow, the gate table, and the edge cases state adjudication before fixes at each review gate, the adjudication gate row, the maintained-Critical escalation edge case, and the ad-hoc review note.
- `test_readme_describes_skill` — the `receiving-code-review` row states verdicts, endorsement, rejection, and selective fix dispatch.
- `test_install_survives_doc_edits` — `tests/test-install.sh` passes.

**Check:** Run `tests/test-install.sh` and `git diff --check`. Read the modified flow, table rows, and README row against the interface contracts.

- [ ] Edit `docs/FLOW_DESCRIPTION.md` and `README.md` per the interface contracts.
- [ ] Check the flow text, the gate-table row, the edge-case row, and the README row against the contracts.
- [ ] Run `tests/test-install.sh` and `git diff --check`.
- [ ] Commit: `git add docs/FLOW_DESCRIPTION.md README.md && git commit -m "docs: document review-finding adjudication in flow and readme"`

---

## Self-review notes

- Spec coverage (spec → plan): per-finding adjudication, criteria, procedure, selective dispatch, dispatch content, confirmation loop, escalation → Task 1. Gate wiring and routing statements → Task 2. Grounding material, grounded findings, pre-report verification, contract anchoring, rejection section → Task 3. Documentation → Task 4. All 13 requirements have a task.
- Reverse coverage (plan → spec): every task names its spec requirements; no task covers material outside the spec. The trial record exists because the approved design mandates the RED/GREEN skill-trial evidence, and it rides with the requirement it tests.
- Placeholder scan: the plan contains no TBD, TODO, or vague contracts; every template and gate change names its sections and content.
- Signature consistency: the terminology matches the spec exactly — adjudicate, endorse, reject, governing contract, confirmation, escalation, inline case.
- Standards coverage: no task prescribes a workaround; the extension agent definitions and Python code stay untouched, as the proposal's out-of-scope list requires.
