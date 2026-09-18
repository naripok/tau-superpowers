# Proposal: OpenCode-aligned task interface

Selected workflow depth: High-risk.

Terms used throughout: a teach-back is a rejection or repair tool result whose content names the valid values and the exact next step. Fail closed means the tool rejects the call and starts no child.

## Intent

Models arrive at the `task` tool with training data from four harnesses. Claude Code, ZCode, Codex, and OpenCode all dispatch one agent per call with a flat argument object. OpenCode even names the tool `task`, like ours. Tau is the only harness with a `tasks` array. The recorded session data shows the result: the most common invalid first call is a flat object, and the first dispatch fails on the majority of sessions.

This change makes the flat form canonical. The array form stays for parallel dispatch. Field names unify to the OpenCode vocabulary, and the tool adopts the OpenCode behaviors the operator selected: roster and guidance prose in the tool description, a task envelope around each child result, and a configurable dispatch depth.

## Baseline Evidence

Selected baseline branch: living-spec domain. The living spec is `docs/specs/subagent-dispatch.md`.

Current behavior (baseline, before this change):

- One tool named `task`. Every call takes `tasks`: 1 to 8 items, each `{agent, task, cwd?}`. Two or more items run in parallel, at most 4 active, results in input order (`docs/specs/subagent-dispatch.md`, "Requirement: task interface and validation"). This proposal keeps the array semantics, and changes the item field names and the agent default; see Required Outcome 2 and Required Outcome 3.
- Top-level `agent`, `task`, `cwd`, and `chain` are rejected as unknown fields. This proposal changes this rule for `agent`, `task`, and `cwd`; see Required Outcome 1 and Required Outcome 4. `chain` stays rejected.
- Placeholder overrides (`default`, `inherit`, `auto`) for `provider`, `model`, and `reasoningEffort` are treated as omitted with a repair note. Kept.
- Literal provider and model overrides fail fast against the scoped catalog. Kept.
- The tool schema embeds the agent roster in the `agent` parameter description. Kept, and extended per Required Outcome 6.
- Result content: one child returns the bare final message; several children return a counts line plus one section per child. This proposal changes the content shape with the task envelope; see Required Outcome 7. Structured `details` stays schemaVersion 2. Kept.
- Children never register the `task` tool: the runner sets `TAU_SUPERPOWERS_SUBAGENT=1` and `setup()` exits early. This proposal changes this behavior; see Required Outcome 8.

Consumers of the call contract: 14 files under the counting basis (a file embeds the call JSON or names the `agent` or `task` field of the call contract): `README.md`, the living spec, `skills/using-superpowers/references/tau-tools.md`, and 11 skill files. The Impact section lists these 11 files plus `subagent-driven-development/SKILL.md`, which instructs agent selection in prose. The change updates all 15. Tests: 267 pass at `b833ebd`.

Evidence for the change:

- Operator-attested input (not re-derivable from the repository): session recordings on this machine show 284 recorded `task` calls, of which 43 used a flat `{agent, task}` object, 1 placed `timeoutSeconds` inside an item, and the first dispatch failed on the majority of observed sessions. The recordings are sandbox session logs and carry no stable path; treat the counts as operator-attested motivation, not as repository evidence.
- Inspectable upstream sources for the external interfaces: OpenCode `task` tool (`anomalyco/opencode`, branch `dev`, `packages/opencode/src/tool/task.ts`, `tool/task.txt`, `tool/registry.ts`); Claude Code `Agent` tool (`@anthropic-ai/claude-code` 2.1.276, `sdk-tools.d.ts`); ZCode `Agent` tool (`zcode-app-cli` 3.12.3-26, extracted runtime `vendor/zcode.cjs`); Codex `spawn_agent` (`openai/codex`, branch `main`, `codex-rs/core/src/tools/handlers/multi_agents_spec.rs`). All four dispatch one agent per call with a flat argument object. OpenCode names the tool `task`.
- Repository evidence: the extension validator rejects every flat shape tested (`dispatch.py`, `validate_arguments`); the child argv passes `--no-extensions` and loads only generated policy extensions (`utils.py`, `build_tau_argv`); the legacy guard env var is `TAU_SUPERPOWERS_SUBAGENT` (`runner.py`).

Material discrepancy: no source conflict. The current spec and code agree. The recorded flat-form calls came from model priors, not from a hidden supported form.

## Required Outcomes

1. A controller can dispatch one child with a flat call: `{"prompt": "...", "subagent_type": "..."}`. `description` and `cwd` stay optional.
2. An omitted `subagent_type` selects `general-purpose`, in the flat form and in array items.
3. The `tasks` array keeps its current parallel semantics. Array items use `subagent_type` and `prompt`.
4. The deprecated names `agent` and `task` become accepted at the top level and stay accepted inside items. Each tolerated use produces a repair note that names the canonical field. Different fields use either spelling independently: a call that uses a deprecated spelling for one field and the canonical spelling for a different field is valid and produces one repair note per deprecated spelling. Both spellings of one field fail closed per Required Outcome 5.
5. A call that carries both spellings of one field fails closed with a teach-back that names the canonical fields.
6. The tool description carries the agent roster with tool-policy annotations, the default selection rule, a when-not-to-use section, and usage notes. The `subagent_type` parameter description keeps the roster.
7. Model-facing result content wraps each child in a task envelope. The envelope id is the child agent name and its zero-based input index joined by a hyphen, in the form `code-review-0`. A child that succeeded carries state `completed`; a child that failed, was cancelled, or timed out carries state `error`. A completed envelope wraps the child final message in a `task_result` tag; an empty final message wraps the placeholder `(no output)`. An error envelope wraps the child final message when one exists, or the child error text otherwise, in a `task_error` tag. One child in the call produces one envelope. Two or more children produce the counts line from the current content, then one envelope per child in input order; the per-child `[agent] (completed|failed)` section headers are replaced by the envelope markers. Repair notes keep their current position as `Note:` lines before the content. Structured `details` stays schemaVersion 2.
8. The extension loads in every child, and the `task` tool registers in every child. The child tool profiles stay unchanged: a child with the `read-only` or `review` profile cannot call `task` at any depth, because the profile hook blocks the call. Depth-gated nesting is reachable only from children with the `general-purpose` profile. Dispatch depth comes from `[defaults] depth` in the subagent config file. The value must be an integer from 1 to 4; any other value, including a value above 4, produces a config diagnostic and the default of 1 applies. `depth` is not a valid key in an `[agents.<name>]` section; it triggers the existing unknown-key diagnostic. The budget rule: the effective budget is the minimum of the configured depth and the depth environment variable. An unset variable means top level and holds the full configured budget. A set integer value above the configured depth produces a `[superpowers-subagent]` diagnostic on the standard error of the process that read the variable, and the configured depth applies. A set non-integer or negative value produces the same diagnostic and an exhausted budget. The diagnostic is retained in that child's `details.results[].stderr`. A set value of 0 holds an exhausted budget. Every dispatch from a level with remaining budget B writes B minus 1 into the child environment. A dispatch in a level with remaining budget 0 fails at execute time with a teach-back that names the `depth` key.
9. The top-level `cwd` field is valid only in the flat form, where it applies to the single child. A call that carries both `cwd` and `tasks` fails with a teach-back that names per-item `cwd`. A call that carries `tasks` together with any flat-form field (`prompt`, `task`, `subagent_type`, `agent`) fails closed with a teach-back that names the two forms. A call that carries neither `tasks` nor `prompt` (or its alias `task`) fails with a teach-back that names both forms. The top-level `chain` field stays rejected as an unknown field.
10. A call in a child that selects a project agent always fails closed. The approval flow that sets `confirmProjectAgents: false` runs at the top level only. The child receives a teach-back that names the approval boundary and directs the child to report `NEEDS_CONTEXT` to its controller. The child marker is a set depth environment variable, so a top-level session started with the variable set is treated as a child and loses the approval escape; that edge fails closed.

## Acceptance Examples

1. A call `{"description": "Review auth", "prompt": "Review the auth module", "subagent_type": "code-review"}` dispatches one `code-review` child. On success the content is one `<task id="code-review-0" state="completed"><task_result>...final message...</task_result></task>` envelope. On failure without a final message the inner tag is `task_error` and its body is the child error text. `details.results` holds one entry.
2. A call `{"prompt": "Find caching options"}` with no `subagent_type` dispatches one `general-purpose` child. A whitespace-only `subagent_type` behaves as omitted, with a repair note that names the canonical field. The rule holds in the flat form and in array items.
3. A call `{"tasks": [{"agent": "general-purpose", "task": "Fix tests"}]}` dispatches one child and produces two repair notes: one that names `subagent_type` and one that names `prompt`.
4. A call `{"prompt": "A", "task": "B"}` fails. The teach-back names the conflict and the canonical field `prompt`.
5. The tool description contains the roster lines in the form `- general-purpose: <description> (Tools: <policy>)`, the sentence about the `general-purpose` default, and a when-not-to-use section.
6. With `[defaults] depth = 2`, a child can dispatch one grandchild: the top level holds budget 2 and writes 1 into the child, the child holds budget 1 and writes 0 into the grandchild, and a dispatch at the grandchild fails at execute time with a message that names the `depth` key.
7. A call `{"tasks": [{"subagent_type": "read-only", "prompt": "A"}, {"subagent_type": "general-purpose", "prompt": "B"}]}` dispatches two children in parallel. The content starts with the counts line and holds two `<task>` envelopes in input order.
8. A call `{"tasks": [{"prompt": "A"}], "prompt": "B"}` fails closed. The teach-back names the two forms and states that one call uses one form.
9. A `read-only` or `document-review` child never completes a `task` call at any depth: the profile hook blocks the call, and the child reports the block in its result.
10. A child session holds a set depth environment variable and dispatches a `subagent_type` value that resolves to a project agent definition, passing `confirmProjectAgents: false`. The call fails closed with a teach-back that names the approval boundary and directs the child to report `NEEDS_CONTEXT` to its controller.

## Scope

**In scope:**

- Flat call form, normalization, defaults, deprecated aliases, conflict detection, repair notes, and teach-back updates in the extension.
- Field renames in array items, with the deprecated aliases accepted.
- Tool description and prompt-guideline restructure; roster with tool-policy annotations.
- Task envelope for model-facing result content, for one child and for several.
- Config `depth` with env plumbing for child depth budgets.
- Updates to the README, the `tau-tools.md` reference, the skill dispatch templates, and the reviewer prompts that embed call examples.
- Unit and extension test updates for every behavior above.

**Out of scope:**

- `task_id` session resume and `background` async dispatch. Each needs its own proposal.
- Per-child tool selection, and the OpenCode built-in agent names (`build`, `plan`, `general`, `explore`).
- Changes to bundled agent names, profiles, discovery, or the project-agent approval flow.
- Changes to the details schema, the usage tracking, the sidebar, or the catalog fail-fast.
- Living-spec synchronization. It happens in the finishing stage per the workflow.

## Constraints

- The tool name stays `task`.
- The bundled agents stay `general-purpose`, `read-only`, `implementation`, `code-review`, and `document-review`.
- Per-call overrides stay: `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`, top level only.
- Child result statuses (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) stay inside the child final messages.
- All developer-facing text follows the writing-unambiguous-text skill.

## Approach

One rule unifies the surface: the flat form is sugar for a one-item array. Validation normalizes `{"prompt", "subagent_type", "cwd"}` to `{"tasks": [{"subagent_type", "prompt", "cwd"}]}` and one code path dispatches both forms.

Field names unify on the OpenCode vocabulary: `subagent_type` and `prompt` in both forms. The old names `agent` and `task` become deprecated aliases, tolerated with repair notes. This keeps sessions with older installed skills working and rescues the recorded flat-form priors. A call with both spellings fails closed, because the intent is ambiguous.

The description restructure copies the OpenCode layout that models know: one-liner, roster with tool-policy annotations, default rule, when-not-to-use, usage notes. Our threshold language and prohibitions stay.

The envelope is a content-only change. `details` consumers (usage tracker, sidebar, renderers) read the structured fields, not the content text.

Depth replaces the recursion guard with one mechanism. Today the runner sets `TAU_SUPERPOWERS_SUBAGENT=1` and children never load the extension, because the child argv passes `--no-extensions` and `-e` only for generated policy extensions. The change gives the runner one more `-e` argument: the extension root directory that holds the running extension, resolved from the extension module location. The budget rule: the effective budget is the minimum of the configured depth and the depth environment variable. Every level holds a remaining budget, the top level holds the configured `[defaults] depth`, and every dispatch from a level with budget B writes B minus 1 into the child environment variable `TAU_SUPERPOWERS_SUBAGENT_DEPTH`. `setup()` reads the variable. An unset variable means top level and holds the full configured budget. A set integer value above the configured depth produces a `[superpowers-subagent]` diagnostic on the standard error of the process that read the variable, and the configured depth applies. A set non-integer or negative value produces the same diagnostic and an exhausted budget. The diagnostic is retained in that child's `details.results[].stderr`. A set value of 0 means exhausted budget: the tool still registers, and every dispatch fails at execute time with a teach-back that names the `depth` key. A positive value at or below the configured depth holds that budget. The legacy binary variable `TAU_SUPERPOWERS_SUBAGENT` is retired; the setup check reads the depth variable only. A child therefore always shows the `task` tool. At the default depth of 1 the child tool rejects every dispatch with the depth teach-back. This costs the child context the tool schema tokens, and it buys a recoverable, self-explaining error in place of a bare unknown-tool error. In a child with the `read-only` or `review` profile, the profile hook blocks every `task` call regardless of depth, so the depth teach-back appears only in `general-purpose`-profile children; the default-depth sentence above applies to those children.

Alternatives considered:

- Full replacement of the array with OpenCode's single-child surface. Rejected: it breaks 15 consumer files, discards the single-call parallel dispatch, and reworks the sidebar and usage aggregation for no additional first-call success.
- Rename inside the array only. Rejected: it keeps the alien array as the only form, so every flat prior still fails.

## Impact

- Code: `extension.py` (schema, description, guidelines), `dispatch.py` (validation, normalization, repair notes, teach-back, result content), `config.py` (depth), `runner.py` (depth env), `rendering.py` (call label for the flat form; today the label derives from `tasks` and flat calls fall back to a generic label), `models.py` if the parsed request carries new fields, tests under `extensions/superpowers-subagent/tests/`.
- Docs: `README.md`, `docs/specs/subagent-dispatch.md` at finishing, `skills/using-superpowers/references/tau-tools.md`.
- Skills: every file that embeds the call shape or the item field names. Counting basis: files that embed the `tasks` array JSON or name the `agent` or `task` field of the call contract. These are `dispatching-parallel-agents/SKILL.md`, `subagent-driven-development/SKILL.md`, `subagent-driven-development/implementer-prompt.md`, `subagent-driven-development/implementation-reviewer-prompt.md`, `requesting-code-review/SKILL.md`, `requesting-code-review/code-reviewer.md`, `writing-skills/testing-skills-with-subagents.md`, `brainstorming/feature-spec-author-prompt.md`, `brainstorming/proposal-document-reviewer-prompt.md`, `brainstorming/spec-document-reviewer-prompt.md`, `writing-plans/plan-document-reviewer-prompt.md`, and `finishing-a-development-branch/living-spec-document-reviewer-prompt.md`.
- Install: the installer copies the extension and skills; a re-install syncs every consumer.
- Sessions: running sessions keep the old schema until restart. New sessions get the new surface.

## Risks

**Compatibility:** models trained on the current array keep working through the deprecated aliases; models trained on OpenCode get the canonical form. A model that mixes spellings gets a fail-closed teach-back. The residual risk is a model sending both spellings and giving up on one failure; the teach-back names the exact conflict. Nested dispatch interacts with project-agent approval: children run headless, and the existing fail-closed message lets a child self-approve repository-controlled prompts by setting `confirmProjectAgents: false` on a retry. Required Outcome 10 removes that path: the approval escape runs at the top level only, and a child that selects a project agent gets a teach-back that directs it to report `NEEDS_CONTEXT`. The project config file can enable deeper nesting without approval; the depth maximum of 4 bounds the nesting depth, while breadth stays bounded by the existing per-call limits.

**Migration:** one coordinated change updates the extension and every consumer file listed under Impact. The installer syncs them together. No operator action beyond re-install and session restart.

**Rollout:** the extension version stays 0.1.0 in `pyproject.toml`; the installer reports updated paths. Behavior changes are observable only after a session restart.

**Rollback:** a single revert of the change branch restores the prior surface. Both directions degrade safely: an old extension that reads a new config file reports the unknown `depth` key through the existing config diagnostic and continues with its default behavior. A new extension that reads an old config file applies the default depth of 1. No data migration exists.

**Observability:** repair notes appear in result content. Config diagnostics report unknown keys as today. Depth failures name the config key. The full test suite passes at the baseline commit `b833ebd` (267 tests per pytest). Tests cover every note and message text.

**Recovery:** none needed. The change holds no persistent state.

**Risk treatment:** the ambiguity rules fail closed: both spellings of one field, both forms in one call, and `cwd` with `tasks` all produce teach-backs. The envelope touches content only, so `details` consumers keep their contract. The effective budget is the minimum of the configured depth and the depth environment variable, so an unexpected or tampered env value never grants more nesting than the configuration allows.

## Assumptions

- The operator re-installs the extension and skills and restarts sessions to pick up the new surface.
- The TUI renderers and the sidebar read `details` fields and do not parse content text.
- OpenCode's `task_id` and `background` behaviors remain absent; no consumer expects them.

## Unresolved Decisions

None.
