/**
 * Superpowers Subagent Extension for Pi
 *
 * Registers a `Task` tool that enables the superpowers skills to dispatch
 * subagents with isolated context windows. Supports single, parallel, and chain modes.
 *
 * Each subagent runs as a separate `pi --mode json -p --no-session --no-skills` process,
 * with the agent's system prompt appended via --append-system-prompt.
 * Status (DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT) is parsed from subagent output.
 */

import type { AgentToolResult } from "@earendil-works/pi-agent-core";
import { StringEnum } from "@earendil-works/pi-ai";
import { type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import type { AgentConfig, AgentScope, SingleResult, TaskDetails } from "./types.js";
import { discoverAgents } from "./agent-discovery.js";
import { runSingleAgent, runParallel, runChain } from "./agent-runner.js";
import { getFinalOutput, getSummarySection } from "./utils.js";
import { renderCall, renderResult } from "./render.js";

const MAX_PARALLEL_TASKS = 8;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const getSummaryText = (result: SingleResult): string => {
  const fullOutput = getFinalOutput(result.messages);
  return getSummarySection(fullOutput) || "";
};

const buildContent = (result: SingleResult): { type: "text"; text: string } => {
  return { type: "text", text: getSummaryText(result) || "(no output)" };
};

// ---------------------------------------------------------------------------
// Parameter schema
// ---------------------------------------------------------------------------

const TaskItemSchema = Type.Object({
  agent: Type.String({ description: "Name of the agent to invoke" }),
  task: Type.String({ description: "Task to delegate to the agent" }),
  cwd: Type.Optional(Type.String({ description: "Working directory for the agent process" })),
});

const ChainItemSchema = Type.Object({
  agent: Type.String({ description: "Name of the agent to invoke" }),
  task: Type.String({ description: "Task with optional {previous} placeholder for prior output" }),
  cwd: Type.Optional(Type.String({ description: "Working directory for the agent process" })),
});

const AgentScopeSchema = StringEnum(["user", "project", "both"] as const, {
  description: 'Which agent directories to search. Default: "user". Use "project" or "both" to include .pi/agents/',
  default: "user",
});

const TaskParams = Type.Object({
  description: Type.Optional(Type.String({ description: "Short description of the task (for display)" })),
  agent: Type.Optional(Type.String({ description: "Agent name for single mode (e.g., 'general-purpose' or 'read-only')" })),
  task: Type.Optional(Type.String({ description: "Task prompt for single mode" })),
  tasks: Type.Optional(Type.Array(TaskItemSchema, { description: "Array of {agent, task} for parallel execution (max 8)" })),
  chain: Type.Optional(Type.Array(ChainItemSchema, { description: "Array of {agent, task} for sequential execution with {previous} placeholder" })),
  model: Type.Optional(Type.String({ description: "Override the agent's default model (e.g., 'vllm/qwen3.6-27b', 'openrouter/anthropic/claude-sonnet-4'). ONLY set when explicitly requested by the user — suggest stronger models for complex tasks but do not set without approval." })),
  agentScope: Type.Optional(AgentScopeSchema),
  confirmProjectAgents: Type.Optional(
    Type.Boolean({ description: "Prompt before running project-local agents. Default: true.", default: true }),
  ),
  cwd: Type.Optional(Type.String({ description: "Working directory for single mode" })),
});

// ---------------------------------------------------------------------------
// Extension entry
// ---------------------------------------------------------------------------

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "Task",
    label: "Task",
    description: [
      "Dispatch tasks to specialized subagents with isolated context.",
      "Modes: single (agent + task), parallel (tasks array), chain (sequential with {previous} placeholder).",
      'Agents: "general-purpose" (full tool access), "read-only" (read, grep, find, ls only).',
      'Default agent scope is "user" (from ~/.pi/agent/agents).',
      'To enable project-local agents in .pi/agents, set agentScope: "both" (or "project").',
    ].join(" "),

    promptSnippet:
      "Dispatch tasks to specialized subagents with isolated context",

    promptGuidelines: [
      'Use "general-purpose" agent for implementation, scouting, and general tasks',
      'Use "read-only" agent for reviews and code inspection (cannot modify files)',
      'Include all context the subagent needs in the task prompt — subagents have no access to your session history',
      'When a subagent returns NEEDS_CONTEXT, provide the missing information and re-dispatch with the same agent',
      'When a subagent returns BLOCKED, consider re-dispatching with a stronger model or breaking the task into smaller pieces',
      'Do NOT set the model parameter unless explicitly requested by the user — suggest stronger models for complex tasks but let the user decide',
      'For parallel tasks (independent failures, different subsystems), use the tasks array for concurrent execution',
      'For sequential pipelines (scout → planner → worker), use the chain array with {previous} placeholder',
      'For review loops (implement → review → fix → re-review), make sequential Task calls from the controller — do not use chain mode for conditional logic',
      'Subagents run with --no-skills, so include all behavioral instructions (TDD, self-review, status reporting) in the task prompt',
      'Subagents must end their report with **Status: DONE**, **Status: DONE_WITH_CONCERNS**, **Status: BLOCKED**, or **Status: NEEDS_CONTEXT**',
    ],

    parameters: TaskParams,

    async execute(_toolCallId, params, signal, onUpdate, ctx) {
      const agentScope: AgentScope = params.agentScope ?? "user";
      const discovery = discoverAgents(ctx.cwd, agentScope);
      const agents = discovery.agents;
      const confirmProjectAgents = params.confirmProjectAgents ?? true;

      const hasChain = (params.chain?.length ?? 0) > 0;
      const hasTasks = (params.tasks?.length ?? 0) > 0;
      const hasSingle = Boolean(params.agent && params.task);
      const modeCount = Number(hasChain) + Number(hasTasks) + Number(hasSingle);

      const makeDetails =
        (mode: "single" | "parallel" | "chain") =>
        (results: SingleResult[]): TaskDetails => ({
          mode,
          agentScope,
          projectAgentsDir: discovery.projectAgentsDir,
          results,
        });

      // Validate: exactly one mode must be provided
      if (modeCount !== 1) {
        const available = agents.map((a) => `${a.name} (${a.source})`).join(", ") || "none";
        return {
          content: [
            {
              type: "text",
              text: `Invalid parameters. Provide exactly one mode: single (agent + task), parallel (tasks array), or chain (chain array).\nAvailable agents: ${available}`,
            },
          ],
          details: makeDetails("single")([]),
        };
      }

      // Confirm project-local agents if requested
      if ((agentScope === "project" || agentScope === "both") && confirmProjectAgents && ctx.hasUI) {
        const requestedAgentNames = new Set<string>();
        if (params.chain) for (const step of params.chain) requestedAgentNames.add(step.agent);
        if (params.tasks) for (const t of params.tasks) requestedAgentNames.add(t.agent);
        if (params.agent) requestedAgentNames.add(params.agent);

        const projectAgentsRequested = Array.from(requestedAgentNames)
          .map((name) => agents.find((a) => a.name === name))
          .filter((a): a is AgentConfig => a?.source === "project");

        if (projectAgentsRequested.length > 0) {
          const names = projectAgentsRequested.map((a) => a.name).join(", ");
          const dir = discovery.projectAgentsDir ?? "(unknown)";
          const ok = await ctx.ui.confirm(
            "Run project-local agents?",
            `Agents: ${names}\nSource: ${dir}\n\nProject agents are repo-controlled. Only continue for trusted repositories.`,
          );
          if (!ok)
            return {
              content: [{ type: "text", text: "Canceled: project-local agents not approved." }],
              details: makeDetails(hasChain ? "chain" : hasTasks ? "parallel" : "single")([]),
            };
        }
      }

      // ------------------------------------------------------------------
      // Chain mode
      // ------------------------------------------------------------------
      if (params.chain && params.chain.length > 0) {
        const results = await runChain(
          ctx.cwd,
          agents,
          params.chain,
          params.model,
          signal,
          onUpdate,
          makeDetails("chain"),
        );

        // Check if chain stopped early
        const failedStep = results.find((r) => r.exitCode !== 0 || r.stopReason === "error" || r.stopReason === "aborted");
        if (failedStep) {
          const errorMsg = failedStep.errorMessage || failedStep.stderr || "(no output)";
          return {
            content: [{ type: "text", text: `Chain stopped at step ${failedStep.step} (${failedStep.agent}): ${errorMsg}` }],
            details: makeDetails("chain")(results),
            isError: true,
          };
        }

        const finalResult = results[results.length - 1];
        return {
          content: [buildContent(finalResult)],
          details: makeDetails("chain")(results),
        };
      }

      // ------------------------------------------------------------------
      // Parallel mode
      // ------------------------------------------------------------------
      if (params.tasks && params.tasks.length > 0) {
        if (params.tasks.length > MAX_PARALLEL_TASKS)
          return {
            content: [
              {
                type: "text",
                text: `Too many parallel tasks (${params.tasks.length}). Max is ${MAX_PARALLEL_TASKS}.`,
              },
            ],
            details: makeDetails("parallel")([]),
          };

        const results = await runParallel(
          ctx.cwd,
          agents,
          params.tasks,
          params.model,
          signal,
          onUpdate,
          makeDetails("parallel"),
        );

        const successCount = results.filter((r) => r.exitCode === 0).length;
        const agentSummaries = results.map((r) => {
          const summary = getSummaryText(r);
          const status = r.exitCode === 0 ? "completed" : "failed";
          return `[${r.agent}] (${status})\n\n${summary || "(no output)"}`;
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
      }

      // ------------------------------------------------------------------
      // Single mode
      // ------------------------------------------------------------------
      if (params.agent && params.task) {
        const result = await runSingleAgent(
          ctx.cwd,
          agents,
          params.agent,
          params.task,
          params.cwd,
          params.model,
          undefined,
          signal,
          onUpdate,
          makeDetails("single"),
        );

        const isError = result.exitCode !== 0 || result.stopReason === "error" || result.stopReason === "aborted";
        if (isError) {
          const errorMsg =
            result.errorMessage || result.stderr || getFinalOutput(result.messages) || "(no output)";
          return {
            content: [{ type: "text", text: `Agent ${result.stopReason || "failed"}: ${errorMsg}` }],
            details: makeDetails("single")([result]),
            isError: true,
          };
        }
        return {
          content: [buildContent(result)],
          details: makeDetails("single")([result]),
        };
      }

      // Fallback (shouldn't reach here due to modeCount check)
      const available = agents.map((a) => `${a.name} (${a.source})`).join(", ") || "none";
      return {
        content: [{ type: "text", text: `Invalid parameters. Available agents: ${available}` }],
        details: makeDetails("single")([]),
      };
    },

    renderCall: renderCall,
    renderResult: renderResult,
  });
}

