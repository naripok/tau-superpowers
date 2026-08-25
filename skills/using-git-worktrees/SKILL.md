---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from the current workspace or before executing implementation plans
---

# Using Git Worktrees

Git worktrees create isolated workspaces that share the same repository. You can work on multiple branches at the same time without switching between them.

**Rule:** worktrees live at `<project_root>/.worktrees/<branch-name>`. No other location. Commit all workflow artifacts (spec, plan, code) to this branch. Never commit them to the default branch.

**Announce at start:** "Using `using-git-worktrees` to set up an isolated workspace."

## Safety Verification

Before you create any worktree, check that git ignores `.worktrees`:

```bash
git check-ignore -q .worktrees
```

If git does not ignore `.worktrees`:

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

### 3. Check a Clean Baseline

Run the test suite of the project (`npm test` / `cargo test` / `pytest` / `go test ./...`).

- **Tests fail:** report the failures. Ask whether to proceed or investigate.
- **Tests pass:** report ready.

### 4. Report Location

```
Worktree ready at <full-path>/.worktrees/<branch-name>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Red Flags

**Never:**
- Create a worktree before you check that git ignores `.worktrees/`
- Skip the baseline test check
- Proceed with failing tests before you ask
- Place worktrees anywhere other than `<project_root>/.worktrees/`
- If a worktree already exists, create a second one. Check first with `git worktree list`.

**Always:**
- Before you create a worktree, check that git ignores the directory
- Auto-detect and run project setup
- Before you start work, check for a clean test baseline

## Integration

**Called by:**
- **brainstorming**: after design approval, before writing any artifact. Commit all artifacts and code to this branch.
- **executing-plans** / **subagent-driven-development**: check that execution happens inside the existing worktree. Do not create a second one.

**Pairs with:**
- **finishing-a-development-branch**: removes the worktree after a local merge.
