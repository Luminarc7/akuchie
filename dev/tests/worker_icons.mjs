// Offline checks of worker.js's test-site icon: the test sites get the pink app icon, warujie.jp
// keeps the green one, and every icon file the pages and manifests name exists.
// Run: node dev/tests/worker_icons.mjs
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
const src = readFileSync(root + 'worker.js', 'utf8');
const html = readFileSync(root + 'index.html', 'utf8');

// Node has no HTMLRewriter: this stand-in runs the Worker's handlers on the page's <link> tags.
globalThis.HTMLRewriter = class {
  constructor() { this.rules = []; }
  on(selector, handler) { this.rules.push([selector, handler]); return this; }
  transform(res) {
    const rules = this.rules;
    const body = res.text().then(text => text.replace(/<link\b[^>]*>/g, tag => {
      const rel = (tag.match(/\brel="([^"]*)"/) || [])[1];
      for (const [selector, handler] of rules) {
        if (selector !== `link[rel="${rel}"]`) continue;
        const el = {
          getAttribute: (a) => (tag.match(new RegExp(`\\b${a}="([^"]*)"`)) || [])[1] ?? null,
          setAttribute: (a, v) => { tag = tag.replace(new RegExp(`\\b${a}="[^"]*"`), `${a}="${v}"`); },
        };
        handler.element(el);
      }
      return tag;
    }));
    return new Response(new ReadableStream({ async start(c) { c.enqueue(new TextEncoder().encode(await body)); c.close(); } }),
      { status: res.status, headers: res.headers });
  }
};
const worker = (await import('data:text/javascript,' + encodeURIComponent(src))).default;
const env = { ASSETS: { fetch: async () => new Response(html, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } }) } };
const page = async (host) => {
  const res = await worker.fetch(new Request(`https://${host}/`, { headers: { 'Accept-Encoding': 'identity' } }), env);
  const text = await res.text();
  const href = (rel) => (text.match(new RegExp(`<link[^>]*rel="${rel}"[^>]*href="([^"]*)"`)) || [])[1];
  return { icon: href('icon'), apple: href('apple-touch-icon'), manifest: href('manifest') };
};

let pass = 0, fail = 0;
const check = (label, ok, detail) => { if (ok) pass++; else fail++; console.log((ok ? 'PASS ' : 'FAIL ') + label + (ok || detail === undefined ? '' : `   [${JSON.stringify(detail)}]`)); };

for (const host of ['warujie.jp', 'www.warujie.jp', 'warujie.warujie-mtg.workers.dev']) {
  const p = await page(host);
  check(`${host}: the green icon and the usual manifest`,
    /-v\d+\.png$/.test(p.icon) && !/test/.test(p.icon + p.apple) && p.manifest === 'manifest.webmanifest', p);
}
for (const host of ['staging-warujie.warujie-mtg.workers.dev', 'backup-2026-10-17-before-x-warujie.warujie-mtg.workers.dev']) {
  const p = await page(host);
  check(`${host}: the pink icon and the test manifest`,
    /-v\d+-test\.png$/.test(p.icon) && /-v\d+-test\.png$/.test(p.apple) && p.manifest === 'manifest-test.webmanifest', p);
  check(`${host}: the pink files exist`, [p.icon, p.apple, p.manifest].every(f => existsSync(root + f)), p);
}
const green = await page('warujie.jp');
check('the green files exist', [green.icon, green.apple, green.manifest].every(f => existsSync(root + f)), green);
for (const m of ['manifest.webmanifest', 'manifest-test.webmanifest']) {
  const icons = JSON.parse(readFileSync(root + m, 'utf8')).icons;
  check(`${m}: every icon it names exists`, icons.length >= 3 && icons.every(i => existsSync(root + i.src)), icons);
  check(`${m}: ${m.includes('test') ? 'only pink' : 'no pink'} icons`, icons.every(i => /-test\.png$/.test(i.src) === m.includes('test')), icons);
}
const sw = readFileSync(root + 'sw.js', 'utf8');
check('sw.js keeps an icon that exists', [...sw.matchAll(/'\/(icons\/[^']+)'/g)].every(m => existsSync(root + m[1])));

console.log(`\n${pass}/${pass + fail} checks passed`);
if (fail) process.exit(1);
