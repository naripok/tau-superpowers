# Spec: Review-Finding Adjudication

## Domain: review-adjudication

### ADDED Requirements

#### Requirement: Per-finding adjudication before action

When a review-agent report arrives at a workflow review gate, the main agent MUST adjudicate every finding before it acts on any finding. For each finding it MUST check the claim against the cited artifact content and the governing contract. For each finding it MUST record one verdict, endorse or reject, with the reason.

##### Scenario: Verdicts before fixes

- GIVEN a review-agent report lists findings at a gate
- WHEN the main agent handles the report
- THEN it records an endorse or reject verdict with a reason for each finding before applying any fix
- AND each verdict rests on the cited artifact content and the governing contract

#### Requirement: Endorsement and rejection criteria

The main agent MUST endorse a finding when it meets all of these conditions:

- The claim is factually correct for the artifact.
- The finding has a concrete consequence.
- No rejection ground applies.

A concrete consequence is one of:

- The claim identifies behavior that the artifact breaks or hides.
- The claim identifies a violation of the governing contract.
- The claim identifies contract-required work that the artifact omits.

The main agent MUST reject a finding when at least one rejection ground applies:

- The claim is factually wrong for the artifact.
- The finding has no concrete consequence.
- The finding demands handling for a scenario the governing contract does not require.
- The finding demands changes beyond the contract scope.

A claim that the artifact does not exhibit at its stated location counts as factually wrong for the artifact.

The main agent MUST split a finding that contains several claims into one finding per claim, and it MUST adjudicate each claim separately.

The governing contract is the stated requirements that the artifact was produced against:

- The task text.
- The plan.
- The feature spec.
- The stated requirements of the proposal for the spec review.
- The stated requirements of an ad-hoc review.

##### Scenario: Misread claim

- GIVEN a finding states that the artifact misses a case
- AND the artifact handles the case
- WHEN the main agent adjudicates the finding
- THEN the verdict is reject with the artifact evidence as the reason

##### Scenario: Contract violation

- GIVEN a finding states that the artifact omits contract-required behavior
- AND the artifact omits the behavior
- WHEN the main agent adjudicates the finding
- THEN the verdict is endorse

##### Scenario: Hypothetical scenario

- GIVEN a finding demands handling for a scenario the governing contract does not require
- WHEN the main agent adjudicates the finding
- THEN the verdict is reject

##### Scenario: No concrete consequence

- GIVEN a finding states a style preference about artifact content
- AND the governing contract does not constrain the content
- AND no observable behavior changes
- WHEN the main agent adjudicates the finding
- THEN the verdict is reject on the no-consequence ground

##### Scenario: Compound finding

- GIVEN a finding contains a factually correct claim with a concrete consequence and a second claim that demands changes beyond the contract scope
- WHEN the main agent adjudicates the finding
- THEN the main agent splits the finding into one finding per claim
- AND the main agent records an endorse verdict for the first claim and a reject verdict for the second

#### Requirement: Adjudication procedure in receiving-code-review

The `receiving-code-review` skill MUST define the adjudication procedure for review-agent findings. The procedure MUST contain these steps in order:

1. Parse the report into findings.
2. Verify each finding against the artifact.
3. Classify each finding with the endorsement and rejection criteria.
4. Record the verdicts.
5. Apply endorsed findings. Apply or defer each endorsed Minor finding, and record a deferral.
6. Send rejections back for confirmation.

The procedure MUST state that the main agent acts only on endorsed findings and records every verdict with its reason. The skill MUST also carry the rejection confirmation loop and the escalation of maintained Critical rejections.

##### Scenario: Reader finds the procedure

- GIVEN a reader opens the `receiving-code-review` skill
- WHEN the reader searches for the review-agent adjudication procedure
- THEN the procedure lists the steps in order from parse to confirmation
- AND the procedure states that endorsed findings drive fixes and rejected findings go back for confirmation

#### Requirement: Gate wiring to the procedure

Each workflow gate that receives a review-agent report MUST direct the main agent to the adjudication procedure before it acts on findings. The gates are:

- The spec review in `brainstorming`.
- The plan review in `writing-plans`.
- The per-task review and the final review in `subagent-driven-development`.
- The checkpoint reviews in `executing-plans`.
- The feedback handling in `requesting-code-review`.

The `brainstorming`, `writing-plans`, `subagent-driven-development`, and `requesting-code-review` gates MUST state that endorsed fixes go to dispatched subagents. The `executing-plans` checkpoint MUST state that the main agent applies endorsed fixes itself.

##### Scenario: Reader finds the direction at each gate

- GIVEN a reader opens the review-handling section of one gate skill
- WHEN the reader reads the step that handles review findings
- THEN the step directs the main agent to the adjudication procedure before any fix action
- AND the step states whether endorsed fixes go to dispatched subagents or to the main agent itself

#### Requirement: Selective fix dispatch

The main agent MUST apply endorsed Critical and Important findings through fix dispatches that carry only endorsed findings. A fix dispatch MUST NOT carry a rejected finding. The executing-plans checkpoint is the inline case. In the inline case the main agent is the implementer and MUST apply endorsed Critical and Important findings itself instead of dispatching fixes. For an endorsed Minor finding the main agent MUST apply it through the same fix path or defer it. The main agent MUST record a deferred Minor finding, and the deferred finding MUST NOT block gate closure.

##### Scenario: Mixed report at a gate that dispatches fixes

- GIVEN a report with one endorsed Critical finding, one endorsed Important finding, and one rejected finding
- WHEN the main agent dispatches fixes at a gate that dispatches fixes
- THEN the fix dispatch contains the endorsed findings
- AND the fix dispatch does not contain the rejected finding

##### Scenario: Inline checkpoint fix

- GIVEN the executing-plans checkpoint review returns endorsed Critical and Important findings
- WHEN the main agent continues
- THEN the main agent applies the endorsed fixes itself without a fix dispatch

##### Scenario: Deferred Minor finding

- GIVEN adjudication endorses a Minor finding
- WHEN the main agent defers the finding
- THEN the main agent records the deferral
- AND the deferred finding does not block gate closure

##### Scenario: Applied Minor finding

- GIVEN adjudication endorses a Minor finding
- AND the main agent does not defer the finding
- WHEN the main agent applies the fixes
- THEN the main agent applies the finding through the same fix path as endorsed Critical and Important findings

#### Requirement: Fix dispatch content

A fix dispatch MUST carry, for each endorsed finding it contains: the finding text, the artifact locations, the governing contract, and the verification commands that the review report provides. If the report provides no verification commands for a finding, the fix dispatch MUST state their absence.

##### Scenario: Fix dispatch is self-contained

- GIVEN adjudication endorses one Critical finding at a gate that dispatches fixes
- AND the review report provides verification commands for the finding
- WHEN the main agent builds the fix dispatch
- THEN the dispatch contains the finding text, the artifact locations, the governing contract, and the verification commands

##### Scenario: Fix dispatch without verification commands

- GIVEN adjudication endorses one Critical finding
- AND the review report provides no verification commands for the finding
- WHEN the main agent builds the fix dispatch
- THEN the dispatch states the absence of verification commands

#### Requirement: Rejection confirmation loop

When adjudication rejected at least one finding, the main agent MUST send every rejected finding back to the same reviewer agent. The re-dispatch that follows the fixes MUST contain the fix results when endorsed findings exist, every rejected finding, and the rejection reason for each. The re-dispatch MUST instruct the reviewer to confirm or withdraw each rejected finding on technical grounds only. When adjudication rejected every finding, the main agent MUST send the rejections back with no fix results.

##### Scenario: Confirmation re-dispatch content

- GIVEN a gate review produced one endorsed finding and one rejected finding
- WHEN the main agent completes the fixes and re-dispatches the reviewer
- THEN the re-dispatch contains the fix results, the rejected finding, and the rejection reason
- AND the re-dispatch instructs the reviewer to confirm or withdraw the rejected finding on technical grounds only

##### Scenario: Withdrawn rejection closes

- GIVEN the reviewer withdraws a rejected finding in the confirmation response
- WHEN the main agent continues the gate
- THEN the finding no longer appears in fix dispatches or findings the gate treats as open

##### Scenario: No rejections skip confirmation

- GIVEN adjudication endorses every finding in a report
- WHEN the main agent applies the fixes
- THEN the gate loop continues without a rejection-confirmation re-dispatch

##### Scenario: Every finding rejected

- GIVEN adjudication rejects every finding in a report
- WHEN the main agent re-dispatches the reviewer
- THEN the re-dispatch carries every rejection with its reason
- AND the re-dispatch carries no fix results

#### Requirement: Escalation of maintained Critical rejections

When the reviewer maintains a rejected Critical finding, the main agent MUST stop all workflow dispatches. The main agent MUST present the disagreement to the user with an architectural overview of the problem area and a summary of the situation. The summary MUST state the finding, the rejection reason, the maintenance reason of the reviewer, and the decision the user must make. The main agent MUST NOT start further workflow dispatches before the user decides. When the reviewer maintains a rejected finding that is not Critical, the main agent MUST record the disagreement, MUST treat the finding as closed, and MUST continue the gate. After the user decides, the main agent MUST apply the decision:

- A decision that upholds the finding makes it an endorsed finding. The main agent applies it through the normal fix path of the gate.
- A decision that upholds the rejection closes the finding. The main agent records the decision and continues the gate.

##### Scenario: Maintained Critical rejection stops the workflow

- GIVEN the reviewer maintains a rejected Critical finding in the confirmation response
- WHEN the main agent reads the response
- THEN the main agent presents an architectural overview and a situation summary to the user
- AND the summary states the finding, the rejection reason, the maintenance reason, and the decision the user must make
- AND the main agent starts no further workflow dispatch before the user decides

##### Scenario: Maintained Important rejection closes

- GIVEN the reviewer maintains a rejected Important finding in the confirmation response
- WHEN the main agent continues the gate
- THEN the main agent records the disagreement and treats the finding as closed

##### Scenario: User upholds the finding

- GIVEN the user decides that a maintained Critical finding stands
- WHEN the main agent applies the decision
- THEN the main agent treats the finding as endorsed and applies it through the normal fix path of the gate

##### Scenario: User upholds the rejection

- GIVEN the user decides that the rejection stands
- WHEN the main agent applies the decision
- THEN the main agent records the decision, treats the finding as closed, and continues the gate

#### Requirement: Reviewer grounding material

The `spec-document-reviewer-prompt.md` and `plan-document-reviewer-prompt.md` templates MUST instruct the main agent to name the paths of the grounding material, and MUST instruct the reviewer to read it. The `implementation-reviewer-prompt.md` template MUST instruct the main agent to include the grounding text in the dispatch.

- The spec reviewer template MUST instruct the main agent to name the living-spec path for the affected domain when a living spec exists. When no living spec exists, the template MUST instruct the main agent to state that in the dispatch. The template MUST instruct the reviewer to check the delta against the living-spec material.
- The plan reviewer template MUST instruct the main agent to name the affected source file paths. When living specs exist, the template MUST instruct the main agent to name the living-spec paths too. The template MUST instruct the reviewer to check the delta and the interface and file claims against that material.
- The implementation reviewer template MUST instruct the main agent to include the living-spec text for every MODIFIED requirement in the feature spec. The template MUST instruct the reviewer to check each MODIFIED requirement against that text.

##### Scenario: Spec reviewer template names the living spec

- GIVEN a reader opens the spec reviewer template
- WHEN the reader reads the input instructions
- THEN the template instructs the main agent to name the living-spec path when a living spec exists
- AND the template instructs the main agent to state the absence when no living spec exists
- AND the template instructs the reviewer to check the delta against the living-spec material

##### Scenario: Plan reviewer template names files and specs

- GIVEN a reader opens the plan reviewer template
- WHEN the reader reads the input instructions
- THEN the template instructs the main agent to name the affected source file paths
- AND the template instructs the main agent to name the living-spec paths when living specs exist
- AND the template instructs the reviewer to check the delta and the interface and file claims against that material

##### Scenario: Implementation reviewer template carries modified behavior

- GIVEN a reader opens the implementation reviewer template
- WHEN the reader reads the required inputs
- THEN the template instructs the main agent to include the living-spec text for every MODIFIED requirement
- AND the template instructs the reviewer to check each MODIFIED requirement against that text

#### Requirement: Grounded findings in reviewer reports

Each reviewer prompt template MUST require every finding to state the artifact location the finding rests on and the concrete consequence. A finding that claims a contract problem MUST state the contract clause it rests on. Each template MUST instruct the reviewer to omit a finding that cannot state them.

##### Scenario: Finding format demands grounding

- GIVEN a reader opens one of the four reviewer prompt templates
- WHEN the reader reads the finding format
- THEN the format demands the artifact location and the concrete consequence for every finding
- AND the format demands the contract clause for a finding that claims a contract problem
- AND the template instructs the reviewer to omit a finding that cannot state them

#### Requirement: Pre-report verification and contract anchoring

Each reviewer prompt template MUST instruct the reviewer to re-check every finding against the artifact and the governing contract before it reports the finding. Each template MUST instruct the reviewer to report only findings that survive the re-check. Each template MUST identify which supplied material is the governing contract for its gate.

##### Scenario: Re-check before reporting

- GIVEN a reader opens one of the four reviewer prompt templates
- WHEN the reader reads the review instructions
- THEN the template instructs the reviewer to re-check every finding against the artifact and the governing contract before reporting
- AND the template instructs the reviewer to report only findings that survive the re-check

##### Scenario: Governing contract identified

- GIVEN a reader opens one of the four reviewer prompt templates
- WHEN the reader looks for the governing contract
- THEN the template identifies the supplied material that is the governing contract for its gate

#### Requirement: Reviewer template rejection section

The reviewer prompt templates `spec-document-reviewer-prompt.md`, `plan-document-reviewer-prompt.md`, `implementation-reviewer-prompt.md`, and `code-reviewer.md` MUST each contain a rejection-confirmation section that the main agent fills only on a confirmation re-dispatch. The section MUST carry a placeholder for each rejected finding with its rejection reason. The section MUST instruct the reviewer to re-check the artifact and to confirm a finding with its concrete consequence or withdraw it. The section MUST state that the reviewer decides on technical grounds and does not withdraw a finding merely because the main agent rejects it.

##### Scenario: Template carries the section

- GIVEN a reader opens one of the four reviewer prompt templates
- WHEN the reader searches for the rejection-confirmation section
- THEN the section carries rejection and reason placeholders
- AND the section states that the main agent fills it only on a confirmation re-dispatch
- AND the section instructs technical confirmation or withdrawal

#### Requirement: Workflow documentation of adjudication

`docs/FLOW_DESCRIPTION.md` MUST describe adjudication before fixes at the spec review, the plan review, the implementation reviews, the checkpoint reviews, and ad-hoc reviews through the `requesting-code-review` gate. Its gate table MUST contain a review-finding adjudication row that covers those gates. Its edge cases MUST contain the maintained Critical rejection escalation. `README.md` MUST describe `receiving-code-review` as the adjudication skill.

##### Scenario: Flow description covers the gates

- GIVEN a reader opens `docs/FLOW_DESCRIPTION.md`
- WHEN the reader reads the flow, the gate table, and the edge cases
- THEN the flow states adjudication before fixes at each review gate
- AND the gate table contains the review-finding adjudication row
- AND the edge cases contain the maintained Critical rejection escalation

##### Scenario: README describes the skill

- GIVEN a reader opens `README.md`
- WHEN the reader reads the skill table row for `receiving-code-review`
- THEN the row describes verdicts, endorsement, rejection, and selective fix dispatch
