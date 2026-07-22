import type { AgentName, TaskRecord, TaskStatus, Trace } from "../../types";

export interface TrendPoint {
  key: string;
  label: string;
  created: number;
  completed: number;
}

export interface SuccessBreakdown {
  completed: number;
  failed: number;
  canceled: number;
  /** 0..1 completion share over decided (terminal) tasks; null when no terminal tasks. */
  rate: number | null;
}

export interface AgentStat {
  agent: AgentName | string;
  tokens: number;
  cost: number;
  avgLatencyMs: number | null;
  runs: number;
}

export interface TokenTrendPoint {
  key: string;
  label: string;
  tokens: number;
}

const TERMINAL: TaskStatus[] = ["completed", "failed", "canceled"];

function dayKey(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function dayLabel(date: Date): string {
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

/** Buckets tasks into per-day created/completed counts for the last `days` days. */
export function deriveTaskTrend(tasks: TaskRecord[], days = 14): TrendPoint[] {
  const buckets = new Map<string, TrendPoint>();
  const today = new Date();
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset);
    const key = dayKey(date);
    buckets.set(key, { key, label: dayLabel(date), created: 0, completed: 0 });
  }

  for (const task of tasks) {
    const created = new Date(task.created_at);
    const createdBucket = buckets.get(dayKey(created));
    if (createdBucket) createdBucket.created += 1;

    if (task.status === "completed") {
      const finished = new Date(task.updated_at);
      const finishedBucket = buckets.get(dayKey(finished));
      if (finishedBucket) finishedBucket.completed += 1;
    }
  }

  return Array.from(buckets.values());
}

/** Computes completion rate over terminal (decided) tasks. */
export function deriveSuccessRate(statusCounts: Record<TaskStatus, number>): SuccessBreakdown {
  const completed = statusCounts.completed ?? 0;
  const failed = statusCounts.failed ?? 0;
  const canceled = statusCounts.canceled ?? 0;
  const decided = completed + failed + canceled;
  return { completed, failed, canceled, rate: decided === 0 ? null : completed / decided };
}

// Rough blended USD-per-token rate used only for a relative cost estimate.
const COST_PER_1K_TOKENS = 0.002;

/**
 * Aggregates per-agent token/cost/latency stats and a per-day token trend from a
 * sample of task traces. This is derived client-side because the backend exposes
 * no per-agent aggregate endpoint.
 */
export function deriveAgentStats(traces: Trace[], days = 14): {
  agents: AgentStat[];
  tokenTrend: TokenTrendPoint[];
} {
  const byAgent = new Map<string, { tokens: number; latencySum: number; latencyCount: number; runs: number }>();
  const trend = new Map<string, TokenTrendPoint>();
  const today = new Date();
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset);
    const key = dayKey(date);
    trend.set(key, { key, label: dayLabel(date), tokens: 0 });
  }

  for (const trace of traces) {
    for (const call of trace.model_calls) {
      const tokens = (call.prompt_tokens ?? 0) + (call.completion_tokens ?? 0);
      const entry = byAgent.get(call.agent_name) ?? { tokens: 0, latencySum: 0, latencyCount: 0, runs: 0 };
      entry.tokens += tokens;
      byAgent.set(call.agent_name, entry);

      const bucket = trend.get(dayKey(new Date(call.created_at)));
      if (bucket) bucket.tokens += tokens;
    }
    for (const run of trace.agent_runs) {
      const entry = byAgent.get(run.agent_name) ?? { tokens: 0, latencySum: 0, latencyCount: 0, runs: 0 };
      entry.runs += 1;
      if (run.latency_ms != null) {
        entry.latencySum += run.latency_ms;
        entry.latencyCount += 1;
      }
      byAgent.set(run.agent_name, entry);
    }
  }

  const agents: AgentStat[] = Array.from(byAgent.entries())
    .map(([agent, value]) => ({
      agent,
      tokens: value.tokens,
      cost: Math.round(value.tokens / 1000 * COST_PER_1K_TOKENS * 10000) / 10000,
      avgLatencyMs: value.latencyCount === 0 ? null : Math.round(value.latencySum / value.latencyCount),
      runs: value.runs,
    }))
    .sort((a, b) => b.tokens - a.tokens);

  return { agents, tokenTrend: Array.from(trend.values()) };
}
