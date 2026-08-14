/**
 * Agent runner module — spawns pi subprocesses and collects results.
 *
 * Each subagent runs as a separate `pi --mode json -p --no-session --no-skills` process,
 * giving it an isolated context window. The agent's system prompt is appended via
 * --append-system-prompt from a temp file.
 */

import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import type { Message } from "@earendil-works/pi-ai";
import type { AgentToolResult } from "@earendil-works/pi-agent-core";
import type { AgentConfig, SingleResult, TaskDetails } from "./types.js";
import { parseStatus } from "./status-parser.js";
import { getFinalOutput } from "./utils.js";

export const SUMMARY_INSTRUCTION = `

## Response Format

End your response with a "## Summary" section containing a concise summary of your work. The summary should cover:
- What you accomplished or found
- Any files that were read or modified
- Any errors or concerns

End the summary with your status on a single line:
**Status: DONE** (or DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT)`;

type OnUpdateCallback = (partial: AgentToolResult<TaskDetails>) => void;

/**
 * Write the agent's system prompt to a temporary file (mode 0o600).
 */
async function writePromptToTempFile(agentName: string, prompt: string): Promise<{ dir: string; filePath: string }> {
  const tmpDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), "pi-subagent-"));
  const safeName = agentName.replace(/[^\w.-]+/g, "_");
  const filePath = path.join(tmpDir, `prompt-${safeName}.md`);
  await fs.promises.writeFile(filePath, prompt, { encoding: "utf-8", mode: 0o600 });
  return { dir: tmpDir, filePath };
}

/**
 * Determine how to invoke the pi binary.
 */
function getPiInvocation(args: string[]): { command: string; args: string[] } {
  const currentScript = process.argv[1];
  const isBunVirtualScript = currentScript?.startsWith("/$bunfs/root/");
  if (currentScript && !isBunVirtualScript && fs.existsSync(currentScript)) {
    return { command: process.execPath, args: [currentScript, ...args] };
  }

  const execName = path.basename(process.execPath).toLowerCase();
  const isGenericRuntime = /^(node|bun)(\.exe)?$/.test(execName);
  if (!isGenericRuntime) {
    return { command: process.execPath, args };
  }

  return { command: "pi", args };
}

/**
 * Run a single subagent with the given task.
 */
export async function runSingleAgent(
  defaultCwd: string,
  agents: AgentConfig[],
  agentName: string,
  task: string,
  cwd: string | undefined,
  modelOverride: string | undefined,
  step: number | undefined,
  signal: AbortSignal | undefined,
  onUpdate: OnUpdateCallback | undefined,
  makeDetails: (results: SingleResult[]) => TaskDetails,
): Promise<SingleResult> {
  const agent = agents.find((a) => a.name === agentName);

  if (!agent) {
    const available = agents.map((a) => `"${a.name}"`).join(", ") || "none";
    const result: SingleResult = {
      agent: agentName,
      agentSource: "unknown",
      task,
      exitCode: 1,
      messages: [],
      stderr: `Unknown agent: "${agentName}". Available agents: ${available}.`,
      usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0, contextTokens: 0, turns: 0 },
      step,
    };
    result.status = parseStatus(result);
    return result;
  }

  const args: string[] = ["--mode", "json", "-p", "--no-session", "--no-skills"];

  // Model resolution: override > agent frontmatter > omit (pi default)
  const effectiveModel = modelOverride ?? agent.model;
  if (effectiveModel) args.push("--model", effectiveModel);

  // Tools: use agent's tools list from frontmatter if defined
  if (agent.tools && agent.tools.length > 0) args.push("--tools", agent.tools.join(","));

  let tmpPromptDir: string | null = null;
  let tmpPromptPath: string | null = null;

  const currentResult: SingleResult = {
    agent: agentName,
    agentSource: agent.source,
    task,
    exitCode: 0,
    messages: [],
    stderr: "",
    usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0, contextTokens: 0, turns: 0 },
    model: effectiveModel,
    step,
  };

  const emitUpdate = () => {
    if (onUpdate) {
      onUpdate({
        content: [{ type: "text", text: getFinalOutput(currentResult.messages) || "(running...)" }],
        details: makeDetails([currentResult]),
      });
    }
  };

  try {
    // Write system prompt to temp file (with summary instruction appended)
    const fullPrompt = agent.systemPrompt.trim()
      ? `${agent.systemPrompt}${SUMMARY_INSTRUCTION}`
      : SUMMARY_INSTRUCTION.trimStart();
    if (fullPrompt.trim()) {
      const tmp = await writePromptToTempFile(agent.name, fullPrompt);
      tmpPromptDir = tmp.dir;
      tmpPromptPath = tmp.filePath;
      args.push("--append-system-prompt", tmpPromptPath);
    }

    args.push(`Task: ${task}`);

    const exitCode = await new Promise<number>((resolve) => {
      const invocation = getPiInvocation(args);
      const proc = spawn(invocation.command, invocation.args, {
        cwd: cwd ?? defaultCwd,
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
      });

      // 1-hour hard timeout per subagent
      const timeoutId = setTimeout(() => proc.kill("SIGTERM"), 60 * 60 * 1000).unref();

      let buffer = "";

      const processLine = (line: string) => {
        if (!line.trim()) return;
        let event: any;
        try {
          event = JSON.parse(line);
        } catch {
          return;
        }

        if (event.type === "message_end" && event.message) {
          const msg = event.message as Message;
          currentResult.messages.push(msg);

          if (msg.role === "assistant") {
            currentResult.usage.turns++;
            const usage = msg.usage;
            if (usage) {
              currentResult.usage.input += usage.input || 0;
              currentResult.usage.output += usage.output || 0;
              currentResult.usage.cacheRead += usage.cacheRead || 0;
              currentResult.usage.cacheWrite += usage.cacheWrite || 0;
              currentResult.usage.cost += usage.cost?.total || 0;
              currentResult.usage.contextTokens = usage.totalTokens || 0;
            }
            if (!currentResult.model && msg.model) currentResult.model = msg.model;
            if (msg.stopReason) currentResult.stopReason = msg.stopReason;
            if (msg.errorMessage) currentResult.errorMessage = msg.errorMessage;
          }
          emitUpdate();
        }

        if (event.type === "tool_result_end" && event.message) {
          currentResult.messages.push(event.message as Message);
          emitUpdate();
        }
      };

      proc.stdout.on("data", (data) => {
        buffer += data.toString();
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) processLine(line);
      });

      proc.stderr.on("data", (data) => {
        currentResult.stderr += data.toString();
      });

      proc.on("close", (code) => {
        clearTimeout(timeoutId);
        if (buffer.trim()) processLine(buffer);
        resolve(code ?? 0);
      });

      proc.on("error", () => {
        clearTimeout(timeoutId);
        resolve(1);
      });

      if (signal) {
        const killProc = () => {
          proc.kill("SIGTERM");
          setTimeout(() => {
            if (!proc.killed) proc.kill("SIGKILL");
          }, 5000);
        };
        if (signal.aborted) killProc();
        else signal.addEventListener("abort", killProc, { once: true });
      }
    });

    currentResult.exitCode = exitCode;
    if (signal?.aborted) {
      currentResult.stopReason = "aborted";
      currentResult.status = "BLOCKED";
      return currentResult;
    }

    // Parse status from output
    currentResult.status = parseStatus(currentResult);

    return currentResult;
  } finally {
    if (tmpPromptPath)
      try {
        fs.unlinkSync(tmpPromptPath);
      } catch {
        /* ignore */
      }
    if (tmpPromptDir)
      try {
        fs.rmdirSync(tmpPromptDir);
      } catch {
        /* ignore */
      }
  }
}

/**
 * Run multiple agents concurrently with a concurrency limit.
 */
export async function runParallel(
  defaultCwd: string,
  agents: AgentConfig[],
  tasks: Array<{ agent: string; task: string; cwd?: string }>,
  modelOverride: string | undefined,
  signal: AbortSignal | undefined,
  onUpdate: OnUpdateCallback | undefined,
  makeDetails: (results: SingleResult[]) => TaskDetails,
): Promise<SingleResult[]> {
  const MAX_CONCURRENCY = 4;

  const allResults: (SingleResult | null)[] = new Array(tasks.length).fill(null);

  const emitParallelUpdate = () => {
    if (onUpdate) {
      const completed = allResults.filter((r) => r !== null);
      const running = allResults.length - completed.length;
      const done = completed.length;
      onUpdate({
        content: [{ type: "text", text: `Parallel: ${done}/${allResults.length} done, ${running} running...` }],
        details: makeDetails(completed as SingleResult[]),
      });
    }
  };

  const results = await mapWithConcurrencyLimit(tasks, MAX_CONCURRENCY, async (t, index) => {
    const result = await runSingleAgent(
      defaultCwd,
      agents,
      t.agent,
      t.task,
      t.cwd,
      modelOverride,
      undefined,
      signal,
      (partial) => {
        if (partial.details?.results[0]) {
          allResults[index] = partial.details.results[0];
          emitParallelUpdate();
        }
      },
      makeDetails,
    );
    allResults[index] = result;
    emitParallelUpdate();
    return result;
  });

  return results;
}

/**
 * Run agents sequentially, passing output from one to the next via {previous} placeholder.
 */
export async function runChain(
  defaultCwd: string,
  agents: AgentConfig[],
  chain: Array<{ agent: string; task: string; cwd?: string }>,
  modelOverride: string | undefined,
  signal: AbortSignal | undefined,
  onUpdate: OnUpdateCallback | undefined,
  makeDetails: (results: SingleResult[]) => TaskDetails,
): Promise<SingleResult[]> {
  const results: SingleResult[] = [];
  let previousOutput = "";

  for (let i = 0; i < chain.length; i++) {
    const step = chain[i];
    const taskWithContext = step.task.replace(/\{previous\}/g, previousOutput);

    // Create update callback that includes all previous results
    const chainUpdate: OnUpdateCallback | undefined = onUpdate
      ? (partial) => {
          const currentResult = partial.details?.results[0];
          if (currentResult) {
            const allResults = [...results, currentResult];
            onUpdate({
              content: partial.content,
              details: makeDetails(allResults),
            });
          }
        }
      : undefined;

    const result = await runSingleAgent(
      defaultCwd,
      agents,
      step.agent,
      taskWithContext,
      step.cwd,
      modelOverride,
      i + 1,
      signal,
      chainUpdate,
      makeDetails,
    );
    results.push(result);

    const isError =
      result.exitCode !== 0 || result.stopReason === "error" || result.stopReason === "aborted";
    if (isError) return results; // Stop on error — caller handles partial results

    previousOutput = getFinalOutput(result.messages);
  }

  return results;
}

/**
 * Run items concurrently with a concurrency limit.
 */
async function mapWithConcurrencyLimit<TIn, TOut>(
  items: TIn[],
  concurrency: number,
  fn: (item: TIn, index: number) => Promise<TOut>,
): Promise<TOut[]> {
  if (items.length === 0) return [];
  const limit = Math.max(1, Math.min(concurrency, items.length));
  const results: TOut[] = new Array(items.length);
  let nextIndex = 0;
  const workers = new Array(limit).fill(null).map(async () => {
    while (true) {
      const current = nextIndex++;
      if (current >= items.length) return;
      results[current] = await fn(items[current], current);
    }
  });
  await Promise.all(workers);
  return results;
}
