---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from the current workspace or before executing implementation plans
---

# Using Git Worktrees

Git worktrees create isolated workspaces sharing the same repository, allowing work on multiple branches simultaneously without switching.

**Rule:** worktrees live at `<project_root>/.worktrees/<branch-name>`. No other location. All workflow artifacts (spec, plan, code) are committed to this branch — never to the default branch.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Safety Verification

Verify `.worktrees` is ignored before creating any worktree:

```bash
git check-ignore -q .worktrees
```

If NOT ignored:

1. Add `.worktrees/` to `.gitignore`
2. Commit the change
3. Proceed with worktree creation

## Creation Steps

### 1. Create the Worktree

```bash
mkdir -p .worktrees
git worktree add .worktrees/$BRANCH_NAME -b "$BRANCH_NAME"
cd ".worktrees/$BRANCH_NAME"
```

### 2. Run Project Setup

Auto-detect and run the appropriate setup:

```bash
if [ -f package.json ]; then npm install; fi
if [ -f Cargo.toml ]; then cargo build; fi
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then poetry install; fi
if [ -f go.mod ]; then go mod download; fi
```

### 3. Verify a Clean Baseline

Run the project's test suite (`npm test` / `cargo test` / `pytest` / `go test ./...`).

- **Tests fail:** report the failures; ask whether to proceed or investigate
- **Tests pass:** report ready

### 4. Report Location

```
Worktree ready at <full-path>/.worktrees/<branch-name>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Red Flags

**Never:**
- Create a worktree without verifying `.worktrees/` is ignored
- Skip the baseline test verification
- Proceed with failing tests without asking
- Place worktrees anywhere other than `<project_root>/.worktrees/`
- Create a second worktree when the workflow already created one — verify with `git worktree list`

**Always:**
- Verify the directory is ignored before creating a worktree
- Auto-detect and run project setup
- Verify a clean test baseline before starting work

## Integration

**Called by:**
- **brainstorming** — after design approval, before writing any artifact; all artifacts and code are committed to this branch
- **executing-plans** / **subagent-driven-development** — verify execution happens inside the existing worktree; do not create a second one

**Pairs with:**
- **finishing-a-development-branch** — removes the worktree after a local merge
