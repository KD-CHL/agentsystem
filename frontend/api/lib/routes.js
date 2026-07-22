// HTTP routing for the serverless API layer. Mirrors the FastAPI /api/v1/*
// contract (snake_case bodies, {error:{code,message}} errors, X-Total-Count
// pagination header) so the unmodified React frontend works against both the
// local backend and this cloud layer. Auth endpoints are fully implemented;
// data endpoints serve the synced read-only snapshot; writes return 501.
import {
  createSession,
  destroySession,
  getSession,
  findUserByUsername,
  findUserById,
  findUserByGithubId,
  verifyPassword,
  createUser,
  createGithubUser,
  updateUser,
  listUsers,
  publicUser,
} from './auth-db.js';
import { githubEnabled, GITHUB_CLIENT_ID, exchangeCode, fetchGithubUser } from './github-oauth.js';
import { getCloudData } from './data-store.js';

const ROLES = ['admin', 'operator', 'reviewer', 'viewer'];

// Mirrors frontend/src/auth/AuthContext.tsx rolePermissions.
const ROLE_PERMISSIONS = {
  admin: ['task:read', 'task:write', 'task:chat', 'approval:decide', 'project:read', 'project:write', 'agent:read', 'agent:manage', 'credential:manage', 'operations:read', 'audit:read', 'user:manage'],
  operator: ['task:read', 'task:write', 'task:chat', 'approval:decide', 'project:read', 'project:write', 'agent:read', 'operations:read', 'audit:read'],
  reviewer: ['task:read', 'task:chat', 'approval:decide', 'project:read', 'agent:read', 'operations:read', 'audit:read'],
  viewer: ['task:read', 'project:read', 'agent:read'],
};

// --- low-level helpers ---

export function sendJson(res, status, obj, extraHeaders) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    ...(extraHeaders || {}),
  });
  res.end(JSON.stringify(obj));
}

function sendError(res, status, code, message) {
  sendJson(res, status, { error: { code, message, details: {} } });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > 1e6) {
        req.destroy();
        reject(new Error('payload too large'));
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch { resolve({}); }
    });
    req.on('error', reject);
  });
}

function bearerToken(req) {
  const header = req.headers['authorization'] || '';
  if (header.toLowerCase().startsWith('bearer ')) return header.slice(7).trim();
  // EventSource cannot set headers — accept ?token= as a fallback.
  try {
    const url = new URL(req.url, 'http://local');
    const queryToken = url.searchParams.get('token');
    if (queryToken) return queryToken;
  } catch { /* ignore malformed URLs */ }
  return null;
}

function authUser(req) {
  const token = bearerToken(req);
  if (!token) return null;
  const session = getSession(token);
  if (!session) return null;
  const user = findUserById(session.userId);
  if (!user || user.status !== 'active') return null;
  return user;
}

function requireAuth(req, res) {
  const user = authUser(req);
  if (!user) sendError(res, 401, 'AUTHENTICATION_REQUIRED', 'Sign in is required');
  return user;
}

function hasPermission(user, permission) {
  const perms = ROLE_PERMISSIONS[user.role] || [];
  return perms.includes(permission);
}

function requirePermission(req, res, permission) {
  const user = requireAuth(req, res);
  if (!user) return null;
  if (!hasPermission(user, permission)) {
    sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return null;
  }
  return user;
}

function readOnly(res) {
  sendError(res, 501, 'CLOUD_READ_ONLY', 'The cloud deployment is a read-only snapshot. Perform this action in the local workbench.');
}

function notFound(res, code, message) {
  sendError(res, 404, code, message);
}

function sessionView(user, token) {
  const view = { user: publicUser(user), auth_mode: 'local' };
  if (token) view.token = token;
  return view;
}

// --- data filtering (mirrors store.query_tasks / list_audit_logs) ---

function paginate(records, params) {
  const limit = Math.min(Math.max(parseInt(params.get('limit') || '100', 10) || 100, 1), 200);
  const offset = Math.max(parseInt(params.get('offset') || '0', 10) || 0, 0);
  return { page: records.slice(offset, offset + limit), total: records.length };
}

function filterTasks(data, params) {
  let records = data.tasks.slice();
  const statuses = params.getAll('status');
  if (statuses.length) records = records.filter((t) => statuses.includes(t.status));
  const priority = params.get('priority');
  if (priority) records = records.filter((t) => t.priority === priority);
  const q = params.get('q');
  if (q) {
    const needle = q.toLowerCase();
    records = records.filter(
      (t) =>
        String(t.prompt || '').toLowerCase().includes(needle) ||
        String(t.repo_id || '').toLowerCase().includes(needle) ||
        String(t.id || '').toLowerCase().includes(needle),
    );
  }
  records.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  return records;
}

function filterAuditLogs(data, params) {
  let records = data.audit_logs.slice();
  const action = params.get('action');
  if (action) records = records.filter((item) => item.action === action);
  const q = params.get('q');
  if (q) {
    const needle = q.toLowerCase();
    records = records.filter(
      (item) =>
        String(item.actor || '').toLowerCase().includes(needle) ||
        String(item.action || '').toLowerCase().includes(needle) ||
        JSON.stringify(item.details || {}).toLowerCase().includes(needle),
    );
  }
  records.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  return records;
}

function parentOf(filePath) {
  const idx = String(filePath).lastIndexOf('/');
  return idx === -1 ? '' : String(filePath).slice(0, idx);
}

function normalizeDirPath(raw) {
  return String(raw || '').replace(/^\/+|\/+$/g, '');
}

// --- auth handlers ---

async function handleLogin(req, res) {
  const body = await readBody(req);
  const username = String(body.username || '').trim();
  const password = String(body.password || '');
  if (!username || !password) {
    return sendError(res, 400, 'VALIDATION_ERROR', 'username and password are required');
  }
  const user = findUserByUsername(username);
  if (!user || !verifyPassword(password, user.salt, user.hash) || user.status !== 'active') {
    return sendError(res, 401, 'INVALID_CREDENTIALS', 'Invalid username or password');
  }
  updateUser(user.id, { last_login_at: new Date().toISOString() });
  const token = createSession(user.id);
  return sendJson(res, 200, sessionView(user, token));
}

async function handleGithubLogin(req, res) {
  if (!githubEnabled()) {
    return sendError(res, 503, 'GITHUB_OAUTH_DISABLED', 'GitHub login is not configured on this deployment');
  }
  const body = await readBody(req);
  const code = String(body.code || '');
  if (!code) return sendError(res, 400, 'VALIDATION_ERROR', 'Missing authorization code');
  try {
    const accessToken = await exchangeCode(code);
    const gh = await fetchGithubUser(accessToken);
    let user = findUserByGithubId(gh.id);
    if (!user) {
      let name = gh.login;
      while (findUserByUsername(name)) name += '_gh';
      user = createGithubUser(name, gh.id);
      if (gh.name) updateUser(user.id, { display_name: gh.name });
    } else if (user.status !== 'active') {
      return sendError(res, 403, 'ACCOUNT_DISABLED', 'This account has been disabled');
    }
    updateUser(user.id, { last_login_at: new Date().toISOString() });
    const token = createSession(user.id);
    return sendJson(res, 200, sessionView(user, token));
  } catch (err) {
    return sendError(res, 502, 'GITHUB_LOGIN_FAILED', 'GitHub login failed: ' + err.message);
  }
}

// --- user management (admin only, mirrors FastAPI user routes) ---

async function handleCreateUser(req, res) {
  const user = requirePermission(req, res, 'user:manage');
  if (!user) return;
  const body = await readBody(req);
  const username = String(body.username || '').trim();
  const password = String(body.password || '');
  const role = ROLES.includes(body.role) ? body.role : 'viewer';
  if (!username || username.length > 120) return sendError(res, 400, 'VALIDATION_ERROR', 'username is required (max 120 chars)');
  if (password.length < 12) return sendError(res, 400, 'VALIDATION_ERROR', 'Initial passwords require at least 12 characters');
  if (findUserByUsername(username)) return sendError(res, 409, 'USER_ALREADY_EXISTS', 'A user with this username already exists');
  const created = createUser(username, password, role, String(body.display_name || username));
  return sendJson(res, 201, publicUser(created));
}

async function handleUpdateUser(req, res, userId) {
  const actor = requirePermission(req, res, 'user:manage');
  if (!actor) return;
  const target = findUserById(userId);
  if (!target) return notFound(res, 'USER_NOT_FOUND', 'User not found');
  const body = await readBody(req);
  const patch = {};
  if (body.display_name !== undefined) patch.display_name = String(body.display_name);
  if (body.role !== undefined) {
    if (!ROLES.includes(body.role)) return sendError(res, 400, 'VALIDATION_ERROR', 'Invalid role');
    patch.role = body.role;
  }
  if (body.status !== undefined) {
    if (!['active', 'disabled'].includes(body.status)) return sendError(res, 400, 'VALIDATION_ERROR', 'Invalid status');
    patch.status = body.status;
  }
  if (body.password !== undefined) {
    if (String(body.password).length < 12) return sendError(res, 400, 'VALIDATION_ERROR', 'Passwords require at least 12 characters');
    const { hashPassword } = await import('./auth-db.js');
    const { salt, hash } = hashPassword(String(body.password));
    patch.salt = salt;
    patch.hash = hash;
  }
  // Protect the last active admin (mirrors FastAPI AuthService.update_user).
  const activeAdmins = listUsers().filter((u) => u.role === 'admin' && u.status === 'active');
  const demotingLastAdmin =
    target.role === 'admin' &&
    target.status === 'active' &&
    activeAdmins.length === 1 &&
    activeAdmins[0].id === target.id &&
    ((patch.role && patch.role !== 'admin') || patch.status === 'disabled');
  if (demotingLastAdmin) {
    return sendError(res, 400, 'LAST_ADMIN_PROTECTED', 'Cannot remove or disable the last active administrator');
  }
  const updated = updateUser(userId, patch);
  return sendJson(res, 200, publicUser(updated));
}

// --- main router ---

export async function handleApi(req, res, urlPath) {
  const method = (req.method || 'GET').toUpperCase();
  let params = new URLSearchParams();
  try {
    params = new URL(req.url, 'http://local').searchParams;
  } catch { /* keep empty params */ }

  // ---- public endpoints ----
  if (urlPath === '/api/v1/auth/login' && method === 'POST') return handleLogin(req, res);
  if (urlPath === '/api/v1/auth/github/config' && method === 'GET') {
    return sendJson(res, 200, { enabled: githubEnabled(), client_id: GITHUB_CLIENT_ID });
  }
  if (urlPath === '/api/v1/auth/github' && method === 'POST') return handleGithubLogin(req, res);
  if (urlPath === '/api/v1/system' && method === 'GET') {
    const data = getCloudData();
    const synced = data.system || {};
    return sendJson(res, 200, {
      name: 'AgentSystem',
      version: synced.version || '0.3.0',
      auth_mode: 'local',
      execution_mode: synced.execution_mode || 'simulated',
      model_calls_enabled: false,
      live_agent_count: synced.live_agent_count || 0,
      simulated_agent_count: synced.simulated_agent_count || 8,
      worker_running: false,
      cloud_read_only: true,
      synced_at: data.synced_at || null,
    });
  }

  // ---- everything below requires a session ----
  const user = requireAuth(req, res);
  if (!user) return;

  const data = getCloudData();

  // ---- auth ----
  if (urlPath === '/api/v1/auth/me' && method === 'GET') {
    return sendJson(res, 200, sessionView(user, null));
  }
  if (urlPath === '/api/v1/auth/logout' && method === 'POST') {
    const token = bearerToken(req);
    if (token) destroySession(token);
    res.writeHead(204, { 'Cache-Control': 'no-store' });
    return res.end();
  }

  // ---- users (admin only) ----
  if (urlPath === '/api/v1/users' && method === 'GET') {
    if (!hasPermission(user, 'user:manage')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, listUsers().map(publicUser));
  }
  if (urlPath === '/api/v1/users' && method === 'POST') return handleCreateUser(req, res);
  let match = urlPath.match(/^\/api\/v1\/users\/([^/]+)$/);
  if (match && method === 'PATCH') return handleUpdateUser(req, res, match[1]);

  // ---- tasks ----
  if (urlPath === '/api/v1/tasks' && method === 'GET') {
    if (!hasPermission(user, 'task:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const records = filterTasks(data, params);
    const { page, total } = paginate(records, params);
    return sendJson(res, 200, page, { 'X-Total-Count': String(total) });
  }
  match = urlPath.match(/^\/api\/v1\/tasks\/([^/]+)$/);
  if (match && method === 'GET') {
    if (!hasPermission(user, 'task:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const view = data.task_views[match[1]];
    if (!view) return notFound(res, 'TASK_NOT_FOUND', 'Task not found');
    return sendJson(res, 200, view);
  }
  match = urlPath.match(/^\/api\/v1\/tasks\/([^/]+)\/messages$/);
  if (match && method === 'GET') {
    if (!hasPermission(user, 'task:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    if (!data.task_views[match[1]]) return notFound(res, 'TASK_NOT_FOUND', 'Task not found');
    return sendJson(res, 200, data.task_messages[match[1]] || []);
  }
  match = urlPath.match(/^\/api\/v1\/tasks\/([^/]+)\/events$/);
  if (match && method === 'GET') {
    // Serverless cannot hold SSE streams; the frontend falls back to polling.
    return sendError(res, 501, 'EVENTS_UNAVAILABLE', 'Live event streaming is unavailable on the cloud snapshot; the workspace polls for updates instead.');
  }

  // ---- approvals ----
  if (urlPath === '/api/v1/approvals' && method === 'GET') {
    if (!hasPermission(user, 'task:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    let records = data.approvals.slice();
    const taskId = params.get('task_id');
    if (taskId) records = records.filter((item) => item.task_id === taskId);
    const approvalStatus = params.get('status');
    if (approvalStatus) records = records.filter((item) => item.status === approvalStatus);
    records.sort((a, b) => String(b.requested_at).localeCompare(String(a.requested_at)));
    return sendJson(res, 200, records);
  }

  // ---- projects ----
  if (urlPath === '/api/v1/projects' && method === 'GET') {
    if (!hasPermission(user, 'project:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.projects);
  }
  match = urlPath.match(/^\/api\/v1\/projects\/([^/]+)\/files$/);
  if (match && method === 'GET') {
    if (!hasPermission(user, 'project:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const files = data.project_files[match[1]];
    if (!files) return notFound(res, 'PROJECT_PATH_NOT_FOUND', 'Project path not found');
    const dir = normalizeDirPath(params.get('path') || '');
    return sendJson(res, 200, files.filter((item) => parentOf(item.path) === dir));
  }
  match = urlPath.match(/^\/api\/v1\/projects\/([^/]+)\/file$/);
  if (match && method === 'GET') {
    return sendError(res, 501, 'CLOUD_READ_ONLY', 'File contents are not synced to the cloud snapshot. Browse them in the local workbench.');
  }

  // ---- agents ----
  if (urlPath === '/api/v1/agents' && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const taskId = params.get('task_id');
    const perTask = taskId ? data.task_agents[taskId] : null;
    return sendJson(res, 200, perTask || data.agents);
  }
  match = urlPath.match(/^\/api\/v1\/agents\/([^/]+)\/capabilities$/);
  if (match && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const caps = data.agent_capabilities[match[1]];
    if (!caps) return notFound(res, 'AGENT_NOT_FOUND', 'Agent not found');
    return sendJson(res, 200, caps);
  }
  match = urlPath.match(/^\/api\/v1\/agents\/([^/]+)\/configuration$/);
  if (match && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const agent = data.agents.find((item) => item.agent_name === match[1]);
    if (!agent) return notFound(res, 'AGENT_NOT_FOUND', 'Agent not found');
    return sendJson(res, 200, agent.configuration);
  }
  match = urlPath.match(/^\/api\/v1\/agents\/([^/]+)\/models$/);
  if (match && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const agent = data.agents.find((item) => item.agent_name === match[1]);
    if (!agent) return notFound(res, 'AGENT_NOT_FOUND', 'Agent not found');
    return sendJson(res, 200, { agent_name: match[1], models: [] });
  }

  // ---- capabilities ----
  if (urlPath === '/api/v1/capabilities/policy' && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.capability_policy || {});
  }
  if (urlPath === '/api/v1/mcp-servers' && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.mcp_servers);
  }
  if (urlPath === '/api/v1/skills' && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.skills);
  }
  if (urlPath === '/api/v1/credentials' && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.credentials);
  }
  if (urlPath === '/api/v1/model-providers' && method === 'GET') {
    if (!hasPermission(user, 'agent:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.model_providers);
  }

  // ---- collaboration / operations / traces ----
  if (urlPath === '/api/v1/collaboration/rules' && method === 'GET') {
    if (!hasPermission(user, 'task:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.collaboration_rules || {});
  }
  if (urlPath === '/api/v1/operations/summary' && method === 'GET') {
    if (!hasPermission(user, 'operations:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    return sendJson(res, 200, data.operations_summary || {
      total_tasks: 0, status_counts: {}, active_tasks: 0, pending_approvals: 0,
      model_calls: { total: 0, live: 0, simulated: 0, cost: 0 },
      tool_calls: { total: 0, denied: 0 },
    });
  }
  if (urlPath === '/api/v1/audit-logs' && method === 'GET') {
    if (!hasPermission(user, 'audit:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const records = filterAuditLogs(data, params);
    const { page, total } = paginate(records, params);
    return sendJson(res, 200, page, { 'X-Total-Count': String(total) });
  }
  match = urlPath.match(/^\/api\/v1\/traces\/([^/]+)$/);
  if (match && method === 'GET') {
    if (!hasPermission(user, 'task:read')) return sendError(res, 403, 'PERMISSION_DENIED', 'You do not have permission to perform this action');
    const trace = data.traces[match[1]];
    if (!trace) return notFound(res, 'TRACE_NOT_FOUND', 'Trace not found');
    return sendJson(res, 200, trace);
  }

  // ---- everything else: non-GET on /api/v1 → read-only 501; unknown GET → 404 ----
  if (urlPath.startsWith('/api/v1/') && method !== 'GET') return readOnly(res);
  return notFound(res, 'API_NOT_FOUND', 'Endpoint not found');
}
