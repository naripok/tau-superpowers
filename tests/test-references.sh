#!/usr/bin/env bash
set -euo pipefail

# Proves the checkout-only reference scan: carried references pass, a
# checkout-only reference fails with a '<path>: <reference>' line, staged
# mode reads index content, the hook wrapper propagates the scan verdict,
# and the shipped tree carries no checkout-only reference.

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
scanner=$repo_root/tests/check-references.sh
temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

# new_fixture NAME — print a fresh source tree with the two resource roots
# the scanner requires
new_fixture() {
  local fixture=$temporary_dir/$1
  mkdir -p "$fixture/skills" "$fixture/extensions/superpowers-subagent"
  printf '%s\n' "$fixture"
}

# write_skill FIXTURE NAME BODY — create skills/<name>/SKILL.md
write_skill() {
  local fixture=$1 name=$2 body=$3
  mkdir -p "$fixture/skills/$name"
  printf '%s\n' "$body" >"$fixture/skills/$name/SKILL.md"
}

# expect_clean_scan FIXTURE LABEL — the worktree scan must find nothing
expect_clean_scan() {
  local fixture=$1 label=$2 out
  if out=$(bash "$scanner" "$fixture"); then
    return 0
  fi
  fail "$label: the scan flagged references:
$out"
}

# expect_finding FIXTURE EXPECTED LABEL — the worktree scan must exit nonzero
# and report exactly the expected '<path>: <reference>' line
expect_finding() {
  local fixture=$1 expected=$2 label=$3 out
  if out=$(bash "$scanner" "$fixture"); then
    fail "$label: the scan exited 0 but a checkout-only reference was expected"
  fi
  printf '%s\n' "$out" | grep -Fx -- "$expected" >/dev/null ||
    fail "$label: the scan did not report '$expected'; it printed:
$out"
}

# expect_usage_error LABEL ARGS... — the scanner must exit 2 for a usage error
expect_usage_error() {
  local label=$1
  shift
  local code=0
  bash "$scanner" "$@" >/dev/null 2>&1 </dev/null || code=$?
  [[ $code -eq 2 ]] || fail "$label: expected exit 2, got $code"
}

# init_git_fixture FIXTURE — git init with a deterministic branch name
init_git_fixture() {
  git -C "$1" -c init.defaultBranch=main init -q
}

# Scenario "Commit with a checkout-only reference fails", scan side: a
# reference whose target exists only at the source root is reported as
# '<path>: <reference>' with exit 1.
fixture=$(new_fixture checkout-only)
mkdir -p "$fixture/docs"
printf 'flow description\n' >"$fixture/docs/FLOW_DESCRIPTION.md"
write_skill "$fixture" bad 'For dispatch conventions, read `docs/FLOW_DESCRIPTION.md`.'
expect_finding \
  "$fixture" \
  "skills/bad/SKILL.md: docs/FLOW_DESCRIPTION.md" \
  "checkout-only detection"

# Scenario "Sibling skill reference resolves": a reference into a sibling
# skill directory resolves inside the installed tree and passes.
fixture=$(new_fixture cross-skill)
write_skill "$fixture" a 'See `../b/ref.md`.'
mkdir -p "$fixture/skills/b"
printf 'carried\n' >"$fixture/skills/b/ref.md"
expect_clean_scan "$fixture" "sibling skill reference"

# Scenario "Carried references resolve": a reference from a skill
# subdirectory to a file in the skill root resolves through the referencing
# file's installed directory and passes.
fixture=$(new_fixture subdir-ref)
write_skill "$fixture" c 'Unused.'
mkdir -p "$fixture/skills/c/sub"
printf 'guide\n' >"$fixture/skills/c/guide.md"
printf 'See `../guide.md`.\n' >"$fixture/skills/c/sub/notes.md"
expect_clean_scan "$fixture" "subdirectory reference to the skill root"

# A skill may reference a file the install places under the extension's
# installed directory; the reference resolves through the installed tree root
# and passes.
fixture=$(new_fixture tree-root)
write_skill "$fixture" d 'Config: `extensions/superpowers-subagent/pyproject.toml`.'
printf '[project]\n' >"$fixture/extensions/superpowers-subagent/pyproject.toml"
expect_clean_scan "$fixture" "tree-root basis"

# Scenario "Extension file reference resolves": an extension Markdown file
# references a file installed beside it in the extension's installed
# directory and passes.
fixture=$(new_fixture extension-ref)
printf '[project]\n' >"$fixture/extensions/superpowers-subagent/pyproject.toml"
printf 'Packaging lives in `pyproject.toml`.\n' \
  >"$fixture/extensions/superpowers-subagent/README.md"
expect_clean_scan "$fixture" "extension resource reference"

# Scenario "Workflow artifact paths are not carried resources": references
# beginning with docs/design/, docs/specs/, or docs/plans/ are never flagged,
# not even when the target is a file that exists only in the checkout.
fixture=$(new_fixture workflow-prefixes)
mkdir -p "$fixture/docs/specs" "$fixture/docs/design" "$fixture/docs/plans"
printf 'spec\n' >"$fixture/docs/specs/review-adjudication.md"
write_skill "$fixture" w \
  'Read `docs/specs/review-adjudication.md`, `docs/design/2026-01-01-topic-spec.md`, and `docs/plans/topic.md`.'
expect_clean_scan "$fixture" "workflow prefixes"

# A target whose checkout-side resolution names an existing directory is
# never flagged, even when a regular file occupies the same name at the
# source-root basis.
fixture=$(new_fixture directory-targets)
write_skill "$fixture" e 'Browse `sub/` and the [sub directory](sub).'
mkdir -p "$fixture/skills/e/sub"
printf 'not a directory\n' >"$fixture/sub"
expect_clean_scan "$fixture" "directory targets"

# Scenario "Nowhere-resolving reference does not fail the scan": a target
# that exists neither in the checkout nor in the produced tree passes.
fixture=$(new_fixture nowhere)
write_skill "$fixture" f 'See `missing/thing.md` and [gone](also/missing.md).'
expect_clean_scan "$fixture" "nowhere-resolving reference"

# Anchored targets classify by their path component: stripping the trailing
# '#fragment' leaves the same verdict as the bare path, carried or
# checkout-only.
fixture=$(new_fixture anchored-carried)
write_skill "$fixture" a 'See `../b/ref.md` and [anchored](../b/ref.md#section).'
mkdir -p "$fixture/skills/b"
printf 'carried\n' >"$fixture/skills/b/ref.md"
expect_clean_scan "$fixture" "anchored carried reference"

fixture=$(new_fixture anchored-checkout-only)
mkdir -p "$fixture/docs"
printf 'other\n' >"$fixture/docs/other.md"
write_skill "$fixture" g 'See [section](docs/other.md#section).'
expect_finding \
  "$fixture" \
  "skills/g/SKILL.md: docs/other.md" \
  "anchored checkout-only reference"

# Non-reference noise is ignored: http(s) targets, mailto targets, pure
# '#fragment' targets, and backticked tokens without a slash.
fixture=$(new_fixture noise)
write_skill "$fixture" h \
  'Visit [site](https://example.com/x), [insecure](http://example.com/y), [mail](mailto:a@b.c), [top](#section), and `plain-token`.'
expect_clean_scan "$fixture" "non-reference noise"

# Staged mode reads index content: a bad staged reference fails even after
# the working-tree copy is corrected without restaging, while the worktree
# scan passes on the correction.
fixture=$(new_fixture staged-mode)
init_git_fixture "$fixture"
mkdir -p "$fixture/docs"
printf 'flow description\n' >"$fixture/docs/FLOW_DESCRIPTION.md"
write_skill "$fixture" bad 'For dispatch conventions, read `docs/FLOW_DESCRIPTION.md`.'
git -C "$fixture" add skills/bad/SKILL.md
printf 'Dispatch conventions live in the flow description.\n' \
  >"$fixture/skills/bad/SKILL.md"
if staged_out=$(cd "$fixture" && bash "$scanner" --staged); then
  fail "staged scan accepted the bad staged reference"
fi
printf '%s\n' "$staged_out" |
  grep -Fx -- "skills/bad/SKILL.md: docs/FLOW_DESCRIPTION.md" >/dev/null ||
  fail "staged scan did not report the staged reference; it printed:
$staged_out"
expect_clean_scan "$fixture" "corrected working tree"

# The hook wrapper runs the staged scan from the fixture top level and
# propagates the verdict: nonzero and naming the file and reference for a
# staged bad reference, zero for a clean staged tree.
fixture=$(new_fixture hook)
init_git_fixture "$fixture"
mkdir -p "$fixture/.githooks" "$fixture/tests" "$fixture/docs"
cp -p "$repo_root/.githooks/pre-commit" "$fixture/.githooks/pre-commit"
cp -p "$scanner" "$fixture/tests/check-references.sh"
printf 'flow description\n' >"$fixture/docs/FLOW_DESCRIPTION.md"
write_skill "$fixture" bad 'For dispatch conventions, read `docs/FLOW_DESCRIPTION.md`.'
git -C "$fixture" add skills/bad/SKILL.md
if hook_out=$(cd "$fixture" && ./.githooks/pre-commit); then
  fail "the hook accepted a staged checkout-only reference"
fi
printf '%s\n' "$hook_out" |
  grep -Fx -- "skills/bad/SKILL.md: docs/FLOW_DESCRIPTION.md" >/dev/null ||
  fail "the hook did not name the offending file and reference; it printed:
$hook_out"
printf 'Dispatch conventions live in the flow description.\n' \
  >"$fixture/skills/bad/SKILL.md"
git -C "$fixture" add skills/bad/SKILL.md
(cd "$fixture" && ./.githooks/pre-commit) >/dev/null ||
  fail "the hook rejected a clean staged tree"

# Usage errors exit 2: --staged combined with ROOT, unknown options, two
# positionals, a ROOT without the resource layout, and --staged outside a
# repository.
fixture=$(new_fixture usage)
expect_usage_error "--staged with ROOT" --staged "$fixture"
expect_usage_error "unknown option" --bogus
expect_usage_error "two positionals" "$fixture" "$fixture"
mkdir -p "$temporary_dir/incomplete-root/extensions/superpowers-subagent"
expect_usage_error "incomplete ROOT" "$temporary_dir/incomplete-root"
code=0
(cd "$temporary_dir" && bash "$scanner" --staged) >/dev/null 2>&1 </dev/null ||
  code=$?
[[ $code -eq 2 ]] ||
  fail "--staged outside a repository: expected exit 2, got $code"

# Scenario "Shipped resources carry no checkout-only references": the
# repository as shipped scans clean. Runs last so the hermetic fixture
# behavior reports before the shipped-tree verdict.
bash "$scanner" ||
  fail "the shipped tree carries checkout-only references"

printf 'Reference scan tests passed.\n'
