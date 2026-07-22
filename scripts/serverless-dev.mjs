#!/usr/bin/env node
// Local dev server for the serverless API layer (mirrors learngit's server.js).
// Runs the exact same handler Vercel uses, in local file-storage mode:
//   node scripts/serverless-dev.mjs            # PORT=8787
// Users/sessions persist to frontend/api/.api-data/*.json.
import http from 'node:http';
import handler from '../frontend/api/index.js';

const PORT = Number(process.env.PORT || 8787);

const server = http.createServer((req, res) => {
  // CORS for local cross-port development (e.g. Vite on :5173).
  const origin = req.headers.origin;
  if (origin) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Idempotency-Key, X-Request-ID');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  }
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }
  Promise.resolve(handler(req, res)).catch((err) => {
    console.error('[serverless-dev] crash:', err);
    if (!res.headersSent) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: { code: 'INTERNAL_ERROR', message: err.message } }));
    }
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[serverless-dev] agentsystem cloud API on http://127.0.0.1:${PORT} (file mode, data in frontend/api/.api-data/)`);
});
