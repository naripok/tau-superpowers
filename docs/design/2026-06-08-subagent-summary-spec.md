# Spec: Subagent Summary Extraction

## Domain: subagent-dispatch

### ADDED Requirements

#### Requirement: Summary instruction appended to subagent prompt
The system SHALL append a summary format instruction to the system prompt of every spawned subagent, directing it to end its response with a `## Summary` section containing a concise summary of its work and ending with a status line in the format `**Status: DONE**`, `**Status: DONE_WITH_CONCERNS**`, `**Status: BLOCKED**`, or `**Status: NEEDS_CONTEXT**` (the existing subagent status convention).

##### Scenario: Instruction appended when subagent is spawned
- GIVEN a subagent is being spawned with a system prompt
- WHEN the system prepares the system prompt for the subagent
- THEN the prompt includes an additional instruction to end the response with a `## Summary` section

##### Scenario: Instruction does not override existing prompt
- GIVEN an agent has an existing system prompt with its own instructions
- WHEN the summary instruction is appended
- THEN the original prompt content is preserved unchanged and the summary instruction is added after it

#### Requirement: Summary section extracted for tool result content
The system SHALL extract the `## Summary` section from the subagent's final text output and return it as the tool result `content`. The extracted section includes the `## Summary` header, all text within the section, and the `**Status: ...**` line. If the output contains multiple `## Summary` headings, the LAST occurrence is used.

##### Scenario: Summary section present in subagent output
- GIVEN a subagent's final output contains a `## Summary` section
- WHEN the Task tool constructs the result
- THEN the `content` field contains the text from the `## Summary` heading to the end of the output

##### Scenario: Multiple summary headings — last one wins
- GIVEN a subagent's final output contains multiple `## Summary` headings
- WHEN the Task tool constructs the result
- THEN the `content` field contains the text from the LAST `## Summary` heading to the end of the output

##### Scenario: Empty summary section
- GIVEN a subagent's final output contains a `## Summary` heading with no content after it (only the status line)
- WHEN the Task tool constructs the result
- THEN the `content` field contains the `## Summary` heading and the status line

##### Scenario: No summary section — fallback to full output
- GIVEN a subagent's final output does not contain a `## Summary` section (e.g., the output is an empty string or plain error text with no markdown headings)
- WHEN the Task tool constructs the result
- THEN the `content` field contains the full final output text unchanged

##### Scenario: Completely empty subagent output
- GIVEN a subagent produced no output at all (empty string)
- WHEN the Task tool constructs the result
- THEN the `content` field contains an empty string

##### Scenario: Malformed summary — heading present but no status line
- GIVEN a subagent's final output contains a `## Summary` heading but no `**Status: ...**` line
- WHEN the Task tool constructs the result
- THEN the `content` field contains the text from the `## Summary` heading to the end of the output (extraction succeeds without the status line)

### MODIFIED Requirements

#### Requirement: Tool result content contract
The `content` field of the Task tool result SHALL contain only the subagent's summary section, not the full final output. The `details` field SHALL contain the complete subagent output for UI rendering.

##### Scenario: Single mode returns summary in content
- GIVEN a single subagent completed successfully with a `## Summary` section
- WHEN the Task tool returns the result
- THEN `content` contains the summary section
- AND the full output is available in the `details` field for UI rendering

##### Scenario: Chain mode returns final summary in content
- GIVEN a chain of subagents completed and the final step produced a `## Summary` section
- WHEN the Task tool returns the result
- THEN `content` contains the final step's summary section

##### Scenario: Chain mode final step has no summary — fallback
- GIVEN a chain of subagents completed but the final step's output lacks a `## Summary` section
- WHEN the Task tool returns the result
- THEN `content` contains the final step's full output text unchanged

##### Scenario: Parallel mode returns aggregated summaries in content
- GIVEN multiple parallel subagents completed, each producing a `## Summary` section
- WHEN the Task tool returns the result
- THEN `content` contains each agent's summary prefixed with `[agent-name]` on its own line, with summaries separated by blank lines
- AND the full output for each agent is available in the `details` field for UI rendering

##### Scenario: Parallel mode some agents missing summary — per-agent fallback
- GIVEN multiple parallel subagents completed but one or more lack a `## Summary` section
- WHEN the Task tool returns the result
- THEN `content` contains the summary section for agents that produced one and the full output for agents that did not, each prefixed with `[agent-name]`
- AND the fallback applies independently per agent, not to the aggregated result as a whole
