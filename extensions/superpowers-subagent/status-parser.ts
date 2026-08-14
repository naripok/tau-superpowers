/**
 * Parse the status from the last assistant message in the subagent output.
 *
 * The subagent's system prompt instructs it to end its report with one of:
 *   **Status: DONE**
 *   **Status: DONE_WITH_CONCERNS**
 *   **Status: BLOCKED**
 *   **Status: NEEDS_CONTEXT**
 *
 * We search for this pattern in the final assistant message.
 * If no pattern is found, we default to DONE (optimistic — the agent
 * completed without error and didn't explicitly flag an issue).
 */

import type { SubagentStatus, SingleResult } from "./types.js";

export function parseStatus(result: SingleResult): SubagentStatus {
  // Find the last assistant message
  const messages = result.messages;
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role !== "assistant") continue;

    // Search for status marker in text content
    for (const part of msg.content) {
      if (part.type !== "text") continue;
      const match = part.text.match(/\*\*Status:\s*(DONE|DONE_WITH_CONCERNS|BLOCKED|NEEDS_CONTEXT)\*\*/i)
        ?? part.text.match(/\bStatus:\s*(DONE|DONE_WITH_CONCERNS|BLOCKED|NEEDS_CONTEXT)\b/i);
      if (match) {
        return match[1].toUpperCase() as SubagentStatus;
      }
    }
    // Only check the last assistant message
    break;
  }

  // Default: if exit code is 0 and no error, treat as DONE
  if (result.exitCode === 0 && !result.errorMessage) {
    return "DONE";
  }

  // If there was an error, treat as BLOCKED
  return "BLOCKED";
}
