// Runs before every Cloudflare deploy (wrangler.jsonc "build"): makes ja_cards.json.br,
// the card database brotli-compressed - about half the size of ja_cards.json.gz.
// worker.js sends it to browsers that take brotli (all current ones), as /ja_cards.json.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import zlib from 'node:zlib';

const SRC = 'ja_cards.json.gz', OUT = 'ja_cards.json.br';
if (!existsSync(SRC)) {
  console.log(`${SRC} not found: nothing to compress`);
  process.exit(0);
}
const started = Date.now();
const raw = zlib.gunzipSync(readFileSync(SRC));
JSON.parse(raw.toString('utf8'));   // a broken file stops the deploy here instead of reaching visitors
const br = zlib.brotliCompressSync(raw, {
  params: {
    [zlib.constants.BROTLI_PARAM_MODE]: zlib.constants.BROTLI_MODE_TEXT,
    [zlib.constants.BROTLI_PARAM_QUALITY]: 10,
    [zlib.constants.BROTLI_PARAM_LGWIN]: 24,
    [zlib.constants.BROTLI_PARAM_SIZE_HINT]: raw.length,
  },
});
if (!zlib.brotliDecompressSync(br).equals(raw)) throw new Error('brotli round trip failed');
writeFileSync(OUT, br);
console.log(`${OUT}: ${(br.length / 1e6).toFixed(2)} MB (gzip ${(readFileSync(SRC).length / 1e6).toFixed(2)} MB, ${((Date.now() - started) / 1000).toFixed(0)} s)`);
