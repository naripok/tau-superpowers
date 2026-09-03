---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to integrate the work
---

# Finishing a Development Branch

Run final acceptance. Review and commit the living-spec synchronization. Then offer the operator a local merge or a pull request.

**Announce at start:** "Using finishing-a-development-branch to complete this work."

## The Process

### Step 1: Final Acceptance

Final acceptance precedes every synchronization action. Check, in order:

1. **Approval identities are current.** Check that cold-review approval and operator approval still attach to the exact current proposal version (commit hash or content digest). Check that the feature-spec, plan, implementation, and final-review approvals attach to their current exact inputs. The plan's approval attaches to the plan's identity of record, the exact reviewed version: progress-tracking checkbox flips do not stale it. A stale approval blocks finishing and returns the work to the owning gate.
2. **High-risk final evidence.** For High-risk work, check that the one final reviewer completed the contract pass and the risk pass and that every mapped High-risk obligation has evidence. Missing evidence blocks finishing.
3. **Depth reassessment.** Reassess the workflow depth once from all accumulated evidence when that evidence changed. A higher result stops finishing and invokes proposal change control. A lower result never silently lowers the approved depth; the work can retain the approved higher depth.
4. **Proposal acceptance examples.** Check every proposal acceptance example against named evidence. A failed example blocks synchronization.
5. **Plan progress record complete.** Check that the plan document shows every task's checkboxes complete. A plan with unchecked boxes blocks synchronization and integration until the record is reconciled: flip the missed completed tasks' boxes and commit each per the tracking-commit convention.
6. **Fresh verification.** Run the repository's complete verification commands fresh (full test suite, lint, type check):

```bash
npm test / cargo test / pytest / go test ./...
```

**If any required review, acceptance example, verification command, or the plan progress record fails:** report the failures and stop. Until final acceptance passes, do not proceed to synchronization.

### Step 2: Determine the Base Branch

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

If ambiguous, ask: "This branch split from <base> — is that correct?"

### Step 3: Review and Commit Living-Spec Synchronization

Read the accepted feature spec at `docs/design/<date>-<topic>-spec.md`.

**If it declares "No Behavioral Changes":** skip this step.

**Otherwise**, produce a candidate synchronization for each `## Domain: <name>` section into `docs/specs/<name>.md`:

- **ADDED requirements:** append the full requirement block under `## Requirements`; treat an already-present requirement as MODIFIED; create the living-spec file when missing with `# <Domain>`, a brief `## Purpose`, and the requirements
- **MODIFIED requirements:** find the requirement by name; add new scenarios; replace same-named scenarios; apply description changes; preserve existing content the feature-spec section does not mention
- **REMOVED requirements:** delete the entire requirement block; already gone → no-op

Rules:

- The sync is idempotent: running it twice produces the same result, and unchanged living-spec behavior stays intact.
- For an existing undocumented or genuinely new domain, the complete reviewed post-change feature spec supplies the initial living spec. Never invent baseline behavior.
- The synchronized living spec must be semantically closed: it expresses complete current behavior without depending on the proposal, plan, or chat history.
- **Cross-domain enumeration update:** when accepted gate-wiring changes make another living spec's factual enumeration stale (for example, a gate-wiring list in another living spec), update only that stale factual content in the same synchronization pass. The procedure and behavior content of that living spec stays unchanged. The update passes through the same synchronization review.

Then dispatch one fresh `document-review` synchronization check for the candidate living-spec version. Use the template at `living-spec-document-reviewer-prompt.md`. The accepted feature spec and the established pre-sync behavior govern the gate. Before you act on any finding, adjudicate every finding per `receiving-code-review`. A changed synchronization candidate receives one new complete initial review. An unchanged rejection confirmation is a targeted adjudication redispatch. The workflow requests no operator approval for synchronization.

Commit the sync to the branch only after the synchronization review approves the exact result:

```bash
git add docs/specs/
git commit -m "sync: update <domain> spec(s)"
```

### Step 4: Present the Options

Present exactly these two options:

```
Implementation complete. How do I integrate it?

1. Merge <feature-branch> into <base-branch> locally
2. Push and create a Pull Request

Or do nothing — the branch stays as-is.
```

No other options. Perform no integration action without an explicit operator selection. If the operator never answers, the branch and worktree stay untouched.

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
  # Remove the worktree first so the branch is no longer checked out anywhere.
  git worktree remove "$WORKTREE_PATH"  # if the work happened in a worktree; run from outside it
  git branch -d "$FEATURE_BRANCH"
else
  echo "Merged-result tests failed; keeping $FEATURE_BRANCH and its worktree" >&2
fi
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

Until the PR is merged, keep the branch and the worktree.

## Red Flags

**Never:**
- Synchronize living specs before final acceptance passes
- Merge or open a PR with failing tests
- When the merged result fails tests, delete the feature branch
- Force-push without an explicit request
- Skip the living-spec sync for behavioral changes
- Invent baseline behavior during synchronization
- Request operator approval for the synchronization
- Present options other than merge or PR
- Integrate without an explicit operator selection

**Always:**
- Check approval identities before anything else
- Check every proposal acceptance example against named evidence before synchronizing
- Run the full test suite fresh before synchronization
- Review the candidate synchronization before committing it
- BEFORE merging or opening the PR, sync and commit living specs to the branch
- Before deleting the branch, run the test suite on the merged result

## Integration

**Called by:**
- **subagent-driven-development**: after the final review passes
- **executing-plans**: after the final whole-change review passes

**Pairs with:**
- **using-git-worktrees**: removes the worktree that skill created
