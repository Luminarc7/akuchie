Japanese websites to search for magic cards
eventually will add prices for local stores

## Test site (staging)

- `main` → **warujie.jp** (live). Every push to `main` goes live.
- `staging` → test site at `https://staging-warujie.<subdomain>.workers.dev` (not indexed by search engines).
  Work is pushed to `staging` first; when it's ready, merge `staging` into `main` to publish.
