// Storage dispatcher (mirrors learngit's server/kv.js):
// Upstash Redis → GitHub repo store. Local file mode is handled directly in
// auth-db.js (write-through JSON files) and never reaches this module.
import { ghGet, ghSet } from './github-store.js';

export const useRedis = Boolean(process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN);
export const useGithubStore = !useRedis && Boolean(process.env.GITHUB_DATA_TOKEN);
export const useCloud = useRedis || useGithubStore;

let redis = null;

async function redisClient() {
  if (!redis) {
    // String concatenation defeats static bundler resolution so the optional
    // dependency is only loaded when Redis is actually configured.
    const mod = await import('@upstash/' + 'redis');
    redis = mod.Redis.fromEnv();
  }
  return redis;
}

async function redisGet(key) {
  const client = await redisClient();
  const value = await client.get(key);
  return value === undefined ? null : value;
}

async function redisSet(key, value) {
  const client = await redisClient();
  await client.set(key, value);
}

export function kvGet(key) {
  return useRedis ? redisGet(key) : ghGet(key);
}

export function kvSet(key, value) {
  return useRedis ? redisSet(key, value) : ghSet(key);
}
