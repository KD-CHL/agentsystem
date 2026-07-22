// GitHub OAuth code exchange (mirrors learngit's server/github.js).
// Must use global fetch (undici): raw node:http is blocked by GitHub's WAF.

export const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID || '';
export const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET || '';

export const githubEnabled = () => Boolean(GITHUB_CLIENT_ID && GITHUB_CLIENT_SECRET);

async function ghJson(url, options = {}) {
  const headers = {
    'User-Agent': 'agentsystem-serverless',
    Accept: 'application/vnd.github+json',
    ...(options.headers || {}),
  };
  const res = await fetch(url, { ...options, headers });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* tolerate non-JSON */ }
  return { status: res.status, data };
}

export async function exchangeCode(code) {
  const res = await ghJson('https://github.com/login/oauth/access_token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: GITHUB_CLIENT_ID,
      client_secret: GITHUB_CLIENT_SECRET,
      code,
    }),
  });
  if (res.status !== 200 || !res.data || !res.data.access_token) {
    const detail = (res.data && (res.data.error_description || res.data.error)) || ('HTTP ' + res.status);
    throw new Error('GitHub token exchange failed: ' + detail);
  }
  return res.data.access_token;
}

export async function fetchGithubUser(accessToken) {
  const res = await ghJson('https://api.github.com/user', {
    headers: { Authorization: 'Bearer ' + accessToken },
  });
  if (res.status !== 200 || !res.data || !res.data.login) {
    throw new Error('GitHub profile fetch failed (HTTP ' + res.status + ')');
  }
  return res.data; // { id, login, name, avatar_url, ... }
}
