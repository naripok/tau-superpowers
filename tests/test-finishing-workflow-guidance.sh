#!/usr/bin/env bash
# Guidance tests for the finishing-stage workflow contracts: final acceptance,
# reviewed living-spec synchronization, and operator-directed integration.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

FAILURES=0

fail() {
  echo "FAIL: $1"
  FAILURES=$((FAILURES + 1))
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

has() {
  has_all "$@"
}

FIN="skills/finishing-a-development-branch/SKILL.md"
SYNC="skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md"

if [ ! -f "$FIN" ]; then
  fail "$FIN exists"
fi

# --- gate order: final review, depth reassessment, acceptance, verification, sync, sync review, integration ---
has_all "finishing: final review precedes synchronization" "$FIN" \
  'final' 'before.*synchron|synchron.*after.*final'
has_all "finishing: depth reassessment from accumulated evidence" "$FIN" \
  'reassess' 'depth|level'
has_all "finishing: higher result stops finishing and invokes proposal change control" "$FIN" \
  'change control|change-control'
has_all "finishing: lower result never silently lowers approved depth" "$FIN" \
  'lower' 'never|silent'
has_all "finishing: checks every proposal acceptance example against named evidence" "$FIN" \
  'acceptance example' 'evidence'
has_all "finishing: runs fresh repository verification" "$FIN" \
  'fresh' 'verification|test'
has_all "finishing: failed review, acceptance, or verification blocks synchronization" "$FIN" \
  'block' 'synchron'

# --- exact approval identities ---
has_all "finishing: cold review and operator approval attach to the current proposal identity" "$FIN" \
  'operator approval' 'identity|version'
has_all "finishing: spec, plan, implementation, and final-review approvals attach to current inputs" "$FIN" \
  'approval' 'current|exact'

# --- finishing: plan checkbox tracking ---
has_all "finishing: final acceptance checks plan checkbox completeness and blocks" "$FIN" \
  'checkbox' 'complete|every task' 'block|synchron'
has_all "finishing: plan approval binds to the identity of record" "$FIN" \
  'identity of record' 'flip|progress-tracking'

# --- High-risk final evidence ---
has_all "finishing: High-risk final approval shows one reviewer completed contract and risk passes" "$FIN" \
  'High-risk' 'contract' 'risk pass|risk'

# --- synchronization behavior ---
has_all "finishing: sync reads the accepted complete feature spec and pre-sync living spec" "$FIN" \
  'feature spec' 'living spec'
has_all "finishing: applies ADDED, MODIFIED, REMOVED idempotently preserving unchanged behavior" "$FIN" \
  'ADDED' 'MODIFIED' 'REMOVED' 'idempotent'
has_all "finishing: creates the living spec from complete reviewed post-change requirements" "$FIN" \
  'create' 'complete|reviewed'
has_all "finishing: never invents baseline behavior during synchronization" "$FIN" \
  'invent'
has_all "finishing: sync commit occurs only after review approval of the exact result" "$FIN" \
  'commit' 'after.*approval|approval.*before'
has_all "finishing: dispatches one fresh document-review synchronization check per candidate version" "$FIN" \
  'document-review' 'candidate|version'
has_all "finishing: adjudicates sync findings before fixes" "$FIN" \
  'adjudicat'
has_all "finishing: changed sync candidate gets one new complete initial review" "$FIN" \
  'changed|new version' 'new complete|complete initial'
has_all "finishing: unchanged sync rejection confirmation stays targeted" "$FIN" \
  'targeted' 'confirm'
has_all "finishing: sync uses the existing strict Document Review format" "$FIN" \
  'Document Review|document-review'
has_all "finishing: no operator approval for synchronization" "$FIN" \
  'no operator approval|without operator|never.*operator approval'

# --- cross-domain enumeration update ---
has_all "finishing: stale cross-domain gate enumeration updated in the same synchronization pass" "$FIN" \
  'enumeration|gate list|gate-wiring'
has_all "finishing: procedure content stays unchanged; only stale factual content changes" "$FIN" \
  'procedure' 'unchanged|only'
has_all "finishing: enumeration update passes the synchronization review" "$FIN" \
  'enumeration|gate list' 'review|check'

# --- integration ---
has_all "finishing: offers exactly local merge or pull request after gates pass" "$FIN" \
  'local merge' 'pull request'
has_all "finishing: performs no integration action without an explicit operator selection" "$FIN" \
  'operator' 'select|choos'
has_all "finishing: operator silence leaves the branch and worktree untouched" "$FIN" \
  'silence|never answers|do nothing' 'untouched'
has_all "finishing: merged-result verification before branch deletion remains" "$FIN" \
  'merged result|merge.*test|verify the merged'

# --- creation gate ---
has_all "finishing: undocumented-domain living spec creation happens only after final acceptance" "$FIN" \
  'after.*acceptance|acceptance.*before' 'create'

# --- sync reviewer template ---
if [ ! -f "$SYNC" ]; then
  fail "$SYNC exists"
else
  has_all "sync reviewer: required inputs include selected depth and approved proposal identity" "$SYNC" \
    'depth' 'identity'
  has_all "sync reviewer: required inputs include accepted feature spec and pre-sync living-spec text or absence" "$SYNC" \
    'feature spec' 'living spec' 'absen|without'
  has_all "sync reviewer: required inputs include candidate living spec, affected domain, and sync diff" "$SYNC" \
    'candidate' 'domain' 'diff'
  has_all "sync reviewer: accepted feature spec and established pre-sync behavior govern the gate" "$SYNC" \
    'govern|contract'
  has_all "sync reviewer: checks semantic closure, fidelity, complete current behavior, idempotence, preservation" "$SYNC" \
    'closure' 'fidelity|faithful' 'idempotent' 'preserv'
  has_all "sync reviewer: undocumented-domain check uses the complete reviewed feature spec as initial living spec" "$SYNC" \
    'undocumented|initial' 'feature spec'
  has_all "sync reviewer: rejects invented behavior and proposal, plan, or chat dependence" "$SYNC" \
    'invent' 'chat|proposal|plan'
  has_all "sync reviewer: one initial review per candidate version, contract, input set, and task" "$SYNC" \
    'one initial|initial review' 'version' 'contract'
  has_all "sync reviewer: added context after BLOCKED or NEEDS_CONTEXT permits one new complete review" "$SYNC" \
    'BLOCKED' 'NEEDS_CONTEXT'
  has_all "sync reviewer: adjudication-compatible rejection section" "$SYNC" \
    'Rejection Confirmation|rejection'
  has_all "sync reviewer: never requests operator approval" "$SYNC" \
    'operator'
  has_all "sync reviewer: cross-domain enumeration update checked against accepted gates with unchanged procedure" "$SYNC" \
    'enumeration|gate' 'procedure'
fi

if [ "$FAILURES" -gt 0 ]; then
  echo "Finishing workflow guidance tests failed: $FAILURES check(s) failed."
  exit 1
fi
echo "Finishing workflow guidance tests passed."
