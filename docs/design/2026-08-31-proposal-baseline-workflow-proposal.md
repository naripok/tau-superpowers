# Proposal: Proposal-baseline development workflow

## Intent

The current workflow asks the operator to approve both a proposal and a feature spec. It reviews only the feature spec before operator review.

The revised workflow makes the reviewed proposal the only formal operator approval artifact. The proposal author uses the brainstorm conversation to transfer accepted decisions into that proposal. The conversation is elicitation, not an approval gate.

A cold-reader reviewer checks the proposal without brainstorm history. The reviewer checks semantic closure, clarity, consistency, brownfield grounding, risk classification, and actionable completeness. It cannot check a decision that the proposal omits entirely. The operator checks that the reviewed proposal captures the intended change.

After approval, the exact approved proposal version is the sole source of operator intent. Spec authors, reviewers, planners, and implementers use approved artifacts and repository evidence, not chat history.

## Brownfield Baseline

The `workflow-governance` domain exists but has no living spec. This change treats it as an undocumented existing domain, not a new domain.

Relevant baseline evidence includes:

- `skills/brainstorming/SKILL.md`, which requires proposal and feature-spec creation, feature-spec review, and operator approval of both artifacts.
- `skills/brainstorming/spec-document-reviewer-prompt.md`, which reviews the feature spec against the proposal but does not review the proposal.
- `skills/writing-plans/SKILL.md` and its reviewer prompt, which use the feature spec as the behavioral contract and the proposal as architecture context.
- `skills/subagent-driven-development/SKILL.md`, `skills/executing-plans/SKILL.md`, and their prompts, which govern implementation and implementation review.
- `skills/finishing-a-development-branch/SKILL.md`, which verifies work and synchronizes living specs before integration.
- `skills/using-superpowers/SKILL.md`, which currently treats artifact-path existence as evidence that brainstorming completed.
- `extensions/superpowers-subagent/agents/document-review.md`, `README.md`, and `docs/FLOW_DESCRIPTION.md`, which describe reviewer scope and workflow handoffs.

The workflow consumers are operators, proposal authors, artifact reviewers, planners, implementers, and repository maintainers. Its interfaces are the proposal, feature spec, plan, living spec, review prompts, review reports, and implementation dispatches. Its contracts include gate order, artifact ownership, review inputs, approval status, and integration eligibility.

No material disagreement exists about current gate order among the authoritative skill files. The material baseline gaps are missing proposal review, dual operator approval, ambiguous brownfield handling, and dispatch-only design repair. The documents differ in detail because no living spec currently unifies this domain.

The change affects development operations, not product runtime behavior. Incorrect gates can still admit unintended work or block valid work. Rollout requires installing the changed skills and reloading active sessions. Rollback uses a repository revert followed by reinstallation.

## Required Outcomes

- Every persisted workflow artifact is understandable without brainstorm history.
- The proposal author transfers every accepted decision that can affect downstream work into the proposal.
- A cold-reader reviewer checks the complete proposal before the operator sees it.
- The operator formally approves only the reviewed proposal.
- The approved proposal version becomes the sole source of operator intent.
- A fresh agent derives the feature spec without brainstorm history.
- For an undocumented existing domain, that spec formalizes all relevant post-change behavior, including unchanged baseline behavior.
- The spec review checks semantic proposal-to-spec fidelity and rejects invented decisions.
- Every non-Direct change resolves blocking decisions and receives reviewer approval before planning.
- Brownfield work establishes a relevant baseline and impact analysis before it defines a delta.
- Planning maps changed behavior to implementation tasks and unchanged baseline behavior to preservation checks.
- The plan review checks feature-spec behavior coverage and proposal-owned constraints before execution.
- Implementation prompts do not repair or resolve design only inside a dispatch.
- Every edit to an approved proposal, or a later depth escalation, returns to cold review and operator reapproval.
- Workflow depth follows deterministic selection rules, reassessment points, and level-specific gates.
- Each automated gate uses one fresh reviewer per artifact version. Each High-risk spec or final review makes explicit contract and risk passes.
- Final acceptance checks the approved proposal and feature spec before living-spec synchronization and integration.
- Review gates use temporary dispositions instead of a permanent coverage ledger.

## Scope

**In scope:**

- `using-superpowers`: define depth selection, reassessment, and completion gates.
- `brainstorming`: establish brownfield behavior, write and review the proposal, obtain proposal-only approval, and derive the feature spec.
- Review prompts and dispatch logic: enforce cold-reader closure, semantic fidelity, one reviewer per artifact version, and High-risk two-pass reviews.
- `writing-plans` and its reviewer: use the proposal and feature spec as complementary contracts.
- Implementation workflows and prompts: prohibit dispatch-only design repair and preserve approved constraints.
- Finishing: check final acceptance, synchronize the living spec, and block premature integration.
- `document-review`: include proposals in its supported document scope.
- Workflow documentation, a new `workflow-governance` living spec, and skill behavior tests.

**Out of scope:**

- Changes to the Tau extension or `task` tool.
- A permanent requirements ledger or persisted coverage matrix.
- Mandatory requirement-category labels in operator-facing proposals.
- Operator approval of the feature spec, plan, or living-spec synchronization.
- A full regulated systems-engineering process.
- Domain-specific deployment, security, or migration procedures.

## Assumptions

None.

## Constraints

- The reviewed proposal is the only formal operator approval artifact.
- Conversation remains elicitation and does not become a separate approval gate.
- Downstream agents do not use brainstorm history.
- Direct changes remain outside the proposal, feature-spec, and plan flow only under the defined Direct test.
- Reviewer traceability remains temporary and does not become a committed ledger.
- Feature specs use RFC 2119 keywords and GIVEN/WHEN/THEN scenarios. Every requirement name is descriptive and under 50 characters.
- Every automated review gate applies `docs/specs/review-adjudication.md` as an unchanged cross-domain contract.
- Each automated review gate uses one fresh reviewer per artifact version. A High-risk spec or final reviewer completes two explicit passes before one report and verdict.
- Before the workflow persists any non-Direct artifact or implementation change, it applies the branch and worktree protection from `using-git-worktrees`. No development work lands directly on the default branch.
- Living-spec synchronization precedes integration. It applies accepted feature-spec changes idempotently and preserves unchanged behavior.
- After finishing gates pass, integration remains operator-controlled. The workflow offers only local merge or pull request, and operator silence leaves the branch untouched.
- The implementation does not modify extension code.

## Unresolved Decisions

None.

## Approach

### Operator intent and artifact ownership

The proposal baseline separates operator intent from downstream formalization. Each artifact has one role and one owner.

| Artifact or input | Author or owner | Governing role | Approval or review |
| --- | --- | --- | --- |
| Brainstorm conversation | Operator and proposal author | Elicitation input for the proposal author only | No formal approval status |
| Baseline evidence | Proposal author | Grounds current behavior, discrepancies, consumers, interfaces, contracts, and impact | Checked during proposal review |
| Proposal | Proposal author, then operator | Intent, scope, acceptance, externally material or binding architecture, operator-selected constraints, assumptions, risks, and non-goals | Cold-reader approval, then operator approval of the exact reviewed version |
| Proposal approval identity | Workflow controller | Identifies the exact approved proposal content | Recorded as workflow state, not a second operator-facing artifact |
| Temporary proposal review report | Cold-reader reviewer | Checks the proposal on its own terms and against named repository evidence | Discarded after the gate closes |
| Feature spec | Fresh spec author | Complete relevant observable post-change behavior and the delta against established current behavior | Automated spec-review approval only |
| Temporary spec dispositions | Spec reviewer | Classifies and disposes every governing proposal claim | Discarded after the gate closes |
| Implementation plan | Planner | File decomposition, internal interfaces, task contracts, and tests within approved boundaries | Automated plan-review approval only |
| Temporary plan review report | Plan reviewer | Checks spec behavior coverage, proposal constraints, buildability, and task proof | Discarded after the gate closes |
| Implementation and tests | Implementer | Realizes the approved proposal, feature spec, and reviewed plan | Per-level implementation reviews |
| Temporary implementation review reports | Implementation reviewers | Check task results and final acceptance against the approved contracts | Discarded after their gates close |
| Living spec | Finishing workflow | Canonical, semantically closed current behavior after acceptance | Automated synchronization check only |

The workflow records an approval identity for the exact proposal content. A commit identity or content digest satisfies this requirement. It does not create a second operator-facing approval artifact.

### Ordered end-to-end state flow

Every non-Direct change follows these states in order. The minimal baseline pass and provisional classification can precede worktree creation only while the workflow persists no artifact or implementation change.

1. **Minimal baseline established:** Inspect enough repository evidence to identify the domain status and classification triggers.
2. **Provisionally classified:** Apply the depth rules and record the selected level, known facts, and unresolved classification facts.
3. **Protected worktree established:** Invoke `using-git-worktrees`. Keep every persisted non-Direct artifact and implementation change on its protected branch, not directly on the default branch.
4. **Proposal drafted:** Complete baseline discovery and proposal content at the selected depth. Transfer accepted brainstorm decisions into the proposal.
5. **Proposal reviewed:** Resolve cold-reader findings. The reviewer approves the exact candidate proposal.
6. **Proposal approved:** The operator approves that reviewed proposal version. This state establishes the sole operator-intent baseline.
7. **Feature spec derived:** A fresh context derives complete relevant behavior from the approved proposal and established baseline.
8. **Feature spec reviewed:** Resolve every disposition and finding. The spec reviewer approves before planning.
9. **Plan written:** Map changed behavior to implementation tasks. Map unchanged baseline behavior to preservation or regression checks.
10. **Plan reviewed:** Confirm decomposition and resolve plan findings. The plan reviewer approves before execution.
11. **Implementation reviewed:** Execute at the selected depth and complete required per-task or inline reviews.
12. **Final acceptance passed:** Reassess depth from accumulated evidence. Complete review, acceptance checks, and fresh repository verification.
13. **Living spec synchronized:** Apply accepted behavior idempotently to a living spec. Check semantic closure, fidelity, and preservation of unchanged behavior.
14. **Integrated:** Integrate only after every prior gate remains valid and the operator selects local merge or pull request.

Artifact existence does not establish a state. Each review or approval attaches to the exact reviewed inputs.

An edit invalidates each review or approval of the edited artifact. A changed upstream input also invalidates every affected downstream review. The workflow restarts at the earliest invalidated state.

### Brownfield baseline branches

The proposal author selects one branch from repository evidence:

1. **Domain with a living spec:** Use the living spec as the current-behavior contract. Inspect relevant code, tests, interfaces, consumers, contracts, and documentation to identify impact and discrepancies.
2. **Existing undocumented domain:** Reconstruct complete relevant current behavior from code, tests, interfaces, consumers, contracts, documentation, and operational evidence. Record evidence sources and conflicts in the proposal.
3. **Genuinely new domain:** Search for existing behavior, interfaces, consumers, contracts, and operational dependencies. Record evidence that the domain is absent and describe adjacent impact.

A missing living spec does not prove that a domain is new. A source discrepancy is material when different resolutions can change a proposal-owned decision. Material discrepancies must be resolved in the proposal before planning. The proposal uses `None` when a required impact category has no relevant content.

For an existing undocumented domain, the feature spec uses the existing feature-spec format. It formalizes complete relevant post-change behavior. This includes established unchanged baseline behavior and requested changes. `ADDED` means addition to the absent living spec, not that every behavior needs implementation work. Planning maps changed behavior to implementation tasks. It maps unchanged baseline behavior to preservation or regression checks, not change tasks. This lets finishing create a complete living spec without inventing behavior or adding a permanent artifact.

### Proposal review and formal approval

The proposal author can use the complete brainstorm conversation. The author transfers every accepted behavioral, scope, architecture, threshold, exception, constraint, assumption, risk, and acceptance decision.

The cold-reader reviewer receives no brainstorm history. It checks semantic closure, clarity, consistency, brownfield grounding, risk classification, and actionable completeness. It checks whether present claims and required sections support downstream work. It does not certify that the author transferred a decision omitted entirely from the proposal.

Every non-Direct proposal contains this minimum content:

- Intent.
- Relevant current behavior and evidence.
- Required outcomes.
- Representative acceptance examples.
- Scope and non-goals.
- Constraints.
- Approach and alternatives.
- Impact and risks.
- Assumptions.
- Unresolved decisions.

Every proposal uses `None` when a required section has no relevant content. A Bounded proposal can make its sections concise. A Standard proposal gives complete relevant impact. A High-risk proposal additionally covers compatibility, migration, rollout, rollback, observability, recovery, and each approved risk treatment.

An unresolved controlled decision blocks cold-review approval and operator approval. The operator reviews the complete, cold-reviewed proposal. Operator approval validates that the proposal captures the intended change. A requested revision returns the proposal to cold review before another operator approval.

### Semantic spec derivation and temporary dispositions

The feature-spec author receives the approved proposal, baseline evidence, and relevant living specs. It receives no brainstorm history. It preserves each claim's actor, trigger, timing, ordering, scope, conditions, exceptions, strength, threshold, and observable result.

The author stops when formalization exposes a decision that can produce different controlled behavior or constraints. It does not select a plausible policy.

A governing proposal claim prescribes downstream behavior, observable quality, work, architecture, a constraint, acceptance, risk treatment, or exclusion. The spec reviewer assigns one temporary classification and disposition to every governing claim, not to every prose sentence:

| Governing claim classification | Required temporary disposition |
| --- | --- |
| Observable behavior, including in-scope behavior | `Mapped to requirement`: cite requirements and scenarios that preserve the claim |
| Observable quality constraint | `Mapped to requirement`: cite measurable requirements and scenarios |
| Internal constraint or non-behavioral work | `Retained for planning`: cite the proposal text and name the required plan-review check or work |
| Acceptance example | `Mapped to scenario`: cite one or more equivalent spec scenarios |
| Exclusion or non-goal | `Explicitly excluded`: confirm that no requirement or implementation work includes it |

Binding architecture, scope obligations, assumptions, and approved risk treatments are internal constraints unless they define observable behavior. In-scope work without observable behavior is retained for planning. Descriptive baseline evidence, source citations, and rationale are checked for grounding. They receive no disposition unless they also prescribe downstream work.

A governing claim with missing, ambiguous, conflicting, or invented treatment receives `Blocked`. Reviewer approval requires a non-blocking disposition for every governing claim.

These dispositions exist only in the review report and gate context. The workflow does not commit them or maintain a coverage ledger. Later reviewers recreate the traceability needed for their own artifact.

### Proposal-owned architecture and plan-owned detail

The proposal owns structure that is externally material or otherwise binding. This includes component boundaries that affect consumers, compatibility, data, security, operations, or acceptance. It also includes any internal choice or constraint that the operator selected as part of a tradeoff.

The plan owns file decomposition, private data structures, internal signatures, task boundaries, and equivalent implementation choices. Those choices must remain within approved behavior, scope, architecture, constraints, and non-goals.

A plan can choose among equivalent internal implementations without operator reapproval. A choice that changes externally material structure or an operator-selected constraint crosses the boundary and requires proposal revision and reapproval.

### Deterministic workflow depth

The workflow starts with a minimal evidence pass before classification. This pass identifies current domain status and the known or unresolved status of every risk trigger. The workflow then selects a provisional depth and writes the proposal at that depth.

The workflow applies the Direct test after this pass. A change is Direct only when established facts show that it changes representation without changing program or controlled-document meaning. It must have no behavioral, contract, data, security, privacy, operational, or controlled-document effect. It must also require no design decision.

A controlled document defines required or current behavior, workflow policy, acceptance, or operations. Proposals, feature specs, plans, living specs, policies, and runbooks are controlled documents.

If the Direct test fails, the workflow applies the High-risk triggers. High-risk applies when the change affects any of these areas:

- An externally consumed contract or compatibility commitment.
- A schema, stored-data migration, or data recovery procedure.
- Security, privacy, authentication, authorization, or secrets.
- Concurrency, distributed consistency, or race safety.
- Runtime event ordering or data ordering whose failure affects observable behavior, safety, consistency, or integrity.
- A destructive or irreversible action.
- Production availability or compliance.
- Rollback that needs coordinated recovery or cannot use a safe revert.

Workflow gate ordering alone is not a High-risk ordering trigger.

A behavioral domain is one named subject area whose current behavior belongs in one living spec.

When classification facts are resolved and no High-risk trigger applies, the change is Bounded only when these pre-plan conditions all hold:

- It affects one behavioral domain.
- The baseline has no material source discrepancy.
- It needs no coordination across a runtime or deployment boundary, consumer, producer, external service, or operational process.
- A single safe revert restores the prior state without migration or recovery work.
- It has one cohesive implementation responsibility.

Every other non-Direct change is Standard. File count and line count never select a higher level by themselves. A mechanical change across many files remains Direct when it passes the Direct test. Future plan task count never selects the provisional level.

The escalation order is Direct, Bounded, Standard, then High-risk. The highest applicable level wins. Any unresolved fact about a High-risk trigger selects provisional High-risk until evidence resolves it. Otherwise, unresolved non-High-risk facts take their least-escalating values for base-level calculation. All such unknowns then cause one aggregate one-level escalation, capped at High-risk. Multiple unknowns do not cause multiple escalations. An operator-selected higher level takes effect only when the approved proposal records it.

Planning confirms decomposition. A provisionally Bounded change can have no more than two cohesive tasks. If a contract-complete plan needs more than two tasks or reveals another higher trigger, planning stops. The workflow escalates and repeats required proposal review and approval before execution.

This proposal is Standard because it changes coordinated workflow contracts across proposal, spec, plan, implementation, and finishing stages. It changes workflow gate ordering, not runtime event or data ordering, and has no High-risk trigger.

### Per-level gates

| Gate | Direct | Bounded | Standard | High-risk |
| --- | --- | --- | --- | --- |
| Baseline and classification | Minimal evidence and Direct test | Concise relevant baseline in proposal | Complete relevant baseline and impact | Standard content plus applicable compatibility, migration, rollout, rollback, observability, recovery, and risk treatment |
| Proposal | None | Concise minimum content, one cold review, operator approval | Complete minimum content and relevant impact, one cold review, operator approval | Standard content plus each High-risk category, one cold review, operator approval |
| Feature spec | None | Concise complete spec and one spec review | Full spec and one spec review | Full spec and one two-pass spec review |
| Plan | None | Concise one-to-two-task plan and plan review | Full task plan and plan review | Map every approved risk treatment and applicable High-risk obligation, then plan review |
| Execution | Targeted edit and relevant checks | Inline execution of one or two tasks | Task execution with per-task review | Produce evidence mapped by the High-risk plan, with per-task review |
| Final acceptance | Relevant repository checks | One final whole-change review and fresh verification | One final whole-change review and fresh verification | One two-pass final review, acceptance checks, and fresh verification |
| Living-spec sync and integration | None, because no controlled-document effect is allowed | Synchronize, check, then integrate | Synchronize, check, then integrate | Synchronize, check, then integrate after final-review approval |

All non-Direct levels retain semantic fidelity, proposal change control, brownfield grounding, artifact reviews, and the ban on dispatch-only design repair. Bounded changes reduce artifact length and task count, not contract integrity.

A High-risk plan maps every applicable compatibility, migration, rollout, rollback, observability, recovery, and approved risk-treatment obligation to a task or check with named evidence. The plan can use `None` only when the approved proposal marks the category inapplicable or approves a no-action treatment. High-risk execution produces every mapped item of evidence. This workflow does not define domain-specific procedures.

### Reassessment and change control

The workflow selects initial depth after the minimal baseline pass. It then reassesses depth whenever classification evidence changes. Expected evidence-bearing points include planning, artifact review, implementation, and final acceptance with all accumulated evidence.

The workflow does not add consecutive reassessments when no evidence changes. Before operator approval, resolution of a classification fact can raise or lower provisional depth. The proposal author updates the proposal to that depth before cold review. A fact resolved after cold review invalidates that review and requires another cold review of the updated proposal.

After operator approval, new evidence that selects a higher depth stops work and enters proposal change control. The proposal author revises depth, impact, risk content, and required sections. The workflow then repeats cold review and operator approval and invalidates affected downstream artifacts.

A postapproval reassessment never silently lowers the approved depth. Work can retain the approved higher depth. Any requested lower approved depth is a proposal change and takes effect only after cold review and operator reapproval.

After proposal approval, every proposal edit follows the same stop-and-reapprove path, including a format-only edit. A format-only correction can remain in an automated review loop only for a downstream derived artifact when meaning cannot change. Uncertainty about meaning returns to proposal revision. Repository facts, paths, diffs, logs, and command output can remain prompt-only evidence only when they cannot change a controlled decision.

### Single High-risk two-pass review

Each automated gate uses one fresh reviewer for each artifact version. The workflow does not dispatch duplicate reviewers for one artifact version and review contract.

At the High-risk spec and final gates, that reviewer completes two explicit passes before it issues one report and verdict:

1. **Contract pass:** Check semantic fidelity, requirement coverage, scope and constraints, testability, and invented decisions.
2. **Risk pass:** Check applicable compatibility, migration, rollback, security and privacy, failure recovery, observability, operations, and approved risk-treatment evidence.

A re-dispatch is valid only when the artifact changed, missing context was added, rejected findings return for confirmation, or the prior result was `BLOCKED` or `NEEDS_CONTEXT`. Each valid re-dispatch changes the artifact, inputs, or review task.

### Artifact-derived execution and finishing

Plans and implementation dispatches derive controlled design context only from the approved proposal, reviewed feature spec, and reviewed plan. A controller cannot repair missing intent, behavior, architecture, thresholds, exceptions, or constraints only in a child prompt.

Prompt-only repository evidence is valid when it selects no controlled outcome. If evidence can change a controlled decision, the workflow stops and repairs the proposal baseline.

Final review checks observable behavior against the feature spec and binding design against the proposal. Final acceptance also checks proposal acceptance examples and fresh repository verification.

After acceptance, the finishing workflow synchronizes observable current behavior into the living spec. It updates an existing living spec or creates one for an undocumented or new domain. Synchronization applies accepted feature-spec changes idempotently and preserves unchanged living-spec behavior. The result must be semantically closed and must not rely on the feature proposal, plan, or conversation for current behavior.

For this existing undocumented domain, the complete reviewed post-change feature spec supplies the initial living spec. It contains unchanged baseline behavior and accepted changes, so finishing does not invent missing behavior.

Integration occurs only after synchronization passes its automated check. The workflow requests no operator approval for the feature spec, plan, or living spec. After every finishing gate passes, it offers only local merge or pull request. It performs only the option that the operator selects. Operator silence leaves the branch untouched.

## Alternatives Rejected

- **Keep operator approval for the proposal and feature spec:** This duplicates the operator gate and weakens the proposal baseline.
- **Ask the cold reader to certify brainstorm-decision capture:** A reviewer without brainstorm history cannot detect a decision omitted entirely from the proposal.
- **Let downstream agents use chat history:** This creates an unreviewed source of intent and prevents reproducible review.
- **Place all content in one comprehensive specification:** This mixes intent, behavior, implementation detail, and current-state ownership.
- **Persist a coverage ledger:** This adds a synchronized artifact when temporary reviewer dispositions provide gate evidence.
- **Use one full workflow for every change:** This adds unnecessary overhead to mechanical changes with no controlled effect.
- **Escalate by file count:** File count does not measure semantic complexity or risk.

## Impact and Risks

This change modifies workflow skills, reviewer prompts, tests, documentation, and the new `workflow-governance` living spec. It does not modify extension code.

Proposal-only approval concentrates operator validation in one artifact. Cold review reduces clarity and grounding defects, but only the operator can detect an entirely omitted intention.

Proposal authors can mistranslate conversation decisions. Explicit author duties and operator fidelity review reduce this risk.

Spec authors can weaken or invent meaning during formalization. Fresh-context derivation and governing-claim dispositions expose this risk before planning.

Brownfield reconstruction can mistake a defect or stale test for intended behavior. Evidence citations, discrepancy handling, and operator resolution prevent silent source selection.

Depth classification can drift without concrete rules. Ordered trigger tests, named reassessment points, and the highest-trigger rule prevent discretionary downgrades.

A High-risk review can underweight either contract fidelity or operational risk. Mandatory explicit contract and risk passes expose both concern classes before one verdict.

Rollout requires skill installation, session reload, behavior tests, and documentation synchronization. Rollback reverts the workflow changes and reinstalls the prior skills.

## Acceptance Examples

### Undefined conversation reference

- GIVEN a proposal refers to `Option X`
- AND the proposal does not define that label
- WHEN the cold-reader reviewer checks the proposal
- THEN the reviewer rejects the proposal before operator review

### Omitted brainstorm decision

- GIVEN the proposal author omits an accepted brainstorm decision entirely
- WHEN the cold-reader reviewer checks only the proposal and repository evidence
- THEN its approval does not certify capture of that omitted decision
- AND the operator remains responsible for checking intended-change fidelity in the proposal

### Faithful spec derivation

- GIVEN an approved proposal requires delivery immediately after output creation
- WHEN a fresh agent derives the feature spec
- THEN the spec preserves the actor, trigger, timing, scope, exceptions, strength, and observable result
- AND the spec reviewer rejects a weaker requirement that permits delivery only before the final verdict

### Missing product decision

- GIVEN spec derivation exposes an unspecified retry policy
- WHEN different policies produce different operator-visible behavior
- THEN the workflow stops and revises the proposal
- AND it does not choose a policy inside the spec or a dispatch prompt

### Brownfield domain without a living spec

- GIVEN affected behavior exists in code but has no living spec
- WHEN the proposal author establishes the baseline and a fresh author derives the feature spec
- THEN the proposal records complete relevant current behavior, evidence, and source discrepancies
- AND the feature spec formalizes established unchanged behavior and requested changes in the existing feature-spec format
- AND planning maps changed behavior to implementation tasks
- AND planning maps unchanged baseline behavior only to preservation or regression checks
- AND finishing can create the complete living spec without inventing behavior

### Mechanical work across many files

- GIVEN a deterministic formatting change affects many files
- AND it changes no program or controlled-document meaning
- WHEN the workflow applies the depth rules
- THEN the change remains Direct

### Architecture boundary crossing

- GIVEN a plan owns a private function signature
- WHEN an equivalent signature change stays within approved boundaries
- THEN plan review can approve it without operator reapproval
- BUT WHEN the change alters an operator-selected component boundary
- THEN the workflow revises, cold-reviews, and reapproves the proposal

### Unknown High-risk trigger

- GIVEN evidence does not establish whether a change affects authorization
- WHEN the workflow selects a provisional level
- THEN it selects High-risk until evidence resolves that fact

### Aggregate non-High-risk uncertainty

- GIVEN confirmed facts and least-escalating unknown values produce a Bounded base level
- AND multiple unresolved non-High-risk facts remain
- WHEN the workflow selects a provisional level
- THEN it applies one aggregate one-level escalation
- AND the provisional level is Standard

### Standard provisional level

- GIVEN confirmed facts and a least-escalating unknown value produce a Bounded base level
- AND one unresolved non-High-risk fact remains
- WHEN the workflow selects a provisional level
- THEN the provisional level is Standard

### Workflow gate ordering remains Standard

- GIVEN a non-Direct change alters only controlled workflow gate ordering
- AND no runtime event ordering, data ordering, or other High-risk trigger applies
- WHEN the workflow selects the depth
- THEN the High-risk ordering trigger does not apply
- AND the change is Standard when it does not meet every Bounded condition

### Planning confirms Bounded decomposition

- GIVEN pre-plan facts select provisional Bounded
- AND a contract-complete plan needs three cohesive tasks
- WHEN planning exposes actual decomposition
- THEN planning stops before execution
- AND the workflow escalates to Standard
- AND the revised proposal receives cold review and operator approval

### Complexity escalation

- GIVEN a Bounded change later reveals a public schema migration
- WHEN the workflow reassesses depth from the new evidence
- THEN it stops work and changes the level to High-risk
- AND the proposal gains migration, compatibility, rollout, rollback, observability, recovery, and risk-treatment details
- AND the operator approves the cold-reviewed revision before work continues

### Preapproval depth downgrade

- GIVEN an unresolved authorization fact selects provisional High-risk
- AND evidence before operator approval proves that authorization is unaffected
- AND all resolved facts select Standard
- WHEN the workflow reassesses before cold review
- THEN it lowers the provisional depth to Standard
- AND it updates the proposal to Standard before cold review

### Postapproval depth does not downgrade

- GIVEN the operator approved a High-risk proposal
- AND later evidence would select Standard
- WHEN the workflow reassesses depth
- THEN it does not silently lower the approved depth
- AND work can retain High-risk depth

### High-risk plan obligations

- GIVEN an approved High-risk proposal defines applicable compatibility and rollback obligations
- AND it marks migration inapplicable
- AND it approves a no-action observability treatment
- WHEN the planner writes the plan
- THEN it maps each applicable obligation to a task or check with named evidence
- AND it can use `None` only for migration and observability with the approved basis
- AND plan review blocks execution if any other applicable obligation uses `None` or lacks a mapping

### High-risk execution evidence

- GIVEN plan review approves a High-risk plan with mapped evidence
- WHEN implementation completes
- THEN execution produces each mapped item of evidence
- AND final review remains blocked when mapped evidence is missing

### Approved proposal format edit

- GIVEN the operator approved an exact proposal version
- WHEN an author makes a format-only edit to that proposal
- THEN the edit creates a new version
- AND the workflow repeats cold review and operator approval

### Governing and descriptive claims

- GIVEN a proposal contains an in-scope behavior, binding architecture, and a baseline citation
- AND the citation prescribes no downstream work
- WHEN the spec reviewer assigns temporary dispositions
- THEN the behavior maps to a requirement and scenario
- AND the architecture is retained for planning
- AND the citation is checked for grounding but receives no disposition

### High-risk review fix

- GIVEN a High-risk final reviewer reports a blocking finding
- WHEN the implementation changes
- THEN the prior final-review approval becomes invalid
- AND one fresh reviewer performs both passes against the corrected complete inputs
- AND integration remains blocked until the new verdict approves the corrected version
