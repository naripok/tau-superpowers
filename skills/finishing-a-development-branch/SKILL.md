---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests → Present options → Execute choice → Sync living specs → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests

**Before presenting options, verify tests pass:**

```bash
# Run project's test suite
npm test / cargo test / pytest / go test ./...
```

**If tests fail:**
```
Tests failing (<N> failures). Must fix before completing:

[Show failures]

Cannot proceed with merge/PR until tests pass.
```

Stop. Don't proceed to Step 2.

**If tests pass:** Continue to Step 2.

### Step 2: Determine Base Branch

```bash
# Try common base branches
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

Or ask: "This branch split from main - is that correct?"

### Step 3: Present Options

Present exactly these 4 options:

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

**Don't add explanation** - keep options concise.

### Step 4: Execute Choice

#### Option 1: Merge Locally

```bash
# Switch to base branch
git checkout <base-branch>

# Pull latest
git pull

# Merge feature branch
git merge <feature-branch>

# Verify tests on merged result
<test command>

# If tests pass
git branch -d <feature-branch>
```

Then: Sync living specs (Step 4.5), then Cleanup worktree (Step 5)

#### Option 2: Push and Create PR

```bash
# Push branch
git push -u origin <feature-branch>

# Create PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

Then: Sync living specs (Step 4.5), then Cleanup worktree (Step 5)

#### Option 3: Keep As-Is

Sync living specs (Step 4.5).

Then report: "Keeping branch <name>. Worktree preserved at <path>."

**Don't cleanup worktree.**

#### Option 4: Discard

**Confirm first:**
```
This will permanently delete:
- Branch <name>
- All commits: <commit-list>
- Worktree at <path>

Type 'discard' to confirm.
```

Wait for exact confirmation.

If confirmed:
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```

**Do NOT sync living specs** — the work is being discarded.

Then: Cleanup worktree (Step 5)

### Step 4.5: Sync Living Specs

**For Options 1, 2, 3 only.** (Skip for Option 4 — discard.)

Read the delta spec from `docs/design/<date>-<topic>-delta.md` and merge it into the living specs in `docs/specs/`.

The delta spec was derived during planning by comparing the feature spec (proposed behavior) against the living spec (current behavior). The sync step merges the approved changes back into the living spec, completing the cycle.

#### If the delta declares "No Behavioral Changes"

Skip the sync entirely. Commit a note if appropriate: `note: <topic> had no behavioral changes`.

#### If the delta has domain changes

For each `## Domain: <name>` section in the delta:

1. **Read** `docs/specs/<name>.md` (may not exist yet)
2. **Read** the delta's domain section
3. **Apply changes:**

   **ADDED Requirements:**
   - If the requirement doesn't exist in the living spec → append the full requirement block under `## Requirements`
   - If the requirement already exists → treat as MODIFIED (merge scenarios)
   - If the living spec file doesn't exist → create it with `# <Domain>`, a `## Purpose` section (brief), and a `## Requirements` section with the ADDED requirements

   **MODIFIED Requirements:**
   - Find the requirement by name in the living spec
   - For each scenario in the delta: if it's a new scenario name → add it; if it's an existing scenario name → replace it
   - If the delta includes a description change → update the description
   - **Preserve** any existing scenarios or content not mentioned in the delta

   **REMOVED Requirements:**
   - Remove the entire requirement block (description + all scenarios)

4. **Show summary** of what changed and get user confirmation before committing:

```
## Living Spec Sync Summary

Updated: docs/specs/notifications.md
  + Added requirement: push-delivery
  ~ Modified requirement: email-delivery (added 1 scenario)

Confirm sync? (y/n)
```

5. **Commit** the sync: `sync: update <domain> spec(s)`

#### Sync Algorithm Notes

- The sync is **idempotent** — running it twice produces the same result
- ADDED requirements that already exist are treated as MODIFIED
- REMOVED requirements that are already gone are no-ops
- The delta represents *intent*, not a wholesale replacement — use judgment to merge changes sensibly
- For multi-domain deltas, iterate over each domain section and update the corresponding `docs/specs/<domain>.md`

### Step 5: Cleanup Worktree

**For Options 1, 2, 4:**

Check if in worktree:
```bash
git worktree list | grep $(git branch --show-current)
```

If yes:
```bash
git worktree remove <worktree-path>
```

**For Option 3:** Keep worktree.

## Quick Reference

| Option | Merge | Push | Keep Worktree | Sync Specs | Cleanup Branch |
|--------|-------|------|---------------|------------|----------------|
| 1. Merge locally | ✓ | - | - | ✓ | ✓ |
| 2. Create PR | - | ✓ | ✓ | ✓ | - |
| 3. Keep as-is | - | - | ✓ | ✓ | - |
| 4. Discard | - | - | - | ✗ | ✓ (force) |

## Common Mistakes

**Skipping test verification**
- **Problem:** Merge broken code, create failing PR
- **Fix:** Always verify tests before offering options

**Open-ended questions**
- **Problem:** "What should I do next?" → ambiguous
- **Fix:** Present exactly 4 structured options

**Automatic worktree cleanup**
- **Problem:** Remove worktree when might need it (Option 2, 3)
- **Fix:** Only cleanup for Options 1 and 4

**No confirmation for discard**
- **Problem:** Accidentally delete work
- **Fix:** Require typed "discard" confirmation

**Syncing living specs for discarded work**
- **Problem:** Living spec describes behavior that doesn't exist (branch was discarded)
- **Fix:** Only sync for Options 1, 2, 3. Never sync for Option 4.

**Syncing before user confirmation**
- **Problem:** Sync changes that the user doesn't want
- **Fix:** Always show sync summary and get confirmation before committing

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
- Sync living specs for discarded work (Option 4)
- Commit sync changes without showing the summary first

**Always:**
- Verify tests before offering options
- Present exactly 4 options
- Get typed confirmation for Option 4
- Clean up worktree for Options 1 & 4 only
- Sync living specs for Options 1, 2, 3 (before merge/PR/keep)
- Show sync summary and get user confirmation before committing

## Integration

**Called by:**
- **subagent-driven-development** (Step 7) - After all tasks complete
- **executing-plans** (Step 5) - After all batches complete

**Pairs with:**
- **using-git-worktrees** - Cleans up worktree created by that skill
