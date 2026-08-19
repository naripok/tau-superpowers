---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to integrate the work
---

# Finishing a Development Branch

Verify tests, sync living specs onto the branch, then merge locally or open a PR.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests

Run the project's full test suite, fresh:

```bash
npm test / cargo test / pytest / go test ./...
```

**If tests fail:** report the failures and stop. Do not proceed until tests pass.

### Step 2: Determine the Base Branch

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

If ambiguous, ask: "This branch split from <base> — is that correct?"

### Step 3: Sync Living Specs

Read the feature spec at `docs/design/<date>-<topic>-spec.md`.

**If it declares "No Behavioral Changes":** skip this step.

**Otherwise**, for each `## Domain: <name>` section, update `docs/specs/<name>.md`:

- **ADDED requirements:**
  - Requirement not present → append the full requirement block under `## Requirements`
  - Requirement already present → treat as MODIFIED
  - Living spec file missing → create it with `# <Domain>`, a brief `## Purpose` section, and a `## Requirements` section holding the ADDED requirements
- **MODIFIED requirements:**
  - Find the requirement by name
  - Add new scenarios; replace same-named scenarios; apply description changes
  - Preserve existing content the feature-spec section doesn't mention
- **REMOVED requirements:**
  - Delete the entire requirement block (description + all scenarios). Already gone → no-op

The sync is idempotent: running it twice produces the same result.

Commit the sync to the branch:

```bash
git add docs/specs/
git commit -m "sync: update <domain> spec(s)"
```

### Step 4: Present the Options

Present exactly these two options:

```
Implementation complete. How should I integrate it?

1. Merge <feature-branch> into <base-branch> locally
2. Push and create a Pull Request

Or do nothing — the branch stays as-is.
```

No other options. If the operator never answers, the work remains on the branch untouched.

### Step 5: Execute the Choice

#### Option 1: Merge Locally

```bash
BASE_BRANCH="replace-with-base-branch"
FEATURE_BRANCH="replace-with-feature-branch"
TEST_COMMAND="replace-with-project-test-command"
WORKTREE_PATH="replace-with-worktree-path"  # if the work happened in a worktree

git checkout "$BASE_BRANCH"
git pull
git merge "$FEATURE_BRANCH"

# Verify the merged result; delete the feature branch only on success.
if bash -lc "$TEST_COMMAND"; then
  git branch -d "$FEATURE_BRANCH"
else
  echo "Merged-result tests failed; keeping $FEATURE_BRANCH" >&2
fi

# Remove the worktree if one was used (run from outside the worktree).
git worktree remove "$WORKTREE_PATH"
```

#### Option 2: Push and Create a PR

```bash
FEATURE_BRANCH="$(git branch --show-current)"
PR_TITLE="replace-with-pull-request-title"

git push -u origin "$FEATURE_BRANCH"
gh pr create --title "$PR_TITLE" --body "$(cat <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

Keep the branch and worktree until the PR is merged.

## Red Flags

**Never:**
- Merge or open a PR with failing tests
- Delete the feature branch when the merged result fails tests
- Force-push without an explicit request
- Skip the living-spec sync for behavioral changes
- Present options other than merge or PR

**Always:**
- Run the full test suite fresh before anything else
- Sync and commit living specs to the branch BEFORE merging or opening the PR
- Run the test suite on the merged result before deleting the branch

## Integration

**Called by:**
- **subagent-driven-development** — after the final review passes
- **executing-plans** — after all tasks complete

**Pairs with:**
- **using-git-worktrees** — removes the worktree that skill created
