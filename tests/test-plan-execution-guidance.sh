#!/usr/bin/env bash
# Guidance tests for the proposal-baseline planning and execution contracts.
# Checks cross-file contracts in writing-plans, subagent-driven-development,
# executing-plans, and the implementation dispatch/review templates.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

FAILURES=0

fail() {
  echo "FAIL: $1"
  FAILURES=$((FAILURES + 1))
}

has() { # has <description> <file> <pattern>
  local desc="$1" file="$2" pattern="$3"
  if ! grep -Eq "$pattern" "$file" 2>/dev/null; then
    fail "$desc"
  fi
}

lacks() { # lacks <description> <file> <pattern>
  local desc="$1" file="$2" pattern="$3"
  if grep -Eq "$pattern" "$file" 2>/dev/null; then
    fail "$desc"
  fi
}

has_all() { # has_all <description> <file> <pattern1> <pattern2> ...
  local desc="$1" file="$2"
  shift 2
  local p
  for p in "$@"; do
    if ! grep -Eq "$p" "$file" 2>/dev/null; then
      fail "$desc"
      return
    fi
  done
}

WP="skills/writing-plans/SKILL.md"
PR="skills/writing-plans/plan-document-reviewer-prompt.md"
SDD="skills/subagent-driven-development/SKILL.md"
IMP="skills/subagent-driven-development/implementer-prompt.md"
IRP="skills/subagent-driven-development/implementation-reviewer-prompt.md"
EP="skills/executing-plans/SKILL.md"

for f in "$WP" "$PR" "$SDD" "$IMP" "$IRP" "$EP"; do
  if [ ! -f "$f" ]; then
    fail "$f exists"
  fi
done

# --- writing-plans: complementary contracts ---
has_all "writing-plans: feature spec owns observable post-change behavior" "$WP" \
  'feature spec' 'observable'
has_all "writing-plans: approved proposal owns intent, scope, binding architecture, constraints, non-goals, acceptance, risk treatment" "$WP" \
  'approved proposal' 'intent' 'scope' 'binding architecture|architecture' 'constraints' 'non-goals' 'acceptance'
has_all "writing-plans: complementary contract language" "$WP" 'complementary'
has_all "writing-plans: plan stops on proposal and spec conflict" "$WP" \
  'conflict|Conflict|incompatible' 'stop'
has_all "writing-plans: changed behavior maps to tasks and proof" "$WP" \
  'changed' 'task' 'proof|test'
has_all "writing-plans: unchanged baseline maps only to preservation or regression checks" "$WP" \
  'preservation or regression checks|preservation'
has_all "writing-plans: proposal-owned work retained by spec review maps to task or check" "$WP" \
  'retained|internal constraint' 'task|check'
has_all "writing-plans: tasks carry applicable proposal constraints and feature-spec requirements" "$WP" \
  '[Pp]roposal [Cc]onstraints|proposal-owned constraint' '[Ss]pec requirement|feature-spec requirement'
has_all "writing-plans: tasks restated without chat or bare cross-references" "$WP" \
  'chat' 'cross-reference'
has_all "writing-plans: requirement mapping for changed clauses and preserved baseline exceptions" "$WP" \
  'mapping' 'preserved baseline|preservation'
has_all "writing-plans: High-risk plan maps obligations to named evidence" "$WP" \
  'High-risk' 'obligation' 'evidence'
has_all "writing-plans: approved None only when proposal marks inapplicable or approves no action" "$WP" \
  'None' 'inapplicable|no action|approves no action'
has_all "writing-plans: provisional Bounded plan one or two cohesive tasks" "$WP" \
  'Bounded' 'one or two|two cohesive|one-to-two'
has_all "writing-plans: third required task stops planning and invokes proposal change control" "$WP" \
  'third task|more than two' 'change control'
has_all "writing-plans: plan header keeps fields and adds approved proposal path and role" "$WP" \
  'header' 'approved proposal'
has_all "writing-plans: self-review checks proposal constraints, delta coverage, preservation mapping, depth, task count" "$WP" \
  'self-review|Self-[Rr]eview' 'proposal' 'preservation|delta' 'depth' 'task count|task-count'
has_all "writing-plans: plan approval stays automated with no operator approval" "$WP" \
  'automated' 'no operator approval|never.*operator|operator never'

# --- writing-plans: depth routing replaces task count ---
has "writing-plans: Step 6 routes execution by workflow depth" "$WP" 'workflow depth'
lacks "writing-plans: no task-count routing wording" "$WP" \
  'Trivial plans \(1-2 small tasks\)|3\+ tasks|substantive \(3'
has "writing-plans: Bounded runs inline via executing-plans" "$WP" 'executing-plans'
has "writing-plans: Standard and High-risk run via subagent-driven-development regardless of task count" "$WP" \
  'regardless of task count|regardless'

# --- plan reviewer template ---
has_all "plan reviewer: required inputs include approved proposal identity and text" "$PR" \
  'approved proposal' 'identity'
has_all "plan reviewer: required inputs include complete reviewed feature spec" "$PR" \
  'feature spec'
has_all "plan reviewer: required inputs include baseline evidence and living specs" "$PR" \
  'baseline' 'living spec'
has_all "plan reviewer: required inputs include affected files and complete plan" "$PR" \
  'affected' 'plan'
has_all "plan reviewer: checks behavior coverage and baseline preservation" "$PR" \
  'behavior' 'preservation|baseline'
has_all "plan reviewer: checks proposal constraints, exclusions, acceptance, architecture ownership" "$PR" \
  'constraint' 'exclusion|non-goal' 'acceptance' 'ownership|architecture'
has_all "plan reviewer: checks buildability, task proof, and depth" "$PR" \
  'buildable|[Bb]uildability' 'proof' '[Dd]epth'
has_all "plan reviewer: rejects cross-reference omitting contract meaning" "$PR" \
  'cross-reference' 'meaning|contract content'
has_all "plan reviewer: rejects unchanged baseline mapped to change work" "$PR" \
  'preservation|unchanged' 'reject|finding|blocks'
has_all "plan reviewer: rejects missing High-risk obligation evidence and unapproved None" "$PR" \
  'High-risk' 'evidence' 'None'
has_all "plan reviewer: one initial review dispatch per version, contract, inputs, and task" "$PR" \
  'one initial|initial review' 'version' 'contract'
has_all "plan reviewer: added context after BLOCKED or NEEDS_CONTEXT permits one new complete review" "$PR" \
  'BLOCKED' 'NEEDS_CONTEXT'
has_all "plan reviewer: findings use the adjudication contract" "$PR" \
  'adjudication|review-adjudication'

# --- subagent-driven-development ---
has_all "sdd: dispatch carries exact approved proposal, reviewed feature spec, reviewed plan task" "$SDD" \
  'approved proposal' 'reviewed feature spec|feature spec' 'plan task|task'
has_all "sdd: dispatch carries artifact identities and non-controlling evidence" "$SDD" \
  'identity' 'evidence'
has_all "sdd: controller never answers missing controlled decision only in a child prompt" "$SDD" \
  'dispatch' 'controlled' 'repair|answer|resolve'
has_all "sdd: missing controlled context stops implementation and repairs upstream artifact" "$SDD" \
  'stop' 'upstream' 'repair'
has_all "sdd: prompt-only evidence only when it selects no controlled outcome" "$SDD" \
  'evidence' 'controlled'
has_all "sdd: Standard and High-risk work receives one per-task implementation review" "$SDD" \
  'per-task' 'review'
has_all "sdd: one initial reviewer per implementation version, input set, and review task" "$SDD" \
  'one initial|initial review' 'version'
has_all "sdd: artifact changes create a new version and one new complete initial review" "$SDD" \
  'new version|changed' 'new complete|complete initial'
has_all "sdd: unchanged rejected-finding confirmation is a targeted adjudication redispatch" "$SDD" \
  'targeted' 'confirm|confirmation' 'adjudication'
has_all "sdd: final whole-change review checks the complete feature spec and approved proposal" "$SDD" \
  'final' 'feature spec' 'approved proposal'
has_all "sdd: High-risk final reviewer performs contract and risk passes before one verdict" "$SDD" \
  'contract pass|contract and risk|risk pass' 'one (report|verdict)|verdict'
has_all "sdd: missing mapped High-risk evidence blocks final approval" "$SDD" \
  'evidence' 'block'
has_all "sdd: controlled artifact change uses proposal change control" "$SDD" \
  'change control'
has_all "sdd: safe derived format repair stays automated only when meaning cannot change" "$SDD" \
  'format' 'meaning'

# --- implementer prompt ---
has_all "implementer: carries approved proposal identity and complete relevant content" "$IMP" \
  'approved proposal' 'identity'
has_all "implementer: carries reviewed feature spec and reviewed plan task without chat additions" "$IMP" \
  'feature spec' 'plan' 'chat'
has_all "implementer: labels repository facts as evidence that cannot select a controlled decision" "$IMP" \
  'evidence' 'controlled'
has_all "implementer: stops before editing when a controlled decision is absent or conflicting" "$IMP" \
  'stop' 'controlled'
has_all "implementer: report names the owning upstream artifact with NEEDS_CONTEXT" "$IMP" \
  'NEEDS_CONTEXT' 'upstream|artifact'
has_all "implementer: does not accept dispatch-only clarification as a substitute for upstream repair" "$IMP" \
  'dispatch-only|redispatch|clarification' 'upstream'
has_all "implementer: TDD, one commit, standards, self-review, report contracts remain" "$IMP" \
  'TDD' '[Cc]ommit' 'self-review|Self-[Rr]eview' 'report'

# --- implementation reviewer prompt ---
has_all "impl reviewer: per-task review uses task text, reviewed plan, feature spec, proposal constraints" "$IRP" \
  'task text|task' 'plan' 'feature spec' 'proposal'
has_all "impl reviewer: final review uses complete feature spec and approved proposal as complementary contracts" "$IRP" \
  'final' 'complementary|both'
has_all "impl reviewer: required evidence includes artifact identities and mapped High-risk evidence" "$IRP" \
  'identity' 'evidence'
has_all "impl reviewer: explicit Standard final and High-risk final scope modes" "$IRP" \
  'Standard final|Standard-final' 'High-risk final|High-risk-final'
has_all "impl reviewer: High-risk final mode performs contract and risk passes before one verdict" "$IRP" \
  'contract pass|contract' 'risk pass|risk'
has_all "impl reviewer: distinguishes complete initial review from targeted unchanged rejection confirmation" "$IRP" \
  'initial review' 'targeted' 'confirm|confirmation'
has_all "impl reviewer: corrected implementation version receives a new complete initial review" "$IRP" \
  'corrected|new version|changed' 'new complete|complete initial'
has_all "impl reviewer: strict Code Review report, grounded findings, adjudication section remain" "$IRP" \
  '## Code Review' 'file:line|file and line|location' 'Rejection Confirmation|rejection'

# --- executing-plans: Bounded inline path ---
has_all "executing-plans: accepts only an approved Bounded workflow" "$EP" \
  'Bounded' 'approved'
has_all "executing-plans: one or two cohesive plan tasks" "$EP" \
  'one or two|two cohesive|one-to-two'
has_all "executing-plans: inline execution with TDD and one commit per task" "$EP" \
  'inline' 'TDD' '[Cc]ommit'
has_all "executing-plans: no per-task reviewers" "$EP" \
  'no per-task|does not dispatch per-task|without per-task'
has_all "executing-plans: one final whole-change reviewer after fresh checks" "$EP" \
  'final whole-change' 'fresh'
has_all "executing-plans: findings use unchanged adjudication" "$EP" \
  'adjudicat'
has_all "executing-plans: third required task or higher trigger stops and invokes proposal change control" "$EP" \
  'third|more than two' 'change control'
has_all "executing-plans: Standard and High-risk route to subagent-driven-development regardless of task count" "$EP" \
  'subagent-driven-development' 'regardless|workflow depth'
lacks "executing-plans: no task-count routing remains" "$EP" \
  '3 or more substantive|plan is substantive \(3\+|1-2 trivial'

# --- preserved baseline roles ---
has_all "preserved: requirement traceability and test proof in plan review" "$PR" \
  'requirement' 'proof|test'
has_all "preserved: implementer freedom for equivalent details" "$IMP" \
  'your decision|You decide|exact implementation'
has_all "preserved: adjudication contract referenced by execution reviews" "$SDD" \
  'review-adjudication|receiving-code-review'
has_all "preserved: writing-plans keeps contract-based task structure" "$WP" \
  'Interface|contract' 'Tests must prove' 'Check'

if [ "$FAILURES" -gt 0 ]; then
  echo "Plan and execution guidance tests failed: $FAILURES check(s) failed."
  exit 1
fi
echo "Plan and execution guidance tests passed."
