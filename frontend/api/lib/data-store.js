// Read-only store for data synced from the local backend (see
// scripts/sync_cloud_data.py). The whole snapshot lives under one key so a
// warm serverless instance needs at most one storage read per TTL window.
import { kvGet, useCloud } from './kv.js';

const R_DATA = 'agentsystem:cloud_data';
const CACHE_TTL_MS = 60 * 1000; // synced snapshots are infrequent; 60s staleness is fine

const EMPTY = Object.freeze({
  tasks: [],
  task_views: {},
  task_messages: {},
  task_agents: {},
  agents: [],
  approvals: [],
  projects: [],
  project_files: {},
  operations_summary: null,
  audit_logs: [],
  traces: {},
  collaboration_rules: null,
  mcp_servers: [],
  skills: [],
  capability_policy: null,
  agent_capabilities: {},
  credentials: [],
  model_providers: [],
  synced_at: null,
});

let cache = null;
let cacheAt = 0;

export async function hydrateData() {
  if (!useCloud) return;
  const now = Date.now();
  if (cache && now - cacheAt < CACHE_TTL_MS) return;
  try {
    cache = (await kvGet(R_DATA)) || null;
  } catch (err) {
    console.error('[agentsystem] cloud data hydrate failed:', err.message);
    // Keep serving the previous snapshot (or empty) instead of failing requests.
  }
  cacheAt = now;
}

export function getCloudData() {
  if (!useCloud) return EMPTY;
  return cache ? { ...EMPTY, ...cache } : EMPTY;
}
