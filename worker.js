// warujie.jp: serves the site's files as they are (Cloudflare Workers static assets).
//
// Only two kinds of request pass through here:
// - The HTML pages go out compressed by this Worker and marked "no-transform", so
//   Cloudflare does not add its own scripts to them (the Web Analytics beacon, the
//   bot-detection script): the site promises no analytics. ("no-transform" alone
//   would also stop Cloudflare compressing the page, 3.5x bigger.)
// - /ja_cards.json, the card database: sent brotli-compressed (ja_cards.json.br, made
//   at deploy by tools/brotli_db.mjs, about half the size of the .gz), or as the .gz
//   to a browser without brotli. The browser unpacks either one itself.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/ja_cards.json') return cardDatabase(request, env, url);
    const res = await env.ASSETS.fetch(request);
    const type = res.headers.get('Content-Type') || '';
    if (!type.startsWith('text/html')) return res;
    const headers = new Headers(res.headers);
    headers.set('Cache-Control', 'public, max-age=0, must-revalidate, no-transform');
    const etag = headers.get('ETag');
    if (etag && !etag.startsWith('W/')) headers.set('ETag', 'W/' + etag);   // the compressed bytes differ from the file
    if (!res.body || !accepts(request, 'gzip')) {
      return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
    }
    headers.set('Content-Encoding', 'gzip');
    headers.delete('Content-Length');
    headers.append('Vary', 'Accept-Encoding');
    return new Response(res.body.pipeThrough(new CompressionStream('gzip')),
      { status: res.status, statusText: res.statusText, headers, encodeBody: 'manual' });
  },
};

function accepts(request, encoding) {
  const accept = (request.cf && request.cf.clientAcceptEncoding) || request.headers.get('Accept-Encoding') || '';
  return new RegExp(`(^|[\\s,])${encoding}(\\s*(;\\s*q=(?!0(\\.0*)?\\b)[\\d.]+)?)?\\s*(,|$)`, 'i').test(accept);
}

async function cardDatabase(request, env, url) {
  for (const [encoding, file] of [['br', '/ja_cards.json.br'], ['gzip', '/ja_cards.json.gz']]) {
    if (!accepts(request, encoding)) continue;
    const res = await env.ASSETS.fetch(new Request(new URL(file, url), request));
    if (res.status === 404) continue;
    const headers = new Headers(res.headers);
    headers.set('Content-Type', 'application/json; charset=utf-8');
    headers.set('Cache-Control', 'public, max-age=0, must-revalidate, no-transform');
    headers.append('Vary', 'Accept-Encoding');
    if (!res.body || res.status === 304) return new Response(null, { status: res.status, statusText: res.statusText, headers });
    headers.set('Content-Encoding', encoding);
    return new Response(res.body, { status: res.status, statusText: res.statusText, headers, encodeBody: 'manual' });
  }
  return new Response('not found', { status: 404 });
}
