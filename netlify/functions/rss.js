// HTDI RSS Proxy — Netlify Function
// Проксирует RSS/Atom фиды, обходя CORS. Кэш 5 мин.

exports.handler = async (event) => {
  const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET' };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: CORS, body: '' };
  }

  const rawUrl = event.queryStringParameters?.url;
  if (!rawUrl) {
    return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'Missing url' }) };
  }

  let parsed;
  try { parsed = new URL(rawUrl); } catch {
    return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'Invalid URL' }) };
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    return { statusCode: 403, headers: CORS, body: JSON.stringify({ error: 'Protocol not allowed' }) };
  }

  try {
    const resp = await fetch(rawUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8,de;q=0.7',
      },
      redirect: 'follow',
      signal: AbortSignal.timeout(9000),
    });

    if (!resp.ok) {
      return { statusCode: resp.status, headers: CORS, body: JSON.stringify({ error: `Upstream ${resp.status}` }) };
    }

    const body = await resp.text();
    const ct = resp.headers.get('content-type') || 'application/xml';

    return {
      statusCode: 200,
      headers: {
        ...CORS,
        'Content-Type': ct,
        'Cache-Control': 'public, s-maxage=300, max-age=60',
      },
      body,
    };
  } catch (e) {
    return { statusCode: 502, headers: CORS, body: JSON.stringify({ error: e.message }) };
  }
};
