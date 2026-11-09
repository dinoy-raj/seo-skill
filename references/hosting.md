# Hosting: headers, redirects, clean URLs

What every host needs:

1. One canonical host: www -> apex (or the reverse) as a 301, for `/` and every path.
2. Clean URLs: `/about` serves `about.html`; `/about.html` and `/index.html` redirect.
3. Real 404 status for unknown paths, with a `404.html` body.
4. Cache headers: hashed/versioned assets one year immutable; images 30 days + stale-while-revalidate; HTML revalidated.
5. Security headers (Lighthouse best practices): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or CSP
   `frame-ancestors`), `Referrer-Policy: strict-origin-when-cross-origin`, `Cross-Origin-Opener-Policy: same-origin`,
   and HSTS once HTTPS is settled (`Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`).
6. `X-Robots-Tag: noindex` on folders that are deployed but shouldn't be indexed (design, tools, drafts).
7. HTTPS with a valid certificate on both apex and www (otherwise the redirect itself errors).

## Vercel (`vercel.json`)

See `templates/vercel.json`. Notes:

- `"cleanUrls": true, "trailingSlash": false`. With `cleanUrls`, `/index.html` 308s to `/`, so any rewrite must target
  `/`, never `/index.html` (that returned 404 for every deep route).
- Once every route is a pre-rendered file, remove SPA rewrites entirely; unknown paths then get `404.html`.
- For a static no-build repo: `"framework": null, "installCommand": "", "buildCommand": "", "outputDirectory": "."`
  so stale dashboard build settings can't break deploys; pin Node via `"engines"` in package.json if Vercel complains.
- www redirect needs two rules (`/` and `/:path*`) with `has: [{ type: 'host', value: 'www.example.com' }]`, and both
  domains added to the project.

## Netlify (`_headers` and `_redirects` in the publish folder)

```
# _redirects
https://www.example.com/*  https://example.com/:splat  301!
/old-path                  /new-path                   301
```

```
# _headers
/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Cross-Origin-Opener-Policy: same-origin
/assets/fonts/*
  Cache-Control: public, max-age=31536000, immutable
/assets/*
  Cache-Control: public, max-age=2592000, stale-while-revalidate=86400
/design/*
  X-Robots-Tag: noindex
```

Enable "Pretty URLs" (asset optimisation) for clean URLs.

## Cloudflare Pages

Same `_headers` / `_redirects` syntax as Netlify. Clean URLs are automatic (`/about` serves `about.html`). www -> apex
is a Bulk Redirect or a Redirect Rule on the zone.

## GitHub Pages

No custom headers. Clean URLs work for `about.html` -> `/about`. www/apex redirect is automatic when the custom domain is
set and DNS has both. Add `.nojekyll`. For cache/security headers, put Cloudflare in front.

## nginx

```nginx
server { listen 443 ssl; server_name www.example.com; return 301 https://example.com$request_uri; }
server {
  listen 443 ssl http2; server_name example.com; root /srv/site;
  add_header X-Content-Type-Options nosniff always;
  add_header X-Frame-Options DENY always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;
  add_header Cross-Origin-Opener-Policy same-origin always;
  location = /index.html { return 301 /; }
  location ~ ^/(.+)\.html$ { return 301 /$1; }
  location / { try_files $uri $uri.html $uri/index.html =404; }
  location /assets/fonts/ { add_header Cache-Control "public, max-age=31536000, immutable"; }
  location /assets/ { add_header Cache-Control "public, max-age=2592000, stale-while-revalidate=86400"; }
  location /design/ { add_header X-Robots-Tag noindex; }
  error_page 404 /404.html;
  gzip on; gzip_types text/css application/javascript image/svg+xml application/json;
}
```

## After deploy

- `curl -sI` the apex, www, a deep route, `/index.html`, a missing page (see audit.md).
- Google Search Console: verify the domain (DNS TXT), submit `sitemap.xml`, inspect and request indexing for the home
  page and changed pages. Bing Webmaster Tools: import from Search Console.
