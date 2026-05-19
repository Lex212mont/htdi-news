// Cloudflare Pages _worker.js — RSS Proxy + Static Assets
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // RSS proxy endpoint
    if (url.pathname === '/api/rss') {
      const CORS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
      };

      if (request.method === 'OPTIONS') {
        return new Response(null, { status: 200, headers: CORS });
      }

      const rawUrl = url.searchParams.get('url');
      if (!rawUrl) {
        return new Response(JSON.stringify({ error: 'Missing url' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });
      }

      let parsed;
      try { parsed = new URL(rawUrl); } catch {
        return new Response(JSON.stringify({ error: 'Invalid URL' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });
      }

      if (!['http:', 'https:'].includes(parsed.protocol)) {
        return new Response(JSON.stringify({ error: 'Protocol not allowed' }), { status: 403, headers: { ...CORS, 'Content-Type': 'application/json' } });
      }

      try {
        const resp = await fetch(rawUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
          },
          signal: AbortSignal.timeout(9000),
        });

        if (!resp.ok) {
          return new Response(JSON.stringify({ error: `Upstream ${resp.status}` }), { status: resp.status, headers: { ...CORS, 'Content-Type': 'application/json' } });
        }

        const body = await resp.text();
        const ct = resp.headers.get('content-type') || 'application/xml';

        return new Response(body, {
          status: 200,
          headers: { ...CORS, 'Content-Type': ct, 'Cache-Control': 'public, s-maxage=300, max-age=60' },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 502, headers: { ...CORS, 'Content-Type': 'application/json' } });
      }
    }

    // All other requests → serve static assets
    return env.ASSETS.fetch(request);
  },
};
