# Proposal: Review-Finding Adjudication

## Intent

Review agents return findings at every workflow review gate: the spec review and the plan review, the per-task and final implementation reviews, the executing-plans checkpoint reviews, and ad-hoc reviews. The gate skills mostly tell the controller to fix what the report lists. `subagent-driven-development` says to evaluate findings and to drop demands beyond the task contract. `requesting-code-review` says to disagree with a wrong reviewer. No skill requires the controller to check each finding against the artifact before it acts, to separate findings with real consequences from misguided or hypothetical ones, or to send only endorsed findings to fix subagents.

Review agents work in isolation with an adversarial stance. That stance produces findings without full controller context. A report can contain misreadings, style preferences, and demanded robustness for scenarios the contract does not name. A controller that fixes every finding builds speculative behavior and widens task scope beyond the contract.

The same isolation degrades the reviewers' inputs. The spec reviewer and the plan reviewer receive no living-spec material, so they guess current behavior when they check a delta or a buildability claim. The plan reviewer is not directed to read the source files its plan modifies. The implementation reviewer receives the feature spec, but a MODIFIED requirement carries only the changed parts, so the reviewer cannot see the behavior it replaces. No template tells a reviewer which supplied material is the governing contract, and no template asks the reviewer to re-check a finding before it reports the finding. Bad inputs and unverified output feed the adjudication loop the controller must then run.

## Scope

**In scope:**

- One adjudication procedure in `receiving-code-review`: parse the report, verify each finding against the artifact, classify it as endorsed or rejected, record the verdicts, dispatch fixes for endorsed findings, send rejections back for confirmation, and escalate maintained Critical rejections.
- Endorsement criteria: the claim is factually correct for the artifact, and the finding has a concrete consequence. Rejection criteria: the claim is factually wrong, the finding has no concrete consequence, it rests on a scenario the governing contract does not require, or it demands work beyond the contract.
- Wiring into all six gates: the brainstorming spec review, the writing-plans plan review, the subagent-driven-development per-task and final reviews, the executing-plans checkpoint reviews, and the requesting-code-review feedback handling.
- Fix dispatch through subagents at the controller-mode gates. In executing-plans the controller is the implementer and applies endorsed fixes itself. Endorsed Critical and Important findings are fixed at the gate. The controller can defer an endorsed Minor finding and records the deferral.
- A rejection-confirmation section in the reviewer prompt templates `spec-document-reviewer-prompt.md`, `plan-document-reviewer-prompt.md`, `implementation-reviewer-prompt.md`, and `code-reviewer.md`.
- Grounding material in the reviewer dispatches: living-spec material for the spec reviewer, the plan reviewer, and the implementation reviewer, and affected source paths for the plan reviewer.
- A grounded-finding format in the four templates: every finding states its artifact location, its concrete consequence, and the contract clause for contract claims.
- A pre-report verification instruction and a governing-contract identification in the four templates.
- Updates to `docs/FLOW_DESCRIPTION.md` and `README.md`.

**Out of scope:**

- Extension code, Python code, and code tests.
- The child status contract, the report heading structure, and the review agent definitions.
- The `task` tool interface.

## Approach

Extend `receiving-code-review` with one procedure and reference it from every gate skill. The procedure runs six steps: parse the report into findings, verify each finding against the artifact, classify it, record the verdicts, dispatch fixes for endorsed findings, and send rejections back for confirmation.

The endorsement test has two parts. The claim must be factually correct for the artifact, and the finding must have a concrete consequence: it breaks or hides behavior, it violates the governing contract, or it omits contract-required work. The governing contract is the stated requirements that the artifact was produced against: the task text, the plan, the feature spec, or the stated requirements of an ad-hoc review. A finding fails the test when the artifact already handles the case, when it has no observable effect, when it demands handling for a hypothetical scenario the contract does not require, or when it demands changes beyond the contract scope. A finding with several claims is split into one finding per claim, and each claim is adjudicated separately.

Fix dispatch carries only endorsed Critical and Important findings. Endorsed Minor findings can be deferred, and the deferral is recorded. A fix prompt states the finding, the file paths, the governing contract, and the verification commands. Rejections go back to the same reviewer agent with the fixes and the rejection reasons. The re-dispatch instructs the reviewer to confirm or withdraw each rejection on technical grounds. The controller closes a withdrawn rejection and continues the gate loop over the endorsed findings. The controller closes a maintained rejection that is not Critical and records the disagreement. A maintained Critical rejection stops the workflow. The controller escalates to the user with an architectural overview of the problem area and a summary of the situation, and it starts no dispatch until the user decides.

In executing-plans the controller applies endorsed Critical and Important fixes itself, because the controller is already the implementer in that skill. The other gates dispatch fix subagents.

The upstream half improves what the reviewers receive and what they report. The templates gain the missing grounding material: living-spec material for the spec, plan, and implementation reviewers, and affected source paths for the plan reviewer, which the reviewer checks interface claims against. The templates gain a grounded-finding format: each finding names its artifact location, its concrete consequence, and the contract clause for a contract claim, and the reviewer omits a finding that cannot name them. The templates gain a pre-report verification instruction that mirrors the controller-side rule. The reviewer re-checks each finding against the artifact and the governing contract and reports only findings that survive. Each template names the governing contract for its gate, with the same definition the spec gives the main agent. Grounded findings make the controller's verification step cheap, and the pre-report check removes the misguided classes at the source.

Two alternatives are rejected. A dedicated adjudication skill duplicates most of the content of `receiving-code-review` and grows the skill count to sixteen. Inlining the procedure in each gate skill duplicates the same text in six places and lets the copies drift.

## Impact

The change touches six skill files, four reviewer prompt templates, and two documentation files. It adds no code. The extension agent definitions stay untouched: their finding shapes already accept the grounded-finding fields. The workflow gains one reviewer re-dispatch per gate review that produces rejections, and one escalation path that stops dispatches until the user decides. Gate loops converge on endorsed findings instead of the full report. Reviewer reports carry grounded findings, so the controller verifies claims instead of guessing what the reviewer read.
