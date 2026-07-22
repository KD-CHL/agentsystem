// GitHub repo data store backed by the Contents API (mirrors learngit's
// server/github-store.js). Each key becomes a JSON file in a private repo;
// updates carry the blob sha for optimistic concurrency with one retry.
// Requires global fetch (undici) — raw node:http is blocked by GitHub's WAF.

const API_BASE = process.env.GITHUB_API_BASE || 'https://api.github.com';
const OWNER = process.env.GITHUB_DATA_OWNER || 'KD-CHL';
const REPO = process.env.GITHUB_DATA_REPO || 'agentsystem-data';
const BRANCH = process.env.GITHUB_DATA_BRANCH || 'main';

const shaCache = new Map(); // key → last read/written blob sha (warm instances only)

function auth() {
  return {
    Authorization: 'Bearer ' + process.env.GITHUB_DATA_TOKEN,
    Accept: 'application/vnd.github+json',
    'User-Agent': 'agentsystem-serverless',
    'Content-Type': 'application/json',
  };
}

// 'agentsystem:users' → 'agentsystem-users.json' (avoid ':' in filenames)
function fileOf(key) {
  return encodeURIComponent(key.replace(/:/g, '-')) + '.json';
}

function apiUrl(key) {
  return `${API_BASE}/repos/${OWNER}/${REPO}/contents/${fileOf(key)}?ref=${BRANCH}`;
}

async function ghJson(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* tolerate non-JSON */ }
  return { status: res.status, data };
}

export async function ghGet(key) {
  const res = await ghJson(apiUrl(key), { headers: auth() });
  if (res.status === 404) return null;
  if (res.status !== 200) throw new Error('GitHub store read failed (' + res.status + ')');
  if (res.data && res.data.sha) shaCache.set(key, res.data.sha);
  const content = (res.data && res.data.content) || '';
  return JSON.parse(Buffer.from(content, 'base64').toString('utf8'));
}

export async function ghSet(key, value) {
  const body = {
    message: 'chore(data): update ' + fileOf(key),
    content: Buffer.from(JSON.stringify(value)).toString('base64'),
    branch: BRANCH,
  };
  const cached = shaCache.get(key);
  if (cached) body.sha = cached; // required for updates

  let res = await ghJson(apiUrl(key), { method: 'PUT', headers: auth(), body: JSON.stringify(body) });
  if (res.status === 422 || res.status === 409) {
    // Stale sha (concurrent writer) — refetch the latest sha and retry once
    // (last writer wins, matching whole-key SET semantics).
    const current = await ghJson(apiUrl(key), { headers: auth() });
    if (current.status === 200 && current.data && current.data.sha) {
      body.sha = current.data.sha;
      res = await ghJson(apiUrl(key), { method: 'PUT', headers: auth(), body: JSON.stringify(body) });
    }
  }
  if (res.status !== 200 && res.status !== 201) {
    throw new Error('GitHub store write failed (' + res.status + ')');
  }
  const newSha = res.data && res.data.content && res.data.content.sha;
  if (newSha) shaCache.set(key, newSha);
}
