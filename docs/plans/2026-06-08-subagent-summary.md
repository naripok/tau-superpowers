# Subagent Summary Extraction Implementation Plan

> **Historical Pi plan (2026-06-08) — do not execute.** The unchecked tasks, npm commands, Pi dependencies, and TypeScript paths below targeted the removed pre-Tau extension. They are preserved as implementation history, not outstanding work. See the [living Tau specification](../specs/subagent-dispatch.md) and current [Tau port plan](2026-08-14-tau-port.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract only the `## Summary` section from subagent output for the main agent's context, reducing context bloat and delaying premature compaction.

**Architecture:** Append a summary instruction to the subagent's system prompt at spawn time. After the subagent completes, extract the `## Summary` section from its final text output and return it as the tool result `content`. The full output remains in `details` for UI rendering.

**Tech Stack:** TypeScript, vitest (new test framework)

**Feature spec:** `docs/design/2026-06-08-subagent-summary-spec.md`

**Delta spec:** `docs/design/2026-06-08-subagent-summary-delta.md`

---

### Task 1: Add vitest test framework

**Files:**
- Modify: `extensions/superpowers-subagent/package.json`
- Create: `extensions/superpowers-subagent/vitest.config.ts`

**Delta requirement:** N/A (infrastructure setup)

- [ ] **Step 1: Add vitest to devDependencies**

Modify `extensions/superpowers-subagent/package.json`:

```json
{
  "name": "superpowers-subagent",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "peerDependencies": {
    "@earendil-works/pi-ai": "*",
    "@earendil-works/pi-agent-core": "*",
    "@earendil-works/pi-coding-agent": "*",
    "@earendil-works/pi-tui": "*",
    "@sinclair/typebox": "*"
  },
  "devDependencies": {
    "@types/node": "^25.6.0",
    "typescript": "^6.0.3",
    "vitest": "^3.0.0"
  }
}
```

- [ ] **Step 2: Create vitest.config.ts**

Create `extensions/superpowers-subagent/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["**/*.test.ts"],
    globals: false,
  },
});
```

- [ ] **Step 3: Install dependencies**

Run: `cd extensions/superpowers-subagent && npm install`

- [ ] **Step 4: Commit**

```bash
git add extensions/superpowers-subagent/package.json extensions/superpowers-subagent/vitest.config.ts
git commit -m "test: add vitest test framework"
```

---

### Task 2: Implement `getSummarySection()` utility

**Files:**
- Modify: `extensions/superpowers-subagent/utils.ts`
- Create: `extensions/superpowers-subagent/utils.test.ts`

**Delta requirement:** ADDED — Summary section extracted for tool result content

- [ ] **Step 1: Write failing tests for `getSummarySection()`**

Create `extensions/superpowers-subagent/utils.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { getSummarySection } from "./utils.js";

describe("getSummarySection", () => {
  it("extracts the ## Summary section from output", () => {
    const output = `Here is my analysis of the codebase.

I found several issues...

## Summary

The codebase has 3 critical issues that need attention.
1. Memory leak in module A
2. Race condition in module B

**Status: DONE**`;

    const result = getSummarySection(output);
    expect(result).toBe(`## Summary

The codebase has 3 critical issues that need attention.
1. Memory leak in module A
2. Race condition in module B

**Status: DONE**`);
  });

  it("uses the LAST ## Summary heading when multiple exist", () => {
    const output = `## Summary

This is an earlier summary.

## Summary

This is the final summary.
**Status: DONE**`;

    const result = getSummarySection(output);
    expect(result).toBe(`## Summary

This is the final summary.
**Status: DONE**`);
  });

  it("returns the summary heading and status line when summary is empty", () => {
    const output = `Some work was done.

## Summary
**Status: DONE**`;

    const result = getSummarySection(output);
    expect(result).toBe("## Summary\n**Status: DONE**");
  });

  it("falls back to full output when no ## Summary section exists", () => {
    const output = `No summary here, just plain text.
**Status: DONE**`;

    const result = getSummarySection(output);
    expect(result).toBe(output);
  });

  it("returns empty string for empty input", () => {
    const result = getSummarySection("");
    expect(result).toBe("");
  });

  it("extracts summary even without a status line", () => {
    const output = `## Summary

Just a summary with no status.`;

    const result = getSummarySection(output);
    expect(result).toBe("## Summary\n\nJust a summary with no status.");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd extensions/superpowers-subagent && npx vitest run utils.test.ts`
Expected: FAIL — `getSummarySection` is not exported from `utils.js`

- [ ] **Step 3: Implement `getSummarySection()` in utils.ts**

Add to `extensions/superpowers-subagent/utils.ts` (after `getFinalOutput`):

```typescript
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd extensions/superpowers-subagent && npx vitest run utils.test.ts`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add extensions/superpowers-subagent/utils.ts extensions/superpowers-subagent/utils.test.ts
git commit -m "feat: add getSummarySection() utility with tests"
```

---

### Task 3: Append summary instruction to subagent system prompt

**Files:**
- Modify: `extensions/superpowers-subagent/agent-runner.ts`

**Delta requirement:** ADDED — Summary instruction appended to subagent prompt

- [ ] **Step 1: Define the summary instruction constant**

Add near the top of `agent-runner.ts` (after imports):

```typescript
const SUMMARY_INSTRUCTION = `

## Response Format

End your response with a "## Summary" section containing a concise summary of your work. The summary should cover:
- What you accomplished or found
- Any files that were read or modified
- Any errors or concerns

End the summary with your status on a single line:
**Status: DONE** (or DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT)`;
```

- [ ] **Step 2: Append the instruction when writing the system prompt**

In `agent-runner.ts`, find the `writePromptToTempFile` call site (around line 120-125). Modify the prompt writing to append the instruction:

Current code in `runSingleAgent`:
```typescript
    // Write system prompt to temp file
    if (agent.systemPrompt.trim()) {
      const tmp = await writePromptToTempFile(agent.name, agent.systemPrompt);
```

Replace with:
```typescript
    // Write system prompt to temp file (with summary instruction appended)
    const fullPrompt = agent.systemPrompt.trim()
      ? `${agent.systemPrompt}${SUMMARY_INSTRUCTION}`
      : SUMMARY_INSTRUCTION.trimStart();
    if (fullPrompt.trim()) {
      const tmp = await writePromptToTempFile(agent.name, fullPrompt);
```

- [ ] **Step 3: Write a test for prompt appending**

Add to `extensions/superpowers-subagent/utils.test.ts`:

```typescript
import { SUMMARY_INSTRUCTION } from "./agent-runner.js";

describe("SUMMARY_INSTRUCTION", () => {
  it("contains the summary format directive", () => {
    expect(SUMMARY_INSTRUCTION).toContain("## Summary");
    expect(SUMMARY_INSTRUCTION).toContain("**Status:");
  });

  it("contains all four status values", () => {
    expect(SUMMARY_INSTRUCTION).toContain("DONE");
    expect(SUMMARY_INSTRUCTION).toContain("DONE_WITH_CONCERNS");
    expect(SUMMARY_INSTRUCTION).toContain("BLOCKED");
    expect(SUMMARY_INSTRUCTION).toContain("NEEDS_CONTEXT");
  });
});
```

Export `SUMMARY_INSTRUCTION` from `agent-runner.ts`:
```typescript
export const SUMMARY_INSTRUCTION = `...`;
```

- [ ] **Step 4: Run tests to verify**

Run: `cd extensions/superpowers-subagent && npx vitest run`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add extensions/superpowers-subagent/agent-runner.ts extensions/superpowers-subagent/utils.test.ts
git commit -m "feat: append summary instruction to subagent system prompt"
```

---

### Task 4: Use `getSummarySection()` in tool result content

**Files:**
- Modify: `extensions/superpowers-subagent/index.ts`

**Delta requirement:** MODIFIED — Tool result content contract

- [ ] **Step 1: Import `getSummarySection` in index.ts**

Add to imports in `index.ts`:

```typescript
import { getFinalOutput, getSummarySection } from "./utils.js";
```

- [ ] **Step 2: Create a helper to build content for a single result**

Add a helper function (can be inline or at module level):

```typescript
const buildContent = (result: SingleResult): { type: "text"; text: string } => {
  const fullOutput = getFinalOutput(result.messages);
  const summary = getSummarySection(fullOutput);
  return { type: "text", text: summary || "(no output)" };
};
```

- [ ] **Step 3: Update single mode to use summary**

In the single mode section of `execute()`, replace:

```typescript
        return {
          content: [{ type: "text", text: getFinalOutput(result.messages) || "(no output)" }],
          details: makeDetails("single")([result]),
        };
```

With:

```typescript
        return {
          content: [buildContent(result)],
          details: makeDetails("single")([result]),
        };
```

- [ ] **Step 4: Update chain mode to use summary**

In the chain mode section, replace the final output construction:

Current:
```typescript
        // Get final output
        const finalResult = results[results.length - 1];
        let finalOutput = "";
        for (let i = results.length - 1; i >= 0; i--) {
          const output = getFinalOutput(results[i].messages);
          if (output) { finalOutput = output; break; }
        }
        return {
          content: [{ type: "text", text: finalOutput || "(no output)" }],
          details: makeDetails("chain")(results),
        };
```

Replace with:
```typescript
        const finalResult = results[results.length - 1];
        return {
          content: [buildContent(finalResult)],
          details: makeDetails("chain")(results),
        };
```

- [ ] **Step 5: Update parallel mode to use aggregated summaries**

In the parallel mode section, replace the content construction:

Current:
```typescript
        const summaries = results.map((r) => {
          const output = getFinalOutput(r.messages);
          const preview = output.slice(0, 100) + (output.length > 100 ? "..." : "");
          return `[${r.agent}] ${r.exitCode === 0 ? "completed" : "failed"}: ${preview || "(no output)"}`;
        });
        return {
          content: [
            {
              type: "text",
              text: `Parallel: ${successCount}/${results.length} succeeded\n\n${summaries.join("\n\n")}`,
            },
          ],
          details: makeDetails("parallel")(results),
        };
```

Replace with:

```typescript
        const agentSummaries = results.map((r) => {
          const summary = getSummarySection(getFinalOutput(r.messages));
          return `[${r.agent}]\n\n${summary || "(no output)"}`;
        });
        return {
          content: [
            {
              type: "text",
              text: `Parallel: ${successCount}/${results.length} succeeded\n\n${agentSummaries.join("\n\n\n")}`,
            },
          ],
          details: makeDetails("parallel")(results),
        };
```

- [ ] **Step 6: Run TypeScript compilation to verify**

Run: `cd extensions/superpowers-subagent && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Run all tests**

Run: `cd extensions/superpowers-subagent && npx vitest run`
Expected: PASS (all tests)

- [ ] **Step 8: Commit**

```bash
git add extensions/superpowers-subagent/index.ts
git commit -m "feat: return ## Summary section as tool result content"
```

---

### Task 5: Integration verification

**Files:**
- No file changes (verification only)

**Delta requirement:** All requirements (end-to-end verification)

- [ ] **Step 1: Verify TypeScript compilation**

Run: `cd extensions/superpowers-subagent && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 2: Run all unit tests**

Run: `cd extensions/superpowers-subagent && npx vitest run`
Expected: PASS (all tests)

- [ ] **Step 3: Manual integration test**

Run the Task tool with a simple single-agent task and verify:
1. The subagent receives the summary instruction (check the temp prompt file or logs)
2. The tool result `content` contains only the `## Summary` section
3. The tool result `details` contains the full output
4. The UI renders correctly (uses `details`)

- [ ] **Step 4: Commit any final adjustments**

```bash
git add -A
git commit -m "verify: confirm integration works end-to-end"
```
(or skip if no changes needed)

---

## Self-Review

### Feature spec coverage (spec → delta)
- ✅ Summary instruction appended → ADDED in delta
- ✅ Summary section extracted → ADDED in delta
- ✅ Tool result content contract → MODIFIED in delta
- ✅ Full output preserved in details → ADDED in delta (via fallback scenarios)

### Delta coverage (delta → plan)
- ✅ Summary instruction appended → Task 3
- ✅ Summary section extracted → Task 2 (getSummarySection) + Task 4 (usage in index.ts)
- ✅ Tool result content contract (single/chain/parallel) → Task 4
- ✅ Fallback scenarios → Task 2 (tests cover all fallback paths)

### Reverse coverage (plan → delta)
- ✅ Task 1: Infrastructure (vitest) — needed for TDD, not scope creep
- ✅ Task 2: getSummarySection — implements extraction requirement
- ✅ Task 3: Prompt appending — implements instruction requirement
- ✅ Task 4: Content construction — implements content contract
- ✅ Task 5: Verification — standard practice

### Placeholder scan
- ✅ No TBDs, TODOs, or vague steps
- ✅ All code blocks are complete
- ✅ All test code is written out
- ✅ All file paths are exact

### Type consistency
- ✅ `getSummarySection(text: string): string` — consistent across utils.ts and tests
- ✅ `buildContent(result: SingleResult)` — uses `SingleResult` from types.ts
- ✅ `SUMMARY_INSTRUCTION` exported for testing — consistent with agent-runner.ts
