// Vercel Functions entry point (mirrors learngit's api/index.js):
// hydrate → route → persist, with persist() chained BEFORE the response
// flushes because serverless instances may freeze right after res.end().
import { hydrate as hydrateAuth, persist } from './lib/auth-db.js';
import { hydrateData } from './lib/data-store.js';
import { handleApi, sendJson } from './lib/routes.js';
import { useCloud } from './lib/kv.js';

export const config = {
  api: { bodyParser: false, externalResolver: true },
};

export default async function handler(req, res) {
  // Cloud guard: on Vercel with no storage backend configured, refuse instead
  // of silently falling back to file mode on the read-only filesystem.
  if (process.env.VERCEL && !useCloud) {
    sendJson(res, 503, {
      error: {
        code: 'STORAGE_NOT_CONFIGURED',
        message: 'Cloud storage is not configured. Set GITHUB_DATA_TOKEN (or UPSTASH_REDIS_REST_URL/TOKEN) on this Vercel project.',
        details: {},
      },
    });
    return;
  }

  let endPromise = null;
  const origEnd = res.end.bind(res);
  res.end = function patchedEnd(...args) {
    if (!endPromise) {
      endPromise = persist()
        .catch((err) => console.error('[agentsystem] persist failed:', err.message))
        .then(() => origEnd(...args));
    }
    return res;
  };

  try {
    await hydrateAuth();
    await hydrateData();
    const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
    await handleApi(req, res, urlPath);
  } catch (err) {
    console.error('[agentsystem] handler error:', err);
    if (!res.headersSent) {
      sendJson(res, 500, { error: { code: 'INTERNAL_ERROR', message: 'Internal server error', details: {} } });
    } else {
      res.end();
    }
  }

  // Fallback: even if the route never called res.end, still flush writes.
  if (endPromise) await endPromise;
  else await persist().catch(() => {});
}
