---
name: seo-skill
description: Audit and fix a website's SEO and page speed following Google Search Central's documentation: every page fully indexable, good Core Web Vitals, Lighthouse/PageSpeed at or near 100. Covers per-page titles, descriptions, canonicals, Open Graph/Twitter cards, schema.org JSON-LD, pre-rendering JS sites so crawlers and AI agents see real content, robots.txt, sitemap.xml, llms.txt, favicons Google will show, www/apex redirects, plus Core Web Vitals work (LCP, INP, CLS) such as self-hosted subset fonts, LCP image preloads, deferring JS until after first paint, cache headers and hydration fixes. Use when the user asks to "SEO optimise", improve search ranking or rich results, fix PageSpeed/Lighthouse findings, speed up a site, make a site crawlable, or add sitemap/robots/structured data/social previews.
---

# SEO and page speed

A repeatable pass that takes a site to: every route served as complete static HTML with its own head and structured data,
good field Core Web Vitals (LCP < 2.5 s, INP < 200 ms, CLS < 0.1), and a mobile Lighthouse score of 100 on performance,
accessibility, best practices and SEO. A perfect Lighthouse score is a speed and quality goal, not a ranking requirement
(Google says so). Where Google's own docs and common SEO advice disagree, Google wins: read
[references/google-search-docs.md](references/google-search-docs.md) before giving advice. It was first done on a static
React (no-build) portfolio deployed on Vercel, but every step is framework-neutral; the references say how to apply it to
Next.js, Astro, Vite/SPA, plain HTML and other hosts.

## How to run the pass

Work in this order. Each phase finishes with a measurement, and nothing is "done" until the number says so.

1. **Audit first, change nothing.** Follow [references/audit.md](references/audit.md):
   - `python3 scripts/seo_audit.py <site-dir-or-url>` for the on-page and crawl-file checks.
   - `bash scripts/lighthouse.sh <url>` for mobile Lighthouse (several runs; one run is noise).
   - View every page with JavaScript off (`curl -s <url> | ...`): what a crawler or AI agent without JS sees is the real page.
   Write down the baseline (score, LCP, FCP, CLS, TBT, failing audits, pages with no content without JS).
2. **Make every page crawlable** ([references/crawlability.md](references/crawlability.md)). If the HTML a server returns
   has no content, nothing else matters: pre-render (`scripts/prerender.js`) or switch the framework to SSG/SSR. One real
   file per route, each with its own head. Clean heading text. robots.txt, sitemap.xml, 404 page, redirects
   (llms.txt is optional: Google says AI features need no special files).
3. **Per-page head** ([references/head-metadata.md](references/head-metadata.md)): title, description, canonical, robots,
   Open Graph, Twitter, from one `routeHead()`-style function. Social image 1200x630. Favicons Google will show.
4. **Structured data** ([references/structured-data.md](references/structured-data.md)): one JSON-LD `@graph` per page,
   built from the same data the page renders, so it cannot drift from the visible content. Check each type against
   Google's required properties before promising a rich result (google-search-docs.md has the table).
5. **Page speed** ([references/performance.md](references/performance.md)): fonts, LCP image, render-blocking CSS/JS,
   hydration, layout shifts, forced reflows, caching. Re-measure after each change; keep the ones that move the number.
6. **Accessibility and best practices** ([references/accessibility.md](references/accessibility.md)): the Lighthouse
   findings that keep a page below 100 (names, contrast, heading order, console errors).
7. **Hosting** ([references/hosting.md](references/hosting.md)): cache headers, security headers, clean URLs, www to apex,
   noindex (not robots.txt Disallow) on build/design folders. `templates/vercel.json` is a working starting point.
8. **Verify and report.** Re-run the audit script and Lighthouse; compare to the baseline in a table; list what is left
   (e.g. "needs Search Console verification", "no backlinks"). Tell the user to verify the site in Search Console,
   submit the sitemap, request indexing for a few key pages (it has a quota), watch the Core Web Vitals field report,
   and expect changes to take weeks.

## Rules that came from real mistakes

- **Content must exist without JavaScript.** A client-rendered page serves zero words to most crawlers and every AI agent.
  Pre-render, then hydrate the markup instead of replacing it.
- **Regenerate the pre-render after every content change.** Stale pre-rendered markup causes a hydration mismatch
  (React error #418): React throws the HTML away and redraws, mobile LCP went 3.3 s to 5.0 s. Make the build fail loudly
  on script errors and on a route that renders as a different route.
- **Head and JSON-LD come from the same data as the page.** Hand-written JSON-LD drifts. Generate both from the data
  arrays the UI renders (apps, talks, posts, products).
- **One page = one URL.** Canonical on every page, www 301s to apex (root path too, not only sub-paths), no duplicate
  `/index.html`, legal/utility pages `noindex, follow` and left out of the sitemap.
- **Heading text is what gets indexed.** Icon-font ligatures (`waving_hand`) and decorative split letters inside `<h1>`
  are read as text ("AndridDevelper"). Draw decoration with CSS `::before { content: attr(data-x) }` and keep the real
  words in the element.
- **Nothing should compete with the LCP element before first paint.** Deferred scripts and unused fonts requested
  before first paint share the throttled connection with the hero image. Start them after the first-contentful-paint
  entry (`templates/after-fcp-loader.html`). This alone moved mobile performance 98-99 to 100.
- **Self-host and subset fonts** (`scripts/subset_fonts.py`): no third-party CSS chain, only the axes and characters in
  use, content-hashed names with a one-year immutable cache, the hero font preloaded, metric-matched fallbacks so the
  swap does not shift layout. Icon fonts: only the glyphs in use (3.1 MB to 5 KB).
- **robots.txt is not for hiding pages.** A `Disallow`ed URL can still be indexed from links, and its `noindex` is never
  read. To keep a folder out of results, let it be crawled and send `X-Robots-Tag: noindex`. (The original project had
  both on `/design/`, which cancels the noindex.)
- **Sitemap `lastmod` must be a real change date**, not the build date on every URL, or Google stops trusting it.
  `scripts/prerender.js` keeps a page's previous `lastmod` when its HTML didn't change.
- **Rich results have required properties.** `MobileApplication` needs `offers` and a genuine `aggregateRating` or
  `review`; `Event` needs a single-event page, a full ISO date and a public physical venue; `WebSite` (site name) belongs
  on the home page. FAQ and HowTo rich results are gone. Markup that isn't eligible still describes entities, but don't
  sell it as a rich result.
- **Don't chase folklore**: no meta keywords, no word-count targets, no character limits as rules (titles and
  descriptions are only truncated), heading order is an accessibility concern, not a ranking one.
- **Keep a search-only description when the on-page copy reads oddly out of context** (an `seo` field next to `desc`).
- **Don't change the design.** SEO work must not alter the look. Compare screenshots at a desktop and a phone width
  before and after; if text or layout changed, restore it.
- **Measure locally with several runs and report ranges** ("LCP 2.1-2.2 s to 1.5-1.6 s over 10 runs"), not one score.

## Files in this skill

| Path | What it is |
| --- | --- |
| `references/google-search-docs.md` | What Google's docs say: myths, easy mistakes, rich result requirements, retired types |
| `references/audit.md` | Baseline: what to measure, commands, a findings checklist |
| `references/crawlability.md` | Pre-rendering, heading text, robots, sitemap, llms.txt, 404, redirects, internal links |
| `references/head-metadata.md` | Title/description rules, the full head template, social images, favicons |
| `references/structured-data.md` | JSON-LD `@graph` patterns per page type, generated from page data |
| `references/performance.md` | Core Web Vitals playbook: fonts, images, JS, CSS, hydration, CLS, caching |
| `references/accessibility.md` | Lighthouse accessibility and best-practice fixes |
| `references/hosting.md` | Vercel, Netlify, Cloudflare Pages, nginx, GitHub Pages headers and redirects |
| `scripts/seo_audit.py` | Static auditor for a build folder or live URL (stdlib Python, no installs) |
| `scripts/prerender.js` | Playwright pre-renderer: routes to static HTML, plus sitemap.xml |
| `scripts/subset_fonts.py` | Self-host Google Fonts trimmed to used axes, characters and icons |
| `scripts/make_icons.py` | Favicon set and 1200x630 social card from one image (Pillow) |
| `scripts/lighthouse.sh` | Repeated mobile Lighthouse runs with a min/median/max summary |
| `templates/` | head, after-FCP loader, fallback fonts, robots, sitemap, llms.txt, 404, vercel.json, JSON-LD examples |
| `examples/prerender-react-hydrate.js` | The original site's pre-renderer: React `renderToString` through a hook, per-route head and JSON-LD written between markers |

Copy scripts and templates into the target project (e.g. under `design/` or `scripts/`) and edit their config blocks;
they are written to be read and adapted, not called as a black box.
