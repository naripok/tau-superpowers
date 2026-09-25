# Agent-facing surface evaluation — task-tool-robustness

Recorded: 2026-09-25T01:38:52+00:00
Session command: `tau --mode json --no-approve --no-extensions -e extensions/superpowers-subagent "<case prompt>"`
Script exit: 0. Passed: every rejected call in the failed-resume cases records the fail-closed contract (no launched-child envelope, an empty `results` array, and the teach-back), and each failed-resume case records at least one rejected call, so the proof is not vacuous.

The sessions pass `--no-extensions` so the pinned `-e` path is the only loaded extension: explicit `-e` paths still load with the flag, while a same-name copy installed under `~/.tau/extensions` otherwise shadows it (Tau's loader dedupes by name and the user dir precedes `-e` extras). The evaluation therefore exercises the repository's implemented surface.

The evaluation runs four scripted controller sessions against the provider and model the harness configures at evaluation time. Results are reported separately from the unit-test outcome. The hard measures bind per rejected call: a follow-up call a model makes after a teach-back is a legitimate new dispatch, so the session-level child counts are recorded, not gated.

## Case 1 — fresh

Prompt: `Use the task tool to dispatch one general-purpose subagent. Ask it to report the working directory it runs in. Relay the report, then finish.`

Session: exit code 0, 19.0s

Provider/model: openrouter / z-ai/glm-5.3-flash

Emitted task-surface calls (1):

1. `task` arguments: `{"prompt": "Run `pwd` in your shell and report the absolute path of the working directory you run in. This is a research/reporting task \u2014 do not write any files. Verify the result by echoing the command's output verbatim in your reply.", "subagent_type": "general-purpose"}`
   own result: launched 1 child(ren) (task_id=2c6a44bf99374c29a713ca516b5ad9fc state=completed)

Fail-closed teach-backs: none observed

Launched children, session-level (recorded, not gated): 1
- call 1 (`task`): task_id=2c6a44bf99374c29a713ca516b5ad9fc state=completed

Tool name observed: `task`. Argument keys within the `task` surface: True.
Optional fields carried: 1 (`subagent_type`).

## Case 2 — resume

Prompt: `Use the task tool to dispatch one general-purpose subagent and ask it to compute one plus one. Then use the task_resume tool to continue that child session and ask it to multiply the result by three. Relay both results.`

Session: exit code 0, 28.5s

Provider/model: openrouter / z-ai/glm-5.3-flash

Emitted task-surface calls (2):

1. `task` arguments: `{"prompt": "Compute one plus one. Report only the numeric result.", "subagent_type": "general-purpose"}`
   own result: launched 1 child(ren) (task_id=75e6ee52dd0d411096d44bcbec084d4f state=completed)
2. `task_resume` arguments: `{"prompt": "Take the result you computed (one plus one) and multiply it by three. Report only the numeric result.", "task_id": "75e6ee52dd0d411096d44bcbec084d4f"}`
   own result: launched 1 child(ren) (task_id=75e6ee52dd0d411096d44bcbec084d4f state=completed)

Fail-closed teach-backs: none observed

Launched children, session-level (recorded, not gated): 2
- call 1 (`task`): task_id=75e6ee52dd0d411096d44bcbec084d4f state=completed
- call 2 (`task_resume`): task_id=75e6ee52dd0d411096d44bcbec084d4f state=completed

Fresh children: 1. Resumed children: 1.
Fresh envelope task_id: `75e6ee52dd0d411096d44bcbec084d4f`. task_resume received task_id: `75e6ee52dd0d411096d44bcbec084d4f`. Passthrough matches: True.
A failure to resume is a recorded observation, not a gate.

## Case 3 — unknown-resume

Prompt: `Use the task_resume tool with task_id set to the exact text nonexistent and the prompt 'Report status.' Wait for the result and relay it verbatim.`

Session: exit code 0, 8.8s

Provider/model: openrouter / z-ai/glm-5.3-flash

Emitted task-surface calls (1):

1. `task_resume` arguments: `{"prompt": "Report status.", "task_id": "nonexistent"}`
   own result: no launched-child envelope. Rejected: the result carries an empty `results` array (teach-back 1 below)

Fail-closed teach-backs (1):

```
Resume failed for task_id 'nonexistent': no child started.

Reason: the session-agent mapping has no entry for task_id 'nonexistent'

task_id 'nonexistent' is preserved and the session is unchanged. To start a fresh child instead, call task with the agent and prompt you want.

The resumed agent comes from the session-agent mapping at /home/tau/.tau/superpowers-subagent-sessions.json, which records each child session's agent name, so the call carries no agent name. Call fields: prompt (required), task_id (required), timeout_seconds (optional).
```

Launched children, session-level (recorded, not gated): 0

Rejected calls: 1. Per-rejected-call proof: every rejected call's own result carries an empty `results` array (the rejection marker), and the launched-child envelopes across those rejected results total 0 (the hard measure holds this at zero).
Teach-back preserves `nonexistent`: True. Directs the caller to `task`: True.
Follow-up observation: 0 follow-up call(s) after the rejected call (none). A follow-up dispatch is a legitimate new dispatch, recorded not gated.

## Case 4 — camelcase

Prompt: `Use the task tool to dispatch one general-purpose subagent. Pass timeoutSeconds with the value 120 as a call argument, exactly that spelling. Relay the result.`

Session: exit code 0, 27.4s

Provider/model: openrouter / z-ai/glm-5.3-flash

Emitted task-surface calls (2):

1. `task` arguments: `{"prompt": "This is a test dispatch. Do research only, no code changes. In the working directory /workspace, run `ls -la` and report a brief summary of what the directory contains. Then report the word \"DONE\" on the final line.", "subagent_type": "general-purpose", "timeoutSeconds": "120"}`
   own result: no launched-child envelope. Rejected: the result carries an empty `results` array (teach-back 1 below)
2. `task` arguments: `{"prompt": "This is a test dispatch. Do research only, no code changes. In the working directory /workspace, run `ls -la` and report a brief summary of what the directory contains. Then report the word \"DONE\" on the final line.", "subagent_type": "general-purpose", "timeout_seconds": 120}`
   own result: launched 1 child(ren) (task_id=750a8f8afeac499194835ffe8a849848 state=completed)

Fail-closed teach-backs (1):

```
Invalid parameters: unknown field(s): timeoutSeconds. The camelCase timeoutSeconds field is removed: pass timeout_seconds instead.

Available agents: - code-review: Adversarial read-only code reviewer. Use for code quality review, spec compliance review, and inspection of named files. (Tools: read, bash)
- document-review: Adversarial read-only document reviewer for the design workflow gates. Use for proposal review, feature-spec review, pl… (Tools: read, bash)
- general-purpose: General-purpose subagent with full tool access. Use for non-trivial tasks that requires reading and writing files or ru… (Tools: all)
- implementation: Implementation subagent for writing code, tests, and running verification. Use for one well-scoped implementation task… (Tools: all)
- read-only: Read-only subagent for multi-file investigation of named files. Cannot modify files or run commands. Use for non-trivia… (Tools: read)
Children resolve provider, model, and thinking level per field from, highest first: the config file's [agents.<name>] section, the agent definition's frontmatter, the config file's [defaults] section, then this session's provider, model, and thinking level. Durable pins belong in the config file or an agent definition.
Example: {"prompt": "Find caching options"}
```

Launched children, session-level (recorded, not gated): 1
- call 2 (`task`): task_id=750a8f8afeac499194835ffe8a849848 state=completed

Rejected calls: 1. Per-rejected-call proof: every rejected call's own result carries an empty `results` array (the rejection marker), and the launched-child envelopes across those rejected results total 0 (the hard measure holds this at zero).
Teach-back names `timeoutSeconds`: True. Shows `timeout_seconds`: True.
Residual-rate observation: the model emitted `timeoutSeconds` on 1 call(s). After the teach-back it made 1 follow-up call(s), 0 re-emitted `timeoutSeconds`, and 1 carried the corrected `timeout_seconds`.

## Key measures

- Optional fields on the ordinary fresh call (case 1 `task`): 1 (argument keys: `prompt`, `subagent_type`).
- Accidental launches after a failed resume (case `unknown-resume`): 0 launched-child envelope(s) across the rejected calls' own results (rejected calls: 1). Session-level children: 0 (recorded, not gated).
- Accidental launches after a failed resume (case `camelcase`): 0 launched-child envelope(s) across the rejected calls' own results (rejected calls: 1). Session-level children: 1 (recorded, not gated).
- Residual camelCase rate (case `camelcase`): 0/1 follow-up call(s) re-emitted `timeoutSeconds` after the teach-back.

Hard measures: PASS. Every rejected call in the failed-resume cases records the fail-closed contract (no launched-child envelope, an empty `results` array, and the teach-back), and each failed-resume case records at least one rejected call, so the proof is not vacuous.
