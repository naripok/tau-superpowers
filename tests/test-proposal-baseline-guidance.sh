#!/usr/bin/env bash
set -u

# Static guidance tests for the proposal-baseline workflow gates.
# Governing plan: docs/plans/2026-08-31-proposal-baseline-workflow.md (Task 1).
#
# The script takes no arguments. It resolves the repository root from its own
# path and checks durable cross-file contracts in the guidance corpus:
# the workflow-depth decision procedure, the level gate matrix, the
# brainstorming baseline and approval flow, the two reviewer templates, the
# feature-spec author template, and the document-review agent scope.
#
# It exits nonzero and prints one FAIL: line per broken contract. When every
# contract holds it prints "Proposal baseline guidance tests passed." and
# exits zero.

if [ "$#" -gt 0 ]; then
  printf 'Usage: tests/test-proposal-baseline-guidance.sh (no arguments)\n' >&2
  exit 2
fi

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)

using=$root/skills/using-superpowers/SKILL.md
brain=$root/skills/brainstorming/SKILL.md
proposal_reviewer=$root/skills/brainstorming/proposal-document-reviewer-prompt.md
spec_author=$root/skills/brainstorming/feature-spec-author-prompt.md
spec_reviewer=$root/skills/brainstorming/spec-document-reviewer-prompt.md
doc_agent=$root/extensions/superpowers-subagent/agents/document-review.md
worktrees=$root/skills/using-git-worktrees/SKILL.md
adjudication=$root/docs/specs/review-adjudication.md

total=0
failures=0

# check LABEL COMMAND... — run the check; on failure print one FAIL: line
check() {
  local label=$1
  shift
  total=$((total + 1))
  if "$@"; then
    return 0
  fi
  failures=$((failures + 1))
  printf 'FAIL: %s\n' "$label"
}

# exists FILE — the file is present
exists() {
  [ -f "$1" ]
}

# has FILE REGEX — the file exists and matches the extended regex
has() {
  [ -f "$1" ] && grep -Eq -- "$2" "$1"
}

# lacks FILE REGEX — the file exists and does not match the extended regex
lacks() {
  [ -f "$1" ] || return 1
  ! grep -Eq -- "$2" "$1"
}

# all_has FILE REGEX... — every regex matches the file
all_has() {
  local file=$1 pattern
  shift
  [ -f "$file" ] || return 1
  for pattern in "$@"; do
    grep -Eq -- "$pattern" "$file" || return 1
  done
}

# ordered FILE EARLY LATE — the first EARLY match appears before the first LATE match
ordered() {
  local file=$1 early=$2 late=$3 first second
  [ -f "$file" ] || return 1
  first=$(grep -En -- "$early" "$file" | head -n 1 | cut -d: -f1)
  second=$(grep -En -- "$late" "$file" | head -n 1 | cut -d: -f1)
  [ -n "$first" ] && [ -n "$second" ] && [ "$first" -lt "$second" ]
}

# --- Workflow depth classification (skills/using-superpowers/SKILL.md) ---

check "using-superpowers: Direct depth is named" has "$using" 'Direct'
check "using-superpowers: Bounded depth is named" has "$using" 'Bounded'
check "using-superpowers: Standard depth is named" \
  has "$using" 'Standard (workflow )?depth|depth.*Standard|Standard.*(Bounded|High-risk|Direct)|(Bounded|High-risk|Direct).*Standard'
check "using-superpowers: High-risk depth is named" has "$using" 'High-risk'
check "using-superpowers: the depth decision procedure precedes the flow router" \
  ordered "$using" '[Dd]epth' '^## The Flow'
check "using-superpowers: the minimal evidence pass identifies domain status and triggers" \
  has "$using" 'evidence pass|domain status'
check "using-superpowers: Direct excludes controlled-document meaning changes" \
  has "$using" 'controlled.document'
check "using-superpowers: Direct excludes design decisions" \
  has "$using" 'no design decision|without (a|any) design decision'
check "using-superpowers: Direct excludes behavioral and data effects" \
  all_has "$using" 'behavioral' 'contract' 'data' 'security' 'privacy' 'operational'
check "using-superpowers: controlled documents include proposals, specs, plans, living specs, policies, runbooks" \
  all_has "$using" 'proposal' 'feature spec' 'plan' 'living spec' 'polic' 'runbook'
check "using-superpowers: High-risk includes external contracts" has "$using" 'external contract'
check "using-superpowers: High-risk includes schemas and stored-data recovery" \
  all_has "$using" 'schema' 'stored.data'
check "using-superpowers: High-risk includes security and privacy" \
  all_has "$using" 'security' 'privacy'
check "using-superpowers: High-risk includes concurrency and distributed consistency" \
  has "$using" 'distributed consistency'
check "using-superpowers: High-risk includes destructive action" has "$using" 'destructive'
check "using-superpowers: High-risk includes availability" has "$using" 'availability'
check "using-superpowers: High-risk includes compliance" has "$using" 'compliance'
check "using-superpowers: High-risk includes coordinated rollback" \
  has "$using" 'coordinated rollback'
check "using-superpowers: runtime ordering is High-risk only on observable failure" \
  has "$using" 'ordering.*only when'
check "using-superpowers: workflow gate ordering alone does not trigger High-risk" \
  has "$using" '[Gg]ate ordering'
check "using-superpowers: Bounded requires one domain" has "$using" 'one domain'
check "using-superpowers: Bounded requires no material discrepancy" \
  has "$using" 'material discrepancy'
check "using-superpowers: Bounded requires no coordination" has "$using" 'coordination'
check "using-superpowers: Bounded requires one safe revert without migration or recovery" \
  has "$using" 'safe revert'
check "using-superpowers: Bounded requires one cohesive responsibility" \
  has "$using" 'cohesive responsibility'
check "using-superpowers: every other non-Direct change is Standard" \
  has "$using" 'non-Direct'
check "using-superpowers: unresolved High-risk facts select High-risk" \
  has "$using" 'unresolved'
check "using-superpowers: other unknowns use least-escalating values" \
  has "$using" 'least-escalating'
check "using-superpowers: unknowns cause one aggregate escalation capped at High-risk" \
  has "$using" 'aggregate escalation'
check "using-superpowers: counts do not increase provisional depth" \
  has "$using" 'provisional depth'
check "using-superpowers: the highest applicable level wins" \
  has "$using" 'highest applicable level'
check "using-superpowers: an operator-selected higher level requires proposal content" \
  has "$using" 'operator-selected|operator selects'
check "using-superpowers: artifact paths do not prove state completion" \
  has "$using" 'do not prove'
check "using-superpowers: exact review and approval status controls routing" \
  has "$using" 'approval status|review and approval status'
check "using-superpowers: the gate matrix names the baseline-and-classification gate" \
  has "$using" 'Baseline and classification'
check "using-superpowers: the gate matrix names the final-acceptance gate" \
  has "$using" 'Final acceptance'
check "using-superpowers: the gate matrix names living-spec synchronization and integration" \
  has "$using" 'Living-spec synchronization'
check "using-superpowers: the gate matrix carries all four depth columns" \
  has "$using" 'Direct.*Bounded.*Standard.*High-risk'
check "using-superpowers: the gate matrix defines synchronization, check, then integrate" \
  has "$using" 'Synchronize, check, then integrate'

# --- Brainstorming flow and gates (skills/brainstorming/SKILL.md) ---

check "brainstorming: gates are level-specific and name High-risk" has "$brain" 'High-risk'
check "brainstorming: gates are level-specific and name Bounded" has "$brain" 'Bounded'
check "brainstorming: Direct work creates no proposal, feature spec, or plan" \
  has "$brain" 'no proposal'
check "brainstorming: the worktree is invoked before artifacts are persisted" \
  ordered "$brain" 'using-git-worktrees' 'docs/design'
check "brainstorming: the baseline selects the living-spec domain branch" \
  has "$brain" 'living.spec domain'
check "brainstorming: the baseline selects the undocumented existing domain branch" \
  has "$brain" 'undocumented'
check "brainstorming: the baseline selects the genuinely new domain branch" \
  has "$brain" 'genuinely new'
check "brainstorming: a missing living spec never proves the domain is new" \
  has "$brain" 'never proves'
check "brainstorming: the undocumented branch reconstructs behavior from operational evidence" \
  has "$brain" 'operational'
check "brainstorming: the proposal records consumers" has "$brain" 'consumers'
check "brainstorming: the proposal records rollout and rollback" \
  all_has "$brain" 'rollout' 'rollback'
check "brainstorming: empty required proposal categories use None" has "$brain" 'None'
check "brainstorming: the proposal records baseline evidence" has "$brain" '[Bb]aseline'
check "brainstorming: the proposal states outcomes" has "$brain" '[Oo]utcomes'
check "brainstorming: the proposal states acceptance examples" \
  has "$brain" 'acceptance example'
check "brainstorming: the proposal states non-goals" has "$brain" '[Nn]on-goals'
check "brainstorming: the proposal states constraints" has "$brain" '[Cc]onstraints'
check "brainstorming: the proposal states assumptions" has "$brain" '[Aa]ssumptions'
check "brainstorming: the proposal states risks" has "$brain" '[Rr]isks'
check "brainstorming: the proposal states alternatives" has "$brain" '[Aa]lternatives'
check "brainstorming: the proposal states unresolved decisions" \
  has "$brain" 'Unresolved Decisions'
check "brainstorming: Unresolved Decisions must equal None before review" \
  has "$brain" 'Unresolved Decisions.*None'
check "brainstorming: cold proposal review precedes operator review" \
  ordered "$brain" 'cold review' 'operator (review|approval)'
check "brainstorming: each artifact version gets one initial review dispatch" \
  has "$brain" 'initial review'
check "brainstorming: an artifact edit gets one new complete review" \
  has "$brain" 'new complete'
check "brainstorming: added missing context after BLOCKED or NEEDS_CONTEXT permits a new review" \
  has "$brain" 'NEEDS_CONTEXT'
check "brainstorming: unchanged rejection confirmation stays a targeted redispatch" \
  has "$brain" 'rejection confirmation|re.dispatch|redispatch'
check "brainstorming: the operator checks that the proposal captures the intended change" \
  has "$brain" 'intended change'
check "brainstorming: operator approval attaches to an immutable proposal identity" \
  has "$brain" 'content digest|commit identity|immutable identity'
check "brainstorming: no operator approval for the spec, plan, or synchronization" \
  has "$brain" 'no operator approval'
check "brainstorming: a fresh author derives the feature spec after proposal approval" \
  has "$brain" 'fresh'
check "brainstorming: planning starts after semantic spec-review approval" \
  has "$brain" 'semantic spec.review|spec.review approval'
check "brainstorming: a proposal edit invalidates cold review and operator approval" \
  has "$brain" 'invalidat'
check "brainstorming: reassessment happens only when classification evidence changes" \
  has "$brain" 'classification evidence'
check "brainstorming: review findings use the receiving-code-review adjudication procedure" \
  has "$brain" 'per `receiving-code-review`'
check "brainstorming: no reference to the checkout-only adjudication living spec" \
  lacks "$brain" 'docs/specs/review-adjudication\.md'
check "brainstorming: stale dual-approval wording is removed" \
  lacks "$brain" 'approve both artifacts|user must approve both'
check "brainstorming: the stale dual-artifact checklist item is removed" \
  lacks "$brain" 'User reviews proposal \+ spec'
check "using-superpowers: the stale both-artifacts completion wording is removed" \
  lacks "$using" 'both exist'

# --- Direct-to-non-direct escalation ---
check "direct-to-non-direct: a behavioral effect stops Direct execution and starts the proposal gate" \
  all_has "$using" 'behavioral effect|becomes non-Direct|reveals a behavioral|stops? Direct' 'proposal'
check "direct-to-non-direct: Direct escalation requires cold review and operator approval before downstream work" \
  all_has "$brain" 'Direct' 'cold review|cold-reader' 'operator approval'

# --- Preserved artifact roles ---

check "brainstorming: RFC 2119 keyword rule is preserved" has "$brain" 'RFC 2119'
check "brainstorming: GIVEN/WHEN/THEN scenario rule is preserved" \
  has "$brain" 'GIVEN.*WHEN.*THEN'
check "brainstorming: requirement names stay under 50 characters" \
  has "$brain" 'under 50 characters|fewer than 50'
check "brainstorming: ADDED/MODIFIED/REMOVED feature-spec structure is preserved" \
  has "$brain" 'ADDED.*MODIFIED.*REMOVED'
check "brainstorming: proposal intent, scope, approach, and impact roles are preserved" \
  all_has "$brain" '## Intent' '## Scope' '## Approach' '## Impact'
check "brainstorming: writing-plans stays the next skill" has "$brain" 'writing-plans'
check "brainstorming: living specs in docs/specs remain the current-behavior input" \
  has "$brain" 'docs/specs'
check "brainstorming: the worktree contract stays using-git-worktrees" \
  has "$brain" 'using-git-worktrees'
check "using-git-worktrees: the protected .worktrees location rule remains" \
  has "$worktrees" '\.worktrees'
check "review-adjudication: the governing adjudication spec exists" exists "$adjudication"

# --- Proposal reviewer template (skills/brainstorming/proposal-document-reviewer-prompt.md) ---

check "proposal-reviewer: the template file exists" exists "$proposal_reviewer"
check "proposal-reviewer: the template defines a document-review dispatch" \
  has "$proposal_reviewer" 'document-review'
check "proposal-reviewer: required input includes the proposal path and complete text" \
  has "$proposal_reviewer" 'complete text'
check "proposal-reviewer: required input includes the selected depth" \
  has "$proposal_reviewer" 'selected depth'
check "proposal-reviewer: required input includes the candidate content identity" \
  has "$proposal_reviewer" 'content identity'
check "proposal-reviewer: required input includes named evidence paths" \
  has "$proposal_reviewer" 'evidence path'
check "proposal-reviewer: required input includes the baseline branch" \
  has "$proposal_reviewer" 'baseline branch'
check "proposal-reviewer: required input includes the review contract" \
  has "$proposal_reviewer" 'review contract'
check "proposal-reviewer: the dispatch excludes brainstorm history" \
  has "$proposal_reviewer" 'brainstorm history'
check "proposal-reviewer: the reviewer checks semantic closure" \
  has "$proposal_reviewer" 'semantic closure'
check "proposal-reviewer: the reviewer checks every required section" \
  has "$proposal_reviewer" 'required section'
check "proposal-reviewer: the reviewer checks internal consistency" \
  has "$proposal_reviewer" 'internal consistency'
check "proposal-reviewer: the reviewer checks evidence grounding" \
  has "$proposal_reviewer" 'grounding|grounded'
check "proposal-reviewer: the reviewer checks depth, impact, and risk" \
  all_has "$proposal_reviewer" 'depth' 'impact' 'risk'
check "proposal-reviewer: the reviewer checks actionable completeness" \
  has "$proposal_reviewer" 'actionable'
check "proposal-reviewer: undefined option labels are blocking closure findings" \
  has "$proposal_reviewer" 'option label'
check "proposal-reviewer: prior-chat references are blocking closure findings" \
  has "$proposal_reviewer" 'prior chat'
check "proposal-reviewer: an unresolved controlled decision blocks approval" \
  all_has "$proposal_reviewer" 'unresolved' 'block'
check "proposal-reviewer: the reviewer states it cannot detect a wholly omitted decision" \
  all_has "$proposal_reviewer" 'cannot' 'omitted'
check "proposal-reviewer: one initial reviewer handles the exact proposal version" \
  has "$proposal_reviewer" 'initial review'
check "proposal-reviewer: a changed proposal version receives a new complete review" \
  has "$proposal_reviewer" 'new complete'
check "proposal-reviewer: unchanged rejection confirmation stays targeted" \
  has "$proposal_reviewer" 'rejection confirmation|re.dispatch|redispatch'
check "proposal-reviewer: the report keeps the strict Document Review heading" \
  has "$proposal_reviewer" '## Document Review'

# --- Feature-spec author template (skills/brainstorming/feature-spec-author-prompt.md) ---

check "spec-author: the template file exists" exists "$spec_author"
check "spec-author: the template defines a fresh general-purpose author dispatch" \
  has "$spec_author" 'general-purpose'
check "spec-author: required input includes the complete approved proposal" \
  has "$spec_author" 'approved proposal'
check "spec-author: required input includes the immutable proposal identity" \
  has "$spec_author" 'immutable identity'
check "spec-author: required input includes baseline evidence" \
  has "$spec_author" 'baseline evidence'
check "spec-author: required input includes every relevant living spec" \
  has "$spec_author" 'living spec'
check "spec-author: the dispatch excludes brainstorm history" \
  has "$spec_author" 'brainstorm history'
check "spec-author: the dispatch excludes prompt-only intent" \
  has "$spec_author" 'prompt.only'
check "spec-author: the author defines every meaning-bearing term" \
  has "$spec_author" 'every term|defines every term|terms,'
check "spec-author: the author preserves actor and trigger" \
  all_has "$spec_author" 'actor' 'trigger'
check "spec-author: the author preserves timing and ordering" \
  all_has "$spec_author" 'timing' 'ordering'
check "spec-author: the author preserves scope and conditions" \
  all_has "$spec_author" 'scope' 'condition'
check "spec-author: the author preserves exceptions" has "$spec_author" 'exception'
check "spec-author: the author preserves strength and threshold" \
  all_has "$spec_author" 'strength' 'threshold'
check "spec-author: the author preserves the observable result" \
  has "$spec_author" 'result'
check "spec-author: the author uses RFC 2119 keywords" has "$spec_author" 'RFC 2119'
check "spec-author: requirement names stay under 50 characters" \
  has "$spec_author" '50 characters'
check "spec-author: scenarios use GIVEN/WHEN/THEN" has "$spec_author" 'GIVEN/WHEN/THEN'
check "spec-author: undocumented domains get complete post-change formalization" \
  all_has "$spec_author" 'undocumented' 'post.change'
check "spec-author: formalization includes established unchanged behavior" \
  has "$spec_author" 'unchanged behavior|established'
check "spec-author: the author never invents decisions or outcomes" \
  has "$spec_author" 'invent'
check "spec-author: two valid controlled meanings return NEEDS_CONTEXT" \
  has "$spec_author" 'NEEDS_CONTEXT'

# --- Spec reviewer template (skills/brainstorming/spec-document-reviewer-prompt.md) ---

check "spec-reviewer: the approved proposal is a complete review input" \
  has "$spec_reviewer" 'approved proposal'
check "spec-reviewer: the baseline is a complete review input" \
  has "$spec_reviewer" 'baseline'
check "spec-reviewer: relevant living specs are complete review inputs" \
  has "$spec_reviewer" 'living spec'
check "spec-reviewer: the reviewer recreates temporary dispositions for governing claims" \
  all_has "$spec_reviewer" 'disposition' 'temporary' 'governing claim'
check "spec-reviewer: behavior and quality map to requirements and scenarios" \
  has "$spec_reviewer" 'map to requirements|requirements and scenarios'
check "spec-reviewer: internal constraints and non-behavioral work remain for planning" \
  has "$spec_reviewer" 'remain for planning|for planning'
check "spec-reviewer: acceptance examples map to equivalent scenarios" \
  has "$spec_reviewer" 'acceptance example'
check "spec-reviewer: exclusions stay explicitly excluded" \
  has "$spec_reviewer" 'excluded|exclusion'
check "spec-reviewer: descriptive evidence gets grounding review without a disposition" \
  has "$spec_reviewer" 'descriptive evidence|prescribes work'
check "spec-reviewer: missing, ambiguous, conflicting, weakened, or invented treatment blocks" \
  has "$spec_reviewer" 'Blocked'
check "spec-reviewer: approval requires a non-blocking disposition per governing claim" \
  has "$spec_reviewer" 'non.blocking disposition'
check "spec-reviewer: dispositions never become a committed artifact" \
  has "$spec_reviewer" 'never become|never.*committed'
check "spec-reviewer: every spec version receives one initial review" \
  has "$spec_reviewer" 'initial review'
check "spec-reviewer: one reviewer performs the contract and risk passes" \
  all_has "$spec_reviewer" 'one reviewer' 'contract pass' 'risk pass'
check "spec-reviewer: the contract pass checks fidelity, coverage, testability, invention" \
  all_has "$spec_reviewer" 'fidelity' 'coverage' 'testability' 'invented'
check "spec-reviewer: the risk pass checks compatibility, migration, rollback, security, privacy, recovery, observability" \
  all_has "$spec_reviewer" 'compatibility' 'migration' 'rollback' 'privacy' 'recovery' 'observability'
check "spec-reviewer: a changed spec version receives a new complete review" \
  has "$spec_reviewer" 'new complete'
check "spec-reviewer: requirement names are strictly fewer than 50 characters" \
  has "$spec_reviewer" '50 characters'
check "spec-reviewer: findings state the artifact location" \
  has "$spec_reviewer" 'artifact location'
check "spec-reviewer: findings state the concrete consequence" \
  has "$spec_reviewer" 'concrete consequence'
check "spec-reviewer: contract findings state the contract clause" \
  has "$spec_reviewer" 'contract clause'
check "spec-reviewer: the reviewer omits findings that cannot state their grounding" \
  has "$spec_reviewer" '[Oo]mit'
check "spec-reviewer: the reviewer re-checks findings before reporting" \
  has "$spec_reviewer" '[Rr]e.[Cc]heck'
check "spec-reviewer: the governing contract is identified explicitly" \
  has "$spec_reviewer" '[Gg]overning contract'
check "spec-reviewer: the rejection-confirmation section fills only on a confirmation redispatch" \
  all_has "$spec_reviewer" 'Rejection Confirmation' 're.dispatch'

# --- Document-review agent scope (extensions/superpowers-subagent/agents/document-review.md) ---

check "document-review: the agent supports the proposal review gate" \
  has "$doc_agent" 'proposal review'
check "document-review: the agent supports the feature-spec review gate" \
  has "$doc_agent" 'feature.spec review'
check "document-review: the agent supports the plan review gate" \
  has "$doc_agent" 'plan review'
check "document-review: the agent supports the living-spec synchronization review gate" \
  has "$doc_agent" 'synchronization review'
check "document-review: the agent checks only the supplied gate contract" \
  has "$doc_agent" 'gate contract|supplied'
check "document-review: the agent checks only the complete supplied inputs" \
  has "$doc_agent" 'complete input'
check "document-review: the read-only profile is preserved" has "$doc_agent" 'read.only'
check "document-review: the strict Document Review heading is preserved" \
  has "$doc_agent" '## Document Review'
check "document-review: the verdict format is preserved" has "$doc_agent" 'Verdict'
check "document-review: grounded findings are preserved" has "$doc_agent" 'grounded'
check "document-review: the status line contract is preserved" has "$doc_agent" 'Status: DONE'

# --- Verdict ---

if [ "$failures" -gt 0 ]; then
  printf 'Proposal baseline guidance tests failed: %s of %s checks failed.\n' \
    "$failures" "$total"
  exit 1
fi
printf 'Proposal baseline guidance tests passed.\n'
exit 0
