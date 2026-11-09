# Page speed playbook (Core Web Vitals)

Targets on mobile Lighthouse: LCP < 2.5 s (aim 1.5 s), FCP < 1.8 s (aim 1.2 s), CLS 0, TBT < 200 ms (aim 0).
Results from the original pass: FCP 1.8 s to 0.8-1.2 s, LCP 5.0 s to 1.5 s, CLS 0.05 to 0, page weight 3.7 MB to
~1.25 MB, performance 98-99 to 100 on every run.

Find the LCP element first (Lighthouse "Largest Contentful Paint element"). Almost every fix below either makes that
element arrive sooner or stops something else from competing with it.

## 1. Paint without JavaScript

- Pre-render (crawlability.md). The hero is in the HTML, so it paints before any script downloads.
- Load every script with `defer` (or `type="module"`), never blocking in `<head>`.
- **Load what the first screen doesn't need after first paint.** Lighthouse's simulated LCP counts every request that
  finishes before the first paint, so deferred framework scripts and a below-the-fold font still slow the LCP image on
  a throttled connection. `templates/after-fcp-loader.html` starts them when the `first-contentful-paint` entry arrives
  (fallbacks: `load` event when paint timing is unsupported, a 3 s timeout for background tabs, at once if nothing was
  pre-rendered). Scripts are appended with `async = false` to run in order; the last one's `onload` boots the app.
  Measured: LCP 2.1-2.2 s to 1.5-1.6 s, FCP 1.5 s to 1.2 s.
- Serve framework/vendor files from your own origin (`/kit/vendor/react.production.min.js`), not a CDN: no extra DNS/TLS.
- Hydrate in `React.startTransition` so it's split into short tasks (TBT).
- Run small layout-critical inline scripts (e.g. fitting a headline) right after the markup, before the framework, so
  the first paint is already final and nothing re-lays out later.

## 2. Fonts

`scripts/subset_fonts.py` does all of this for Google Fonts:

- **Self-host** instead of `fonts.googleapis.com`: removes a render-blocking CSS request and a three-hop chain
  (HTML -> CSS -> font file on another origin).
- **Trim variable fonts to the axis ranges used** (`instancer.instantiateVariableFont`): Google Sans Flex 117 KB to 54 KB
  by keeping width 62-100 and weight 400-700.
- **Subset to the characters used** (Latin + common punctuation); keep `math`/`symbols` files as separate faces with
  `unicode-range` so they only download when a page uses such a character.
- **Icon fonts: only the glyphs in use** (Material Symbols `&icon_names=a,b,c`): 3.1 MB to ~5 KB. Keep a list of icon
  names in the script; add to it when the UI uses a new icon.
- **Content-hashed filenames** (`inter-latin-1a2b3c4d.woff2`) served with `Cache-Control: public, max-age=31536000, immutable`.
- **Inline the `@font-face` rules** in `<head>` (no CSS request) and **preload only the font that draws the LCP text**:
  `<link rel="preload" as="font" type="font/woff2" href="..." crossorigin>`.
- **`font-display: swap` for text**, and **metric-matched local fallbacks** so the swap doesn't shift layout
  (`templates/fallback-fonts.css`: `size-adjust`, `ascent-override`, `descent-override`, `line-gap-override` on a
  `local('Arial')` face; tune by overlaying screenshots of the fallback and the web font). CLS 0.05 to 0.
- **Icon fonts with ligatures**: swap too, but keep icons `color: transparent` while the font loads (a class on `<html>`
  removed when `document.fonts.load()` resolves, 3 s timeout) so names like `arrow_forward` never flash as text.
  Avoid `display=block` for icons: it holds up rendering.
- **Fonts nothing in the first screen uses** (a display serif used further down) go in a `<template id="late-fonts">`
  copied into `<head>` after first paint.

## 3. The LCP image

- Preload it, with responsive candidates and high priority, in the page's own head only (not on pages that don't show it):
  `<link rel="preload" as="image" href="/hero.webp" imagesrcset="/hero-420.webp 420w, /hero.webp 600w" imagesizes="210px" type="image/webp" fetchpriority="high">`
- On the `<img>`: `fetchpriority="high"`, never `loading="lazy"`, `width`/`height` set.
- WebP (or AVIF) with a JPEG fallback in `<picture>`; sized to the rendered size x2 at most.
- Make sure nothing else (fonts, scripts, other images) is requested before it unless it draws the first screen.

## 4. Other images

- `srcset` + `sizes` with a half-size copy (e.g. `shot-270.webp 270w, shot.webp 540w`, `sizes="(max-width: 760px) 30vw, 210px"`).
- `width` and `height` on every image (CLS), `loading="lazy"` and `decoding="async"` below the fold.
- Convert screenshots to WebP; strip metadata. Python: `Image.open(p).save(out, 'WEBP', quality=80, method=6)`.

## 5. CSS

- Inline the CSS the first screen needs (for a small site, all of it: a design-system bundle inlined in `<head>`
  removed the only render-blocking request). Larger sites: inline critical CSS, load the rest with
  `<link rel="preload" as="style" onload="this.rel='stylesheet'">`.
- No `@import` in CSS (serial requests).
- Watch for global class-name collisions when inlining several stylesheets.

## 6. Layout shift and main thread

- Reserve space: `width`/`height` or `aspect-ratio` on media, fixed heights for nav and pills, `min-height` for
  late-loading blocks.
- Pre-rendered markup must equal the first client render, or hydration replaces it (shift + slower LCP).
- **No forced reflows**: don't read layout (`getBoundingClientRect`, `offsetWidth`, `scrollHeight`) right after
  writing styles or right after the framework commits. Read inside a `ResizeObserver` callback (runs after layout) and
  write in the next `requestAnimationFrame`. Don't clone nodes to measure them; measure a hidden probe.
- Animations: animate only `transform` and `opacity`; skip entrance animations on first measure (27 to 4
  non-composited animations during load). Respect `prefers-reduced-motion`.
- Start animations after first paint with negative `animation-delay` if they must already be moving.
- Break long tasks; use `content-visibility: auto` on long below-the-fold sections.

## 7. Network and caching

- Cache headers (hosting.md): one year `immutable` for hashed/versioned files (fonts, `/kit/`, build output);
  30 days with `stale-while-revalidate` for unversioned images; icons 30 days; HTML short or revalidated.
- Versioned script URLs for files without hashes (`/kit/bundle.js?v=5136988d`, first 8 hex of `sha256sum`); bump on change.
- `preconnect` only to origins really used in the first seconds (after self-hosting there are often none).
- Compression (Brotli/gzip) and HTTP/2 or 3 come from the host; check they're on.
- Remove what isn't used: unused JS bundles, polyfills, analytics loaded synchronously (load analytics after `load`).

## 8. Measure

```bash
bash scripts/lighthouse.sh https://example.com/ 10
```

Change one thing, re-run several times, keep it only if the range moves. Write the before/after ranges into the commit
message.
