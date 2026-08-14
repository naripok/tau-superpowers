/**
 * Shared utilities used across agent-runner, index, and render modules.
 */

import type { Message } from "@earendil-works/pi-ai";

/**
 * Get the final text output from the last assistant message.
 */
export function getFinalOutput(messages: Message[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === "assistant") {
      for (const part of msg.content) {
        if (part.type === "text") return part.text;
      }
    }
  }
  return "";
}

/**
 * Extract the ## Summary section from the subagent's final text output.
 * If no ## Summary section exists, returns the full output unchanged (fallback).
 * If multiple ## Summary headings exist, uses the LAST occurrence.
 */
export function getSummarySection(text: string): string {
  if (!text) return text;
  const lastSummaryIndex = text.lastIndexOf("## Summary");
  if (lastSummaryIndex === -1) return text;
  return text.slice(lastSummaryIndex);
}
