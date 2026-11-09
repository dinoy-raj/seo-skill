# Crawlability: real HTML for every page

## Pre-render every route

Search engines render JavaScript late and unreliably; most other crawlers (link previews, AI assistants, Bing for many
pages) do not run it at all. Every route must come back from the server as finished HTML.

Pick the cheapest route to that for the stack:

| Stack | Do this |
| --- | --- |
| Next.js / Nuxt / SvelteKit / Astro / Remix | Use SSG (`output: 'export'`, `prerender = true`, `getStaticProps`) or SSR for every public route. Check `generateMetadata`/`head()` is per page. |
| Vite/CRA SPA, Vue SPA | Add a pre-render step (vite-plugin-ssr/vike, `vite-ssg`, or `scripts/prerender.js`), or move to SSG. |
| No-build static site rendered by a script (React via CDN, htm, etc.) | `scripts/prerender.js`: load each route in headless Chromium and save the HTML, or render with `react-dom/server` through a hook (below). |
| Plain HTML | Already fine; still give each page its own head. |

### How the original project did it (no build step, React + htm from local files)

- `index.html` holds a data block (apps, talks, posts) and the app script; it is also the template.
- The app exposes `window.__site = { routes, key(), head(), jsonld() }` and, when `window.__prerender` is set, hands its
  root element to that hook instead of mounting.
- `prerender.js` (Playwright) serves the repo from disk via request interception (no server), opens each route, injects
  `react-dom-server` from cdnjs, calls `renderToString(window.__app)` and writes:
  - the head between `<!-- seo:head -->` markers (title, meta, OG, Twitter, canonical, preload),
  - JSON-LD between `<!-- seo:jsonld -->` markers,
  - the markup into `<div id="root" data-route="KEY">` between `<!-- prerender:start/end -->` markers, with no
    whitespace inside `#root` (hydration matches child nodes one for one),
  - `<route>.html` next to `index.html` (Vercel `cleanUrls` serves it at `/route`), a "generated, don't edit" comment,
  - `sitemap.xml` from every route whose head is not `index: false`.
- The client hydrates only if `root.dataset.route` matches the current route; otherwise it clears and renders fresh.
- The build fails on any `pageerror` during render and if a route renders as a different route (e.g. the 404 view).

`scripts/prerender.js` in this skill is the generic version: it snapshots the DOM after load (works for any framework) and
can optionally restrict the snapshot to a root element. Re-run it after every content change and commit the output.

### After pre-rendering

- Hydrate, don't replace: `hydrateRoot` (React), `createSSRApp` (Vue) etc. Replacing the DOM throws away the paint and
  hurts LCP and CLS.
- Hydrate inside `React.startTransition(() => ReactDOM.hydrateRoot(root, app))` so it runs as short tasks (lower TBT).
- A hydration mismatch is a bug, not a warning: React discards the markup and redraws. Usual causes: pre-render is
  stale, dates/random values, `window` reads during render, whitespace inside the root.
- Client-side navigation must keep `document.title`, the canonical `href` and the meta description in step with the
  route, from the same `routeHead()` the pre-renderer used. On first load the server HTML already has the right
  canonical; JS must not change it then (Google: "make sure that JavaScript doesn't change the canonical link element").
- Mobile and desktop must get the same content, structured data and meta (mobile-first indexing).

## Heading and text hygiene

Crawlers index `textContent`. Things that look fine but read badly:

- Icon fonts with ligatures: `<h2>Let's talk <span class="icon">waving_hand</span></h2>` indexes as "Let's talk
  waving_hand". Use `<span class="icon" data-icon="waving_hand" aria-hidden="true"></span>` with
  `.icon::before { content: attr(data-icon) }`.
- Letters split for animation: `<h1><span>A</span><span>n</span>...` can index as "AndridDevelper" when a letter is
  replaced by a shape. Keep the real words in a `.sr-only` span and draw the animated letters from `data-t` via
  `::before`, `aria-hidden` on the decoration.
- Exactly one `<h1>` per page, containing the main keyword/name ("Dinoy Raj, Android Developer", not "Hey!").
- Headings in order (h1, h2, h3; no jumps from h2 to h4).
- Decorative giant wordmarks: draw with CSS from a data attribute and `aria-hidden`, or they become the page's most
  repeated "keyword".

## Crawl files

- `robots.txt` (`templates/robots.txt`): allow all and give the `Sitemap:` absolute URL. robots.txt controls crawling,
  not indexing: a disallowed URL can still be indexed from links, and its `noindex` is never read. So **don't
  `Disallow` folders you want out of the index**; send `X-Robots-Tag: noindex` (or meta robots) and let them be crawled.
  Use `Disallow` only for crawl waste (internal search results, carts, endless filters). Google reads only
  `user-agent`, `allow`, `disallow`, `sitemap` (no `crawl-delay`). Never block CSS/JS the page needs to render.
- `sitemap.xml` (`templates/sitemap.xml`): only canonical, indexable 200 URLs; `lastmod` as `YYYY-MM-DD` and **true**:
  the date of the last significant change to that page, not the build date (Google ignores `lastmod` that isn't
  "consistently and verifiably accurate"). `priority` and `changefreq` are ignored, leave them out. Up to 50,000 URLs /
  50 MB per file. `image:image` with `image:loc` is still supported (caption/title/license tags were dropped).
  Generate it with the pre-render so it can't drift.
- `llms.txt` (`templates/llms.txt`): optional. Google says AI Overviews and AI Mode need no special files or markup;
  some other AI tools read it. A plain markdown summary: who/what, key pages, products, contact, profiles.
- `404.html`: a real 404 status (that alone removes the URL from Google; `noindex` is optional), a link home, inline CSS.
- Never ship `noindex` in the server HTML of a page you want indexed and remove it with JS: Google may not render it.
- Routing by path with the History API; Google ignores `#fragment` routes.

## URLs and redirects

- Choose one host. Redirect the other with a 301 for **both** `/` and `/:path*` (a rule for `/:path*` alone may leave
  the root serving a 200 duplicate on some hosts).
- Clean URLs (`/about`, not `/about.html`), no trailing slash variation, `/index.html` redirects to `/`.
- When a route moves (e.g. `/#all-apps` to `/apps`), redirect: server-side 301 for paths, `history.replaceState` for
  hash routes (hashes never reach the server).
- Only rewrite known routes to the SPA shell; everything else must hit the 404 page with a 404 status.
- With Vercel `cleanUrls: true`, `/index.html` redirects to `/`, so rewrites must target `/`, not `/index.html`
  (rewrites to `/index.html` returned 404 for every deep route).

## Internal linking

- Readable URLs with words and hyphens (`/talks/offline-rag-android`), not ids; paths are case-sensitive.
- Every page reachable from plain `<a href>` links in nav or footer (a footer row linking every product page fixed
  pages that were only reachable through JS).
- Descriptive anchor text ("Dino Minimalist Launcher"), not "click here"; give repeated links distinct accessible names.
- Add hub pages (`/apps`, `/talks`, `/blog`) that list children, and child pages that link back (breadcrumbs).
- Pages need real substance (Google has no word-count target, but a talk page with abstract, takeaways and events is
  more useful than a card with a title).
- Outbound links: `rel="sponsored"` for paid, `rel="ugc"` for user content, `nofollow` only for sources you don't trust.
- Lazy-loaded content must load without clicks (Googlebot doesn't click or scroll); infinite scroll needs paginated URLs.
