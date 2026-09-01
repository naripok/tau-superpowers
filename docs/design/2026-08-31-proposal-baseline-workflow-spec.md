# Spec: Proposal-baseline development workflow

## Domain: workflow-governance

### ADDED Requirements

The domain has no living spec. This section uses the existing feature-spec format for complete relevant post-change behavior. Its requirements include established unchanged behavior and requested changes. `ADDED` means addition to the absent living spec, not that every behavior needs implementation work.

##### Requirement delta map

`ADDED` means that each requirement is an addition to the absent living spec. It does not classify implementation work. Every clause in every listed requirement is **Changed** unless its row names a **Preserved baseline exception**. Changed clauses map to implementation tasks. Preserved baseline exceptions map only to preservation or regression checks. The exceptions are exhaustive for each row. An adjacent or otherwise unlisted clause is Changed. Each requirement appears exactly once.

| Requirement | Exhaustive delta classification |
| --- | --- |
| `Deterministic workflow depth classification` | **No preserved baseline exceptions.** |
| `Level-specific workflow gates` | **Preserved baseline exception:** Every automated review gate continues to apply the existing `docs/specs/review-adjudication.md` contract without redefining its procedure. |
| `Depth reassessment and escalation` | **No preserved baseline exceptions.** |
| `Ordered proposal-baseline state flow` | **Preserved baseline exception:** Existing branch and worktree protection through `using-git-worktrees` remains unchanged. |
| `Artifact semantic closure and role ownership` | **Preserved baseline exceptions:** Feature-spec requirements continue to use RFC 2119 keywords, descriptive names under 50 characters, and at least one GIVEN/WHEN/THEN scenario. The proposal retains its existing intent, scope, and approach roles. The feature spec remains the behavioral contract and a delta against current behavior. The plan retains its existing file-decomposition, internal-interface, and task-boundary roles. The living spec remains the current-behavior contract. |
| `Complete brownfield baseline and impact analysis` | **Preserved baseline exceptions:** The workflow continues to read a relevant living spec as the current-behavior contract and to explore relevant project context before proposal authoring. An undocumented-domain feature spec continues to use the existing feature-spec format. |
| `Proposal authoring from elicitation` | **Preserved baseline exceptions:** Brainstorming conversation remains elicitation input. Proposals retain their existing intent, in-scope and out-of-scope, approach and alternatives, and impact content. |
| `Proposal cold-reader gate` | **No preserved baseline exceptions.** |
| `Proposal-only approval identity` | **No preserved baseline exceptions.** |
| `Isolated and faithful feature-spec derivation` | **Preserved baseline exception:** An undocumented-domain feature spec continues to use the existing feature-spec format. |
| `Temporary governing-claim dispositions` | **No preserved baseline exceptions.** |
| `Proposal-to-spec review gate` | **Preserved baseline exceptions:** A fresh `document-review` context continues to review the feature spec before planning. The review retains its existing behavioral-coverage, testability, and living-spec alignment checks. |
| `Proposal-owned architecture and plan-owned detail` | **Preserved baseline exceptions:** The proposal retains its existing architectural-approach role. The plan retains its existing file-decomposition, private-data-structure, internal-signature, and task-boundary roles. Implementers can still choose equivalent internal details within the reviewed contracts. |
| `Complementary plan-review contracts` | **Preserved baseline exceptions:** The feature spec remains the behavioral contract, and the proposal retains its approach-context role. Existing requirement-to-task traceability and test proof remain unchanged. A fresh plan reviewer continues to check behavioral coverage, task buildability, decomposition, and test proof. Plan-review approval continues to gate execution, with no operator approval of the plan. |
| `Artifact-derived implementation context` | **No preserved baseline exceptions.** |
| `Approved proposal change control` | **No preserved baseline exceptions.** |
| `Single High-risk two-pass review` | **Preserved baseline exception:** Rejection confirmation continues to use the existing finding-adjudication contract in `docs/specs/review-adjudication.md`. |
| `Implementation reviews and final acceptance` | **Preserved baseline exceptions:** Existing per-task implementation review and final full-spec review remain unchanged where they apply. Fresh repository verification continues to precede finishing. |
| `Living-spec synchronization and integration` | **Preserved baseline exceptions:** Living-spec synchronization continues to update or create living specs from the accepted feature spec before integration. Synchronization remains idempotent and preserves unchanged behavior. It continues without operator approval. The operator retains the existing local-merge-or-pull-request choice, and operator silence leaves the branch and worktree untouched. |

#### Requirement: Deterministic workflow depth classification

Before provisional classification, the workflow MUST perform a minimal evidence pass. The pass MUST identify the current domain status and the known or unresolved status of every risk trigger. The workflow MUST then select a provisional level before it drafts the proposal at that level.

A change MUST be Direct only when established facts show all these conditions:

- The change alters representation without altering program or controlled-document meaning.
- The change has no behavioral, contract, data, security, privacy, operational, or controlled-document effect.
- The change requires no design decision.

A controlled document MUST mean a document that defines required or current behavior, workflow policy, acceptance, or operations. Proposals, feature specs, plans, living specs, policies, and runbooks MUST count as controlled documents.

A non-Direct change MUST be High-risk when it affects any of these areas:

- An externally consumed contract or compatibility commitment.
- A schema, stored-data migration, or data recovery procedure.
- Security, privacy, authentication, authorization, or secrets.
- Concurrency, distributed consistency, or race safety.
- Runtime event ordering or data ordering whose failure affects observable behavior, safety, consistency, or integrity.
- A destructive or irreversible action.
- Production availability or compliance.
- Rollback that needs coordinated recovery or cannot use a safe revert.

Workflow gate ordering alone MUST NOT activate the High-risk ordering trigger.

A behavioral domain MUST mean one named subject area whose current behavior belongs in one living spec.

When classification facts are resolved, a non-Direct, non-High-risk change MUST be Bounded only when all these pre-plan conditions hold:

- The change affects one behavioral domain.
- The baseline has no material source discrepancy.
- The change needs no coordination across a runtime or deployment boundary, consumer, producer, external service, or operational process.
- A single safe revert restores the prior state without migration or recovery work.
- The change has one cohesive implementation responsibility.

Every other non-Direct change MUST be Standard. File count and line count MUST NOT select a higher level by themselves. Future implementation-plan task count MUST NOT select the provisional level. The highest applicable level MUST govern the work.

The escalation order MUST be Direct, Bounded, Standard, then High-risk. Any unresolved fact about a High-risk trigger MUST select provisional High-risk until evidence resolves the fact. Otherwise, the workflow MUST assign unresolved non-High-risk facts their least-escalating values for base-level calculation. All unresolved non-High-risk facts MUST then cause one aggregate one-level escalation, capped at High-risk. Multiple such facts MUST NOT cause multiple escalations.

The operator MAY select a higher level, but the proposal MUST record that selection before approval.

##### Scenario: Mechanical change across many files

- GIVEN a deterministic formatting change affects many files
- AND established facts show no program or controlled-document meaning change
- AND the change has none of the excluded Direct effects
- AND it requires no design decision
- WHEN the workflow classifies the change
- THEN it classifies the change as Direct

##### Scenario: Bounded change

- GIVEN established pre-plan facts satisfy every Bounded condition
- AND no High-risk trigger applies
- WHEN the workflow classifies the change
- THEN it classifies the change as Bounded
- AND it does not use a future plan task count

##### Scenario: Standard coordination change

- GIVEN a non-Direct change coordinates behavior across two runtime components
- AND no High-risk trigger applies
- WHEN the workflow classifies the change
- THEN it classifies the change as Standard
- AND the number of changed files does not determine that result

##### Scenario: High-risk trigger wins

- GIVEN a change otherwise satisfies the Bounded conditions
- AND it changes stored data through a schema migration
- WHEN the workflow classifies the change
- THEN it classifies the change as High-risk

##### Scenario: Runtime ordering affects behavior

- GIVEN a change controls runtime event ordering
- AND an ordering failure can change observable behavior or integrity
- WHEN the workflow classifies the change
- THEN it classifies the change as High-risk

##### Scenario: Workflow gate ordering is not High-risk

- GIVEN a non-Direct change alters only controlled workflow gate ordering
- AND no runtime event ordering, data ordering, or other High-risk trigger applies
- WHEN the workflow classifies the change
- THEN the High-risk ordering trigger does not apply
- AND it selects Standard when the change does not meet every Bounded condition

##### Scenario: Unresolved High-risk fact

- GIVEN confirmed facts otherwise select Bounded
- AND evidence does not establish whether the change affects authorization
- WHEN the workflow selects the provisional level
- THEN it selects High-risk until evidence resolves the authorization fact

##### Scenario: Multiple non-High-risk unknowns

- GIVEN confirmed facts and least-escalating unknown values produce a Bounded base level
- AND multiple unresolved non-High-risk classification facts remain
- WHEN the workflow selects the provisional level
- THEN it applies one aggregate one-level escalation
- AND it selects Standard

##### Scenario: Standard provisional level

- GIVEN confirmed facts and a least-escalating unknown value produce a Bounded base level
- AND one unresolved non-High-risk classification fact remains
- WHEN the workflow selects the provisional level
- THEN it selects Standard

#### Requirement: Level-specific workflow gates

The selected level MUST control workflow depth through this gate matrix:

| Gate | Direct | Bounded | Standard | High-risk |
| --- | --- | --- | --- | --- |
| Baseline and classification | Minimal evidence and Direct test | Concise relevant baseline in the proposal | Complete relevant baseline and impact | Standard content plus applicable compatibility, migration, rollout, rollback, observability, recovery, and risk treatment |
| Proposal | None | Concise minimum content, one cold review, operator approval | Complete minimum content and relevant impact, one cold review, operator approval | Standard content plus each High-risk category, one cold review, operator approval |
| Feature spec | None | Concise complete spec and one spec review | Full spec and one spec review | Full spec and one two-pass spec review |
| Plan | None | Concise one-to-two-task plan and one plan review | Full task plan and one plan review | Obligation-mapped plan and one plan review |
| Execution | Targeted edit and relevant checks | Inline execution of one or two tasks | Task execution with per-task review | Produce all evidence mapped by the plan, with per-task review |
| Final acceptance | Relevant repository checks | One final whole-change review and fresh verification | One final whole-change review and fresh verification | One two-pass final review, acceptance checks, and fresh verification |
| Living-spec synchronization and integration | None | Synchronize, check, then integrate | Synchronize, check, then integrate | Synchronize, check, then integrate after final-review approval |

Every non-Direct level MUST retain semantic fidelity, proposal change control, brownfield grounding, artifact reviews, and the prohibition on dispatch-only design repair. Bounded artifacts MAY be concise, but they MUST remain complete for their roles.

Every automated review gate MUST apply the unchanged `docs/specs/review-adjudication.md` living-spec contract. This feature spec MUST NOT redefine that contract's detailed procedure.

A High-risk plan MUST map every applicable compatibility, migration, rollout, rollback, observability, recovery, and approved risk-treatment obligation to a task or check with named evidence. It MUST use `None` only when the approved proposal marks the category inapplicable or approves a no-action treatment. High-risk execution MUST produce every mapped item of evidence. The workflow contract MUST NOT invent domain-specific procedures.

##### Scenario: Bounded workflow depth

- GIVEN the selected level is Bounded
- WHEN the workflow executes the change
- THEN it uses a concise proposal, feature spec, and one-to-two-task plan
- AND each artifact receives its required review
- AND the agent executes the tasks inline
- AND one final whole-change review approves the result before finishing

##### Scenario: Direct workflow depth

- GIVEN the selected level is Direct
- WHEN the workflow executes the change
- THEN it creates no proposal, feature spec, or implementation plan
- AND it makes a targeted edit
- AND it runs the relevant repository checks

##### Scenario: Automated gates use adjudication

- GIVEN an automated proposal, spec, plan, implementation, final, or synchronization review returns findings
- WHEN the workflow handles those findings
- THEN it applies the existing `review-adjudication` living-spec contract
- AND this domain does not replace that contract's detailed procedure

##### Scenario: High-risk plan maps obligations

- GIVEN an approved High-risk proposal defines applicable compatibility and rollback obligations
- AND it marks migration inapplicable
- AND it approves a no-action observability treatment
- WHEN the planner writes the High-risk plan
- THEN it maps compatibility and rollback to tasks or checks with named evidence
- AND it can assign `None` only to migration and observability with the approved basis
- AND plan review blocks execution if another applicable obligation uses `None` or lacks a mapping

##### Scenario: High-risk execution proves obligations

- GIVEN plan review approves a High-risk plan with mapped evidence
- WHEN implementation completes
- THEN execution produces each mapped item of evidence
- AND final review remains blocked when mapped evidence is missing

#### Requirement: Depth reassessment and escalation

The workflow MUST select initial depth after the minimal baseline pass. It MUST reassess depth whenever classification evidence changes. Such evidence can arise during planning, artifact review, implementation, or the final check of all accumulated evidence. The workflow MUST NOT perform consecutive reassessments when no evidence changes.

Before operator approval, resolution of a classification fact MAY raise or lower provisional depth. The workflow MUST update the proposal to the selected depth before cold review. When a fact resolves after cold review, the update MUST invalidate that review and receive a new cold review before operator approval.

After operator approval, new evidence that selects a higher depth MUST stop work and use proposal change control. The workflow MUST revise the proposal with the new depth, impact, risk, and required content. It MUST repeat proposal cold review and operator approval. It MUST invalidate and regenerate or re-review every affected downstream artifact before work resumes.

A postapproval reassessment MUST NOT silently lower the approved depth. Work MAY retain the approved higher depth. A lower approved depth MUST take effect only through proposal revision, cold review, and operator reapproval.

A provisional Bounded plan MUST contain no more than two cohesive tasks. If a contract-complete plan needs more than two tasks or reveals another higher trigger, planning MUST stop before execution. The workflow MUST escalate and complete the required proposal change control.

When Direct work becomes non-Direct, the workflow MUST stop and create the required proposal. It MUST cold-review the proposal and obtain operator approval before downstream work starts.

##### Scenario: Bounded work reveals a migration

- GIVEN work began at the Bounded level
- AND implementation evidence reveals a stored-data migration
- WHEN the workflow reassesses depth
- THEN it stops implementation
- AND it revises the proposal for High-risk depth
- AND it repeats cold review and operator approval
- AND it invalidates affected spec, plan, and implementation approvals
- AND work remains stopped until regenerated or repaired artifacts receive their required reviews

##### Scenario: Preapproval evidence lowers depth

- GIVEN an unresolved authorization fact selects provisional High-risk
- AND evidence before operator approval proves that authorization is unaffected
- AND all resolved facts select Standard
- WHEN the workflow receives the resolved fact before cold review
- THEN it reassesses the depth as Standard
- AND it updates the proposal to Standard before cold review

##### Scenario: Postapproval evidence does not downgrade

- GIVEN the operator approved a High-risk proposal
- AND later evidence would select Standard
- WHEN the workflow reassesses depth
- THEN it does not silently lower the approved depth
- AND work can retain High-risk depth

##### Scenario: Direct work reveals behavior

- GIVEN work began at the Direct level
- WHEN the edit reveals a behavioral effect
- THEN the workflow stops Direct execution
- AND it creates and cold-reviews a non-Direct proposal
- AND it obtains operator approval before downstream work starts

##### Scenario: Bounded plan exceeds two tasks

- GIVEN pre-plan facts selected provisional Bounded
- AND a contract-complete plan needs three cohesive tasks
- WHEN planning exposes the actual decomposition
- THEN planning stops before execution
- AND the workflow escalates to Standard
- AND it repeats proposal cold review and operator approval

##### Scenario: Planning reveals a higher trigger

- GIVEN a plan has no more than two cohesive tasks
- AND planning reveals cross-boundary coordination
- WHEN the workflow reassesses from that new fact
- THEN planning stops before execution
- AND the workflow escalates from Bounded to Standard

##### Scenario: Artifact review reveals a trigger

- GIVEN proposal review reveals a previously unknown external contract
- WHEN the workflow receives that classification fact
- THEN it reassesses depth immediately
- AND proposal approval remains blocked until the High-risk content is complete

##### Scenario: Final reassessment uses all evidence

- GIVEN no individual artifact review revealed a higher trigger
- WHEN the workflow reaches final acceptance
- THEN it reassesses depth from all accumulated evidence
- AND final acceptance remains blocked if that evidence selects a higher level

#### Requirement: Ordered proposal-baseline state flow

Every non-Direct change MUST pass these states in order:

1. Minimal baseline evidence established.
2. Provisionally classified.
3. Protected worktree established through `using-git-worktrees`.
4. Baseline and proposal completed at the selected depth.
5. Proposal cold-reviewed and approved by the reviewer.
6. Exact reviewed proposal version approved by the operator.
7. Feature spec derived.
8. Feature spec reviewed and approved.
9. Plan written.
10. Plan reviewed and approved.
11. Implementation completed with level-required reviews.
12. Final acceptance passed.
13. Living spec synchronized and checked.
14. Integration completed.

The workflow MAY perform the minimal baseline pass and provisional classification before worktree creation only while it persists no non-Direct artifact or implementation change. Before it persists such work, it MUST invoke `using-git-worktrees`. Every non-Direct artifact and implementation change MUST remain on that protected branch or worktree and MUST NOT land directly on the default branch.

Artifact existence MUST NOT establish completion of a state. Each review and approval MUST attach to the exact input version that received it. Any artifact edit MUST invalidate that artifact's prior review or approval. A changed upstream input MUST invalidate every affected downstream review and approval. The workflow MUST NOT enter planning until all unresolved controlled decisions and blocking spec-review dispositions are resolved.

##### Scenario: Artifact paths exist without approvals

- GIVEN proposal and feature-spec files exist
- AND the proposal lacks cold-reader or operator approval for its current version
- WHEN the workflow evaluates the current state
- THEN it does not mark proposal approval or feature-spec review complete
- AND it does not enter planning

##### Scenario: Worktree precedes persisted artifacts

- GIVEN a change fails the Direct test
- AND the workflow has established a minimal baseline and provisional depth
- WHEN it prepares to persist the proposal or another development change
- THEN it first establishes the protected worktree through `using-git-worktrees`
- AND it keeps all artifacts and implementation changes off the default branch

##### Scenario: Full non-Direct flow

- GIVEN a non-Direct proposal version has cold-reader and operator approval
- WHEN all later gates approve their exact inputs in order
- THEN final acceptance precedes living-spec synchronization
- AND living-spec synchronization precedes integration

#### Requirement: Artifact semantic closure and role ownership

Every proposal, feature spec, implementation plan, and living spec MUST define every term, option label, decision, constraint, assumption, exception, and reference needed for its role. No such artifact MAY depend on brainstorm or other chat history for meaning.

Every feature-spec requirement MUST use an RFC 2119 keyword. Its name MUST be descriptive and under 50 characters. Every feature-spec requirement MUST include at least one GIVEN/WHEN/THEN scenario.

Cross-document references MAY provide traceability, but they MUST NOT replace contract content needed to understand the referencing artifact. Artifact authors MUST preserve these ownership boundaries:

- The proposal owns operator intent, scope, acceptance, externally material or binding architecture, operator-selected constraints, assumptions, risks, and non-goals.
- The feature spec owns complete relevant observable post-change behavior and identifies the delta against established current behavior.
- The plan owns file decomposition, private data structures, internal signatures, task boundaries, and equivalent implementation choices within approved boundaries.
- The living spec owns complete current observable behavior after accepted changes.

##### Scenario: Undefined proposal label

- GIVEN a proposal refers to `Option C`
- AND the proposal does not define that label
- WHEN the cold-reader reviewer checks semantic closure
- THEN the reviewer rejects the proposal
- AND the workflow does not present it for operator approval

##### Scenario: Semantically closed living spec

- GIVEN finishing synchronizes an accepted feature spec into a living spec
- WHEN a reader opens the living spec without the proposal or chat history
- THEN the reader can understand the complete current behavior from the living spec

##### Scenario: Cross-reference replaces required meaning

- GIVEN a plan names a proposal section but omits the binding constraint needed by a task
- WHEN the plan reviewer checks semantic closure
- THEN the reviewer rejects the plan

#### Requirement: Complete brownfield baseline and impact analysis

Before drafting a proposal, the workflow MUST select one baseline branch from repository evidence:

- A domain with a living spec.
- An existing domain without a living spec.
- A genuinely new domain.

For a domain with a living spec, the workflow MUST use that spec as the current-behavior contract. It MUST inspect relevant code, tests, interfaces, consumers, contracts, documentation, and operational evidence when those sources can reveal impact or discrepancies.

For an existing domain without a living spec, the workflow MUST reconstruct complete relevant current behavior from all relevant evidence. Relevant evidence includes code, tests, interfaces, consumers, contracts, documentation, and operational records. The proposal MUST record that behavior, its evidence, and material discrepancies.

For that undocumented domain, the feature spec MUST use the existing feature-spec format. It MUST formalize complete relevant post-change behavior, including established unchanged baseline behavior and requested changes. Planning MUST map changed behavior to implementation tasks. It MUST map unchanged baseline behavior to preservation or regression checks, not change tasks.

For a genuinely new domain, the workflow MUST search for existing behavior, interfaces, consumers, contracts, and operational dependencies. It MUST record evidence that the domain is absent and describe relevant adjacent impact.

A missing living spec MUST NOT prove that a domain is new. The proposal MUST record relevant consumers, interfaces, contracts, data effects, security effects, operational effects, rollout, and rollback. It MUST use `None` for a required category with no relevant content.

A source discrepancy MUST be material when different resolutions can alter a controlled decision. The workflow MUST expose every material source discrepancy. It MUST resolve that discrepancy through the proposal before proposal approval.

##### Scenario: Domain with a living spec

- GIVEN a living spec defines the affected domain
- WHEN the workflow establishes the baseline
- THEN it uses the living spec as the current-behavior contract
- AND it checks relevant repository sources for impact and discrepancies
- AND the feature spec expresses a delta against the living spec

##### Scenario: Existing undocumented domain

- GIVEN affected behavior exists in the project
- AND no living spec defines its domain
- WHEN the workflow establishes the baseline and derives the feature spec
- THEN it inspects relevant implementation, tests, interfaces, consumers, contracts, documentation, and operational evidence
- AND the proposal records complete relevant current behavior, evidence, discrepancies, and impact
- AND the feature spec uses the existing format for unchanged baseline behavior and requested changes

##### Scenario: Undocumented baseline plan mapping

- GIVEN a feature spec formalizes unchanged baseline behavior and requested changes
- WHEN the planner maps that spec to implementation work
- THEN requested changes map to implementation tasks
- AND unchanged baseline behavior maps to preservation or regression checks
- AND unchanged baseline behavior does not create change tasks

##### Scenario: Genuinely new domain

- GIVEN repository evidence shows no affected domain or behavior
- WHEN the workflow establishes the baseline
- THEN it identifies the domain as new
- AND it records adjacent consumers, interfaces, contracts, and operational impact when relevant
- AND the feature spec expresses complete new behavior as ADDED requirements

##### Scenario: Material evidence conflict

- GIVEN a living spec and implementation disagree about material current behavior
- WHEN the discrepancy can change the requested contract
- THEN the proposal records and resolves the discrepancy before approval
- AND the workflow does not silently select one source

#### Requirement: Proposal authoring from elicitation

For every non-Direct change, the proposal author MUST use the brainstorm conversation as elicitation input and MUST transfer every accepted downstream decision into the proposal. The conversation MUST NOT act as a formal approval gate or a downstream design source.

Every non-Direct proposal MUST contain this minimum content:

- Intent.
- Relevant current behavior and evidence.
- Required outcomes.
- Representative acceptance examples.
- Scope and non-goals.
- Constraints.
- The selected approach and relevant alternatives.
- Impact and risks.
- Assumptions.
- Unresolved decisions.

Each required section MUST use `None` when it has no relevant content. A Bounded proposal MAY make its sections concise. A Standard proposal MUST give complete relevant impact. A High-risk proposal MUST additionally cover each compatibility, migration, rollout, rollback, observability, recovery, and risk-treatment category.

The author MUST transfer every accepted decision about behavior, scope, externally material or binding architecture, thresholds, exceptions, constraints, assumptions, risk treatment, and acceptance. Every unresolved decision that can govern downstream work MUST block cold-review approval and operator approval. The `Unresolved Decisions` section MUST read `None` before either approval.

##### Scenario: Accepted decision exists only in conversation

- GIVEN the operator accepts a behavioral decision during elicitation
- WHEN the proposal author prepares the proposal
- THEN the author restates the complete decision in the proposal
- AND downstream agents do not need the conversation to use it

##### Scenario: Conversation agreement without proposal approval

- GIVEN the operator agrees with an approach during brainstorming conversation
- AND the reviewed proposal version lacks formal operator approval
- WHEN the workflow evaluates the operator gate
- THEN the gate remains incomplete

##### Scenario: Required section has no content

- GIVEN a Bounded proposal has no assumptions or unresolved decisions
- WHEN the author completes the proposal
- THEN its `Assumptions` and `Unresolved Decisions` sections contain `None`

##### Scenario: Standard proposal impact

- GIVEN a Standard change affects operations and two internal consumers
- WHEN the author completes the proposal
- THEN the proposal gives complete relevant impact for operations and both consumers

##### Scenario: High-risk proposal categories

- GIVEN a High-risk change needs rollback and observability treatment
- AND migration does not apply
- WHEN the author completes the proposal
- THEN it covers rollback, observability, and each approved risk treatment
- AND its migration category contains `None`

##### Scenario: Unresolved controlled decision

- GIVEN a proposal leaves a controlled retry policy unresolved
- WHEN the reviewer or operator evaluates approval
- THEN cold-review approval remains blocked
- AND operator approval remains blocked

#### Requirement: Proposal cold-reader gate

A fresh `document-review` context without brainstorm history MUST review the complete proposal before operator review. It MUST receive the proposal, named repository evidence, and the review contract.

The reviewer MUST check semantic closure, clarity, internal consistency, brownfield grounding, evidence discrepancies, risk classification, required depth content, and actionable completeness. It MUST check whether present claims and required sections support downstream work. It MUST NOT claim that it can detect an accepted brainstorm decision that the author omitted entirely.

The workflow MUST resolve adjudicated blocking findings and obtain reviewer approval of the exact proposal version before operator review.

##### Scenario: Proposal is self-contained

- GIVEN the proposal defines complete and consistent intent
- AND named repository evidence supports its baseline and risk classification
- WHEN the cold-reader reviewer checks the proposal without brainstorm history
- THEN the reviewer approves it for operator review

##### Scenario: Reviewer needs brainstorm history

- GIVEN a proposal statement requires brainstorm history for interpretation
- WHEN the cold-reader reviewer checks it
- THEN the reviewer reports a blocking semantic-closure finding
- AND it does not infer missing meaning from dispatch context

##### Scenario: Decision omitted from the proposal

- GIVEN the proposal author omits an accepted brainstorm decision entirely
- WHEN the cold-reader reviewer checks only the proposal and named repository evidence
- THEN reviewer approval does not certify capture of that omitted decision

#### Requirement: Proposal-only approval identity

For every non-Direct change, the operator MUST review and approve the complete cold-reviewed proposal. Operator approval MUST validate that the proposal captures the intended change. The workflow MUST NOT request operator review or approval of the feature spec, implementation plan, or living-spec synchronization.

The workflow MUST identify the exact approved proposal content with a commit identity, content digest, or equivalent immutable identity. That proposal version MUST become the sole source of operator intent for downstream work. Spec authors, reviewers, planners, and implementers MUST NOT use brainstorm history as an additional intent source.

When the operator requests a proposal change, the workflow MUST revise the proposal, repeat cold review, and request operator approval of the new exact version.

##### Scenario: Operator approves the proposal

- GIVEN the cold-reader reviewer approved an exact proposal version
- WHEN the operator confirms that version captures the intended change
- THEN the workflow records its immutable approval identity
- AND it proceeds to feature-spec derivation
- AND it requests no operator approval of the spec or plan

##### Scenario: Operator requests a revision

- GIVEN the operator requests a meaning change during proposal review
- WHEN the proposal author revises the proposal
- THEN the previous reviewer approval is invalid
- AND the workflow repeats cold review before requesting operator approval

#### Requirement: Isolated and faithful feature-spec derivation

A fresh author context without brainstorm history MUST derive the feature spec from the approved proposal version, established current behavior, and relevant living specs. The feature spec MUST define complete relevant observable post-change behavior for every affected requirement.

For an existing domain without a living spec, the author MUST use the existing feature-spec format. The feature spec MUST formalize established unchanged baseline behavior and requested changes. It MUST NOT defer unchanged baseline formalization to planning or finishing.

For each governing claim that maps to the feature spec, derivation MUST preserve each applicable semantic property:

- Actor.
- Trigger.
- Timing.
- Ordering.
- Scope.
- Conditions.
- Exceptions.
- Strength.
- Threshold.
- Observable result.

The author MUST NOT invent a decision, threshold, exception, policy, constraint, or operator-visible outcome absent from the approved proposal or established current behavior.

When formalization exposes two valid meanings with different controlled results, the author MUST stop. It MUST return the missing decision through proposal revision and MUST NOT choose one meaning in the feature spec.

##### Scenario: Semantic strength remains intact

- GIVEN an approved proposal requires an action immediately after an event
- WHEN the author derives the feature spec
- THEN the corresponding requirement preserves the actor, trigger, timing, scope, exceptions, strength, and result
- AND it does not permit the action at a later point

##### Scenario: Derivation exposes a missing decision

- GIVEN two valid retry policies produce different observable behavior
- AND the approved proposal selects neither policy
- WHEN the author derives the feature spec
- THEN it stops derivation
- AND it returns the decision through proposal revision
- AND it does not invent a retry policy

##### Scenario: Derive an undocumented domain spec

- GIVEN an existing domain has established behavior but no living spec
- WHEN the author derives its feature spec
- THEN the spec uses the existing feature-spec format
- AND it formalizes complete relevant post-change behavior
- AND that behavior includes unchanged baseline behavior and requested changes

#### Requirement: Temporary governing-claim dispositions

A governing proposal claim MUST mean a proposal statement that prescribes downstream behavior, observable quality, work, architecture, a constraint, acceptance, risk treatment, or exclusion. The spec reviewer MUST assign one classification and disposition to every governing proposal claim. It MUST NOT classify every prose sentence. It MUST split a compound governing claim when its parts need different dispositions.

| Governing claim classification | Required temporary outcome |
| --- | --- |
| Observable behavior, including in-scope behavior | `Mapped to requirement`: cite feature-spec requirements and scenarios that preserve the claim |
| Observable quality constraint | `Mapped to requirement`: cite measurable feature-spec requirements and scenarios |
| Internal constraint | `Retained for planning`: cite the proposal text and name the required plan-review check |
| Non-behavioral in-scope work | `Retained for planning`: cite the proposal text and name the required plan work |
| Acceptance example | `Mapped to scenario`: cite one or more equivalent feature-spec scenarios |
| Exclusion or non-goal | `Explicitly excluded`: confirm that it receives no requirement or implementation work |

Binding architecture, non-observable scope obligations, assumptions, and approved risk treatments MUST count as internal constraints. When any such claim defines observable behavior, it MUST map to a requirement instead. In-scope work without observable behavior MUST remain available for planning and MUST NOT become invented feature-spec behavior.

The reviewer MUST check descriptive baseline evidence, source citations, and rationale for grounding. Those statements MUST receive no disposition unless they also prescribe downstream work.

A missing, ambiguous, conflicting, weakened, or invented treatment MUST receive a `Blocked` outcome. Reviewer approval MUST require a non-blocking disposition for every governing proposal claim.

Dispositions MUST remain temporary review output. The workflow MUST NOT commit them as a ledger or maintain a permanent coverage matrix.

##### Scenario: Behavior and quality map to requirements

- GIVEN a proposal contains in-scope behavior and an observable latency constraint
- WHEN the spec reviewer classifies those governing claims
- THEN it maps both claims to feature-spec requirements and scenarios
- AND the latency requirement contains a measurable observable threshold

##### Scenario: Internal obligations remain constraints

- GIVEN a proposal defines binding architecture, an assumption, and a non-observable risk treatment
- WHEN the spec reviewer classifies those governing claims
- THEN it retains each claim for planning as an internal constraint
- AND it names a plan-review check for each claim

##### Scenario: Non-behavioral work remains for planning

- GIVEN proposal scope requires documentation work that defines no observable behavior
- WHEN the spec reviewer classifies that governing claim
- THEN it retains the work for planning
- AND it does not invent a feature-spec requirement for that work

##### Scenario: Acceptance example maps to scenarios

- GIVEN a proposal contains an acceptance example
- WHEN the spec reviewer checks its disposition
- THEN the disposition cites one or more equivalent feature-spec scenarios

##### Scenario: Non-goal remains excluded

- GIVEN a proposal excludes automatic retries
- WHEN the spec reviewer checks its disposition
- THEN it marks automatic retries as explicitly excluded
- AND it confirms that the feature spec creates no retry requirement
- AND it confirms that downstream work does not implement retries

##### Scenario: Descriptive evidence gets no disposition

- GIVEN a proposal cites tests as descriptive baseline evidence
- AND the citation prescribes no downstream work
- WHEN the spec reviewer checks grounding and dispositions
- THEN it checks whether the evidence grounds the baseline
- AND it assigns no disposition to the citation

##### Scenario: Rationale also prescribes work

- GIVEN a rationale statement also requires downstream migration work
- WHEN the spec reviewer checks that statement
- THEN it assigns a disposition to the prescribed work
- AND it does not assign a disposition to rationale alone

##### Scenario: Temporary dispositions are not persisted

- GIVEN all governing proposal claims receive non-blocking dispositions
- WHEN the spec-review gate closes
- THEN the workflow retains no committed coverage ledger or permanent disposition matrix

#### Requirement: Proposal-to-spec review gate

A fresh `document-review` context MUST review the derived feature spec against the complete approved proposal version, established baseline, and relevant living specs. The reviewer MUST check semantic equivalence, complete behavioral coverage, testability, artifact closure, current-behavior alignment, and absence of invented decisions.

The reviewer MUST apply the governing-claim classifications and temporary dispositions. It MUST reject a feature-spec requirement name that is not descriptive or contains 50 or more characters. Every non-Direct change MUST resolve all blocking findings and dispositions and MUST receive every level-required spec-review approval before planning starts.

##### Scenario: Complete faithful coverage

- GIVEN a feature spec preserves every behavioral and observable quality claim
- AND it maps every acceptance example
- AND it retains internal constraints for planning
- AND it excludes every non-goal
- WHEN the spec reviewer completes all dispositions
- THEN it approves the spec for planning

##### Scenario: Invalid requirement name blocks review

- GIVEN a feature-spec requirement name is not descriptive or contains 50 characters
- WHEN the spec reviewer checks the naming contract
- THEN it rejects the requirement name
- AND planning remains blocked until the corrected spec receives review approval

##### Scenario: Invented behavior blocks planning

- GIVEN a feature spec selects an error policy absent from the proposal and established baseline
- WHEN the spec reviewer checks fidelity
- THEN it assigns a blocking invented-decision disposition
- AND planning remains blocked
- AND the workflow returns the decision through proposal revision

##### Scenario: Unresolved disposition blocks planning

- GIVEN one governing proposal claim lacks a non-blocking disposition
- WHEN the spec-review gate evaluates completion
- THEN the reviewer does not approve the spec
- AND the workflow does not start planning

#### Requirement: Proposal-owned architecture and plan-owned detail

The proposal MUST own every architectural choice that is externally material or otherwise binding. This ownership MUST include component boundaries that affect consumers, compatibility, data, security, operations, or acceptance. It MUST also include internal constraints that the operator selected as part of a tradeoff.

The plan MAY own file decomposition, private data structures, internal signatures, task boundaries, and equivalent implementation choices. Plan-owned choices MUST remain within approved behavior, scope, architecture, constraints, and non-goals.

A change to plan-owned detail MAY proceed without operator reapproval only when it remains equivalent within approved boundaries. A change that alters externally material structure or an operator-selected constraint MUST follow proposal change control.

##### Scenario: Equivalent internal signature

- GIVEN the plan selects a private function signature
- WHEN the planner replaces it with an equivalent internal signature within approved boundaries
- THEN plan review can approve the choice without operator reapproval

##### Scenario: Binding component boundary changes

- GIVEN the approved proposal fixes a component boundary that affects consumers
- WHEN planning proposes a different boundary
- THEN planning stops
- AND the workflow applies proposal change control before execution

#### Requirement: Complementary plan-review contracts

Every implementation plan MUST treat the feature spec as the observable-behavior contract. It MUST treat the approved proposal as the contract for intent, scope, binding architecture, constraints, non-goals, acceptance, and risk treatment.

The plan MUST map changed feature-spec behavior to implementation tasks and proof. It MUST map established unchanged baseline behavior to preservation or regression checks, not change tasks. Every plan task MUST trace to changed behavior or proposal work retained for planning. Each task MUST carry every applicable proposal-owned constraint. The plan MUST stop when the proposal and feature spec conflict.

Planning MUST confirm decomposition. A fresh plan reviewer MUST check complete behavior coverage, baseline preservation, proposal-constraint coverage, task buildability, test proof, scope exclusions, and architecture ownership. The workflow MUST resolve blocking findings and obtain plan-review approval before execution. It MUST NOT request operator approval of the plan.

##### Scenario: Plan covers behavior and constraints

- GIVEN the feature spec requires new observable behavior
- AND the approved proposal prohibits a dependency change
- WHEN the plan reviewer checks the plan
- THEN each behavior maps to tasks and tests
- AND each relevant task carries the dependency constraint
- AND execution remains blocked until the reviewer approves

##### Scenario: Proposal and spec conflict

- GIVEN the approved proposal and feature spec prescribe incompatible outcomes
- WHEN planning detects the conflict
- THEN planning stops
- AND it repairs and re-reviews the affected upstream artifact
- AND execution does not start from a locally selected interpretation

##### Scenario: Unchanged baseline maps to checks

- GIVEN an undocumented-domain feature spec contains unchanged baseline behavior and changed behavior
- WHEN the planner creates a contract-complete plan
- THEN changed behavior maps to implementation tasks and proof
- AND unchanged baseline behavior maps to preservation or regression checks
- AND unchanged baseline behavior does not map to change tasks

#### Requirement: Artifact-derived implementation context

Implementation dispatches MUST derive controlled design context from the approved proposal, reviewed feature spec, and reviewed plan. A dispatch MAY add repository facts, file paths, diffs, command output, logs, and operational evidence only when that evidence cannot change a controlled decision.

A dispatch MUST NOT introduce or resolve intent, behavior, scope, binding architecture, thresholds, exceptions, constraints, assumptions, risk treatment, or operator-visible outcomes absent from approved artifacts. When an implementer needs missing controlled information, the controller MUST repair the appropriate upstream artifact instead of supplying the decision only in a dispatch.

##### Scenario: Missing controlled decision

- GIVEN an implementer reports that approved artifacts omit a required behavior decision
- WHEN the controller handles the report
- THEN it stops implementation
- AND it applies proposal change control
- AND it does not answer the decision only inside a redispatch

##### Scenario: Prompt-only repository evidence

- GIVEN an implementer needs current test output
- AND that output cannot change a controlled decision
- WHEN the controller obtains the output
- THEN it MAY include the output in a complete redispatch
- AND no operator reapproval is required

##### Scenario: Evidence can change meaning

- GIVEN repository evidence reveals an undocumented consumer
- AND supporting that consumer can change scope or behavior
- WHEN the controller receives the evidence
- THEN it stops implementation
- AND it returns the decision through proposal change control

#### Requirement: Approved proposal change control

After operator approval, every proposal edit MUST stop downstream work and create a new version. This rule MUST include format-only edits. The workflow MUST repeat cold review and operator approval for the new exact version.

A controlled meaning change MUST invalidate every affected downstream artifact and approval. Controlled meaning includes intent, behavior, scope, binding architecture, thresholds, exceptions, constraints, assumptions, risk treatment, and operator-visible outcomes. The workflow MUST regenerate or repair and re-review each affected feature spec, plan, implementation result, and living-spec change before work resumes.

A format-only correction MAY remain in an automated artifact-review loop only for a downstream derived artifact when meaning cannot change. Uncertainty about whether a correction changes meaning MUST trigger proposal revision and reapproval.

##### Scenario: Consumer discovery changes behavior

- GIVEN implementation reveals a previously unknown consumer requirement
- AND satisfying it changes observable behavior
- WHEN the workflow classifies the discovery
- THEN it stops work
- AND it revises, cold-reviews, and reapproves the proposal
- AND it invalidates and re-reviews affected downstream artifacts

##### Scenario: Format-only spec correction

- GIVEN a derived feature-spec scenario omits a required GIVEN keyword
- AND adding the keyword cannot change controlled meaning
- WHEN the reviewer reports the defect
- THEN the author fixes and re-reviews the spec
- AND the workflow does not request operator reapproval

##### Scenario: Format-only proposal correction

- GIVEN an operator-approved proposal contains a formatting defect
- WHEN the author corrects that defect
- THEN the correction creates a new proposal version
- AND the workflow repeats cold review and operator approval

##### Scenario: Meaning uncertainty

- GIVEN an artifact correction can have more than one controlled meaning
- WHEN the workflow evaluates change control
- THEN it stops downstream work
- AND it returns to proposal revision, cold review, and operator reapproval

#### Requirement: Single High-risk two-pass review

An initial review dispatch MUST request a complete gate review of one artifact version against one review contract and its supplied review inputs. The workflow MUST make one initial review dispatch for each gate, artifact version, review contract, complete input set, and review task. It MUST use one fresh reviewer context for that dispatch. It MUST NOT dispatch a duplicate initial review when the artifact version, review contract, review inputs, and review task are identical.

An artifact edit MUST create a new artifact version. The new version MUST receive a new complete initial review. When the workflow adds missing context, it MAY make a new initial review dispatch for the same artifact version. When a `BLOCKED` or `NEEDS_CONTEXT` result changes the review inputs or task, it MAY also make a new initial review dispatch. Each such dispatch MUST use the complete new inputs and task.

At each High-risk spec or final gate, every initial review MUST complete these explicit passes before it issues one report and verdict:

1. **Contract pass:** The reviewer MUST check semantic fidelity, requirement coverage, scope and constraints, testability, and invented decisions.
2. **Risk pass:** The reviewer MUST check applicable compatibility, migration, rollback, security and privacy, failure recovery, observability, operations, and approved risk-treatment evidence.

Each High-risk initial review after an artifact change, an input change, or a task change MUST perform both passes against the complete new inputs. Planning or finishing MUST remain blocked until the initial-review report and each required targeted confirmation leave no blocking finding for the reviewed artifact version.

A rejection-confirmation re-dispatch required by `docs/specs/review-adjudication.md` MUST be exempt from the duplicate-initial-review prohibition. It MUST use the same reviewer agent profile as the initial review that produced the finding. It MUST perform only the targeted confirmation task. When the artifact is unchanged, the confirmation MUST NOT repeat the complete initial review or both High-risk passes.

When confirmation or fixes change the artifact, the corrected artifact MUST become a new version. That version MUST receive a new complete initial review. At a High-risk gate, the new initial review MUST perform both passes against the complete corrected inputs.

##### Scenario: High-risk spec uses two passes

- GIVEN a High-risk feature-spec version is ready for initial review
- WHEN the fresh reviewer performs the initial review
- THEN it completes the contract pass and the risk pass
- AND it issues one report and verdict for that feature-spec version
- AND planning remains blocked unless that initial-review verdict approves

##### Scenario: High-risk risk pass is complete

- GIVEN compatibility, migration, rollback, security, privacy, failure recovery, observability, operations, and risk-treatment evidence apply to a High-risk change
- WHEN the final reviewer performs the risk pass
- THEN it checks each applicable area before its report and verdict

##### Scenario: Duplicate initial review is prohibited

- GIVEN an initial review has been dispatched for one gate, artifact version, and review contract
- AND the review inputs and review task are identical
- WHEN the workflow prepares another initial review dispatch
- THEN it rejects the duplicate initial review dispatch

##### Scenario: Changed artifact receives full review

- GIVEN a confirmation or fix changes the reviewed High-risk artifact
- WHEN the workflow returns the corrected artifact version to its review gate
- THEN it dispatches one new complete initial review for the new version
- AND the reviewer performs both High-risk passes against the complete corrected inputs
- AND it issues one report and verdict for the corrected version

##### Scenario: Unchanged confirmation is targeted

- GIVEN finding adjudication rejects a finding from a High-risk review
- AND the reviewed artifact remains unchanged
- WHEN the workflow sends the finding and rejection reason for confirmation
- THEN the confirmation re-dispatch is exempt from the duplicate-initial-review prohibition
- AND it uses the same reviewer agent profile
- AND it performs only the targeted confirmation task
- AND it does not repeat the complete initial review or both High-risk passes

##### Scenario: Added context receives full review

- GIVEN an initial High-risk review lacks context or returns `BLOCKED` or `NEEDS_CONTEXT`
- AND the workflow adds the missing context or changes the review inputs or task
- WHEN the workflow makes a new initial review dispatch
- THEN the reviewer uses the complete new inputs and task
- AND it performs both High-risk passes before one report and verdict

#### Requirement: Implementation reviews and final acceptance

Standard and High-risk execution MUST receive a review for each plan task. Bounded execution MUST run inline for one or two tasks and MUST receive its artifact reviews and final whole-change review.

Every final whole-change review MUST check observable compliance against the complete feature spec. It MUST also check scope, binding architecture, constraints, non-goals, and acceptance against the approved proposal.

Before living-spec synchronization, the workflow MUST check every proposal acceptance example and run fresh repository verification. A failed required review, acceptance example, or verification command MUST block finishing.

##### Scenario: Behavior passes but a constraint fails

- GIVEN implementation passes every feature-spec behavior test
- AND it violates a binding proposal constraint
- WHEN final review checks the whole change
- THEN the reviewer rejects the change
- AND finishing remains blocked

##### Scenario: Acceptance example fails

- GIVEN unit tests pass
- AND one proposal acceptance example does not hold
- WHEN final acceptance runs
- THEN living-spec synchronization and integration remain blocked

##### Scenario: Standard task review

- GIVEN a Standard plan contains three tasks
- WHEN execution completes each task
- THEN each task receives its required review
- AND a final whole-change review still checks the complete proposal and feature spec

#### Requirement: Living-spec synchronization and integration

After final acceptance, the workflow MUST synchronize accepted observable behavior into the affected living spec. It MUST update an existing living spec or create one for an existing undocumented or genuinely new domain. Synchronization MUST apply accepted feature-spec changes idempotently and MUST preserve unchanged living-spec behavior.

The synchronized living spec MUST be semantically closed and MUST express complete current behavior for its domain. It MUST preserve accepted feature-spec meaning and MUST NOT depend on the proposal, plan, or chat history for current behavior. For this existing undocumented `workflow-governance` domain, the complete reviewed post-change feature spec MUST supply the initial living spec. Finishing MUST NOT invent missing baseline behavior.

An automated synchronization check MUST approve the living-spec result before integration. The workflow MUST NOT request operator approval of that synchronization. Integration MUST remain blocked until every prior gate remains valid and synchronization passes.

After all finishing gates pass, the workflow MUST offer the operator exactly two integration actions: local merge or pull request. It MUST perform an action only when the operator selects it. When the operator is silent, the workflow MUST leave the branch and worktree untouched.

##### Scenario: Workflow domain gains its initial spec

- GIVEN the complete reviewed feature spec formalizes unchanged baseline behavior and accepted changes for `workflow-governance`
- WHEN finishing synchronizes current behavior
- THEN that complete feature spec supplies the initial semantically closed living spec
- AND finishing invents no baseline behavior

##### Scenario: Synchronization is idempotent

- GIVEN a living spec contains unchanged behavior and an accepted feature-spec change
- WHEN finishing applies that change more than once
- THEN each completed synchronization produces the same living-spec content
- AND unchanged behavior remains intact

##### Scenario: Synchronization invents behavior

- GIVEN a synchronized living spec adds behavior absent from established current behavior and the accepted feature spec
- WHEN the synchronization check reviews fidelity
- THEN it rejects the living spec
- AND integration remains blocked

##### Scenario: Integration follows synchronization

- GIVEN final acceptance passed
- AND the living-spec synchronization check approved its exact result
- WHEN the workflow evaluates integration eligibility
- THEN it offers only local merge or pull request
- AND it performs the option that the operator selects without another artifact-approval gate

##### Scenario: Silence leaves the branch untouched

- GIVEN all finishing gates passed
- AND the workflow offered local merge or pull request
- WHEN the operator selects neither option
- THEN the workflow performs no integration action
- AND it leaves the branch and worktree untouched
