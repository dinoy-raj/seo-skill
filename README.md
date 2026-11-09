# seo-skill

A Claude skill that runs a full SEO and page-speed pass on a website: crawlable pre-rendered pages, per-page metadata,
schema.org structured data, sitemap/robots/llms.txt, favicons and social cards, and the Core Web Vitals work that takes
mobile Lighthouse to 100 across performance, accessibility, best practices and SEO.

It is distilled from the work on [dinoyraj.com](https://dinoyraj.com): mobile LCP 5.0 s to 1.5 s, FCP 1.8 s to 0.8-1.2 s,
CLS 0.05 to 0, page weight 3.7 MB to ~1.25 MB, every route indexable with its own head and JSON-LD.

## Install

Personal (every project):

```bash
git clone https://github.com/dinoy-raj/seo-skill ~/.claude/skills/seo-skill
```

One project only (commit it so cloud sessions get it too):

```bash
git clone https://github.com/dinoy-raj/seo-skill .claude/skills/seo-skill && rm -rf .claude/skills/seo-skill/.git
```

Update later with `git -C ~/.claude/skills/seo-skill pull`.

## Use

Ask Claude in the site's repository, for example:

- "SEO optimise this site"
- "Fix the PageSpeed findings for https://example.com"
- "Make this React site crawlable and add structured data"
- "/seo-skill" (invokes it directly)

Claude audits first (baseline numbers), then works through crawlability, head tags, structured data, performance,
accessibility and hosting, re-measuring as it goes, and reports before/after.

## What's inside

| Path | Purpose |
| --- | --- |
| [`SKILL.md`](SKILL.md) | The workflow and the rules learned the hard way |
| [`references/`](references) | Audit, crawlability, head metadata, structured data, performance, accessibility, hosting |
| [`scripts/seo_audit.py`](scripts/seo_audit.py) | Static auditor for a build folder or live site (stdlib only) |
| [`scripts/prerender.js`](scripts/prerender.js) | Playwright pre-renderer for any JS site, writes sitemap.xml |
| [`scripts/subset_fonts.py`](scripts/subset_fonts.py) | Self-host and subset Google Fonts and Material Symbols |
| [`scripts/make_icons.py`](scripts/make_icons.py) | Favicons Google will show, plus a 1200x630 social card |
| [`scripts/lighthouse.sh`](scripts/lighthouse.sh) | Repeated mobile Lighthouse runs with min/median/max |
| [`templates/`](templates) | Head, after-first-paint loader, fallback fonts, robots, sitemap, llms.txt, 404, vercel.json, JSON-LD |
| [`examples/prerender-react-hydrate.js`](examples/prerender-react-hydrate.js) | The original site's React server-render pre-renderer |

## Script quick start

```bash
python3 scripts/seo_audit.py ./dist --site https://example.com
```

```bash
python3 scripts/seo_audit.py https://example.com --crawl
```

```bash
node scripts/prerender.js --root dist --site https://example.com --root-selector '#root'
```

```bash
bash scripts/lighthouse.sh https://example.com/ 5
```

Requirements: Python 3.8+ (audit), Node 18+ with Playwright (pre-render, Lighthouse), `fonttools brotli` (fonts),
`Pillow` (icons).
