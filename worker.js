// warujie.jp: serves the site's files as they are (Cloudflare Workers static assets).
//
// Only these requests pass through here:
// - The HTML pages go out compressed by this Worker and marked "no-transform", so
//   Cloudflare does not add its own scripts to them (the Web Analytics beacon, the
//   bot-detection script): the site promises no analytics. ("no-transform" alone
//   would also stop Cloudflare compressing the page, 3.5x bigger.)
// - Link previews: when LINE, X, Discord, Slack, a search engine... asks for a card's
//   or a deck's page, its title, text and picture are written into the page's share
//   tags (og:…), so the shared link shows that card. People get the page unchanged.
// - /ja_cards.json, the card database: sent brotli-compressed (ja_cards.json.br, made
//   at deploy by tools/brotli_db.mjs, about half the size of the .gz), or as the .gz
//   to a browser without brotli. The browser unpacks either one itself.
// - /shop/rakuten: Secret Lairs and booster boxes on sale at Rakuten Books (楽天ブックス),
//   asked from Rakuten's API here (the keys are Cloudflare secrets) and kept an hour.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/ja_cards.json') return cardDatabase(request, env, url);
    if (url.pathname === '/shop/rakuten') return rakutenItems(env, url);
    let res = await env.ASSETS.fetch(request);
    const type = res.headers.get('Content-Type') || '';
    if (!type.startsWith('text/html')) return res;
    if (res.status === 200 && isPreviewBot(request) && url.search) {
      try {
        const tags = await shareTags(url, env);
        if (tags) res = rewriteTags(res, tags);
      } catch (err) { /* the page's own tags stay */ }
    }
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

// ---- Rakuten Books (楽天ブックス): Secret Lairs and booster boxes for sale ---------------------
// GET /shop/rakuten?kind=sl                  Secret Lair products, newest first
// GET /shop/rakuten?kind=box[&set=<name>]    booster boxes (of one set, by its Japanese name)
//     [&aff=<Rakuten affiliate ID>]          links come back as Rakuten Affiliate links
// Answers { ok, items: [{ title, price, url, image, date, avail }] }, or ok: false with a
// reason ("not-configured" until the two secrets RAKUTEN_APP_ID and RAKUTEN_ACCESS_KEY are set
// in Cloudflare). Only these fixed searches can be asked for, so nobody can use our API quota
// for anything else, and each answer is kept an hour so Rakuten is asked rarely.
const RAKUTEN_API = 'https://openapi.rakuten.co.jp/services/api/BooksTotal/Search/20170404';
const RAKUTEN_SITE = 'https://warujie.jp/';   // the site registered with the app (its "allowed website")
const RAKUTEN_HOSTS = /^https:\/\/(books\.rakuten\.co\.jp|hb\.afl\.rakuten\.co\.jp|thumbnail\.image\.rakuten\.co\.jp)\//;
async function rakutenItems(env, url) {
  const answer = (obj, status = 200, maxAge = 600) => new Response(JSON.stringify(obj), {
    status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': `public, max-age=${maxAge}` },
  });
  const p = url.searchParams;
  const kind = p.get('kind');
  const set = clip(p.get('set'), 40).replace(/[^\p{L}\p{N}\s:：・'’&!-]/gu, '');
  const aff = /^[0-9a-f.]{8,80}$/i.test(p.get('aff') || '') ? p.get('aff') : '';
  if (kind !== 'sl' && kind !== 'box') return answer({ ok: false, reason: 'bad-request', items: [] }, 400);
  if (!env.RAKUTEN_APP_ID || !env.RAKUTEN_ACCESS_KEY) return answer({ ok: false, reason: 'not-configured', items: [] }, 200, 300);
  const api = new URL(RAKUTEN_API);
  api.search = new URLSearchParams({
    applicationId: env.RAKUTEN_APP_ID, accessKey: env.RAKUTEN_ACCESS_KEY, format: 'json', formatVersion: '2',
    keyword: kind === 'sl' ? 'ギャザリング Secret Lair' : `ギャザリング ${set} ブースター`.replace(/\s+/g, ' '),
    booksGenreId: '006', sort: '-releaseDate', hits: '30', ...(aff ? { affiliateId: aff } : {}),
  });
  let data;
  try {
    const res = await fetch(api, {
      headers: { Referer: RAKUTEN_SITE, Origin: RAKUTEN_SITE.slice(0, -1), 'User-Agent': 'Warujie/1.0 (+https://warujie.jp)', Accept: 'application/json' },
      cf: { cacheEverything: true, cacheTtlByStatus: { '200-299': 3600, '404': 3600 } },
    });
    if (res.status === 404) return answer({ ok: true, items: [] }, 200, 1800);
    if (!res.ok) return answer({ ok: false, reason: `rakuten-${res.status}`, items: [] }, 200, 120);
    data = await res.json();
  } catch (err) {
    return answer({ ok: false, reason: 'rakuten-unreachable', items: [] }, 200, 120);
  }
  const items = [];
  for (const raw of data.Items || data.items || []) {
    const it = raw.Item || raw.item || raw;
    const title = String(it.title || '');
    const price = Number(it.itemPrice) || 0;
    const link = String(it.affiliateUrl || it.itemUrl || '');
    if (!/ギャザリング|magic/i.test(title) || !price || !RAKUTEN_HOSTS.test(link)) continue;
    // a box, not one pack, a bundle or a deck (box titles often don't say "BOX")
    if (kind === 'box' && (!/ブースター|BOX|ボックス/i.test(title) || /バンドル|デッキ|(^|[^0-9０-９])[1１]パック|単品/.test(title) || price < 8000)) continue;
    if (kind === 'sl' && !/secret\s*lair|シークレット・?レイヤー/i.test(title)) continue;
    const image = String(it.largeImageUrl || it.mediumImageUrl || '');
    items.push({ title, price, url: link, image: RAKUTEN_HOSTS.test(image) ? image : '',
                 date: String(it.salesDate || ''), avail: String(it.availability || '') });
    if (items.length >= 12) break;
  }
  return answer({ ok: true, items }, 200, 1800);
}

// ---- link previews -------------------------------------------------------------------------
// The apps and search engines that read a page's share tags (people's browsers don't need them).
const PREVIEW_BOTS = /bot\b|bot\/|crawler|spider|slurp|facebookexternalhit|meta-externalagent|embedly|slack|discord|telegram|whatsapp|line\/|linespider|skype|pinterest|applebot|bingpreview|hatena|mastodon|misskey|cardyb|bluesky|google-inspectiontool|yandex|duckduck|baidu|naver|daum|iframely|vkshare|redditbot|quora link preview|preview/i;
function isPreviewBot(request) {
  return PREVIEW_BOTS.test(request.headers.get('User-Agent') || '');
}

const FORMAT_JA = { standard: 'スタンダード', pioneer: 'パイオニア', modern: 'モダン', legacy: 'レガシー', vintage: 'ヴィンテージ', pauper: 'パウパー' };
const SITE = '悪知恵（warujie）';
const clip = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };

async function scryfall(path) {
  const res = await fetch('https://api.scryfall.com' + path, {
    headers: { 'User-Agent': 'Warujie/1.0 (+https://warujie.jp)', Accept: 'application/json' },
    cf: { cacheTtl: 86400, cacheEverything: true },
  });
  return res.ok ? res.json() : null;
}

// title, description and picture for the page the URL points at (null: the site's own)
async function shareTags(url, env) {
  const p = url.searchParams;
  const pageUrl = url.origin + url.pathname + url.search;
  const id = p.get('card');
  if (id && /^[0-9a-f-]{36}$/i.test(id)) {
    const c = await scryfall(`/cards/${id}`);
    if (!c) return null;
    const faces = c.card_faces || [];
    const name = c.name || faces.map(f => f.name).join(' // ');
    const printed = c.printed_name || faces.map(f => f.printed_name).filter(Boolean).join(' // ');
    const text = c.printed_text || c.oracle_text || faces.map(f => f.printed_text || f.oracle_text || '').filter(Boolean).join(' / ');
    const type = c.printed_type_line || c.type_line || faces.map(f => f.printed_type_line || f.type_line || '').join(' // ');
    const img = (c.image_uris && c.image_uris.normal) || (faces[0] && faces[0].image_uris && faces[0].image_uris.normal) || '';
    return {
      title: `${printed && printed !== name ? `${printed}（${name}）` : name} | ${SITE}`,
      description: clip(`${type}。${text}`, 160),
      image: img, width: img ? '488' : '', height: img ? '680' : '', card: 'summary', url: pageUrl,
    };
  }
  const view = p.get('view');
  const format = (p.get('format') || '').toLowerCase();
  if (view === 'deck' && p.get('deck')) {
    const deck = p.get('deck');
    let facts = '';
    try {
      const meta = await (await env.ASSETS.fetch(new URL('/meta.json', url))).json();
      const days = p.get('days') || Object.keys(meta.windows || {}).sort((a, b) => a - b)[0];
      const a = ((((meta.windows || {})[days] || {}).formats || {})[format] || {}).archetypes || [];
      const row = a.find(x => x.name === deck);
      if (row) facts = `使用率 ${row.share.toFixed(1)}%（${row.decks}デッキ）` + (typeof row.winrate === 'number' && row.wins + row.losses >= 20 ? `・勝率 ${row.winrate.toFixed(1)}%` : '') + `（直近${days}日）。`;
    } catch (err) { /* without the numbers */ }
    return {
      title: `${deck} — ${FORMAT_JA[format] || format} のデッキ | ${SITE}`,
      description: clip(`${facts}大会で結果を出したサンプルリスト、よく使われるカード、使用率の推移。MTGアリーナ・MTGO形式でも書き出せます。`, 160),
      url: pageUrl,
    };
  }
  if (view === 'meta') {
    return { title: `メタゲーム — ${FORMAT_JA[format] || 'スタンダード'} | ${SITE}`, description: '大会結果から集計した、フォーマットごとのデッキの使用率・勝率・推移とサンプルリスト。', url: pageUrl };
  }
  if (view === 'import') {
    return { title: `デッキの価格を調べる | ${SITE}`, description: 'デッキリストを貼り付けると、いちばん安い版でそろえた金額を円で計算。MTGアリーナ・MTGOのリスト、日本語名・英語名どちらでも。', url: pageUrl };
  }
  if (view === 'prices') {
    return { title: `価格の動き | ${SITE}`, description: '値上がり・値下がりしたカード（米国・欧州の相場、円換算つき）。', url: pageUrl };
  }
  const set = p.get('set');
  if (set && /^[a-z0-9]{2,6}$/i.test(set)) {
    const s = await scryfall(`/sets/${set.toLowerCase()}`);
    if (s && s.name) return { title: `${s.name}（${s.code.toUpperCase()}）のカード一覧 | ${SITE}`, description: `${s.name} のカード${s.card_count ? ` ${s.card_count}枚` : ''}を日本語で。`, url: pageUrl };
  }
  return null;
}

function rewriteTags(res, tags) {
  const set = (value) => ({ element(el) { if (value !== undefined && value !== '') el.setAttribute('content', value); } });
  let rw = new HTMLRewriter()
    .on('title', { element(el) { el.setInnerContent(tags.title); } })
    .on('meta[property="og:title"]', set(tags.title))
    .on('meta[name="description"]', set(tags.description))
    .on('meta[property="og:description"]', set(tags.description))
    .on('meta[property="og:url"]', set(tags.url))
    .on('meta[name="twitter:card"]', set(tags.card));
  if (tags.image) {
    rw = rw.on('meta[property="og:image"]', set(tags.image))
      .on('meta[property="og:image:width"]', set(tags.width))
      .on('meta[property="og:image:height"]', set(tags.height));
  }
  return rw.transform(res);
}
