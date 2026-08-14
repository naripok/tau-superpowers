# Proposal: Subagent Summary Extraction

## Intent
The Task tool currently returns the subagent's full final output as the tool result `content`, which is added to the main agent's LLM context. This inflates the context window and causes compaction to trigger earlier than necessary, because the subagent's detailed work product (tool call logs, intermediate analysis, verbose explanations) occupies context space that could be used for the main agent's actual reasoning.

The subagent's conclusions — what was done, what was found, what to do next — are typically a small fraction of the full output. By extracting only the summary section and passing that to the main agent's context, we reduce context bloat and delay unnecessary compaction.

## Scope
**In scope:**
- Appending a summary instruction to the system prompt when spawning subagents
- Extracting the `## Summary` section from the subagent's final output
- Returning only the summary as tool result `content`
- Preserving full output in `details` for UI rendering

**Out of scope:**
- Changes to pi-coding-agent core (compaction logic, token tracking, message types)
- Changes to existing agent definition files in `~/.pi/agent/agents/` or `.pi/agents/`
- LLM-generated summarization of subagent output
- Truncation of any subagent output

## Approach
Append a summary instruction to the system prompt when spawning each subagent, instructing it to end its response with a `## Summary` section. Extract this section in the Task tool and return it as `content`. The full `SingleResult[]` remains in `details` for UI rendering via `renderResult()`.

This requires changes only in the extension (`agent-runner.ts` for prompt appending, `index.ts` for summary extraction). No changes to pi-coding-agent core are needed.

## Impact
- **agent-runner.ts**: Append summary instruction to the temp system prompt file
- **index.ts**: Extract `## Summary` section from `getFinalOutput()` result before returning as `content`
- **utils.ts**: Add a `getSummarySection()` function (or inline the extraction)
- **render.ts**: No changes (already reads from `details`)
- **Agent behavior**: Subagents will produce a `## Summary` section at the end of responses; this is additive to the existing `**Status: ...**` convention
