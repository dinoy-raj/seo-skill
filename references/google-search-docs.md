# What Google Search Central actually says

Checked against https://developers.google.com/search/docs (starter guide, crawling and indexing, appearance,
structured data, page experience) on 2026-11-09. When folklore and these docs disagree, follow the docs. Re-check the
[documentation updates log](https://developers.google.com/search/updates) before relying on a rich result type.

## Things Google says don't matter (don't spend time on them)

| Folklore | Google |
| --- | --- |
| Meta keywords | "Google Search doesn't use the keywords meta tag." |
| Word count minimums | "there's no magical word count target, minimum or maximum." |
| One `<h1>`, heading order | Heading order "doesn't matter" for Search, no ideal number of headings. (Still do it for accessibility.) |
| Title 60 chars / description 160 chars | "there's no limit on how long a `<title>` element can be"; same for meta descriptions. Both are only truncated to fit the device width. Use the numbers as a display guide, not a rule. |
| Keywords in domain/URL | "hardly any effect beyond appearing in breadcrumbs." Use readable words with hyphens for users. |
| Duplicate content penalty | Not a spam violation and no manual action; it's inefficient. Canonicalise it. |
| E-E-A-T as a ranking factor | "E-E-A-T itself isn't a specific ranking factor." Trust matters most. |
| Subdomain vs subdirectory | "do whatever makes sense for your business." |
| Special files/markup for AI Overviews and AI Mode (llms.txt etc.) | "You don't need to create new machine readable files, AI text files, or markup to appear in these features." llms.txt is optional, for other AI tools only. |
| `priority`, `changefreq` in sitemaps | "Google ignores `<priority>` and `<changefreq>` values." |
| `crawl-delay`, `noarchive` | Not supported by Google. robots.txt supports only `user-agent`, `allow`, `disallow`, `sitemap`. |
| Perfect Lighthouse score for SEO | Good scores don't guarantee rankings; "trying to get a perfect score just for SEO reasons may not be the best use of your time." Field Core Web Vitals are what ranking systems use. |
| Meta description affects ranking | Google mostly builds snippets from page text; it uses the meta description when that's more accurate. |

## Rules that are easy to get wrong

Crawling and indexing
- **robots.txt does not stop indexing**, and a disallowed URL's `noindex` (meta or `X-Robots-Tag`) is never seen. To keep
  a page out of results, allow crawling and send `noindex`. Use `Disallow` only to save crawl on endless/useless URLs
  (internal search, carts, filters), never on pages that carry `noindex`.
- **`lastmod` must be accurate**: Google uses it only if "consistently and verifiably accurate", for the last
  significant change. Don't stamp every URL with the build date.
- Sitemaps list canonical HTTPS URLs only; max 50,000 URLs / 50 MB per file; submitting is "merely a hint". Submit in
  Search Console or with the `Sitemap:` line in robots.txt.
- **Don't put `noindex` in the initial HTML and remove it with JavaScript**: Google may skip rendering when it sees it.
- Canonical: absolute URLs, exactly one per page, correct in the server HTML; "make sure that JavaScript doesn't change
  the canonical link element." Don't use `noindex` or robots.txt to pick canonicals.
- Routing: History API, not `#fragments` ("Google generally doesn't support URL fragments").
- SPAs and soft 404s: unknown routes must return a real 404 status (or JS-redirect to a URL that does, or add `noindex`).
  A 404 page doesn't need `noindex`; the status code is enough.
- Redirects: 301/308 permanent, 302/307 temporary, instant meta refresh = permanent. JS redirects only as a last resort.
- Dynamic rendering (bots get a different render) "was a workaround and not a long-term solution": use SSR, static
  rendering or pre-rendering with hydration.
- Links must be `<a href>`; anchor text describes the target. `rel="sponsored"` for paid links, `rel="ugc"` for user
  content, `nofollow` only for sources you don't trust.
- Lazy loading must not depend on clicks or scrolling events Googlebot won't fire; "Google won't load content that
  requires user interactions." Native `loading="lazy"` and IntersectionObserver are fine. Infinite scroll needs
  paginated URLs.
- Mobile-first: the mobile page must have the same content, headings, structured data, robots meta, title, description
  and image URLs/alt as desktop.

Appearance
- **Favicon**: square, at least 8x8 px, larger than 48x48 recommended (192x192 is a good choice); formats BMP, GIF, ICO,
  PNG, JPEG (SVG isn't in Google's list, so give a PNG/ICO even if you also ship SVG); `rel="icon"`; on the home page;
  one per hostname; stable URL; neither the home page nor the icon blocked by robots.txt. Takes days to weeks to show.
- Title links: Google rewrites half-empty titles, boilerplate repeated across pages, obsolete years, titles that don't
  match the page's main heading, and duplicated site names. Put the site name at the start or end with a delimiter.
- Images: use `<img>`/`<picture>` ("Google doesn't index CSS images"), descriptive `alt`, short descriptive file names
  (`black-kitten.jpg`, not `IMG00023.JPG`), always a `src` fallback with `srcset`, near relevant text. Supported:
  BMP, GIF, JPEG, PNG, WebP, SVG, AVIF.
- `og:image` / `primaryImageOfPage` influence which image Google shows: make it representative, not a generic logo.
- Snippet controls: `nosnippet`, `max-snippet`, `data-nosnippet` (on span/div/section, not toggled by JS); `nosnippet`
  also applies to AI Overviews and AI Mode. `Google-Extended` in robots.txt controls Gemini training/grounding use.

Page experience
- Core Web Vitals "good": **LCP < 2.5 s, INP < 200 ms, CLS < 0.1**, from field data (Search Console's Core Web Vitals
  report, PageSpeed Insights' field section, CrUX). Lighthouse is lab data; TBT is its stand-in for INP.
- Core Web Vitals are used by ranking systems; HTTPS, mobile-friendliness and no intrusive interstitials matter for
  users but "don't directly help your website rank higher."

Content
- Helpful, people-first, original content with clear authorship (bylines, about page) beats any technical tweak.
  Don't fake freshness by changing dates. Mass-produced AI content without oversight is treated as low effort.
- Changes take "a few hours" to "several months" to show; wait a few weeks before judging.

## Structured data eligibility (rich results)

General: JSON-LD recommended (injected by JS is read, but static is safer); markup must describe content visible on
the page; items missing required properties are not eligible; don't block marked-up pages with robots.txt or noindex.
Markup that isn't eligible for a rich result still helps Google understand entities, so it's fine to keep, but don't
promise rich results from it.

| Type | Google feature | Requirements that bite |
| --- | --- | --- |
| `WebSite` | Site name | Must be on the **home page** (domain or subdomain root): `name`, `url`, optional `alternateName` list. Elsewhere, reference it by `@id` only. |
| `ProfilePage` | Profile page | `mainEntity` Person/Organization with `name`. "The primary focus of the page must be a single person or organization". Good: about-me page, author page. Bad: a store's home page. A personal home page qualifies only if it's mainly about the person; the `/about` page is the safest place. |
| `Organization` | Logo, knowledge panel | No required props; home or about page; logo at least 112x112 px, crawlable. |
| `BreadcrumbList` | Breadcrumb | At least two `ListItem`s with `position`, `name`, `item` (last item's `item` optional). |
| `SoftwareApplication` / `MobileApplication` / `WebApplication` | Software app | **Required: `name`, `offers.price` (0 if free), and `aggregateRating` or `review`.** Without a real rating/review it's not eligible. Recommended: `applicationCategory`, `operatingSystem`. Ratings must be genuine and shown on the page. |
| `Article` / `BlogPosting` | Article | No required props; `headline`, `image`, `datePublished`/`dateModified` (full ISO 8601), every visible author as a separate `Person` with `name` (name only) and `url`. Only for the article's own page. |
| `Event` | Event | **Single-event leaf page**, publicly bookable, at a physical venue; `name`, `startDate` (full ISO 8601 date, not a month), `location` with `address`. Pages listing many events (e.g. a speaker's appearances) aren't eligible. |
| `VideoObject` | Video | `name`, `thumbnailUrl`, `uploadDate`. |
| `ImageObject` | Image metadata / Licensable | `contentUrl` plus `creator`, `creditText`, `copyrightNotice` or `license`. |
| `Review` / `AggregateRating` | Review snippet | Not self-serving for Organization/LocalBusiness; no fake or undisclosed incentivised reviews. |
| `Product`, `LocalBusiness`, `Recipe`, `JobPosting`, `Course` list, `Dataset`... | various | See the search gallery. |

**Retired, don't add**: FAQ (removed from Search May 2026), HowTo (2023), Course info, Claim review, Estimated salary,
Learning video, Special announcement, Vehicle listing (2025), Practice problem (2026). Dataset is used only by Dataset
Search.

## After launch

- Verify the site in Search Console (domain property via DNS), submit the sitemap, check Page indexing and Core Web
  Vitals reports.
- URL Inspection shows the rendered HTML Googlebot sees; "Request indexing" is for a few URLs, has a quota, and
  repeating it doesn't speed anything up.
- `site:example.com` to see what's indexed.
