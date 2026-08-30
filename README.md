# Tau Superpowers

Tau Superpowers is a collection of Agent Skills for spec-driven development, TDD, debugging, planning, and review, plus a Python Tau extension that registers an isolated-subagent `task` tool.

The project combines ideas and material from [obra/superpowers](https://github.com/obra/superpowers) and [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec), adapted for [Tau](https://github.com/earendil-works/tau).

## What You Get

- 15 Tau-discoverable Agent Skills covering the full design-to-delivery workflow.
- A `task` tool that dispatches one or more isolated Tau subprocesses.
- Bundled child agents: `general-purpose`, tool-enforced `read-only`, `implementation`, `code-review`, and `document-review` (`read` + read-only `bash`, strict `## Code Review`/`## Document Review` reports). Children inherit the parent session's active provider, model, and thinking effort by default, after call-level, config-file, and agent-definition values.
- User and project agent definitions with deterministic precedence and explicit project-agent approval.
- A per-subagent config file (`~/.tau/superpowers-subagent.toml` and `<project>/.tau/superpowers-subagent.toml`) that pins provider, model, and `reasoningEffort` globally or per agent; an example file ships as `superpowers-subagent.example.toml`.
- Per-child `reasoningEffort` at call or config-file level, applied as the child's Tau thinking level.
- Parent-model content is each child's complete final assistant message, with the complete wire messages retained in structured result details.

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
| `executing-plans` | Execute a written implementation plan inline with checkpoints |
| `finishing-a-development-branch` | Verify, sync living specs, and merge or open a PR |
| `receiving-code-review` | Review-finding adjudication: endorse and reject verdicts per finding and fix dispatches that carry only endorsed findings |
| `requesting-code-review` | Request focused review before completion |
| `subagent-driven-development` | Execute plan tasks with fresh implementer and reviewer contexts, one two-dimension review per task |
| `systematic-debugging` | Diagnose root causes before changing code |
| `test-driven-development` | Apply red-green-refactor discipline |
| `using-git-worktrees` | Isolate feature work in Git worktrees |
| `using-superpowers` | Discover and apply the workflow skills |
| `verification-before-completion` | Require fresh evidence before completion claims |
| `writing-developer-facing-text` | Write developer-facing text with ASD-STE100 Simplified Technical English rules |
| `writing-plans` | Turn a feature spec into contract-based implementation plans |
| `writing-skills` | Author and test Tau Agent Skills |

Tau initially loads only skill names, descriptions, and paths. It reads the full `SKILL.md` when a skill matches the task. Use `/skill:<name>` to invoke one explicitly.

## The `task` Extension

The extension launches child `tau --mode json` processes with isolated conversation context. Every delegated task must therefore include all requirements, file paths, relevant command output, and expected response format.

Dispatch a subagent only for substantive multi-step work that benefits from an isolated context window, or for long-running work that must not block the parent session. Simple reads, searches, commands, and small edits are the parent's own tool calls, and a subagent replaces the parent's tool calls for its task — never duplicate that work.

Every call takes a `tasks` array. The snippets below are tool argument objects.

### Task list

`tasks` is required: an array of 1–8 items, each `{agent, task, cwd?}`. One item runs a single child; two or more run in parallel (at most four active) and results keep input order. Conditional sequences — implement → review → fix if needed → re-review, or any loop where a later step depends on an earlier result — require separate calls so the controller can inspect each result.

```json
{
  "tasks": [
    {
      "agent": "general-purpose",
      "task": "Implement the cache behavior described below, run the named tests, and report changed files.\n\n[COMPLETE REQUIREMENTS]",
      "cwd": "/path/to/worktree"
    }
  ]
}
```

Two or more items dispatch in parallel — independent work only:

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

### Common Options

| Field | Meaning |
| --- | --- |
| `description` | Short orchestration label |
| `agentScope` | `user` (default), `project`, or `both` |
| `confirmProjectAgents` | Require project-agent confirmation (default `true`); `false` is explicit per-call approval |
| `provider` | Optional literal provider override. Omit it to inherit configuration; otherwise pass an exact configured provider name from `tau providers`. |
| `model` | Optional literal model override. Omit it to inherit configuration; otherwise pass an exact supported model ID. |
| `reasoningEffort` | Optional literal reasoningEffort override. Omit it to inherit configuration; otherwise pass exactly `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`. It overrides the config file and agent definition; otherwise the level falls back to the config file, then the agent definition, then the parent session's thinking level. |
| `timeoutSeconds` | Per-child timeout, greater than 0 and at most 3600; default 3600 |

`cwd` is per item, resolved relative to the parent session's working directory.

### Live TUI visibility

While children run, the tool row refreshes after every child message so you can watch the work happen: status icons (`✓` DONE, `⚠` DONE_WITH_CONCERNS, `✗` BLOCKED, `?` NEEDS_CONTEXT, `…` in flight), each child's streamed tool calls (`→ $ command`, `read path:lines`, `write path (N lines)`, `edit path`) and assistant text, plus usage counters (`turns`, `↑`/`↓` tokens, cache reads/writes, cost, context, model). Collapsed rows show compact per-child previews with accurate live counts (`2/4 succeeded · 1 running · 1 pending`); press `Ctrl+O` to expand the full per-child work stream, delegated task, status hints, and aggregate usage.

Parent-model content is each child's complete final assistant message — one child produces the bare message (or a concise failure), several produce a `<succeeded>/<total> succeeded` header plus one `[<agent>] (completed|failed)` section per child; the complete wire messages stay in `details.results`.

The complete argument, status, progress, and schema-v2 result contract is in [the Tau `task` tool reference](skills/using-superpowers/references/tau-tools.md).

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

`name` and `description` are required. `profile` is `general-purpose` (default), `read-only`, or `review`; `provider`, `model`, and `reasoningEffort` are optional independent strings.

`agentScope: "user"` includes bundled and user agents. `"project"` includes bundled and project agents. `"both"` includes all layers. Precedence is bundled, then user, then nearest project.

When a selected definition resolves to project-controlled Markdown, the extension asks in the TUI by default and fails closed in headless mode. After inspecting it, `"confirmProjectAgents": false` explicitly approves that definition for one call. Tau's project trust decision does not approve these extension-managed agent prompts.

The `read-only` profile loads a temporary public Tau hook that blocks every Tau tool except `read`. It cannot run commands, search unknown paths, or produce its own `git diff`; provide those inputs in the delegated prompt. The `review` profile (used by `code-review` and `document-review`) permits `read` plus `bash` for read-only operations — git read commands, grep/rg/find searches — and instructs the child to never change the state of the repository or environment. The hook cannot parse bash command semantics, so read-only bash usage is instruction-governed. Both profiles are tool-layer policies, **not** an OS, filesystem, network, credential, model, provider, or prompt-injection sandbox.

## Provider, Model, and Thinking Effort Selection

Normally omit `provider`, `model`, and `reasoningEffort`. Omission inherits configuration: subagents use the parent session's active provider, model, and thinking effort unless a config file or agent definition pins one. Each field is an optional literal override. When you provide one, use the exact configured provider name from `tau providers`, exact model ID supported by the selected provider, or one of the exact reasoning levels below. Do not use `default`, `inherit`, or `auto`; these placeholders do not select defaults and the task call rejects them. Run `tau providers` to discover configured providers and their exact supported model IDs. Configure durable Tau defaults with `/login` and `/model`.

Per-field resolution, highest first:

1. `task` call `provider` / `model` / `reasoningEffort`;
2. the subagent config file `[agents.<name>]` section;
3. the selected agent definition's frontmatter;
4. the subagent config file `[defaults]` section;
5. the parent session's active provider, model, and thinking level.

The subagent config file is a TOML file named `superpowers-subagent.toml` in either `~/.tau/` or the nearest ancestor `<project>/.tau/`, the same directories Tau reads its other durable configs from. A project file shadows the user file per key. An example file ships at `extensions/superpowers-subagent/superpowers-subagent.example.toml`:

```toml
[defaults]
# provider = "openai"
# model = "gpt-5.6-sol"
# reasoningEffort = "medium"   # off | minimal | low | medium | high | xhigh

[agents.code-review]
# provider = "openrouter"
# model = "z-ai/glm-5.3"
# reasoningEffort = "medium"
```

Per-call overrides are separate and map directly to Tau's separate CLI settings:

```json
{
  "tasks": [
    {
      "agent": "general-purpose",
      "task": "Complete the delegated task."
    }
  ],
  "provider": "openai-codex",
  "model": "gpt-5.3-codex"
}
```

A call value overrides only the corresponding lower layer. The extension never splits combined strings or infers a provider from a slash in a model identifier. An unpersisted model or thinking level selected only in the parent process is carried into children as the parent-session fallback for values pinned nowhere else.

## Isolation and Security Boundaries

Children run with discovered extensions and protected project resources disabled, a recursion guard, and no Tau auto-approval. User-global skills cannot currently be disabled independently; children are instructed not to invoke them, but that prompt is behavioral guidance rather than enforcement.

Installing or explicitly loading this extension executes Python with the same account privileges as Tau. Tau project trust controls project-input loading; it is not a process, filesystem, shell, network, credential, provider, or model sandbox. Use OS-level isolation and restricted credentials/network when those boundaries matter.

## Living-Spec Workflow

A living spec at `docs/specs/<domain>.md` describes current behavior. Feature work follows this artifact chain:

```text
living spec
  -> proposal + behavioral feature spec (the delta against the living spec)
  -> contract-based implementation plan
  -> TDD implementation + combined spec/quality review
  -> verified integration
  -> feature spec merged back into the living spec
```

The main flow is:

1. **Brainstorm:** read living specs, clarify requirements, compare approaches, and write an approved proposal and feature spec. All artifacts and code live on a branch or worktree, never on the default branch.
2. **Plan:** map every feature-spec requirement to tasks defining architecture, interface signatures, expected behavior, and the tests to prove it — the exact implementation is the implementer's decision.
3. **Execute:** use a fresh implementer context per task, then a single review pass per task covering spec compliance and code quality, plus a final whole-change review.
4. **Finish:** run fresh verification, sync the accepted feature-spec changes into living specs, and merge the branch or open a PR.

| Artifact | Role |
| --- | --- |
| `docs/specs/<domain>.md` | Canonical current behavior |
| `docs/design/YYYY-MM-DD-<topic>-proposal.md` | Intent, scope, and approach |
| `docs/design/YYYY-MM-DD-<topic>-spec.md` | Behavioral contract and delta against the living spec |
| `docs/plans/YYYY-MM-DD-<topic>.md` | Interface and behavior contracts, tests to prove |

## Repository Layout

```text
.agents/
  skills -> ../skills                  # relative project discovery link
skills/                                 # canonical Agent Skill sources
extensions/superpowers-subagent/
  extension.py                          # Tau loader entry point
  superpowers-subagent.example.toml      # example config template
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
