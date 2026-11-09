# Per-page head

## One function, every page

Keep all head data in one function keyed by route, used by both the pre-renderer and client-side navigation:

```js
function routeHead(r) {
  if (r.page === 'about') return { path: '/about', title: 'About Jane Doe | Product Designer, Berlin', desc: '...' };
  if (r.page === 'product') return { path: '/' + p.slug, title: p.name + ': ' + p.tagline + ' | Jane Doe', desc: p.seo || p.desc };
  if (r.page === 'privacy') return { path: '/' + p.slug + '/privacy', title: 'Privacy policy · ' + p.name, desc: '...', index: false };
  if (r.page === 'missing') return { path: location.pathname, title: 'Not found · Jane Doe', desc: '', index: false };
  return { path: '/', title: 'Jane Doe | Product Designer & Speaker', type: 'profile', preload: true,
           social: 'Shorter, punchier line for social cards.', desc: 'Full search description.' };
}
```

Fields: `path` (canonical path), `title`, `desc`, optional `social` (OG/Twitter description), `type` (`website`,
`profile`, `article`), `index: false` (noindex, left out of the sitemap), `preload` (page-specific LCP preload).
`templates/head.html` is the rendered result; `scripts/prerender.js` has a `headHtml()` that produces it.

## Titles

- Unique per page, about 50-60 characters, most specific words first: `Talk title | Brand`, `Product: what it does | Brand`.
- Home: `Name | Role & Role` or `Brand | What it is`. Use the job title the person actually uses (don't upgrade
  "Android Developer" to "Product Engineer" unless asked).
- Put the platform in when people search for it ("... for Android"), without doubling it ("Android launcher for Android").
- Legal pages: `Privacy policy · Product`, `noindex, follow`.

## Descriptions

- 140-160 characters, a plain sentence naming the who/what/where: "Jane Doe is a product designer in Berlin who ...".
- Write a separate `seo` text when the on-page copy relies on context ("Several of the apps below began as tools
  inside it." reads oddly in a result). Use it for the meta description and JSON-LD; leave the page copy alone.
- Include location for people/local businesses ("Thiruvananthapuram, Kerala, India") on the about page.

## Must-have tags

```html
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#fbf6ee">
<title>...</title>
<meta name="description" content="...">
<meta name="author" content="...">
<meta name="robots" content="index, follow, max-image-preview:large">   <!-- or "noindex, follow" -->
<link rel="canonical" href="https://example.com/path">                    <!-- absolute, no trailing slash variance -->
```

`max-image-preview:large` lets Google show big image previews (Discover, image results).

## Open Graph and Twitter

Set all of them explicitly; X does not reliably fall back to OG for title/description/image alt.

```html
<meta property="og:type" content="website">          <!-- profile on a person's home page, article on posts/talks -->
<meta property="og:site_name" content="Jane Doe">
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:url" content="https://example.com/path">   <!-- same as canonical -->
<meta property="og:locale" content="en_US">
<meta property="og:image" content="https://example.com/assets/og.jpg">
<meta property="og:image:secure_url" content="https://example.com/assets/og.jpg">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Jane Doe, Product Designer">
<meta property="profile:first_name" content="Jane"> <meta property="profile:last_name" content="Doe">   <!-- og:type profile -->
<meta property="article:author" content="https://example.com/about">                                   <!-- og:type article -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@handle"> <meta name="twitter:creator" content="@handle">
<meta name="twitter:title" content="..."> <meta name="twitter:description" content="...">
<meta name="twitter:image" content="https://example.com/assets/og.jpg"> <meta name="twitter:image:alt" content="...">
```

Social image: 1200x630 JPEG under ~300 KB, text large enough to read at 600 px wide, absolute URL. Per-page images
are better when the pages are products/posts; one site card is fine otherwise. `scripts/make_icons.py --og` builds a
simple one from a photo and a name.

## Favicons that Google shows in results

Google needs a square favicon whose size is a multiple of 48 px and that is crawlable. An SVG letter tile often gets
ignored; a 192x192 PNG works.

```html
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192">
<link rel="icon" href="/favicon.ico" sizes="32x32">        <!-- also stops /favicon.ico 404s in console -->
<link rel="apple-touch-icon" href="/apple-touch-icon.png"> <!-- 180x180 -->
```

`python3 scripts/make_icons.py photo.jpg --out .` writes all three from one image (center square crop). For a personal
site, the person's face as favicon helps recognition in results.

## Keep it in sync on client navigation

```js
useEffect(() => {
  const h = routeHead(route);
  document.title = h.title;
  document.querySelector('link[rel=canonical]').href = SITE + h.path;
  document.querySelector('meta[name=description]').content = h.desc;
}, [route]);
```
