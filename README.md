# Tau Superpowers

Tau Superpowers is a collection of Agent Skills for spec-driven development, TDD, debugging, planning, and review, plus a Python Tau extension that registers an isolated-subagent `task` tool.

The project combines ideas and material from [obra/superpowers](https://github.com/obra/superpowers) and [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec), adapted for [Tau](https://github.com/earendil-works/tau).

## What You Get

- 14 Tau-discoverable Agent Skills covering the full design-to-delivery workflow.
- A `task` tool for single, parallel, and chained Tau subprocesses.
- Bundled `general-purpose` and tool-enforced `read-only` child profiles.
- User and project agent definitions with deterministic precedence and explicit project-agent approval.
- Summary-sized parent context with complete child messages retained in structured result details.

## Requirements

- Tau 0.3.9 or newer, installed and configured with a provider and model.
- Git and Bash for the symlink installer.
- Python 3.14 is supplied by current Tau installations; the extension executes inside Tau and has no separate runtime installation step.

## Install for Your User

Clone the repository, inspect the extension code, and run the installer:

```bash
git clone <repository-url> tau-superpowers
cd tau-superpowers
./install.sh
```

The installer creates individual links without replacing unrelated resources:

```text
~/.tau/skills/<skill-name>                     -> <checkout>/skills/<skill-name>
~/.tau/extensions/superpowers-subagent         -> <checkout>/extensions/superpowers-subagent
```

It preflights every destination and stops without creating links if a path already exists and points elsewhere. Keep the checkout in place because the installation refers to it. After pulling updates, restart Tau; run `./install.sh` again if a release adds a skill. `/reload` is enough to refresh changed skills in an active TUI session.

Start Tau normally and explicitly invoke the bootstrap skill if desired:

```text
/skill:using-superpowers
```

Tau discovers the installed user extension by default, so the `task` tool is available without an `-e` option.

## Use Directly from a Checkout

The checkout has a relative `.agents/skills -> ../skills` link, so Tau can discover the canonical skill tree as protected project input after project approval. Executable extension code is deliberately **not** linked under project `.tau/extensions`.

From the repository root, explicitly load the extension for development:

```bash
tau --approve -e extensions/superpowers-subagent
```

`--approve` is a run-only project-input decision. The explicit `-e` path loads Python code independently of project-extension discovery, so inspect it first. Cloning this repository alone never exposes executable code through project `.tau/extensions`.

If you intentionally create your own project extension link, Tau requires both project trust and `--project-extensions`. A user-installed link under `~/.tau/extensions`, as created by `install.sh`, is user code and is discovered by default.

## Included Skills

| Skill | Purpose |
| --- | --- |
| `brainstorming` | Explore requirements and produce an approved proposal and behavioral feature spec |
| `dispatching-parallel-agents` | Coordinate independent work concurrently |
| `executing-plans` | Execute a written implementation plan with checkpoints |
| `finishing-a-development-branch` | Verify, integrate, and sync living specs |
| `receiving-code-review` | Evaluate review feedback with technical verification |
| `requesting-code-review` | Request focused review before completion |
| `subagent-driven-development` | Execute plan tasks with fresh implementer and reviewer contexts |
| `systematic-debugging` | Diagnose root causes before changing code |
| `test-driven-development` | Apply red-green-refactor discipline |
| `using-git-worktrees` | Isolate feature work in Git worktrees |
| `using-superpowers` | Discover and apply the workflow skills |
| `verification-before-completion` | Require fresh evidence before completion claims |
| `writing-plans` | Derive delta specs and bite-sized implementation plans |
| `writing-skills` | Author and test Tau Agent Skills |

Tau initially loads only skill names, descriptions, and paths. It reads the full `SKILL.md` when a skill matches the task. Use `/skill:<name>` to invoke one explicitly.

## The `task` Extension

The extension launches child `tau --mode json` processes with isolated conversation context. Every delegated task must therefore include all requirements, file paths, relevant command output, and expected response format.

Call `task` with exactly one mode. The snippets below are tool argument objects.

### Single

```json
{
  "agent": "general-purpose",
  "task": "Implement the cache behavior described below, run the named tests, and report changed files.\n\n[COMPLETE REQUIREMENTS]",
  "cwd": "/path/to/worktree"
}
```

### Parallel

Parallel mode accepts at most eight tasks, runs at most four concurrently, and returns results in input order:

```json
{
  "description": "Investigate independent failures",
  "tasks": [
    {
      "agent": "general-purpose",
      "task": "Investigate the authentication failures. Do not modify the batch module."
    },
    {
      "agent": "general-purpose",
      "task": "Investigate the batch failures. Do not modify the authentication module."
    }
  ]
}
```

### Chain

Chain mode is sequential. Every `{previous}` occurrence receives the preceding child's complete final assistant text:

```json
{
  "chain": [
    {
      "agent": "general-purpose",
      "task": "Investigate the supplied failure and return structured findings."
    },
    {
      "agent": "general-purpose",
      "task": "Create an implementation plan from these findings:\n\n{previous}"
    }
  ]
}
```

A chain stops for child process/protocol failure, timeout, or cancellation. Semantic `BLOCKED` or `NEEDS_CONTEXT` status alone does not stop a cleanly exited chain step; use separate calls for conditional review/fix loops.

### Common Options

| Field | Meaning |
| --- | --- |
| `description` | Short orchestration label |
| `agentScope` | `user` (default), `project`, or `both` |
| `confirmProjectAgents` | Require project-agent confirmation (default `true`); `false` is explicit per-call approval |
| `provider` | Independent opaque Tau provider override |
| `model` | Independent opaque Tau model override |
| `timeoutSeconds` | Per-child timeout, greater than 0 and at most 3600; default 3600 |

In single mode, `cwd` is top-level. Parallel and chain items each carry their own optional `cwd`.

The complete argument, status, progress, and schema-v1 result contract is in [the Tau `task` tool reference](skills/using-superpowers/references/tau-tools.md).

## Agents and Tool Profiles

Bundled agent definitions live in `extensions/superpowers-subagent/agents/`. Add custom Markdown definitions at:

1. `~/.tau/agents/*.md` for user agents;
2. the nearest ancestor `.tau/agents/*.md` for project agents.

Definitions use YAML frontmatter and a Markdown instruction body:

```markdown
---
name: focused-reviewer
description: Reviews named files against supplied requirements.
profile: read-only
provider: openai-codex
model: gpt-5.3-codex
---

Review only the named files and return findings by severity.
```

`name` and `description` are required. `profile` is `general-purpose` (default) or `read-only`; `provider` and `model` are optional independent strings.

`agentScope: "user"` includes bundled and user agents. `"project"` includes bundled and project agents. `"both"` includes all layers. Precedence is bundled, then user, then nearest project.

When a selected definition resolves to project-controlled Markdown, the extension asks in the TUI by default and fails closed in headless mode. After inspecting it, `"confirmProjectAgents": false` explicitly approves that definition for one call. Tau's project trust decision does not approve these extension-managed agent prompts.

The `read-only` profile loads a temporary public Tau hook that blocks every Tau tool except `read`. It cannot run commands, search unknown paths, or produce its own `git diff`; provide those inputs in the delegated prompt. This is a tool-layer policy, **not** an OS, filesystem, network, credential, model, provider, or prompt-injection sandbox.

## Provider and Model Selection

Normally omit `provider` and `model`. Child processes then use Tau's configured defaults or optional values from the selected agent definition. Configure durable Tau defaults with `/login` and `/model`.

Per-call overrides are separate and map directly to Tau's separate CLI settings:

```json
{
  "agent": "general-purpose",
  "task": "Complete the delegated task.",
  "provider": "openai-codex",
  "model": "gpt-5.3-codex"
}
```

A call value overrides only the corresponding agent value. The extension never splits combined strings or infers a provider from a slash in a model identifier. An unpersisted model selected only in the parent process is not guaranteed to carry into children.

## Isolation and Security Boundaries

Children run with discovered extensions and protected project resources disabled, a recursion guard, and no Tau auto-approval. User-global skills cannot currently be disabled independently; children are instructed not to invoke them, but that prompt is behavioral guidance rather than enforcement.

Installing or explicitly loading this extension executes Python with the same account privileges as Tau. Tau project trust controls project-input loading; it is not a process, filesystem, shell, network, credential, provider, or model sandbox. Use OS-level isolation and restricted credentials/network when those boundaries matter.

## Living-Spec Workflow

A living spec at `docs/specs/<domain>.md` describes current behavior. Feature work follows this artifact chain:

```text
living spec
  -> proposal + behavioral feature spec
  -> delta spec + implementation plan
  -> TDD implementation + spec/code review
  -> verified integration
  -> delta merged back into the living spec
```

The main flow is:

1. **Brainstorm:** read living specs, clarify requirements, compare approaches, and write an approved proposal and feature spec.
2. **Plan:** derive an ADDED/MODIFIED/REMOVED delta against current behavior and map every requirement to implementation and tests.
3. **Execute:** use a fresh implementer context per task, then spec-compliance and code-quality review loops.
4. **Finish:** run fresh verification, choose an integration outcome, and sync accepted deltas into living specs.

| Artifact | Role |
| --- | --- |
| `docs/specs/<domain>.md` | Canonical current behavior |
| `docs/design/YYYY-MM-DD-<topic>-proposal.md` | Intent, scope, and approach |
| `docs/design/YYYY-MM-DD-<topic>-spec.md` | Behavioral contract |
| `docs/design/YYYY-MM-DD-<topic>-delta.md` | Change against the living spec |
| `docs/plans/YYYY-MM-DD-<topic>.md` | TDD implementation steps |

## Repository Layout

```text
.agents/
  skills -> ../skills                  # relative project discovery link
skills/                                 # canonical Agent Skill sources
extensions/superpowers-subagent/
  extension.py                          # Tau loader entry point
  superpowers_subagent/                 # Python implementation
  agents/                               # bundled agent definitions
  tests/                                # unit and runtime integration tests
install.sh                              # safe per-resource user linker
```

No project `.tau/extensions` link is shipped.

## Verification and Development

Inspect project skill discovery and explicit extension loading without making a provider request:

```bash
tau --mode text --approve --no-extensions \
  -e extensions/superpowers-subagent /system
```

The printed system prompt should list the skills and `task`. For a user installation, run this from another directory:

```bash
tau --mode text --no-approve /system
```

It should still list the installed user skills and `task`. Tau must have a configured provider even though `/system` itself does not call the model.

Run the installer regression test:

```bash
tests/test-install.sh
```

Run extension checks with the site-packages directory belonging to the installed `tau` executable available to the development environment:

```bash
cd extensions/superpowers-subagent
TAU_PYTHON=$(sed -n '1s/^#!//p' "$(command -v tau)")
TAU_SITE_PACKAGES=$(
  "$TAU_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'
)
uv sync --all-groups --locked
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest
PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy
uv run ruff check .
uv run ruff format --check .
```

The integration suite loads the extension through Tau's real extension runtime while using deterministic child-process fixtures for dispatch behavior.
