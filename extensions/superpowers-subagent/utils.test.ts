import { describe, it, expect } from "vitest";
import { getSummarySection } from "./utils.js";
import { SUMMARY_INSTRUCTION } from "./agent-runner.js";

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
