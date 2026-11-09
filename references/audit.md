# Audit: get a baseline before changing anything

## 1. What a crawler sees

```bash
curl -sL https://example.com/ | python3 -c "import sys,re,html; t=sys.stdin.read(); t=re.sub(r'(?s)<(script|style|template)[^>]*>.*?</\1>','',t); print(re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))[:3000])"
```

If this prints almost nothing, the site is client-rendered and invisible to non-JS crawlers, link unfurlers and AI
agents. That is the first fix (see crawlability.md). Repeat for a deep route (`/about`, `/product/x`): SPAs often 404
on deep links or serve the home page's head for every route.

Also check:

```bash
curl -sI https://example.com/            # 200, cache headers, security headers
curl -sI https://www.example.com/        # must be 301 to the apex (root path too)
curl -sI https://example.com/index.html  # should 301/308 to /
curl -sI https://example.com/nope        # must be a real 404 status, not 200
curl -s  https://example.com/robots.txt
curl -s  https://example.com/sitemap.xml
```

## 2. Static audit

```bash
python3 scripts/seo_audit.py ./dist                      # a build folder
python3 scripts/seo_audit.py https://example.com --crawl  # live site, follows the sitemap
```

It reports per page: title and description length, canonical, robots, lang, viewport, Open Graph and Twitter tags,
`<h1>` count and text, JSON-LD validity and types, images without `alt`/`width`/`height`, word count, and whether
`noindex` pages are in the sitemap or sitemap URLs are missing. Fix every ERROR; read every WARN.

Validate structured data at https://validator.schema.org and https://search.google.com/test/rich-results, and social
cards with the platforms' debuggers (LinkedIn Post Inspector, Facebook Sharing Debugger).

## 3. Lighthouse (mobile)

```bash
bash scripts/lighthouse.sh https://example.com/ 5
```

Mobile uses simulated slow 4G and a 4x CPU slowdown, so it is the strict one; desktop usually follows. Record for each
run: performance, accessibility, best practices, SEO, LCP, FCP, CLS, TBT, Speed Index. Open the JSON report and note:

- the LCP element and its breakdown (TTFB, load delay, load time, render delay)
- render-blocking requests and the network dependency tree (chains like HTML -> fonts.googleapis.com CSS -> fonts.gstatic.com)
- unused JS/CSS, total byte weight, image audits (`uses-responsive-images`, `modern-image-formats`)
- `layout-shifts` culprits, `non-composited-animations`, forced reflows in `bootup-time`/`mainthread-work-breakdown`
- console errors (`errors-in-console`): a hydration error here is a performance bug too

For a local build, serve over HTTP/2 or test the deployed preview; a plain `python -m http.server` (HTTP/1.1, no
compression) under-reports.

## 4. Findings checklist

Crawl and index
- [ ] Every route returns its full content as HTML without JS
- [ ] Every route is its own URL with a 200, unknown URLs return 404
- [ ] One host (apex or www), the other 301s, including `/`
- [ ] robots.txt allows the site, blocks build/design folders, points to the sitemap
- [ ] sitemap.xml lists exactly the indexable pages with `lastmod`
- [ ] Internal links from nav/footer reach every page (no orphan pages)
- [ ] Headings read as real words (no icon ligature names, split letters)

Head
- [ ] Unique title (about 50-60 chars) and description (about 140-160 chars) per page, naming the brand/person
- [ ] Canonical, robots, `lang`, viewport, theme-color
- [ ] Open Graph + Twitter with a 1200x630 image and alt text
- [ ] Favicon: square PNG, multiple of 48 px (192 works), plus favicon.ico and apple-touch-icon

Structured data
- [ ] One `@graph` per page: Person/Organization + WebSite everywhere, plus the page's own type and a BreadcrumbList
- [ ] Generated from page data, parses, passes the Rich Results test

Speed
- [ ] No render-blocking third-party CSS; fonts self-hosted and subset; hero font and LCP image preloaded
- [ ] JS not needed for first paint is loaded after it
- [ ] CLS 0: images have width/height, fallback fonts metric-matched
- [ ] Hashed/versioned static files cached a year, immutable
