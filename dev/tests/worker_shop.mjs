// Offline checks of worker.js's /shop/rakuten (Rakuten Books' API answered from a fixture).
// Run: node dev/tests/worker_shop.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const src = readFileSync(fileURLToPath(new URL('../../worker.js', import.meta.url)), 'utf8');
const worker = (await import('data:text/javascript,' + encodeURIComponent(src))).default;

const sent = [];
let reply = { status: 200, body: {} };
globalThis.fetch = async (url, init) => {
  sent.push({ url: new URL(url), init });
  return new Response(JSON.stringify(reply.body), { status: reply.status, headers: { 'Content-Type': 'application/json' } });
};
const env = { RAKUTEN_APP_ID: 'app-id', RAKUTEN_ACCESS_KEY: 'access-key', ASSETS: { fetch: async () => new Response('x') } };
const ask = async (q, e = env) => {
  const res = await worker.fetch(new Request('https://warujie.jp/shop/rakuten' + q), e);
  return { status: res.status, cache: res.headers.get('Cache-Control'), body: await res.json() };
};
const item = (title, price, extra = {}) => ({ title, itemPrice: price, itemUrl: 'https://books.rakuten.co.jp/rb/1/', largeImageUrl: 'https://thumbnail.image.rakuten.co.jp/a.jpg', salesDate: '2026年11月中旬', availability: '5', ...extra });

let pass = 0, fail = 0;
const check = (label, ok, detail) => { if (ok) pass++; else fail++; console.log((ok ? 'PASS ' : 'FAIL ') + label + (ok || detail === undefined ? '' : `   [${JSON.stringify(detail)}]`)); };

let r = await ask('?kind=sl', {});
check('no keys yet: answers not-configured, asks nobody', r.body.ok === false && r.body.reason === 'not-configured' && !sent.length, r);
r = await ask('?kind=anything');
check('only the fixed searches: anything else is refused, Rakuten not asked', r.status === 400 && !sent.length, r);

reply = { status: 200, body: { Items: [
  item('マジック：ザ・ギャザリング Secret Lair x Hatsune Miku 日本語版', 6600),
  item('ポケモンカード Secret Lair', 5000),
  item('マジック：ザ・ギャザリング プレイマット', 3000),
  item('マジック：ザ・ギャザリング Secret Lair elsewhere', 5000, { itemUrl: 'https://example.com/x' }),
  item('マジック：ザ・ギャザリング Secret Lair bad picture', 5000, { largeImageUrl: 'https://example.com/a.jpg', affiliateUrl: 'https://hb.afl.rakuten.co.jp/hgc/x/?pc=y' }),
] } };
r = await ask('?kind=sl&aff=1a2b3c4d.5e6f7a8b');
const q = sent[0].url.searchParams;
check('asks Books Total Search on openapi.rakuten.co.jp with both keys, the games genre, newest first',
  sent[0].url.origin + sent[0].url.pathname === 'https://openapi.rakuten.co.jp/services/api/BooksTotal/Search/20170404'
  && q.get('applicationId') === 'app-id' && q.get('accessKey') === 'access-key' && q.get('booksGenreId') === '006'
  && q.get('sort') === '-releaseDate' && q.get('keyword') === 'ギャザリング Secret Lair' && q.get('formatVersion') === '2', String(sent[0].url));
check('passes the affiliate ID on', q.get('affiliateId') === '1a2b3c4d.5e6f7a8b');
check('sends the registered site as Referer and Origin', sent[0].init.headers.Referer === 'https://warujie.jp/' && sent[0].init.headers.Origin === 'https://warujie.jp');
check('keeps Rakuten\'s answer an hour at Cloudflare', sent[0].init.cf && sent[0].init.cf.cacheTtlByStatus['200-299'] === 3600);
check('keeps only Magic Secret Lairs with Rakuten links; the affiliate link wins; a picture from elsewhere is dropped',
  r.body.ok && r.body.items.length === 2 && r.body.items[0].price === 6600 && r.body.items[0].avail === '5' && r.body.items[0].date === '2026年11月中旬'
  && r.body.items[1].url.startsWith('https://hb.afl.rakuten.co.jp/') && r.body.items[1].image === '', r.body);
check('never sends the keys back', !JSON.stringify(r.body).includes('access-key') && !JSON.stringify(r.body).includes('app-id'));
check('visitors\' browsers keep it half an hour', r.cache === 'public, max-age=1800', r.cache);

sent.length = 0;
reply = { status: 200, body: { items: [
  { item: item('マジック：ザ・ギャザリング ローウィンの昏明 プレイ・ブースター 日本語版', 17867) },
  item('マジック：ザ・ギャザリング ローウィンの昏明 プレイ・ブースター 日本語版 1パック', 650),
  item('マジック：ザ・ギャザリング ローウィンの昏明 バンドル', 9000),
  item('マジック：ザ・ギャザリング ローウィンの昏明 コレクター・ブースター 日本語版 BOX', 36000),
  // a real Rakuten Books title (books.rakuten.co.jp/rb/18155696/), 30 packs: a box, not "1パック"
  item('『マジック：ザ・ギャザリングーーFINAL FANTASY』 プレイ・ブースター 日本語版 【30パック入りBOX】【クレジットカード決済限定】', 21421),
  item('マジック：ザ・ギャザリング プレイ・ブースター 【１パック】', 650),
] } };
r = await ask('?kind=box&set=' + encodeURIComponent('ローウィンの昏明<script>'));
check('boxes of one set: searched by its name (odd characters dropped), formatVersion 1 or 2 both read',
  sent[0].url.searchParams.get('keyword') === 'ギャザリング ローウィンの昏明script ブースター' && r.body.items.length === 3, [sent[0].url.searchParams.get('keyword'), r.body]);
check('a single pack and a bundle are not boxes; a 30-pack box is', r.body.items.every(i => i.price >= 8000) && r.body.items.some(i => i.title.includes('30パック入りBOX')), r.body.items.map(i => i.title));
sent.length = 0;
await ask('?kind=box&aff=' + encodeURIComponent('bad id!'));
check('a malformed affiliate ID is not passed on', !sent[0].url.searchParams.has('affiliateId'));

reply = { status: 404, body: { error: 'not_found' } };
r = await ask('?kind=sl');
check('Rakuten finds nothing: an empty list', r.body.ok === true && r.body.items.length === 0, r.body);
reply = { status: 429, body: { error: 'too_many_requests' } };
r = await ask('?kind=sl');
check('Rakuten busy: says so, kept only two minutes', r.body.ok === false && r.body.reason === 'rakuten-429' && r.cache === 'public, max-age=120', r);

console.log(`\n${pass}/${pass + fail} checks passed`);
if (fail) process.exit(1);
