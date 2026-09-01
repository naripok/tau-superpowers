# Proposal-Baseline Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a depth-aware proposal baseline that controls specification, planning, implementation, final acceptance, living-spec synchronization, and operator-directed integration.

**Architecture:** The workflow controller classifies work from repository evidence, then uses one cold-reviewed proposal version as the sole operator-intent baseline. Fresh author and reviewer contexts derive and check each downstream artifact. Planning, execution, and finishing preserve complementary proposal and feature-spec contracts without prompt-only design repair.

**Tech Stack:** Markdown Agent Skills and prompt templates, Tau isolated-subagent `task` trials, Bash guidance tests, ripgrep

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose.

**Feature spec:** `docs/design/2026-08-31-proposal-baseline-workflow-spec.md` (the behavioral contract)

**Approved proposal:** `docs/design/2026-08-31-proposal-baseline-workflow-proposal.md` (the intent, scope, architecture, constraints, risks, acceptance, and non-goal contract)

---

## Commands

Run every command from the worktree root. This repository has no Markdown formatter, linter, or type checker. The shell syntax checks and guidance tests are the focused static gates.

```bash
# Focused guidance suites
bash tests/test-proposal-baseline-guidance.sh
bash tests/test-plan-execution-guidance.sh
bash tests/test-finishing-workflow-guidance.sh

# Shell syntax
bash -n tests/test-proposal-baseline-guidance.sh \
  tests/test-plan-execution-guidance.sh \
  tests/test-finishing-workflow-guidance.sh \
  tests/test-install.sh

# Existing baseline and reference regressions
tests/test-install.sh
bash tests/test-references.sh

# Whitespace and forbidden-artifact checks
git diff --check
test ! -e docs/specs/workflow-governance.md
```

Use these exact inspection checks after the relevant task:

```bash
# Task 1: depth, proposal, baseline, and feature-spec contracts
rg -n 'Direct|Bounded|Standard|High-risk|controlled document|unresolved.*High-risk' \
  skills/using-superpowers/SKILL.md skills/brainstorming/SKILL.md
rg -n 'actor|trigger|timing|ordering|scope|conditions|exceptions|strength|threshold|observable result' \
  skills/brainstorming/feature-spec-author-prompt.md \
  skills/brainstorming/spec-document-reviewer-prompt.md
rg -n 'cold|brainstorm|current behavior|evidence|discrepanc|classification|operator' \
  skills/brainstorming/proposal-document-reviewer-prompt.md
rg -n 'proposal|feature spec|implementation plan|living.spec' \
  extensions/superpowers-subagent/agents/document-review.md
if rg -n 'approve both|approves both|User reviews proposal \+ spec|user must approve both artifacts' \
  skills/using-superpowers/SKILL.md skills/brainstorming/SKILL.md; then
  exit 1
fi

# Task 2: complementary contracts and review accounting
rg -n 'approved proposal|feature spec|changed behavior|unchanged baseline|preservation|risk treatment' \
  skills/writing-plans/SKILL.md skills/writing-plans/plan-document-reviewer-prompt.md
rg -n 'approved proposal|reviewed feature spec|reviewed plan|controlled decision|proposal change control' \
  skills/subagent-driven-development/SKILL.md \
  skills/subagent-driven-development/implementer-prompt.md
rg -n 'one initial|artifact version|contract pass|risk pass|targeted confirmation|duplicate' \
  skills/subagent-driven-development/SKILL.md \
  skills/subagent-driven-development/implementation-reviewer-prompt.md
rg -n 'Bounded|inline|one or two|final whole-change review' \
  skills/executing-plans/SKILL.md skills/subagent-driven-development/SKILL.md

# Task 3: final acceptance, synchronization, and integration
rg -n 'final acceptance|acceptance example|depth|fresh.*verification|approved proposal' \
  skills/finishing-a-development-branch/SKILL.md
rg -n 'idempotent|semantic|unchanged|invent|feature spec|initial living spec' \
  skills/finishing-a-development-branch/SKILL.md \
  skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md
rg -n 'local merge|pull request|silence|untouched|operator' \
  skills/finishing-a-development-branch/SKILL.md

# Task 4: public workflow and completed evidence record
rg -n 'Direct|Bounded|Standard|High-risk|proposal|feature spec|final acceptance|living spec|local merge|pull request' \
  README.md docs/FLOW_DESCRIPTION.md
rg -n '^## (Method|Task 1|Task 2|Task 3|Full regression|Coverage assessment)' \
  docs/skill-tests/2026-08-31-proposal-baseline-workflow.md
rg -n 'test-proposal-baseline-guidance|test-plan-execution-guidance|test-finishing-workflow-guidance' \
  tests/test-install.sh
```

Run isolated behavior trials with Tau's `task` tool. Follow `skills/writing-skills/SKILL.md` and `skills/writing-skills/testing-skills-with-subagents.md`. Use one `read-only` child per call. Use separate calls for RED and GREEN. Do not set `provider`, `model`, or `reasoningEffort`, so each pair inherits identical parent settings.

For RED, include the complete current text of every skill and template named by that trial. For GREEN, include the complete candidate text from the same paths. Keep each scenario byte-for-byte identical within its pair. Tell the child to state decisions only and to make no repository changes.

Record these items verbatim in `docs/skill-tests/2026-08-31-proposal-baseline-workflow.md`:

- The full scenario text.
- The complete final child message from each RED and GREEN call.
- The semantic status and process result.
- The failing or passing criterion assessment.
- The focused shell command, exit status, and complete output.

For each RED call, set `tasks` to one item with `agent` set to `read-only`. Build its `task` text in this exact order:

1. `This is an isolated behavior trial against the current workflow guidance.`
2. `Follow only the supplied guidance.`
3. `Read the scenario, state every decision and gate result, and explain each result.`
4. `Do not modify files or run commands.`
5. A `## Current Guidance` heading and the complete current corpus from the trial's named paths.
6. A `## Scenario` heading and the complete scenario from the applicable task.

For each GREEN call, use the same `tasks` shape and exact scenario. Change `Current Guidance` to `Candidate Guidance` and include the complete candidate corpus.

## Governing Proposal Contracts

Apply these contracts to every task:

- The reviewed proposal is the only formal operator approval artifact.
- Brainstorm conversation is elicitation for the proposal author only.
- Downstream agents use approved artifacts and repository evidence, not chat history.
- Direct work bypasses artifacts only when every Direct condition is established.
- Temporary review dispositions never become a committed ledger or coverage matrix.
- Every automated review gate applies `docs/specs/review-adjudication.md` without redefining its procedure.
- One fresh reviewer handles each initial gate review for one artifact version and contract.
- A High-risk spec or final reviewer performs one contract pass and one risk pass before one verdict.
- Branch and worktree protection remains the existing `using-git-worktrees` contract.
- Living-spec synchronization precedes integration and needs no operator approval.
- Integration offers only local merge or pull request. Operator silence changes nothing.
- No task changes extension Python, the Tau `task` tool, or provider behavior.
- No task adds mandatory operator-facing requirement labels or domain-specific operational procedures.
- The implementation assumes nothing beyond repository evidence and the approved artifacts.
- No task creates a permanent systems-engineering process or a persisted traceability artifact.
- No implementation task creates `docs/specs/workflow-governance.md`. The finishing workflow creates it after final acceptance.

## Spec-Requirement Mapping

The feature spec defines a complete domain because no living spec exists. Changed clauses map to implementation tasks. Preserved baseline exceptions map only to named preservation checks.

| Feature-spec requirement | Changed-clause task mapping | Exhaustive preserved-baseline proof |
| --- | --- | --- |
| Deterministic workflow depth classification | Task 1 guidance, static tests, and classification trial | None. |
| Level-specific workflow gates | Tasks 1, 2, and 3 define authoring, execution, acceptance, and integration gates | `test_review_adjudication_contract_preserved` checks that every automated gate still references `docs/specs/review-adjudication.md`. |
| Depth reassessment and escalation | Task 1 defines evidence-driven classification and proposal control. Tasks 2 and 3 enforce planning, implementation, and final reassessment | None. |
| Ordered proposal-baseline state flow | Tasks 1 through 3 implement the ordered handoffs. Task 4 documents them | `test_worktree_protection_preserved` checks the unchanged `using-git-worktrees` handoff before persisted non-Direct work. |
| Artifact semantic closure and role ownership | Task 1 defines proposal and feature-spec ownership. Task 2 defines plan ownership. Task 3 defines living-spec ownership | `test_artifact_format_roles_preserved` checks RFC 2119, requirement-name length, scenarios, proposal intent/scope/approach, feature-spec delta, plan internals, and living-spec current behavior. |
| Complete brownfield baseline and impact analysis | Task 1 establishes all three baseline branches. Task 2 maps unchanged behavior to checks. Task 3 creates complete current behavior only after acceptance | `test_existing_baseline_inputs_preserved` checks living-spec reading, repository exploration, and the existing feature-spec format. |
| Proposal authoring from elicitation | Task 1 | `test_proposal_roles_preserved` checks conversation elicitation plus intent, scope, alternatives, and impact content. |
| Proposal cold-reader gate | Task 1 | None. |
| Proposal-only approval identity | Task 1 | None. |
| Isolated and faithful feature-spec derivation | Task 1 | `test_undocumented_domain_format_preserved` checks the existing feature-spec format. |
| Temporary governing-claim dispositions | Task 1 | None. |
| Proposal-to-spec review gate | Task 1 | `test_spec_review_baseline_preserved` checks the fresh `document-review` context, coverage, testability, and living-spec alignment. |
| Proposal-owned architecture and plan-owned detail | Tasks 1 and 2 | `test_artifact_ownership_preserved` checks proposal approach, plan decomposition and signatures, and implementer freedom for equivalent details. |
| Complementary plan-review contracts | Task 2 | `test_plan_review_baseline_preserved` checks feature-spec behavior, proposal context, requirement traceability, test proof, fresh review, buildability, and no operator plan approval. |
| Artifact-derived implementation context | Task 2 | None. |
| Approved proposal change control | Tasks 1 through 3 | None. |
| Single High-risk two-pass review | Tasks 1 and 2 | `test_targeted_adjudication_confirmation_preserved` checks the unchanged rejection-confirmation contract. |
| Implementation reviews and final acceptance | Tasks 2 and 3 | `test_implementation_review_baseline_preserved` checks existing per-task review, final full-spec review, and fresh repository verification where each applies. |
| Living-spec synchronization and integration | Task 3 | `test_sync_and_integration_baseline_preserved` checks update-or-create behavior, idempotence, unchanged behavior, no sync approval, the two integration choices, and silence. |

Every feature-spec scenario maps to these named proofs:

| Requirement | Scenario-to-proof mapping |
| --- | --- |
| Deterministic workflow depth classification | `Mechanical change across many files`, `Standard coordination change`, `High-risk trigger wins`, `Runtime ordering affects behavior`, `Workflow gate ordering is not High-risk`, and `Unresolved High-risk fact` map to `test_depth_classification_matrix`. `Bounded change` maps to `test_bounded_classification`. `Multiple non-High-risk unknowns` and `Standard provisional level` map to `test_depth_unknown_aggregation`. |
| Level-specific workflow gates | `Bounded workflow depth` maps to `test_level_authoring_gates`, `test_level_execution_paths`, and `test_final_acceptance_order`. `Direct workflow depth` maps to `test_level_authoring_gates`. `Automated gates use adjudication` maps to `test_review_adjudication_contract_preserved`. `High-risk plan maps obligations` maps to `test_high_risk_plan_obligations`. `High-risk execution proves obligations` maps to `test_high_risk_execution_evidence`. |
| Depth reassessment and escalation | `Bounded work reveals a migration` maps to `test_depth_escalation_on_migration`. `Preapproval evidence lowers depth` and `Postapproval evidence does not downgrade` map to `test_preapproval_and_postapproval_depth`. `Direct work reveals behavior` maps to `test_direct_to_non_direct`. `Bounded plan exceeds two tasks` maps to `test_bounded_plan_limit`. `Planning reveals a higher trigger` maps to `test_planning_trigger_escalation`. `Artifact review reveals a trigger` maps to `test_artifact_review_trigger`. `Final reassessment uses all evidence` maps to `test_final_depth_reassessment`. |
| Ordered proposal-baseline state flow | `Artifact paths exist without approvals` and `Worktree precedes persisted artifacts` map to `test_workflow_order_and_state_identity`. `Full non-Direct flow` maps to `test_flow_state_order` and Task 3's `test_final_acceptance_order`. |
| Artifact semantic closure and role ownership | `Undefined proposal label` maps to `test_proposal_content_and_closure`. `Semantically closed living spec` maps to `test_sync_semantic_closure`. `Cross-reference replaces required meaning` maps to `test_plan_semantic_closure`. |
| Complete brownfield baseline and impact analysis | `Domain with a living spec`, `Existing undocumented domain`, and `Genuinely new domain` map to `test_brownfield_branch_selection`. `Undocumented baseline plan mapping` maps to `test_changed_and_unchanged_mapping`. `Material evidence conflict` maps to `test_material_discrepancy_block`. |
| Proposal authoring from elicitation | `Accepted decision exists only in conversation` maps to `test_conversation_decisions_transferred`. `Conversation agreement without proposal approval` maps to `test_proposal_only_approval_identity`. `Required section has no content` and `Unresolved controlled decision` map to `test_proposal_content_and_closure`. `Standard proposal impact` and `High-risk proposal categories` map to `test_level_authoring_gates`. |
| Proposal cold-reader gate | `Proposal is self-contained` and `Reviewer needs brainstorm history` map to `test_proposal_content_and_closure`. `Decision omitted from the proposal` maps to `test_proposal_reviewer_limit`. |
| Proposal-only approval identity | `Operator approves the proposal` maps to `test_proposal_only_approval_identity`. `Operator requests a revision` maps to `test_approved_proposal_change_control`. |
| Isolated and faithful feature-spec derivation | `Semantic strength remains intact` maps to `test_semantic_property_preservation`. `Derivation exposes a missing decision` maps to `test_spec_author_refuses_invention`. `Derive an undocumented domain spec` maps to `test_undocumented_domain_formalization`. |
| Temporary governing-claim dispositions | `Behavior and quality map to requirements`, `Internal obligations remain constraints`, `Non-behavioral work remains for planning`, `Acceptance example maps to scenarios`, `Non-goal remains excluded`, `Descriptive evidence gets no disposition`, `Rationale also prescribes work`, and `Temporary dispositions are not persisted` map to `test_governing_claim_dispositions`. |
| Proposal-to-spec review gate | `Complete faithful coverage`, `Invalid requirement name blocks review`, `Invented behavior blocks planning`, and `Unresolved disposition blocks planning` map to `test_spec_review_blocks_invalid_content`. |
| Proposal-owned architecture and plan-owned detail | `Equivalent internal signature` and `Binding component boundary changes` map to `test_plan_architecture_boundary`. |
| Complementary plan-review contracts | `Plan covers behavior and constraints` maps to `test_complementary_plan_contracts`. `Proposal and spec conflict` maps to `test_proposal_spec_conflict_stops`. `Unchanged baseline maps to checks` maps to `test_changed_and_unchanged_mapping`. |
| Artifact-derived implementation context | `Missing controlled decision` maps to `test_missing_controlled_context_repairs_upstream`. `Prompt-only repository evidence` maps to `test_noncontrolling_evidence_redispatch`. `Evidence can change meaning` maps to `test_meaning_changing_evidence_returns_upstream`. |
| Approved proposal change control | `Consumer discovery changes behavior` maps to `test_meaning_changing_evidence_returns_upstream`. `Format-only spec correction`, `Format-only proposal correction`, and `Meaning uncertainty` map to `test_format_and_proposal_change_control`. |
| Single High-risk two-pass review | `High-risk spec uses two passes` maps to `test_high_risk_spec_review_shape`. `High-risk risk pass is complete` maps to `test_high_risk_two_pass_reviewer`. `Duplicate initial review is prohibited` maps to `test_one_initial_reviewer_per_version`. `Changed artifact receives full review` maps to `test_changed_version_gets_complete_review`. `Unchanged confirmation is targeted` maps to `test_targeted_unchanged_confirmation`. `Added context receives full review` maps to `test_added_context_gets_complete_review`. |
| Implementation reviews and final acceptance | `Behavior passes but a constraint fails` maps to `test_binding_constraint_blocks_finishing`. `Acceptance example fails` maps to `test_acceptance_example_blocks_finishing`. `Standard task review` maps to `test_level_execution_paths`. |
| Living-spec synchronization and integration | `Workflow domain gains its initial spec` maps to `test_initial_living_spec_from_complete_spec`. `Synchronization is idempotent` maps to `test_sync_idempotence_and_preservation`. `Synchronization invents behavior` maps to `test_sync_rejects_invention`. `Integration follows synchronization` maps to `test_integration_actions`. `Silence leaves the branch untouched` maps to `test_operator_silence`. |

### Task 1: Proposal baseline, depth, and semantic specification

**Dispatch:** Send this complete task to one fresh `implementation` agent. The agent produces one commit after all RED and GREEN evidence passes.

**Files:**

- Modify: `skills/using-superpowers/SKILL.md` — select workflow depth from evidence and route by verified state, not artifact paths
- Modify: `skills/brainstorming/SKILL.md` — govern baseline discovery, proposal review, proposal-only approval, isolated spec derivation, and spec review
- Create: `skills/brainstorming/proposal-document-reviewer-prompt.md` — define the cold proposal review contract
- Create: `skills/brainstorming/feature-spec-author-prompt.md` — define fresh-context feature-spec derivation
- Modify: `skills/brainstorming/spec-document-reviewer-prompt.md` — define semantic proposal-to-spec review and temporary dispositions
- Modify: `extensions/superpowers-subagent/agents/document-review.md` — support proposal, feature-spec, plan, and living-spec synchronization reviews
- Create: `tests/test-proposal-baseline-guidance.sh` — enforce durable authoring-stage cross-file contracts
- Create: `docs/skill-tests/2026-08-31-proposal-baseline-workflow.md` — record Task 1 RED and GREEN outputs verbatim

**Spec requirement:** Deterministic workflow depth classification, Level-specific workflow gates, Depth reassessment and escalation, Ordered proposal-baseline state flow, Artifact semantic closure and role ownership, Complete brownfield baseline and impact analysis, Proposal authoring from elicitation, Proposal cold-reader gate, Proposal-only approval identity, Isolated and faithful feature-spec derivation, Temporary governing-claim dispositions, Proposal-to-spec review gate, Proposal-owned architecture and plan-owned detail, Approved proposal change control, and Single High-risk two-pass review.

**Proposal constraints:** Keep the proposal as the sole operator approval artifact. Give no downstream child brainstorm history. Create no approval ledger, coverage matrix, mandatory proposal labels, extension Python change, or `workflow-governance` living spec.

**Interface:**

- `skills/using-superpowers/SKILL.md` gains one workflow-depth decision procedure before its flow router.
  - The minimal evidence pass identifies domain status and every known or unresolved trigger.
  - `Direct` requires representation-only change, no program or controlled-document meaning change, no behavioral, contract, data, security, privacy, operational, or controlled-document effect, and no design decision.
  - Controlled documents include proposals, feature specs, plans, living specs, policies, and runbooks.
  - `High-risk` includes external contracts, schemas and stored-data recovery, security and privacy, concurrency and distributed consistency, destructive action, availability, compliance, and coordinated rollback.
  - Runtime or data ordering is High-risk only when failure affects observable behavior, safety, consistency, or integrity.
  - Workflow gate ordering alone does not activate the ordering trigger.
  - `Bounded` requires one domain, no material discrepancy, no runtime, deployment, consumer, producer, external-service, or operational-process coordination, one safe revert without migration or recovery, and one cohesive responsibility.
  - Every other non-Direct change is `Standard`.
  - Unresolved High-risk facts select High-risk. Other unknowns use their least-escalating values for base classification, then cause one aggregate escalation capped at High-risk.
  - File count, line count, and future task count do not increase provisional depth.
  - The highest applicable level wins. An operator-selected higher level requires proposal content.
  - Artifact paths do not prove state completion. Exact review and approval status controls routing.
  - The router carries this complete gate matrix:

| Gate | Direct | Bounded | Standard | High-risk |
| --- | --- | --- | --- | --- |
| Baseline and classification | Minimal evidence and Direct test | Concise relevant baseline in proposal | Complete relevant baseline and impact | Standard content plus applicable compatibility, migration, rollout, rollback, observability, recovery, and risk treatment |
| Proposal | None | Concise complete proposal, one cold review, operator approval | Complete proposal and impact, one cold review, operator approval | Standard proposal plus every High-risk category, one cold review, operator approval |
| Feature spec | None | Concise complete spec and one review | Full spec and one review | Full spec and one two-pass review |
| Plan | None | Concise one-to-two-task plan and one review | Full plan and one review | Obligation-mapped plan and one review |
| Execution | Targeted edit and relevant checks | Inline execution of one or two tasks | Per-task implementation and review | Mapped evidence plus per-task implementation and review |
| Final acceptance | Relevant repository checks | One final whole-change review and fresh verification | One final whole-change review and fresh verification | One two-pass final review, acceptance checks, and fresh verification |
| Living-spec synchronization and integration | None | Synchronize, check, then integrate | Synchronize, check, then integrate | Synchronize, check, then integrate after final-review approval |

- `skills/brainstorming/SKILL.md` replaces its universal dual-artifact gate with the level matrix.
  - Direct work creates no proposal, feature spec, or plan.
  - Every non-Direct change invokes `using-git-worktrees` before persisting an artifact.
  - Bounded uses concise but complete artifacts. Standard uses complete relevant impact. High-risk adds every applicable risk category.
  - The baseline procedure selects living-spec domain, undocumented existing domain, or genuinely new domain from evidence.
  - A missing living spec never proves that the domain is new.
  - The undocumented branch reconstructs complete relevant behavior from implementation, tests, interfaces, consumers, contracts, documentation, and operational evidence.
  - The proposal records evidence, material discrepancies, consumers, interfaces, contracts, data, security, operations, rollout, and rollback. Empty required categories use `None`.
  - The proposal author transfers every accepted behavior, scope, architecture, threshold, exception, constraint, assumption, risk, and acceptance decision from elicitation.
  - The proposal includes intent, baseline evidence, outcomes, acceptance examples, scope, non-goals, constraints, approach, alternatives, impact, risks, assumptions, and unresolved decisions.
  - `Unresolved Decisions` must equal `None` before cold review and operator review.
  - Cold proposal review precedes operator review. Findings use the unchanged adjudication contract.
  - Each proposal and spec gate makes one initial review dispatch per artifact version, contract, complete input set, and review task.
  - An artifact edit gets one new complete initial review. Added missing context after `BLOCKED` or `NEEDS_CONTEXT` permits one new complete review with changed inputs or task.
  - Unchanged rejection confirmation stays a targeted adjudication redispatch.
  - The operator checks that the complete cold-reviewed proposal captures the intended change.
  - Operator approval attaches to that exact proposal by commit identity, content digest, or equivalent immutable identity.
  - The workflow requests no operator approval for the feature spec, plan, or living-spec synchronization.
  - A fresh author derives the feature spec after proposal approval. Planning starts only after semantic spec-review approval.
  - Any proposal edit invalidates cold review and operator approval. A changed upstream input invalidates affected downstream reviews.
  - Reassessment occurs only when classification evidence changes. Higher postapproval depth uses proposal change control.
- `skills/brainstorming/proposal-document-reviewer-prompt.md` defines a `document-review` dispatch template.
  - Required inputs are proposal path and complete text, selected depth, candidate content identity, named evidence paths, baseline branch, and review contract.
  - The dispatch explicitly excludes brainstorm history.
  - The reviewer checks semantic closure, every required section, internal consistency, evidence grounding, discrepancies, depth, impact, risk, and actionable completeness.
  - Undefined option labels and references to prior chat are blocking closure findings.
  - Any unresolved controlled decision blocks approval.
  - The reviewer states that it cannot detect or certify a brainstorm decision omitted wholly from the proposal.
  - One initial reviewer handles the exact proposal version and complete inputs before one report.
  - A changed proposal version receives one new complete initial review. Unchanged rejection confirmation remains targeted.
  - One report uses the existing strict `## Document Review` format and grounded-finding rules.
- `skills/brainstorming/feature-spec-author-prompt.md` defines a fresh `general-purpose` author dispatch.
  - Required inputs are the complete approved proposal and immutable identity, selected depth, baseline evidence, and every relevant living spec.
  - The dispatch excludes brainstorm history and other prompt-only intent.
  - The author defines every term, option label, decision, constraint, assumption, exception, and reference needed for feature-spec meaning.
  - The author preserves actor, trigger, timing, ordering, scope, conditions, exceptions, strength, threshold, and observable result.
  - The author uses RFC 2119 keywords, descriptive names under 50 characters, and GIVEN/WHEN/THEN scenarios.
  - For an undocumented existing domain, the author formalizes complete relevant post-change behavior. This includes established unchanged behavior and requested changes.
  - The author never invents policy, threshold, exception, constraint, or outcome.
  - If two controlled meanings remain valid, the author writes no guessed decision. It reports the proposal repair with `NEEDS_CONTEXT`.
- `skills/brainstorming/spec-document-reviewer-prompt.md` treats the approved proposal, baseline, and relevant living specs as complete review inputs.
  - The reviewer recreates temporary dispositions for governing claims, not prose sentences.
  - Observable behavior and quality map to requirements and scenarios.
  - Internal constraints and non-behavioral work remain for planning.
  - Acceptance examples map to equivalent scenarios. Exclusions remain explicitly excluded.
  - Descriptive evidence gets grounding review without a disposition unless it also prescribes work.
  - Missing, ambiguous, conflicting, weakened, or invented treatment is `Blocked`.
  - Approval requires every governing claim to have a non-blocking disposition.
  - Dispositions stay in temporary review output and never become a committed artifact.
  - Every spec version receives one initial review for one complete input set and task.
  - High-risk review uses one reviewer. That reviewer performs contract and risk passes before one report and verdict.
  - The contract pass checks semantic fidelity, requirement coverage, scope, constraints, testability, and invented decisions.
  - The risk pass checks applicable compatibility, migration, rollback, security, privacy, failure recovery, observability, operations, and approved risk treatments.
  - A changed spec version receives one new complete initial review. Unchanged rejection confirmation remains targeted.
  - Requirement-name length is strictly fewer than 50 characters.
- `extensions/superpowers-subagent/agents/document-review.md` expands document scope without changing its read-only profile.
  - Supported gates are proposal review, feature-spec review, plan review, and living-spec synchronization review.
  - The agent checks only the supplied gate contract and complete inputs.
  - Its strict report heading, verdicts, grounded findings, and status line stay compatible with existing templates.
- `tests/test-proposal-baseline-guidance.sh` has interface `tests/test-proposal-baseline-guidance.sh` with no arguments.
  - It resolves the repository root from its own path.
  - It exits nonzero with a `FAIL:` line when a required cross-file contract is absent or stale dual-approval wording remains.
  - It checks all four depth names, Direct exclusions, High-risk triggers, unknown handling, worktree order, all baseline branches, proposal sections, cold review order, approval identity, fresh spec authorship, semantic properties, temporary dispositions, and one High-risk reviewer.
  - It checks that both new templates exist and that `document-review` names all four supported document gates.
  - For `skills/brainstorming/spec-document-reviewer-prompt.md`, it checks the adjudication-mandated template obligations: the grounded-finding format (artifact location, concrete consequence, contract clause, omit-if-absent), the re-check-before-reporting instruction, explicit governing-contract identification, and the rejection-confirmation section filled only on a confirmation redispatch.
  - It checks preserved RFC 2119, scenario, requirement-name, proposal, feature-spec, plan, living-spec, adjudication, and worktree roles.
  - It prints `Proposal baseline guidance tests passed.` and exits zero when all checks pass.

**Behavior:**

- The flow moves through evidence, classification, worktree, proposal, cold review, operator approval, isolated spec authoring, and spec review in that order.
- Existing undocumented behavior receives baseline reconstruction and complete post-change formalization. It never enters the new-domain branch automatically.
- Proposal review rejects references that need chat history. It does not claim impossible coverage of wholly omitted decisions.
- Spec derivation and review preserve all semantic dimensions. Missing controlled decisions return upstream.
- A format-only approved-proposal edit still creates a new version and repeats both approvals.
- A derived artifact can receive an automated format fix only when meaning cannot change.

**Tests must prove:**

- `test_depth_classification_matrix` — mechanical multi-file work stays Direct. Cross-boundary coordination is Standard. Schema, security, and behavior-affecting runtime ordering are High-risk. Workflow gate order alone is not High-risk. An unresolved High-risk fact selects High-risk.
- `test_bounded_classification` — resolved facts that meet every Bounded condition select Bounded without using future plan task count.
- `test_depth_unknown_aggregation` — unresolved non-High-risk facts cause one aggregate escalation. Several facts do not cause several escalations.
- `test_workflow_order_and_state_identity` — paths alone do not establish approval. The protected worktree precedes persisted non-Direct artifacts.
- `test_level_authoring_gates` — Direct skips artifacts. Bounded remains concise and complete. Standard carries full impact. High-risk carries all applicable risk categories.
- `test_depth_reassessment_authoring` — changed evidence triggers reassessment without consecutive checks when evidence is unchanged.
- `test_depth_escalation_on_migration` — a newly found migration stops Bounded work and enters High-risk proposal change control.
- `test_preapproval_and_postapproval_depth` — resolved preapproval evidence can lower depth before review. Postapproval evidence never lowers approved depth silently.
- `test_direct_to_non_direct` — a behavioral effect stops Direct execution and starts the complete non-Direct proposal gate.
- `test_artifact_review_trigger` — a contract trigger found during artifact review causes immediate reassessment before approval.
- `test_brownfield_branch_selection` — living, undocumented, and new domains use evidence-based branches. Missing living specs never imply new domains.
- `test_undocumented_domain_formalization` — existing undocumented behavior appears completely in baseline evidence and post-change feature-spec guidance.
- `test_material_discrepancy_block` — a discrepancy that can change controlled meaning blocks proposal approval until resolution.
- `test_proposal_content_and_closure` — every required section exists. Empty sections use `None`. Undefined labels and prior-chat references block cold approval.
- `test_conversation_decisions_transferred` — every accepted elicitation decision appears completely in the proposal before downstream use.
- `test_proposal_reviewer_limit` — cold approval does not certify capture of a wholly omitted brainstorm decision.
- `test_proposal_only_approval_identity` — only the exact cold-reviewed proposal receives operator approval. Later artifacts receive no operator approval.
- `test_isolated_spec_author` — the author receives approved artifacts and repository evidence without brainstorm history.
- `test_spec_author_refuses_invention` — absent retry policy and numeric threshold return upstream. The author selects neither.
- `test_semantic_property_preservation` — author and reviewer guidance preserves actor, trigger, timing, ordering, scope, conditions, exceptions, strength, threshold, and result.
- `test_governing_claim_dispositions` — behavior, quality, internal work, acceptance, exclusions, evidence, and compound claims receive their specified temporary treatment.
- `test_spec_review_blocks_invalid_content` — invented behavior, unresolved dispositions, invalid names, and closure defects block planning.
- `test_one_initial_authoring_reviewer` — each proposal and spec version receives one initial review per contract, complete input set, and task.
- `test_high_risk_spec_review_shape` — one initial reviewer performs contract and risk passes before one verdict.
- `test_approved_proposal_change_control` — any proposal edit repeats cold review and operator approval. Safe downstream format repair stays automated.
- `test_review_adjudication_contract_preserved` — each Task 1 automated review gate references `docs/specs/review-adjudication.md` without copying its procedure.
- `test_worktree_protection_preserved` — the existing `using-git-worktrees` branch protection remains the only worktree contract.
- `test_artifact_format_roles_preserved` — preserved feature-spec and proposal format roles remain explicit.
- `test_existing_baseline_inputs_preserved` — living specs remain current-behavior contracts and repository exploration remains required.
- `test_proposal_roles_preserved` — proposal intent, scope, alternatives, impact, and elicitation roles remain present.
- `test_undocumented_domain_format_preserved` — undocumented-domain specs retain ADDED/MODIFIED/REMOVED feature-spec structure.
- `test_spec_review_baseline_preserved` — fresh review retains coverage, testability, and living-spec alignment checks.

**Isolated behavior trials:**

Use these exact Task 1 corpora:

- `trial_depth_and_brownfield`: current or candidate `skills/using-superpowers/SKILL.md` and `skills/brainstorming/SKILL.md`.
- `trial_cold_proposal_limits`: current or candidate `skills/brainstorming/SKILL.md`, `extensions/superpowers-subagent/agents/document-review.md`, and `skills/brainstorming/proposal-document-reviewer-prompt.md` when that file exists. Record its RED absence explicitly.
- `trial_faithful_spec_derivation`: current or candidate `skills/brainstorming/SKILL.md`, `skills/brainstorming/spec-document-reviewer-prompt.md`, and `skills/brainstorming/feature-spec-author-prompt.md` when that file exists. Record its RED absence explicitly.

1. `trial_depth_and_brownfield` presents seven classification cases and one undocumented domain.
   - A deterministic formatting edit touches 40 files and changes no program or controlled-document meaning.
   - A runtime change coordinates a producer and consumer but triggers no High-risk category.
   - Separate changes affect a schema, authorization, and behavior-affecting runtime event order.
   - One case has unresolved authorization impact.
   - One case changes only workflow gate order without another High-risk trigger.
   - One existing domain has implementation, tests, consumers, and documentation but no living spec.
   - GREEN passes only if results are Direct, Standard, High-risk, High-risk, High-risk, High-risk, and Standard as applicable.
   - GREEN also requires evidence-based undocumented-domain reconstruction and complete post-change formalization.
2. `trial_cold_proposal_limits` presents one proposal with undefined `Option C` and the phrase `as agreed earlier`.
   - It also presents a second proposal that is complete on its face, while the harness states that elicitation contained one wholly omitted decision.
   - GREEN rejects the first proposal before operator review.
   - GREEN states that cold review cannot detect or certify the wholly omitted decision in the second proposal.
   - GREEN leaves intended-change fidelity with the operator's proposal review.
3. `trial_faithful_spec_derivation` presents an approved proposal with a named actor, event, immediate timing, strict ordering, scope, condition, exception, strength, threshold, and observable result.
   - Neither the proposal nor established current behavior gives a retry policy or threshold for a second unrelated behavior.
   - GREEN preserves every supplied semantic property.
   - GREEN invents neither missing value and returns both controlled decisions through proposal revision.

**Check:** Before any listed skill or prompt edit, run the new guidance script and all three RED trials. Each RED trial must fail at least one named GREEN criterion. After the edits, run all three GREEN trials and the full Task 1 command set. Every GREEN criterion and command must pass.

- [ ] Create `tests/test-proposal-baseline-guidance.sh` and the Task 1 test-record sections.
- [ ] Run the focused script against current files. Record its nonzero status and output verbatim.
- [ ] Run all Task 1 RED trials against the complete current guidance corpus. Record every result verbatim.
- [ ] Check that every RED trial fails at least one named GREEN criterion for the expected guidance gap.
- [ ] Modify the six guidance files only after the RED evidence exists.
- [ ] Run all Task 1 GREEN trials against the complete candidate corpus. Record every result verbatim.
- [ ] Run `bash tests/test-proposal-baseline-guidance.sh` and record its zero status and output verbatim.
- [ ] Run the Task 1 `rg` checks, `tests/test-install.sh`, `bash tests/test-references.sh`, `git diff --check`, and the forbidden-artifact check.
- [ ] Review the complete Task 1 diff against the approved proposal, feature spec, and governing contracts.
- [ ] Commit: `git add skills/using-superpowers/SKILL.md skills/brainstorming/SKILL.md skills/brainstorming/proposal-document-reviewer-prompt.md skills/brainstorming/feature-spec-author-prompt.md skills/brainstorming/spec-document-reviewer-prompt.md extensions/superpowers-subagent/agents/document-review.md tests/test-proposal-baseline-guidance.sh docs/skill-tests/2026-08-31-proposal-baseline-workflow.md && git commit -m "docs: establish proposal-baseline authoring gates"`

### Task 2: Complementary planning and artifact-derived execution

**Dispatch:** Send this complete task to one fresh `implementation` agent after Task 1 review passes. The agent produces one commit after all RED and GREEN evidence passes.

**Files:**

- Modify: `skills/writing-plans/SKILL.md` — make proposal and feature spec complementary planning contracts
- Modify: `skills/writing-plans/plan-document-reviewer-prompt.md` — review both contracts, baseline preservation, and High-risk obligations
- Modify: `skills/subagent-driven-development/SKILL.md` — enforce artifact-derived dispatches and level-specific review accounting
- Modify: `skills/subagent-driven-development/implementer-prompt.md` — carry exact approved artifact context and stop on missing controlled decisions
- Modify: `skills/subagent-driven-development/implementation-reviewer-prompt.md` — check proposal plus spec and define one-reviewer High-risk passes
- Modify: `skills/executing-plans/SKILL.md` — limit inline execution to Bounded work and retain final whole-change review
- Create: `tests/test-plan-execution-guidance.sh` — enforce planning and execution cross-file contracts
- Modify: `docs/skill-tests/2026-08-31-proposal-baseline-workflow.md` — append Task 2 RED and GREEN outputs verbatim

**Spec requirement:** Level-specific workflow gates, Depth reassessment and escalation, Ordered proposal-baseline state flow, Artifact semantic closure and role ownership, Complete brownfield baseline and impact analysis, Proposal-owned architecture and plan-owned detail, Complementary plan-review contracts, Artifact-derived implementation context, Approved proposal change control, Single High-risk two-pass review, and Implementation reviews and final acceptance.

**Proposal constraints:** Keep implementation context artifact-derived. Preserve one initial reviewer per artifact version. Do not resolve design in a dispatch, persist dispositions, request plan approval, or define domain-specific risk procedures.

**Interface:**

- `skills/writing-plans/SKILL.md` treats two artifacts as complementary contracts.
  - The reviewed feature spec owns observable post-change behavior.
  - The exact approved proposal owns intent, scope, binding architecture, constraints, non-goals, acceptance, and risk treatment.
  - The plan stops on conflict. It repairs and re-reviews the affected upstream artifact instead of choosing locally.
  - Changed behavior maps to tasks and named proof. Established unchanged baseline behavior maps only to preservation or regression checks.
  - Proposal work retained by spec review maps to a task or check.
  - Every task defines the terms, constraints, assumptions, exceptions, and references needed to implement it without chat or bare cross-references.
  - Every task states applicable proposal constraints and feature-spec requirements.
  - Every plan includes a requirement mapping for changed clauses and exhaustive preserved baseline exceptions.
  - A High-risk plan maps compatibility, migration, rollout, rollback, observability, recovery, and approved risk treatments to named evidence.
  - `None` is valid only when the approved proposal marks a category inapplicable or approves no action.
  - A provisional Bounded plan has one or two cohesive tasks. A third required task stops planning and invokes proposal change control.
  - Step 6 routes execution by workflow depth, not plan task count: Bounded runs inline via `executing-plans`; Standard and High-risk run via `subagent-driven-development` regardless of task count.
  - The required plan header keeps its current fields and adds the approved proposal path and role.
  - Self-review checks proposal constraints, delta-map coverage, reverse coverage, preservation mapping, depth, and task count.
  - Plan approval stays automated. The operator never approves the plan.
- `skills/writing-plans/plan-document-reviewer-prompt.md` names both governing contracts.
  - Required inputs include exact approved proposal identity and text, complete reviewed feature spec, baseline evidence, living specs, affected files, and complete plan.
  - The reviewer checks behavior coverage, baseline preservation, proposal constraints, exclusions, acceptance, architecture ownership, buildability, task proof, and depth.
  - It rejects a cross-reference that omits contract meaning needed by a task.
  - It rejects unchanged baseline mapped to change work.
  - It rejects missing High-risk obligation evidence and unapproved `None` values.
  - It makes one initial review dispatch for one plan version, contract, complete input set, and review task.
  - Added missing context after `BLOCKED` or `NEEDS_CONTEXT` permits one new complete review with changed inputs or task.
  - Findings retain the existing adjudication-compatible format.
- `skills/subagent-driven-development/SKILL.md` becomes the Standard and High-risk execution path.
  - The When-to-Use section routes by workflow depth, not plan task count: Standard and High-risk work uses this skill regardless of task count, and Bounded work runs inline via `executing-plans`.
  - Each implementer dispatch carries the exact approved proposal, reviewed feature spec, reviewed plan task, artifact identities, and non-controlling repository evidence.
  - A controller never answers missing intent, behavior, scope, architecture, threshold, exception, constraint, assumption, risk, or outcome only in a child prompt.
  - Missing controlled context stops implementation and repairs the owning upstream artifact.
  - Repository facts, diffs, logs, paths, and command output can enter a redispatch only when they select no controlled outcome.
  - Standard and High-risk work receives one per-task implementation review after each task.
  - One initial reviewer reviews each implementation version against one complete input set and review task.
  - Artifact changes create a new version and require one new complete initial review.
  - Added context or changed review tasks permit one new complete initial review with complete inputs.
  - An unchanged rejected-finding confirmation is a targeted adjudication redispatch to the same reviewer profile. It does not repeat a complete review.
  - The final whole-change review checks the complete feature spec and approved proposal.
  - A High-risk final reviewer performs contract and risk passes before one report and verdict.
  - The contract pass checks fidelity, coverage, scope, constraints, testability, and invention.
  - The risk pass checks compatibility, migration, rollback, security, privacy, recovery, observability, operations, and approved evidence.
  - Missing mapped High-risk evidence blocks final approval.
  - Any controlled artifact change uses proposal change control. Safe derived format repair stays in its automated loop only when meaning cannot change.
- `skills/subagent-driven-development/implementer-prompt.md` adds required controlled-context sections.
  - The prompt carries approved proposal identity and complete relevant content.
  - It carries the reviewed feature spec and reviewed plan task without chat-derived additions.
  - It labels repository facts as evidence that cannot select a controlled decision.
  - The implementer stops before editing when a controlled decision is absent or conflicting.
  - The report names the owning upstream artifact and missing decision with `NEEDS_CONTEXT`.
  - The implementer does not accept dispatch-only clarification as a substitute for upstream repair.
  - Existing TDD, one-commit, standards, self-review, and report contracts remain.
- `skills/subagent-driven-development/implementation-reviewer-prompt.md` defines per-task and final contracts without duplicate review dispatches.
  - Per-task review uses task text, reviewed plan, feature spec, and applicable proposal constraints.
  - Final review uses the complete feature spec and approved proposal as complementary governing contracts.
  - It checks observable behavior against the feature spec. It checks scope, binding architecture, constraints, non-goals, acceptance, and risk treatment against the proposal.
  - Required evidence includes artifact identities, all relevant files, complete diff, verification output, and mapped High-risk evidence.
  - The template has explicit `Standard final` and `High-risk final` scope modes.
  - High-risk final mode instructs one reviewer to complete contract and risk passes before one verdict.
  - The template distinguishes a complete initial review from targeted unchanged rejection confirmation.
  - A corrected implementation version receives a new complete initial review.
  - The strict `## Code Review` report, grounded findings, and adjudication section remain compatible.
- `skills/executing-plans/SKILL.md` becomes the Bounded inline path.
  - It accepts only Bounded work: an approved Bounded workflow with one or two cohesive plan tasks.
  - The controller executes tasks inline with TDD and one commit per task.
  - It does not dispatch per-task reviewers.
  - It dispatches one final whole-change reviewer after all Bounded tasks and fresh checks.
  - Findings use unchanged adjudication. Endorsed inline fixes remain controller-owned.
  - A required third task or higher trigger stops before execution and invokes proposal change control.
  - Standard and High-risk work routes to `subagent-driven-development`, regardless of task count.
- `tests/test-plan-execution-guidance.sh` has interface `tests/test-plan-execution-guidance.sh` with no arguments.
  - It resolves the repository root from its own path.
  - It checks complementary contracts, changed-versus-unchanged mapping, retained proposal work, and task proposal constraints.
  - It checks High-risk obligation mapping and approved use of `None`.
  - It checks exact approved-artifact inputs in implementer and reviewer templates.
  - It checks the dispatch-only design ban and upstream repair path.
  - It checks Bounded inline execution, Standard and High-risk per-task review, and all-level final review.
  - It pins the depth routing rule in `skills/writing-plans/SKILL.md` Step 6, `skills/subagent-driven-development/SKILL.md` When-to-Use, and `skills/executing-plans/SKILL.md`, and fails while any of the three keeps task-count routing wording.
  - It checks one initial reviewer per version, both High-risk passes, and targeted unchanged confirmation.
  - It checks preserved plan roles, traceability, test proof, reviewer freshness, implementer freedom, and adjudication references.
  - It exits nonzero with `FAIL:` for a broken contract.
  - It prints `Plan and execution guidance tests passed.` and exits zero on success.

**Behavior:**

- Plans are complete against both approved artifacts. Proposal constraints do not disappear because they are not feature-spec behavior.
- Undocumented unchanged behavior produces preservation proof and no change task.
- Missing controlled implementation context repairs the proposal or feature spec before redispatch.
- Review accounting allows one complete initial review per version and contract. It does not multiply High-risk reviewers.
- A High-risk reviewer issues one report after two explicit passes.
- Bounded work runs inline, but still receives one final whole-change review.
- Every approved-proposal edit repeats cold review and operator approval. A safe downstream format correction remains automated.

**Tests must prove:**

- `test_complementary_plan_contracts` — feature-spec behavior and proposal-owned constraints both govern each relevant task.
- `test_proposal_spec_conflict_stops` — incompatible approved artifacts return upstream. The planner chooses no local interpretation.
- `test_changed_and_unchanged_mapping` — changed behavior maps to work and proof. Established unchanged behavior maps only to preservation checks.
- `test_retained_proposal_work_mapping` — internal constraints and non-behavioral in-scope work receive task or check coverage.
- `test_plan_semantic_closure` — every task restates needed binding constraints instead of relying on a bare cross-reference.
- `test_plan_architecture_boundary` — equivalent private details remain plan-owned. Consumer-affecting boundaries return to proposal control.
- `test_bounded_plan_limit` — one or two cohesive tasks remain Bounded. A required third task stops and escalates.
- `test_planning_trigger_escalation` — newly found cross-boundary coordination or another higher trigger stops planning before execution.
- `test_high_risk_plan_obligations` — every applicable risk category maps to named evidence. Unapproved `None` blocks review.
- `test_high_risk_execution_evidence` — each mapped item is produced. Missing evidence blocks final review.
- `test_plan_review_contract` — one fresh reviewer checks coverage, preservation, constraints, exclusions, acceptance, ownership, buildability, and proof.
- `test_artifact_derived_implementer_prompt` — dispatch context comes only from the exact approved proposal, reviewed spec, and reviewed plan.
- `test_missing_controlled_context_repairs_upstream` — absent behavior, threshold, exception, or architecture stops implementation. Redispatch-only clarification is rejected.
- `test_noncontrolling_evidence_redispatch` — current test output can enter a complete redispatch when it changes no controlled decision.
- `test_meaning_changing_evidence_returns_upstream` — a newly discovered consumer stops work and invokes proposal change control.
- `test_level_execution_paths` — Bounded is inline with final review. Standard and High-risk use per-task reviews plus final review.
- `test_depth_routing_replaces_task_count` — `writing-plans` Step 6, `subagent-driven-development` When-to-Use, and `executing-plans` route by workflow depth, not plan task count: Bounded runs inline via `executing-plans`, and Standard and High-risk use `subagent-driven-development` regardless of task count. Remaining task-count routing wording in any of the three files fails.
- `test_one_initial_reviewer_per_version` — identical artifact, inputs, contract, and task never receive duplicate initial reviews.
- `test_high_risk_two_pass_reviewer` — one High-risk final reviewer performs contract and risk passes before one verdict.
- `test_changed_version_gets_complete_review` — a fix creates a new version and one new complete initial review.
- `test_added_context_gets_complete_review` — changed complete inputs after missing context receive one new complete initial review.
- `test_targeted_unchanged_confirmation` — unchanged rejection confirmation uses the same reviewer profile and only the targeted adjudication task.
- `test_format_and_proposal_change_control` — all approved-proposal edits require cold review and operator reapproval. Meaning-safe derived format fixes do not.
- `test_review_adjudication_contract_preserved` — plan, per-task, final, and Bounded review gates retain the unchanged adjudication contract.
- `test_plan_review_baseline_preserved` — requirement traceability, proof, fresh review, decomposition, and no operator approval remain.
- `test_artifact_ownership_preserved` — plan internals and equivalent implementer choices remain inside approved boundaries.
- `test_targeted_adjudication_confirmation_preserved` — rejection confirmation still follows `docs/specs/review-adjudication.md`.
- `test_implementation_review_baseline_preserved` — per-task and final full-spec review stay present where their selected level requires them.

**Isolated behavior trials:**

Use these exact Task 2 corpora:

- `trial_missing_implementation_context`: current or candidate `skills/subagent-driven-development/SKILL.md` and `skills/subagent-driven-development/implementer-prompt.md`.
- `trial_review_dispatch_accounting`: current or candidate `skills/subagent-driven-development/SKILL.md`, `skills/subagent-driven-development/implementation-reviewer-prompt.md`, `skills/brainstorming/SKILL.md`, and `skills/brainstorming/spec-document-reviewer-prompt.md`.
- `trial_approved_artifact_change_control`: current or candidate `skills/brainstorming/SKILL.md`, `skills/subagent-driven-development/SKILL.md`, and `skills/subagent-driven-development/implementer-prompt.md`. The change-control contracts live in these paths.

Every corpus embeds the complete text of each named path and excludes chat history and the trial assertions.

1. `trial_missing_implementation_context` gives an implementer a reviewed plan that needs a timeout threshold absent from both approved artifacts.
   - The deadline is one hour, two tasks are already committed, and the operator is unavailable.
   - The controller offers either a dispatch-only value or an upstream proposal repair.
   - GREEN stops implementation and selects upstream repair, cold review, operator reapproval, and affected downstream re-review.
   - GREEN does not use dispatch-only clarification despite time and sunk-cost pressure.
2. `trial_review_dispatch_accounting` gives a High-risk spec version and a High-risk final implementation version.
   - Each has one complete input set and no prior initial review.
   - One reviewer reports an endorsed finding that changes the artifact and one rejected finding on an unchanged artifact.
   - GREEN dispatches one initial reviewer per gate, version, contract, complete input set, and review task.
   - GREEN requires one reviewer to perform contract and risk passes before one verdict.
   - GREEN sends the unchanged rejection only for targeted adjudication confirmation.
   - GREEN sends the corrected new version through one new complete two-pass review.
3. `trial_approved_artifact_change_control` presents three edits.
   - The first changes only heading whitespace in the operator-approved proposal.
   - The second adds a missing GIVEN keyword to a derived scenario where meaning cannot change.
   - The third has two possible controlled meanings.
   - GREEN sends the proposal edit through cold review and operator reapproval.
   - GREEN keeps only the safe derived format repair in automated review.
   - GREEN sends the ambiguous repair through proposal change control.

**Check:** Before any listed skill or prompt edit, run the new guidance script and all three RED trials. Each RED trial must fail at least one named GREEN criterion. After the edits, run all three GREEN trials and the full Task 2 command set. Every GREEN criterion and command must pass.

- [ ] Create `tests/test-plan-execution-guidance.sh` and append the Task 2 test-record sections.
- [ ] Run the focused script against current files. Record its nonzero status and output verbatim.
- [ ] Run all Task 2 RED trials against their complete per-trial current corpora. Record every result verbatim.
- [ ] Check that every RED trial fails at least one named GREEN criterion for the expected guidance gap.
- [ ] Modify the six guidance files only after the RED evidence exists.
- [ ] Run all Task 2 GREEN trials against their complete per-trial candidate corpora. Record every result verbatim.
- [ ] Run `bash tests/test-plan-execution-guidance.sh` and record its zero status and output verbatim.
- [ ] Run the Task 2 `rg` checks, all available guidance suites, `tests/test-install.sh`, `bash tests/test-references.sh`, `git diff --check`, and the forbidden-artifact check.
- [ ] Review the complete Task 2 diff against the approved proposal, feature spec, and governing contracts.
- [ ] Commit: `git add skills/writing-plans/SKILL.md skills/writing-plans/plan-document-reviewer-prompt.md skills/subagent-driven-development/SKILL.md skills/subagent-driven-development/implementer-prompt.md skills/subagent-driven-development/implementation-reviewer-prompt.md skills/executing-plans/SKILL.md tests/test-plan-execution-guidance.sh docs/skill-tests/2026-08-31-proposal-baseline-workflow.md && git commit -m "docs: enforce artifact-derived planning and review"`

### Task 3: Final acceptance, living-spec review, and integration

**Dispatch:** Send this complete task to one fresh `implementation` agent after Task 2 review passes. The agent produces one commit after all RED and GREEN evidence passes.

**Files:**

- Modify: `skills/finishing-a-development-branch/SKILL.md` — enforce final acceptance, reviewed living-spec synchronization, and operator-directed integration
- Create: `skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md` — define synchronization fidelity review
- Create: `tests/test-finishing-workflow-guidance.sh` — enforce finishing-stage cross-file contracts
- Modify: `docs/skill-tests/2026-08-31-proposal-baseline-workflow.md` — append Task 3 RED and GREEN outputs verbatim

**Spec requirement:** Level-specific workflow gates, Depth reassessment and escalation, Ordered proposal-baseline state flow, Artifact semantic closure and role ownership, Complete brownfield baseline and impact analysis, Approved proposal change control, Single High-risk two-pass review, Implementation reviews and final acceptance, and Living-spec synchronization and integration.

**Proposal constraints:** Synchronize only after final acceptance. Request no operator sync approval. Offer only local merge or pull request. Leave the branch untouched on silence. Do not create the workflow living spec during implementation.

**Interface:**

- `skills/finishing-a-development-branch/SKILL.md` puts final acceptance before synchronization.
  - It checks that cold review and operator approval still attach to the current proposal identity.
  - It checks that spec, plan, implementation, and final-review approvals attach to their current exact inputs.
  - It reassesses depth once from all accumulated evidence when that evidence changed.
  - A higher result stops finishing and invokes proposal change control. A lower result never silently lowers approved depth.
  - It checks every proposal acceptance example against named evidence.
  - It runs the repository's complete verification commands fresh.
  - Failed review, acceptance, or verification blocks living-spec synchronization.
  - High-risk final approval must show one reviewer completed contract and risk passes.
  - Synchronization reads the accepted complete feature spec and pre-sync living spec when one exists.
  - It applies ADDED, MODIFIED, and REMOVED behavior idempotently while preserving unchanged behavior.
  - For an existing undocumented or new domain, it creates the living spec from complete reviewed post-change requirements.
  - It never invents baseline behavior during synchronization.
  - It dispatches one fresh `document-review` synchronization check for each candidate living-spec version.
  - It adjudicates findings through `docs/specs/review-adjudication.md` before fixes.
  - A changed synchronization candidate receives one new complete initial review. Unchanged rejection confirmation remains targeted.
  - The sync commit occurs only after review approval of the exact result.
  - The workflow requests no operator approval for synchronization.
  - After every gate passes, it offers exactly local merge or pull request.
  - It performs no integration action without an explicit operator selection.
  - Operator silence leaves the branch and worktree untouched.
- `skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md` defines a `document-review` dispatch template.
  - Required inputs are selected depth, exact approved proposal identity, accepted feature spec, pre-sync living-spec text or explicit absence, candidate living spec, affected domain, and sync diff.
  - The accepted feature spec and established pre-sync behavior govern the gate.
  - The reviewer checks semantic closure, feature-spec fidelity, complete current behavior, idempotence, and preservation of unchanged content.
  - Semantic closure requires every term, decision, constraint, assumption, exception, and reference needed for current behavior.
  - For an undocumented domain, it checks that the complete reviewed feature spec supplies the initial living spec.
  - It rejects invented behavior and dependence on proposal, plan, or chat for current meaning.
  - It performs one initial review per candidate version, review contract, complete input set, and review task.
  - Added missing context after `BLOCKED` or `NEEDS_CONTEXT` permits one new complete review with changed inputs or task.
  - It uses the existing strict `## Document Review` format and adjudication-compatible rejection section.
  - It never requests operator approval.
- `tests/test-finishing-workflow-guidance.sh` has interface `tests/test-finishing-workflow-guidance.sh` with no arguments.
  - It resolves the repository root from its own path.
  - It checks gate order: final review, depth reassessment, acceptance examples, fresh verification, synchronization, synchronization review, integration.
  - It checks exact approval identities and proposal change control.
  - It checks complete initial living-spec creation, idempotence, preservation, closure, fidelity, and invention rejection.
  - It checks one initial synchronization reviewer per version and targeted unchanged confirmation.
  - It checks no synchronization approval request, exactly two integration actions, and silence behavior.
  - It checks the unchanged adjudication reference and existing merge-result verification.
  - It checks that the finishing guidance creates an undocumented domain spec only after final acceptance.
  - It exits nonzero with `FAIL:` for a broken contract.
  - It prints `Finishing workflow guidance tests passed.` and exits zero on success.

**Behavior:**

- Passing feature-spec tests cannot hide a violated proposal constraint or failed acceptance example.
- Final acceptance blocks before synchronization whenever review, evidence, or verification fails.
- The complete reviewed feature spec supplies the initial workflow-governance living spec only when finishing runs after acceptance.
- Synchronization is reviewed as an exact candidate version and cannot invent behavior.
- Integration remains an operator action after all automated gates. Silence preserves the branch and worktree.

**Tests must prove:**

- `test_final_acceptance_order` — final review, depth reassessment, acceptance examples, and fresh verification all precede synchronization.
- `test_binding_constraint_blocks_finishing` — feature-spec behavior can pass while a proposal constraint fails. Finishing stays blocked.
- `test_acceptance_example_blocks_finishing` — a failed proposal example blocks synchronization despite passing tests.
- `test_final_depth_reassessment` — all accumulated changed evidence controls the final level. A higher level returns through proposal control.
- `test_exact_approval_inputs` — stale proposal, spec, plan, implementation, or review approval blocks finishing.
- `test_high_risk_final_evidence` — High-risk finishing requires the one-reviewer contract and risk pass result plus mapped evidence.
- `test_initial_living_spec_from_complete_spec` — the undocumented workflow domain receives complete reviewed post-change behavior without invention.
- `test_sync_idempotence_and_preservation` — repeated synchronization is identical and retains unchanged living-spec behavior.
- `test_sync_semantic_closure` — current behavior stands alone without proposal, plan, or chat references.
- `test_sync_rejects_invention` — behavior absent from baseline and accepted spec blocks integration.
- `test_single_sync_reviewer_per_version` — one initial synchronization reviewer handles each exact candidate, contract, complete input set, and task.
- `test_targeted_sync_confirmation` — unchanged rejection confirmation stays targeted and does not repeat the complete review.
- `test_sync_needs_no_operator_approval` — automated review approval closes synchronization without a user gate.
- `test_integration_actions` — finishing offers exactly local merge and pull request after all gates pass.
- `test_operator_silence` — no selection leaves branch and worktree untouched.
- `test_sync_and_integration_baseline_preserved` — update-or-create, idempotence, unchanged preservation, merge-result checks, and operator choices remain.
- `test_living_spec_creation_gate` — the finishing guidance creates an undocumented domain living spec only after final acceptance.
- `test_review_adjudication_contract_preserved` — synchronization review retains the unchanged adjudication contract.

**Isolated behavior trial:**

The Task 3 trial uses the complete current or candidate text from `skills/finishing-a-development-branch/SKILL.md` and its new reviewer template when present. Record the template's RED absence explicitly.

1. `trial_final_acceptance_and_sync` presents four finishing states.
   - In state one, feature-spec tests pass but implementation violates an approved no-dependency constraint.
   - In state two, tests pass but one proposal acceptance example fails.
   - In state three, final acceptance passes for an undocumented domain and the candidate living spec adds one unsupported retry behavior.
   - In state four, every gate passes and the operator gives no integration response.
   - GREEN blocks states one and two before synchronization.
   - GREEN derives state three's initial living spec from the complete accepted feature spec and rejects the invented retry behavior.
   - GREEN requests no operator sync approval.
   - GREEN offers only local merge or pull request in state four and changes nothing on silence.

**Check:** Before either listed skill or prompt edit, run the new guidance script and the RED trial. The RED trial must fail at least one named GREEN criterion. After the edits, run the GREEN trial and the full Task 3 command set. Every GREEN criterion and command must pass.

- [ ] Create `tests/test-finishing-workflow-guidance.sh` and append the Task 3 test-record sections.
- [ ] Run the focused script against current files. Record its nonzero status and output verbatim.
- [ ] Run the Task 3 RED trial against the complete current guidance corpus. Record the result verbatim.
- [ ] Check that the RED trial fails at least one named GREEN criterion for the expected guidance gap.
- [ ] Modify the finishing skill and create its reviewer template only after the RED evidence exists.
- [ ] Run the Task 3 GREEN trial against the complete candidate corpus. Record the result verbatim.
- [ ] Run `bash tests/test-finishing-workflow-guidance.sh` and record its zero status and output verbatim.
- [ ] Run the Task 3 `rg` checks, all three guidance suites, `tests/test-install.sh`, `bash tests/test-references.sh`, `git diff --check`, and the forbidden-artifact check.
- [ ] Review the complete Task 3 diff against the approved proposal, feature spec, and governing contracts.
- [ ] Commit: `git add skills/finishing-a-development-branch/SKILL.md skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md tests/test-finishing-workflow-guidance.sh docs/skill-tests/2026-08-31-proposal-baseline-workflow.md && git commit -m "docs: gate finishing on accepted living specs"`

### Task 4: Public workflow, regression wiring, and evidence completion

**Dispatch:** Send this complete task to one fresh `implementation` agent after Task 3 review passes. The agent produces one documentation commit after all regression gates pass.

**Files:**

- Modify: `README.md` — describe depth selection, proposal-only approval, isolated authoring and review, final acceptance, and operator integration
- Modify: `docs/FLOW_DESCRIPTION.md` — describe the complete ordered state flow, gate matrix, invalidation, review accounting, and edge cases
- Modify: `tests/test-install.sh` — run all three durable guidance suites as baseline regressions
- Modify: `docs/skill-tests/2026-08-31-proposal-baseline-workflow.md` — complete the campaign summary, full regression evidence, and coverage assessment

**Spec requirement:** Documentation and regression proof for all feature-spec requirements. Direct coverage includes Ordered proposal-baseline state flow, Level-specific workflow gates, Approved proposal change control, Implementation reviews and final acceptance, and Living-spec synchronization and integration.

**Proposal constraints:** Describe current behavior only. Do not add an operator gate, permanent ledger, domain-specific risk procedure, extension Python change, or workflow living spec.

**Interface:**

- `README.md` updates the included-skill and workflow summaries.
  - `using-superpowers` selects Direct, Bounded, Standard, or High-risk from evidence.
  - `brainstorming` reconstructs the baseline, cold-reviews the proposal, obtains proposal-only approval, and derives a reviewed spec in isolation.
  - `writing-plans` uses proposal and feature spec as complementary contracts.
  - `subagent-driven-development` handles Standard and High-risk work with per-task and final review.
  - `executing-plans` handles one or two Bounded tasks inline with final review.
  - `finishing-a-development-branch` performs final acceptance, reviewed synchronization, and operator-controlled integration.
  - `document-review` supports proposal, feature-spec, plan, and synchronization gates.
  - The artifact table states proposal identity and ownership boundaries.
  - The workflow summary states that only the reviewed proposal receives operator approval.
  - The installation and extension sections remain unchanged except where their workflow descriptions need current reviewer scope.
  - Existing installation text continues to require skill installation and `/reload` after guidance changes.
- `docs/FLOW_DESCRIPTION.md` replaces the old linear dual-approval flow.
  - It describes the minimal evidence pass and deterministic depth rules.
  - It includes the complete Direct, Bounded, Standard, and High-risk gate matrix.
  - It lists all 14 non-Direct states in order, from baseline through integration.
  - It states that artifact existence does not establish review or approval.
  - It describes all three brownfield branches and undocumented-domain formalization.
  - It describes proposal cold review, exact operator approval identity, fresh spec authoring, temporary dispositions, and complementary planning.
  - It describes one initial reviewer per version and the High-risk contract and risk passes.
  - It distinguishes changed-version full review from unchanged targeted confirmation.
  - It describes Bounded inline execution and Standard or High-risk per-task review.
  - It describes final acceptance before reviewed living-spec synchronization.
  - It describes invalidation, proposal edits, depth escalation, and meaning-safe downstream format repair.
  - It states that integration offers local merge or pull request only and that silence leaves work untouched.
  - Its edge cases include missing living specs, omitted brainstorm decisions, missing controlled implementation context, Bounded task overflow, evidence-driven escalation, and sync invention.
  - It keeps the existing review-adjudication and Tau isolation descriptions accurate.
  - It states this workflow guidance rollout: install the changed skills and reload active sessions.
  - It states this workflow guidance rollback: revert the workflow change, reinstall the prior skills, and reload active sessions.
- `tests/test-install.sh` gains one baseline regression function.
  - The function runs each new guidance suite from `repo_root` and fails when any suite exits nonzero.
  - It runs beside the existing full reference scan before installer fixture mutations.
  - The suite header comment names all three guidance regressions.
  - Existing installer fixtures, output contracts, and final `Installer tests passed.` line remain unchanged.
- `docs/skill-tests/2026-08-31-proposal-baseline-workflow.md` becomes the complete durable test record.
  - `## Method` names isolated calls, inherited model settings, current-versus-candidate corpora, exact-scenario pairing, and verbatim capture.
  - `## Task 1`, `## Task 2`, and `## Task 3` contain every scenario, RED result, GREEN result, shell result, and criterion assessment.
  - `## Full regression` records exact commands, statuses, and outputs from the final clean run.
  - `## Coverage assessment` maps each required behavior-trial scenario to its result and pass criteria.
  - The record states that no trial relies on brainstorm history or an ambient skill.
  - The record contains no unfinished result section.

**Behavior:**

- Public documentation matches the installed skill flow and uses one term per artifact and gate.
- The baseline installer test fails when any new cross-file guidance contract regresses.
- The completed skill-test record preserves exact evidence instead of a paraphrased success claim.
- No implementation commit contains `docs/specs/workflow-governance.md`.

**Tests must prove:**

- `test_readme_workflow_summary` — README names all depths, proposal-only approval, isolated derivation, complementary planning, review levels, final acceptance, and operator integration.
- `test_flow_state_order` — the flow description presents every non-Direct state in required order.
- `test_flow_gate_matrix` — all four levels and every gate appear with their specified depth.
- `test_flow_change_control` — approved proposal edits and higher depth invalidate the correct downstream states.
- `test_flow_review_accounting` — one initial reviewer, High-risk passes, new-version review, and targeted confirmation are distinct.
- `test_flow_brownfield_behavior` — undocumented existing domains receive reconstruction, complete formalization, preservation mapping, and finishing-time creation.
- `test_flow_final_acceptance` — proposal and spec checks plus fresh verification precede synchronization and integration.
- `test_flow_operator_integration` — only local merge and pull request appear, with silence preserving work.
- `test_install_runs_guidance_suites` — `tests/test-install.sh` invokes all three new scripts and propagates failure.
- `test_skill_record_complete` — every required scenario has verbatim RED and GREEN output plus an assessment.
- `test_full_regression_recorded` — the final command set and exact passing output appear in the record.
- `test_no_workflow_spec_created` — `docs/specs/workflow-governance.md` remains absent.
- `test_rollout_rollback_documented` — public documentation states installation, reload, revert, and prior-skill reinstallation steps.

**Check:** Run the complete Commands section and all Task 4 `rg` checks. Then inspect the full four-task diff. Every command must pass, and the test record must contain the exact final output.

- [ ] Update README and the flow description from the reviewed skill contracts.
- [ ] Wire all three guidance suites into `tests/test-install.sh` without changing installer fixture behavior.
- [ ] Complete the skill-test method, trial index, regression evidence, and coverage assessment.
- [ ] Run all three guidance suites and `bash -n` on every changed shell script.
- [ ] Run `tests/test-install.sh`, `bash tests/test-references.sh`, `git diff --check`, and `test ! -e docs/specs/workflow-governance.md`.
- [ ] Record the exact final command output and status in the skill-test record.
- [ ] Run the Task 4 `rg` checks and inspect every documentation claim against the final skills.
- [ ] Review `git diff --stat` and the complete diff for scope, current-state prose, and accidental extension Python changes.
- [ ] Commit: `git add README.md docs/FLOW_DESCRIPTION.md tests/test-install.sh docs/skill-tests/2026-08-31-proposal-baseline-workflow.md && git commit -m "docs: document proposal-baseline workflow"`

## Self-Review

- **Spec coverage:** All 19 feature-spec requirements map to Tasks 1 through 4. Every feature-spec scenario maps to a named static check, behavior trial, review gate, or preservation proof.
- **Delta coverage:** Every Changed clause maps to implementation guidance. Every preserved baseline exception maps to the exhaustive proof named in the requirement table.
- **Reverse coverage:** Every task implements approved workflow behavior, documentation, or required proof. No task introduces product runtime work.
- **Proposal coverage:** The tasks preserve proposal constraints, acceptance examples, risk rules, non-goals, and artifact ownership.
- **Cross-task consistency:** Task 1 establishes approved artifact identities and classifies depth. Task 2 consumes them and routes execution by workflow depth, not plan task count. Task 3 checks them before synchronization. Task 4 documents the same flow.
- **Review consistency:** Every automated gate retains adjudication. One initial reviewer handles one version and contract. Only High-risk spec and final gates add two explicit passes.
- **TDD order:** Tasks 1 through 3 require failing static guidance and isolated trials over per-trial current-guidance corpora before any skill edit. Candidate trials over the same per-trial candidate corpora follow the relevant edits.
- **Proportionality:** Four tasks separate authoring, planning and execution, finishing, and public regression documentation. Each task fits one implementer dispatch and one commit.
- **Scope protection:** No task changes extension Python or creates `docs/specs/workflow-governance.md`. Finishing creates that living spec only after final acceptance.
- **Completeness:** Every task has exact files, interfaces, behavior, named tests, checks, TDD checkboxes, and one commit command.
