# Structured data (JSON-LD)

## Principles

- **One `<script type="application/ld+json">` per page holding an `@graph`.** Nodes reference each other by `@id`
  (`https://example.com/#person`, `.../#website`, `.../product#app`), so the same entity is described once.
- **Generate it from the data the page renders** (the arrays of apps, talks, posts, products), in a `routeJsonLd(route)`
  function next to `routeHead(route)`. Hand-written JSON-LD drifts from the page and Google penalises markup that
  doesn't match visible content.
- **Write it into the static HTML** at pre-render time (crawlers that don't run scripts still see it), between
  `<!-- seo:jsonld -->` markers. Escape `<` as `<` in the serialised JSON so `</script>` in data can't break out.
- Every page gets the identity nodes (Person or Organization, and WebSite), plus a page node (`ProfilePage`,
  `AboutPage`, `CollectionPage`, `WebPage`) with `isPartOf` the website, a `BreadcrumbList`, and its `mainEntity`.
- Legal and 404 pages: no JSON-LD (return `null`).
- Validate: https://validator.schema.org and Google's Rich Results Test.

## Identity nodes (every page)

```js
const PERSON = {
  '@type': 'Person', '@id': SITE + '/#person', name: 'Jane Doe', alternateName: 'Jane', givenName: 'Jane', familyName: 'Doe',
  url: SITE + '/', image: SITE + '/assets/jane.jpg', jobTitle: 'Product Designer', description: '...',
  email: 'mailto:' + EMAIL,
  address: { '@type': 'PostalAddress', addressLocality: 'Berlin', addressCountry: 'DE' },
  hasOccupation: { '@type': 'Occupation', name: 'Product Designer', skills: 'Figma, design systems, prototyping' },
  knowsAbout: ['Design systems', 'Prototyping', '...'],
  sameAs: [LINKS.github, LINKS.linkedin, LINKS.x, LINKS.youtube, LINKS.medium],   // every profile: this is how Google links them
};
const WEBSITE = { '@type': 'WebSite', '@id': SITE + '/#website', url: SITE + '/', name: 'Jane Doe',
  alternateName: ['Jane', 'janedoe.com'], inLanguage: 'en', publisher: { '@id': SITE + '/#person' } };
```

For a company use `Organization` (`logo`, `contactPoint`, `sameAs`) in place of Person; for a shop or office add
`LocalBusiness` with `address`, `geo`, `openingHoursSpecification`, `telephone`.

`alternateName` matters: a site named "Dinoy Raj" also ranked for "Dinoy" once Person and WebSite carried it.

## Page types

```js
const crumbs = list => ({ '@type': 'BreadcrumbList', itemListElement: [['Home', '/'], ...list]
  .map(([name, path], i) => ({ '@type': 'ListItem', position: i + 1, name, item: SITE + path })) });

function routeJsonLd(r) {
  const h = routeHead(r), url = SITE + h.path;
  const page = (type, extra) => ({ '@type': type, '@id': url + '#page', url, name: h.title, description: h.desc,
    isPartOf: { '@id': SITE + '/#website' }, inLanguage: 'en', ...extra });
  const graph = [PERSON, WEBSITE];
  if (r.page === 'home') graph.push(page('ProfilePage', { '@id': SITE + '/#profile', mainEntity: { '@id': SITE + '/#person' } }), /* lists, events, posts */);
  else if (r.page === 'about') graph.push(page('AboutPage', { mainEntity: { '@id': SITE + '/#person' }, breadcrumb: crumbs([['About', '/about']]) }));
  else if (r.page === 'list') graph.push(page('CollectionPage', { breadcrumb: crumbs([['Apps', '/apps']]),
    mainEntity: { '@type': 'ItemList', itemListElement: APPS.map((a, i) => ({ '@type': 'ListItem', position: i + 1, url: SITE + '/' + a.slug, name: a.name })) } }));
  else if (r.page === 'app') graph.push(appNode(r.app), page('WebPage', { mainEntity: { '@id': SITE + '/' + r.app.slug + '#app' },
    breadcrumb: crumbs([['Apps', '/apps'], [r.app.name, '/' + r.app.slug]]) }));
  else return null;   // legal pages, 404
  return { '@context': 'https://schema.org', '@graph': graph };
}
```

### Which type for what

| Content | Type | Useful properties |
| --- | --- | --- |
| Personal home page | `ProfilePage` + `Person` | `mainEntity`, `primaryImageOfPage`, `hasPart` (lists) |
| Company home | `WebPage` + `Organization` | `logo`, `sameAs`, `contactPoint` |
| Mobile app | `MobileApplication` | `operatingSystem`, `applicationCategory` (e.g. `ProductivityApplication`, `HealthApplication`, `DeveloperApplication`, `UtilitiesApplication`), `installUrl`/`downloadUrl` (store link), `screenshot`, `image` (icon), `author`, `publisher`, `alternateName` (store tagline), `sameAs` (store, website, source), `keywords` |
| Web/desktop software | `WebApplication` / `SoftwareApplication` | as above, `offers` (price `0` for free) |
| Product for sale | `Product` | `offers` (`price`, `priceCurrency`, `availability`), `brand`, `aggregateRating` only if real |
| Blog post (on or off site) | `BlogPosting` / `Article` | `headline`, `datePublished`, `dateModified`, `author`, `publisher`, `image` |
| Talk / course / video | `CreativeWork`, `VideoObject`, `Course` | `abstract`, `author`, `keywords`, `uploadDate` (video) |
| Conference appearance | `Event` with the person as `performer` | `startDate` (ISO, month precision ok), `location` (`Place` with `address`), `eventAttendanceMode`, `eventStatus`, `url`; on Person: `performerIn` |
| Index of items | `CollectionPage` + `ItemList` | `ListItem` with `position`, `url`, `name` (or full `item`) |
| FAQ | `FAQPage` | only for real Q&A visible on the page |

schema.org has no "speaking engagement": use `Event` with `performer: { '@id': '#person' }`.

### Example app node built from data

```js
const appNode = a => ({
  '@type': 'MobileApplication', '@id': SITE + '/' + a.slug + '#app', name: a.name, alternateName: a.store,
  url: SITE + '/' + a.slug, description: a.seo || a.desc, operatingSystem: 'Android',
  applicationCategory: CATEGORY[a.id] || 'UtilitiesApplication', image: SITE + '/assets/apps/' + a.id + '-icon.webp',
  screenshot: a.shots.map((_, i) => SITE + shot(a, i + 1)), author: { '@id': SITE + '/#person' }, publisher: { '@id': SITE + '/#person' },
  keywords: a.tags.join(', '),
  ...(a.play ? { installUrl: a.play, downloadUrl: a.play } : {}),
  ...(a.links ? { sameAs: a.links.map(([, href]) => href) } : {}),
});
```

## Writing it into the page

```js
out = between(out, '<!-- seo:jsonld -->\n', '<!-- /seo:jsonld -->',
  jsonld ? '<script type="application/ld+json">\n' + JSON.stringify(jsonld, null, 1).replace(/</g, '\\u003c') + '\n</script>\n' : '');
```

See `templates/jsonld-examples.json` for complete graphs (home, app page, talk page).
