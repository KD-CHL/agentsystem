// Users + sessions store (mirrors learngit's server/db.js, adapted to the
// agentsystem user shape). Cloud mode: full-dataset hydrate per request with
// dirty-flagged persist chained before the response flushes. Local mode:
// write-through JSON files so the API layer can be exercised without Vercel.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { kvGet, kvSet, useCloud } from './kv.js';

const R_USERS = 'agentsystem:users';
const R_SESSIONS = 'agentsystem:sessions';
const SESSION_TTL_MS = 7 * 24 * 3600 * 1000; // 7 days

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = process.env.AGENTSYSTEM_DATA_DIR || path.join(__dirname, '..', '.api-data');

let users = [];
let sessions = {};
let usersDirty = false;
let sessionsDirty = false;
let loaded = false;

// --- password hashing (scrypt + random salt, timing-safe compare) ---

export function hashPassword(password, salt) {
  salt = salt || crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(String(password), salt, 64).toString('hex');
  return { salt, hash };
}

export function verifyPassword(password, salt, hash) {
  const { hash: candidate } = hashPassword(password, salt);
  const a = Buffer.from(candidate, 'hex');
  const b = Buffer.from(hash, 'hex');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// --- users ---

function saveUsers() {
  usersDirty = true;
  if (!useCloud) writeLocal('users.json', users);
}

function saveSessions() {
  sessionsDirty = true;
  if (!useCloud) writeLocal('sessions.json', sessions);
}

function writeLocal(file, data) {
  try {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.writeFileSync(path.join(DATA_DIR, file), JSON.stringify(data, null, 2));
  } catch (err) {
    console.error('[agentsystem] local write failed:', err.message);
  }
}

function readLocal(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), 'utf8'));
  } catch {
    return fallback;
  }
}

export function createUser(username, password, role = 'viewer', displayName) {
  const { salt, hash } = hashPassword(password);
  const now = new Date().toISOString();
  const user = {
    id: 'user_' + crypto.randomBytes(8).toString('hex'),
    tenant_id: 'default',
    username: String(username),
    display_name: displayName || String(username),
    role,
    status: 'active',
    created_at: now,
    updated_at: now,
    last_login_at: null,
    github_id: null,
    salt,
    hash,
  };
  users.push(user);
  saveUsers();
  return user;
}

export function createGithubUser(username, githubId) {
  // GitHub users get an unguessable random password — password login is impossible.
  const user = createUser(username, crypto.randomBytes(24).toString('hex'), 'viewer', username);
  user.github_id = githubId;
  saveUsers();
  return user;
}

export function findUserByUsername(username) {
  const needle = String(username || '').toLowerCase();
  return users.find((u) => u.username.toLowerCase() === needle) || null;
}

export function findUserById(id) {
  return users.find((u) => u.id === id) || null;
}

export function findUserByGithubId(githubId) {
  return users.find((u) => u.github_id === githubId) || null;
}

export function updateUser(id, patch) {
  const user = findUserById(id);
  if (!user) return null;
  Object.assign(user, patch, { updated_at: new Date().toISOString() });
  saveUsers();
  return user;
}

export function listUsers() {
  return users;
}

export function publicUser(user) {
  if (!user) return null;
  const { salt, hash, github_id, ...rest } = user;
  return rest;
}

// --- sessions (token → { userId, expires }) ---

export function createSession(userId, ttlMs = SESSION_TTL_MS) {
  const token = crypto.randomBytes(32).toString('hex');
  sessions[token] = { userId, expires: Date.now() + ttlMs };
  saveSessions();
  return token;
}

export function getSession(token) {
  const session = sessions[token];
  if (!session) return null;
  if (session.expires < Date.now()) {
    delete sessions[token];
    saveSessions();
    return null;
  }
  return session;
}

export function destroySession(token) {
  if (sessions[token]) {
    delete sessions[token];
    saveSessions();
  }
}

function pruneSessions() {
  const now = Date.now();
  let changed = false;
  for (const [token, session] of Object.entries(sessions)) {
    if (session.expires < now) {
      delete sessions[token];
      changed = true;
    }
  }
  if (changed) saveSessions();
}

// --- bootstrap admin ---

function seedAdminIfNeeded() {
  if (users.some((u) => u.role === 'admin')) return;
  const username = process.env.AGENTSYSTEM_BOOTSTRAP_ADMIN_USERNAME || 'admin';
  let password = process.env.AGENTSYSTEM_BOOTSTRAP_ADMIN_PASSWORD || '';
  if (!password) {
    password = 'admin12345678';
    console.warn('[agentsystem] AGENTSYSTEM_BOOTSTRAP_ADMIN_PASSWORD not set — seeding INSECURE default admin password. Set the env var!');
  }
  const admin = createUser(username, password, 'admin', 'Cloud Administrator');
  admin.created_at = new Date().toISOString();
  console.log('[agentsystem] bootstrap admin created:', username);
}

// --- serverless lifecycle ---

export async function hydrate() {
  if (loaded && useCloud) {
    // Warm instance: re-read every request so other instances' writes are seen.
    usersDirty = false;
    sessionsDirty = false;
  }
  if (!useCloud) {
    if (!loaded) {
      users = readLocal('users.json', []);
      sessions = readLocal('sessions.json', {});
      loaded = true;
    }
  } else {
    users = (await kvGet(R_USERS)) || [];
    sessions = (await kvGet(R_SESSIONS)) || {};
    loaded = true;
  }
  seedAdminIfNeeded();
  pruneSessions();
}

export async function persist() {
  if (!useCloud) return; // local mode already wrote through
  if (usersDirty) {
    await kvSet(R_USERS, users);
    usersDirty = false;
  }
  if (sessionsDirty) {
    await kvSet(R_SESSIONS, sessions);
    sessionsDirty = false;
  }
}
