// warujie.jp: serves the site's files as they are (Cloudflare Workers static assets).
//
// Only the HTML pages pass through here. They go out compressed by this Worker and
// marked "no-transform", so Cloudflare does not add its own scripts to them (the Web
// Analytics beacon, the bot-detection script): the site promises no analytics.
// ("no-transform" alone would also stop Cloudflare compressing the page, 3.5x bigger.)
export default {
  async fetch(request, env) {
    const res = await env.ASSETS.fetch(request);
    const type = res.headers.get('Content-Type') || '';
    if (!type.startsWith('text/html')) return res;
    const headers = new Headers(res.headers);
    headers.set('Cache-Control', 'public, max-age=0, must-revalidate, no-transform');
    const etag = headers.get('ETag');
    if (etag && !etag.startsWith('W/')) headers.set('ETag', 'W/' + etag);   // the compressed bytes differ from the file
    const accept = (request.cf && request.cf.clientAcceptEncoding) || request.headers.get('Accept-Encoding') || '';
    if (!res.body || !/\bgzip\b/i.test(accept)) {
      return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
    }
    headers.set('Content-Encoding', 'gzip');
    headers.delete('Content-Length');
    headers.append('Vary', 'Accept-Encoding');
    return new Response(res.body.pipeThrough(new CompressionStream('gzip')),
      { status: res.status, statusText: res.statusText, headers, encodeBody: 'manual' });
  },
};
