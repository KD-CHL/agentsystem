import { describe, expect, it } from "vitest";

import { deriveAgentStats, deriveSuccessRate, deriveTaskTrend } from "../components/charts/derive";
import type { TaskRecord, TaskStatus, Trace } from "../types";

function makeTask(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    id: "task-1",
    trace_id: "trace-1",
    run_id: null,
    tenant_id: "t",
    owner_id: "o",
    repo_id: "repo",
    base_branch: "main",
    prompt: "do work",
    issue_url: null,
    workspace_path: null,
    approval_policy: "auto",
    priority: "normal",
    status: "completed",
    current_step: "pr",
    branch_name: null,
    pr_url: null,
    failure_code: null,
    failure_reason: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("deriveTaskTrend", () => {
  it("buckets a task created today into the last day", () => {
    const trend = deriveTaskTrend([makeTask()], 7);
    expect(trend).toHaveLength(7);
    expect(trend.at(-1)?.created).toBe(1);
  });

  it("counts completed tasks in the completed series", () => {
    const trend = deriveTaskTrend([makeTask({ status: "completed" })], 7);
    expect(trend.at(-1)?.completed).toBe(1);
  });

  it("returns zero-filled buckets when there are no tasks", () => {
    const trend = deriveTaskTrend([], 14);
    expect(trend).toHaveLength(14);
    expect(trend.every((point) => point.created === 0 && point.completed === 0)).toBe(true);
  });
});

describe("deriveSuccessRate", () => {
  const counts = (overrides: Partial<Record<TaskStatus, number>> = {}) =>
    ({ created: 0, queued: 0, running: 0, awaiting_approval: 0, input_required: 0, completed: 0, canceled: 0, failed: 0, ...overrides }) as Record<TaskStatus, number>;

  it("computes the rate over terminal tasks only", () => {
    const result = deriveSuccessRate(counts({ completed: 3, failed: 1, running: 5 }));
    expect(result.rate).toBeCloseTo(0.75);
    expect(result.completed).toBe(3);
  });

  it("returns a null rate when there are no terminal tasks", () => {
    expect(deriveSuccessRate(counts({ running: 2 })).rate).toBeNull();
  });
});

describe("deriveAgentStats", () => {
  const trace: Trace = {
    task: makeTask(),
    events: [],
    agent_runs: [
      { id: "r1", agent_name: "coding", input_summary: "", output_summary: null, handoff_to: null, latency_ms: 1000, started_at: new Date().toISOString(), completed_at: null },
      { id: "r2", agent_name: "coding", input_summary: "", output_summary: null, handoff_to: null, latency_ms: 3000, started_at: new Date().toISOString(), completed_at: null },
    ],
    model_calls: [
      { id: "m1", agent_name: "coding", provider: "p", model: "m", api_format: "responses", simulated: false, prompt_tokens: 100, completion_tokens: 50, provider_request_id: null, error_message: null, latency_ms: 10, created_at: new Date().toISOString() },
    ],
    tool_calls: [],
    audit_logs: [],
    artifacts: [],
    chat_messages: [],
  };

  it("aggregates tokens and average latency per agent", () => {
    const { agents } = deriveAgentStats([trace]);
    const coding = agents.find((item) => item.agent === "coding");
    expect(coding).toBeDefined();
    expect(coding?.tokens).toBe(150);
    expect(coding?.avgLatencyMs).toBe(2000);
    expect(coding?.runs).toBe(2);
  });

  it("produces a token trend with the requested number of days", () => {
    const { tokenTrend } = deriveAgentStats([trace], 7);
    expect(tokenTrend).toHaveLength(7);
    expect(tokenTrend.at(-1)?.tokens).toBe(150);
  });
});
