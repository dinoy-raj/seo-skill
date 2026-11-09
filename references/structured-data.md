# Structured data (JSON-LD)

## Principles

- **One `<script type="application/ld+json">` per page holding an `@graph`.** Nodes reference each other by `@id`
  (`https://example.com/#person`, `.../#website`, `.../product#app`), so the same entity is described once.
- **Generate it from the data the page renders** (the arrays of apps, talks, posts, products), in a `routeJsonLd(route)`
  function next to `routeHead(route)`. Hand-written JSON-LD drifts from the page and Google penalises markup that
  doesn't match visible content.
- **Write it into the static HTML** at pre-render time (crawlers that don't run scripts still see it), between
  `<!-- seo:jsonld -->` markers. Escape `<` as `<` in the serialised JSON so `</script>` in data can't break out.
- Every page gets the identity node (Person or Organization) and a page node (`ProfilePage`, `AboutPage`,
  `CollectionPage`, `WebPage`) with `isPartOf: { '@id': SITE + '/#website' }`, a `BreadcrumbList`, and its `mainEntity`.
  The full `WebSite` node (name, url, alternateName) goes on the **home page**: that's where Google reads site names.
- Legal and 404 pages: no JSON-LD (return `null`).
- **Markup must describe what is visible on the page.** Don't add facts that aren't shown, even if true.
- **Rich results need Google's required properties** (table in google-search-docs.md). Markup without them is still
  valid schema.org and helps Google understand entities, but don't promise a rich result. Never invent ratings.
- Retired in Google Search, don't add for rich results: FAQ, HowTo, Course info, Claim review, Estimated salary, Learning
  video, Special announcement, Vehicle listing, Practice problem.
- Dates are full ISO 8601 (`2026-03-14`, or with time); month-only values (`2026-03`) are valid schema.org but not
  accepted by Google's features.
- Validate: https://validator.schema.org and Google's Rich Results Test (which shows eligibility per feature).

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

`alternateName` on WebSite is Google's documented way to suggest alternative site names (in order of preference).
For an Organization, a `logo` at least 112x112 px, crawlable, helps the logo show in results.

## Page types

```js
const crumbs = list => ({ '@type': 'BreadcrumbList', itemListElement: [['Home', '/'], ...list]
  .map(([name, path], i) => ({ '@type': 'ListItem', position: i + 1, name, item: SITE + path })) });

function routeJsonLd(r) {
  const h = routeHead(r), url = SITE + h.path;
  const page = (type, extra) => ({ '@type': type, '@id': url + '#page', url, name: h.title, description: h.desc,
    isPartOf: { '@id': SITE + '/#website' }, inLanguage: 'en', ...extra });
  const graph = [PERSON];
  if (r.page === 'home') graph.push(WEBSITE, page('ProfilePage', { '@id': SITE + '/#profile', mainEntity: { '@id': SITE + '/#person' } }), /* lists, posts */);
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
| Personal home / about page | `ProfilePage` + `Person` | `mainEntity` (required, Person with `name`), `image`, `sameAs`, `dateModified`. Google: "The primary focus of the page must be a single person or organization": an about page always fits; a home page only if it's mainly about the person. |
| Company home | `WebPage` + `Organization` | `logo`, `sameAs`, `contactPoint` |
| Mobile app | `MobileApplication` | **Google requires `name`, `offers` (`price`, `0` if free, `priceCurrency`) and `aggregateRating` or `review`** for the Software app rich result; recommended `operatingSystem`, `applicationCategory`. Only add a rating that is real and shown on the page (e.g. the store rating you display). Other useful props: `operatingSystem`, `applicationCategory` (e.g. `ProductivityApplication`, `HealthApplication`, `DeveloperApplication`, `UtilitiesApplication`), `installUrl`/`downloadUrl` (store link), `screenshot`, `image` (icon), `author`, `publisher`, `alternateName` (store tagline), `sameAs` (store, website, source), `keywords` |
| Web/desktop software | `WebApplication` / `SoftwareApplication` | same requirements as above |
| Product for sale | `Product` | `offers` (`price`, `priceCurrency`, `availability`), `brand`, `aggregateRating` only if real |
| Blog post (on its own page) | `BlogPosting` / `Article` | `headline`, `image`, full-date `datePublished`/`dateModified`, each visible author as its own `Person` with `name` (name only) and `url`. For posts hosted elsewhere (Medium), a plain list of links is enough; they don't get rich results from your page. |
| Talk / course / video | `CreativeWork`, `VideoObject`, `Course` | `abstract`, `author`, `keywords`, `uploadDate` (video) |
| Conference appearance | `Event` with the person as `performer` | Google's Event feature only covers **a page about a single event** that the public can book at a physical venue, with `name`, full-date `startDate`, `location` with `address`. A speaker's list of appearances won't get event rich results; marking them up (full dates, `performer`, `performerIn`) still links the person to the events. |
| Index of items | `CollectionPage` + `ItemList` | `ListItem` with `position`, `url`, `name` (or full `item`) |
| FAQ | `FAQPage` | **Retired** from Google Search (May 2026); skip unless another consumer needs it |

schema.org has no "speaking engagement": use `Event` with `performer: { '@id': '#person' }`, knowing it's entity data,
not a rich result.

### Example app node built from data

```js
const appNode = a => ({
  '@type': 'MobileApplication', '@id': SITE + '/' + a.slug + '#app', name: a.name, alternateName: a.store,
  url: SITE + '/' + a.slug, description: a.seo || a.desc, operatingSystem: 'Android',
  applicationCategory: CATEGORY[a.id] || 'UtilitiesApplication', image: SITE + '/assets/apps/' + a.id + '-icon.webp',
  screenshot: a.shots.map((_, i) => SITE + shot(a, i + 1)), author: { '@id': SITE + '/#person' }, publisher: { '@id': SITE + '/#person' },
  keywords: a.tags.join(', '),
  offers: { '@type': 'Offer', price: a.price || 0, priceCurrency: 'USD' },                       // required by Google
  ...(a.rating ? { aggregateRating: { '@type': 'AggregateRating', ratingValue: a.rating.value, ratingCount: a.rating.count } } : {}), // only if real and shown on the page
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
