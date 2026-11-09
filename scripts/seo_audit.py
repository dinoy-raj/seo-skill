#!/usr/bin/env python3
"""Static SEO audit for a build folder or a live site. Standard library only.

    python3 seo_audit.py ./dist                       # every .html file in a folder
    python3 seo_audit.py ./dist --site https://example.com   # also check canonicals/sitemap against this origin
    python3 seo_audit.py https://example.com          # one live page plus robots.txt / sitemap.xml
    python3 seo_audit.py https://example.com --crawl  # every URL in the live sitemap (up to --max)
    python3 seo_audit.py ./dist --json                # machine-readable output

Checks per page: <html lang>, viewport, title and description presence and length, canonical, robots meta,
Open Graph and Twitter tags, one <h1> with real words (no icon ligature names), heading order (accessibility), JSON-LD parses, full ISO dates,
Google's required properties for Software app / Event / ProfilePage / Breadcrumb, retired types (FAQ, HowTo), images missing alt/width/height, pages with almost no text before JavaScript runs.
Checks per site: robots.txt (exists, has Sitemap), sitemap.xml (parses, URLs map to pages, no noindex pages
in it, indexable pages missing from it, lastmod that looks like a build date), robots.txt Disallow rules that hide a
noindex (meta or vercel.json X-Robots-Tag), duplicate titles/descriptions, 404.html.
Severity: ERROR breaks indexing or a Google requirement, WARN is likely a problem, NOTE is informational (things Google
says don't matter for ranking, or markup that won't get a rich result). Exit code 1 if any ERROR.
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request
from html.parser import HTMLParser
from xml.etree import ElementTree

UA = "Mozilla/5.0 (compatible; seo-audit/1.0)"
TITLE = (30, 65)
DESC = (70, 170)
OG_REQUIRED = ["og:title", "og:description", "og:url", "og:image", "og:type"]
TW_REQUIRED = ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]
LIGATURE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")  # e.g. waving_hand, arrow_forward


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None; self.title = None; self.meta = {}; self.links = []; self.headings = []
        self.jsonld = []; self.images = []; self.text = []; self.anchors = []
        self._stack = []; self._skip = 0; self._cur_heading = None; self._in_title = False; self._in_ld = False; self._ld = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html": self.lang = a.get("lang")
        elif tag == "title": self._in_title = True; self.title = ""
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key: self.meta.setdefault(key.lower(), a.get("content", ""))
        elif tag == "link": self.links.append(a)
        elif tag == "img": self.images.append(a)
        elif tag == "a" and "href" in a: self.anchors.append(a["href"])
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json": self._in_ld = True; self._ld = []
        if tag in ("script", "style", "template", "noscript", "svg"): self._skip += 1
        if re.fullmatch(r"h[1-6]", tag): self._cur_heading = [int(tag[1]), ""]

    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
        if tag == "script" and self._in_ld: self._in_ld = False; self.jsonld.append("".join(self._ld))
        if tag in ("script", "style", "template", "noscript", "svg"): self._skip = max(0, self._skip - 1)
        if re.fullmatch(r"h[1-6]", tag) and self._cur_heading:
            self.headings.append((self._cur_heading[0], re.sub(r"\s+", " ", self._cur_heading[1]).strip())); self._cur_heading = None

    def handle_data(self, data):
        if self._in_ld: self._ld.append(data); return
        if self._in_title: self.title += data; return
        if self._skip: return
        self.text.append(data)
        if self._cur_heading: self._cur_heading[1] += data


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def types_of(node, out):
    if isinstance(node, dict):
        t = node.get("@type")
        if t: out.extend(t if isinstance(t, list) else [t])
        for v in node.values(): types_of(v, out)
    elif isinstance(node, list):
        for v in node: types_of(v, out)
    return out


def audit_page(name, html):
    p = Page(); p.feed(html)
    issues = []
    err = lambda m: issues.append(("ERROR", m))
    warn = lambda m: issues.append(("WARN", m))
    note = lambda m: issues.append(("NOTE", m))  # worth knowing, not counted: Google doesn't require it
    robots = p.meta.get("robots", "")
    noindex = "noindex" in robots.lower()
    title = (p.title or "").strip()
    desc = p.meta.get("description", "").strip()
    canon = next((l.get("href") for l in p.links if "canonical" in l.get("rel", "").lower().split()), None)

    if not p.lang: err("<html> has no lang attribute")
    if "viewport" not in p.meta: err("no meta viewport")
    elif "user-scalable=no" in p.meta["viewport"].replace(" ", "") or "maximum-scale=1" in p.meta["viewport"].replace(" ", ""):
        warn("viewport disables zoom")
    if not title: err("no <title>")
    elif not noindex and not (TITLE[0] <= len(title) <= TITLE[1]): note(f"title is {len(title)} chars; Google has no limit but shows about {TITLE[1]} before truncating: {title!r}")
    if not noindex:
        if not desc: err("no meta description")
        elif not (DESC[0] <= len(desc) <= DESC[1]): note(f"description is {len(desc)} chars; no limit, but about {DESC[1]} show before truncation")
        if not canon: err("no canonical link")
        elif not canon.startswith("http"): warn(f"canonical is not absolute: {canon}")
        missing = [k for k in OG_REQUIRED if k not in p.meta]
        if missing: err("missing Open Graph: " + ", ".join(missing))
        if "og:image" in p.meta and not p.meta["og:image"].startswith("http"): err("og:image is not an absolute URL")
        if "og:image" in p.meta and ("og:image:width" not in p.meta or "og:image:alt" not in p.meta): warn("og:image without width/height/alt")
        missing = [k for k in TW_REQUIRED if k not in p.meta]
        if missing: warn("missing Twitter: " + ", ".join(missing))
        if canon and p.meta.get("og:url") and p.meta["og:url"] != canon: warn(f"og:url {p.meta['og:url']} != canonical {canon}")
    icons = [l for l in p.links if "icon" in l.get("rel", "").lower().split() or l.get("rel", "").lower() == "shortcut icon"]
    if not icons: warn("no favicon link")
    elif all(l.get("href", "").lower().split("?")[0].endswith(".svg") for l in icons): warn("only an SVG favicon: Google lists BMP, GIF, ICO, PNG, JPEG; add a PNG/ICO larger than 48x48")
    if "keywords" in p.meta: note("meta keywords is ignored by Google")

    h1 = [t for lvl, t in p.headings if lvl == 1]
    if not noindex:
        if len(h1) == 0: warn("no <h1>: Google uses the main heading for title links (and screen readers need it)")
        elif len(h1) > 1: note(f"{len(h1)} <h1> elements (fine for Google; one clear main title helps title links): {h1}")
    for lvl, t in p.headings:
        if LIGATURE.search(t): warn(f"h{lvl} text contains an icon-like token: {t!r} (draw icons from a data attribute)")
        if not t: warn(f"empty h{lvl}")
    prev = 0
    for lvl, t in p.headings:
        if prev and lvl > prev + 1: note(f"heading order jumps h{prev} -> h{lvl} ({t!r}): an accessibility issue, not a ranking one"); break
        prev = lvl

    types, nodes = [], []
    for raw in p.jsonld:
        try: data = json.loads(raw); types_of(data, types); collect(data, nodes)
        except Exception as e: err(f"JSON-LD does not parse: {e}")
    for msg in check_rich_results(nodes): (note if msg.startswith("(not eligible)") else warn)(msg)
    if not noindex and not p.jsonld: warn("no JSON-LD structured data")

    no_alt = [i.get("src", "?") for i in p.images if "alt" not in i]
    no_dim = [i.get("src", "?") for i in p.images if not (i.get("width") and i.get("height"))]
    if no_alt: err(f"{len(no_alt)} <img> without alt, e.g. {no_alt[0]}")
    if no_dim: warn(f"{len(no_dim)} <img> without width/height (layout shift), e.g. {no_dim[0]}")

    words = len(re.findall(r"\w+", " ".join(p.text)))
    # Google has no word-count target; this only catches pages that are empty until JavaScript runs.
    if not noindex and words < 50: err(f"only {words} words of text in the HTML: the page looks client-rendered (pre-render it)")

    return {"page": name, "title": title, "description": desc, "canonical": canon, "noindex": noindex, "words": words,
            "h1": h1, "jsonld_types": sorted(set(types)), "anchors": p.anchors, "issues": issues}


DATE_KEYS = ("startDate", "endDate", "datePublished", "dateModified", "uploadDate", "dateCreated")
RETIRED = {"FAQPage", "HowTo", "ClaimReview", "SpecialAnnouncement", "Quiz"}


def collect(node, out):
    if isinstance(node, dict):
        if "@type" in node: out.append(node)
        for v in node.values(): collect(v, out)
    elif isinstance(node, list):
        for v in node: collect(v, out)
    return out


def check_rich_results(nodes):
    """Google's required properties for the rich results these types are usually added for (Search Central docs)."""
    msgs = []
    for n in nodes:
        t = n["@type"] if isinstance(n["@type"], list) else [n["@type"]]
        name = n.get("name") or n.get("headline") or n.get("@id") or t[0]
        for k in DATE_KEYS:
            v = n.get(k)
            if isinstance(v, str) and re.fullmatch(r"\d{4}(-\d{2})?", v): msgs.append(f"{t[0]} {name!r}: {k} {v!r} is not a full ISO 8601 date (Google needs YYYY-MM-DD)")
        if RETIRED & set(t): msgs.append(f"{'/'.join(t)} rich results are retired in Google Search; markup brings no rich result")
        if {"SoftwareApplication", "MobileApplication", "WebApplication"} & set(t):
            miss = [x for x in ("offers",) if x not in n] + ([] if ("aggregateRating" in n or "review" in n) else ["aggregateRating or review"])
            if miss: msgs.append(f"(not eligible) {t[0]} {name!r} lacks {', '.join(miss)} required for Google's Software app rich result")
        if "Event" in t:
            loc = n.get("location") if isinstance(n.get("location"), dict) else {}
            miss = [x for x in ("name", "startDate") if x not in n] + ([] if loc.get("address") else ["location.address"])
            if miss: msgs.append(f"Event {name!r} lacks {', '.join(miss)} (required by Google)")
        if "ProfilePage" in t and "mainEntity" not in n: msgs.append("ProfilePage without mainEntity (required)")
        if "BreadcrumbList" in t and len(n.get("itemListElement", [])) < 2: msgs.append("BreadcrumbList needs at least two items")
    events = [n for n in nodes if "Event" in (n["@type"] if isinstance(n["@type"], list) else [n["@type"]])]
    if len(events) > 1: msgs.append(f"(not eligible) {len(events)} Events on one page: Google's event rich results need one event per page")
    return msgs


def disallow_conflicts(robots_txt, noindex_paths):
    """robots.txt Disallow hides a page's noindex from Google, so the page can still be indexed from links."""
    rules = re.findall(r"(?im)^disallow:\s*(/\S*)", robots_txt)
    return [(rule, path) for path in noindex_paths for rule in rules if rule != "/" and path.startswith(rule.rstrip("*$"))]


def html_files(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".") and x not in ("node_modules",)]
        for f in files:
            if f.endswith(".html"): yield os.path.join(d, f)


def route_of(root, path):
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    if rel == "index.html": return "/"
    if rel.endswith("/index.html"): return "/" + rel[: -len("/index.html")]
    return "/" + rel[: -len(".html")]


def parse_sitemap(xml):
    root = ElementTree.fromstring(xml)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [(u.findtext("s:loc", namespaces=ns) or "").strip() for u in root.findall("s:url", ns)], \
           [(u.findtext("s:loc", namespaces=ns) or "").strip() for u in root.findall("s:sitemap", ns)]


def sitemap_notes(xml):
    out = []
    if re.search(r"<(priority|changefreq)>", xml): out.append(("NOTE", "sitemap has priority/changefreq, which Google ignores"))
    dates = re.findall(r"<lastmod>([^<]+)</lastmod>", xml)
    if len(dates) >= 5 and len(set(dates)) == 1:
        out.append(("WARN", f"all {len(dates)} sitemap lastmod values are {dates[0]}: if that's the build date, Google stops trusting lastmod; use each page's real last change"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target"); ap.add_argument("--site", help="production origin, e.g. https://example.com")
    ap.add_argument("--crawl", action="store_true"); ap.add_argument("--max", type=int, default=200)
    ap.add_argument("--exclude", action="append", default=[], help="skip routes starting with this path (repeatable); robots.txt Disallow paths are skipped too")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--quiet", action="store_true", help="only pages with issues")
    a = ap.parse_args()

    results, site_issues = [], []
    serr = lambda m: site_issues.append(("ERROR", m)); swarn = lambda m: site_issues.append(("WARN", m))
    live = a.target.startswith("http")

    if live:
        origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(a.target))
        site = a.site or origin
        urls = [a.target]
        robots = ""
        try:
            st, robots = fetch(origin + "/robots.txt")
            if "sitemap:" not in robots.lower(): swarn("robots.txt has no Sitemap: line")
            if re.search(r"(?im)^disallow:\s*/\s*$", robots): serr("robots.txt disallows the whole site")
        except Exception as e: serr(f"robots.txt: {e}")
        sitemap = []
        try:
            _, xml = fetch(origin + "/sitemap.xml"); sitemap, children = parse_sitemap(xml); site_issues.extend(sitemap_notes(xml))
            for c in children[:20]:
                try: sitemap += parse_sitemap(fetch(c)[1])[0]
                except Exception as e: swarn(f"child sitemap {c}: {e}")
        except Exception as e: serr(f"sitemap.xml: {e}")
        if a.crawl:
            norm = lambda u: u if urllib.parse.urlparse(u).path else u + "/"
            urls = list(dict.fromkeys(norm(u) for u in [a.target] + sitemap))[: a.max]
            sitemap = [norm(u) for u in sitemap]
        for u in urls:
            try:
                st, html = fetch(u); r = audit_page(u, html)
                if r["noindex"] and u in sitemap: r["issues"].append(("ERROR", "noindex page is listed in sitemap.xml"))
                results.append(r)
            except Exception as e: results.append({"page": u, "issues": [("ERROR", f"fetch failed: {e}")]})
        try:
            urllib.request.urlopen(urllib.request.Request(origin + "/this-page-should-not-exist-404", headers={"User-Agent": UA}), timeout=20)
            serr("unknown URL returned 200 (soft 404); serve 404.html with a 404 status")
        except urllib.error.HTTPError as e:
            if e.code != 404: swarn(f"unknown URL returned {e.code}, expected 404")
        except Exception: pass
    else:
        root = os.path.abspath(a.target); site = (a.site or "").rstrip("/")
        pages = {}
        skip = list(a.exclude)
        rp = os.path.join(root, "robots.txt")
        robots_txt = open(rp).read() if os.path.exists(rp) else ""
        skip += re.findall(r"(?im)^disallow:\s*(/\S+)", robots_txt)
        # noindex sent by headers (vercel.json X-Robots-Tag) or meta, checked against Disallow rules
        noindexed = []
        vp = os.path.join(root, "vercel.json")
        if os.path.exists(vp):
            try:
                for h in json.load(open(vp)).get("headers", []):
                    if any(x.get("key", "").lower() == "x-robots-tag" and "noindex" in x.get("value", "").lower() for x in h.get("headers", [])):
                        noindexed.append(re.sub(r"\(\.\*\)|:path\*|\*.*$", "", h.get("source", "")))
            except Exception as e: swarn(f"vercel.json: {e}")
        for f in html_files(root):
            if re.search(r"<meta[^>]+name=[\"']robots[\"'][^>]+noindex", open(f, encoding="utf-8", errors="replace").read(), re.I):
                noindexed.append(route_of(root, f))
        for rule, path in disallow_conflicts(robots_txt, noindexed):
            serr(f"robots.txt 'Disallow: {rule}' blocks {path}, so Google never sees its noindex and may index it from links; remove the Disallow")
        for f in sorted(html_files(root)):
            rel = os.path.relpath(f, root)
            if any(route_of(root, f).startswith(x.rstrip("*")) or ("/" + rel).startswith(x.rstrip("*")) for x in skip): continue
            if os.path.basename(f) == "404.html": continue
            r = audit_page(rel, open(f, encoding="utf-8", errors="replace").read())
            r["route"] = route_of(root, f); pages[r["route"]] = r; results.append(r)
            if site and r["canonical"] and not r["noindex"] and r["canonical"].rstrip("/") != (site + r["route"]).rstrip("/"):
                r["issues"].append(("WARN", f"canonical {r['canonical']} does not match its route {site + r['route']}"))
        if not os.path.exists(os.path.join(root, "404.html")): swarn("no 404.html")
        rp = os.path.join(root, "robots.txt")
        if not os.path.exists(rp): serr("no robots.txt")
        else:
            robots = open(rp).read()
            if "sitemap:" not in robots.lower(): swarn("robots.txt has no Sitemap: line")
            if re.search(r"(?im)^disallow:\s*/\s*$", robots): serr("robots.txt disallows the whole site")
        sp = os.path.join(root, "sitemap.xml")
        if not os.path.exists(sp): serr("no sitemap.xml")
        else:
            try:
                xml = open(sp, encoding="utf-8").read()
                locs, _ = parse_sitemap(xml)
                site_issues.extend(sitemap_notes(xml))
                in_map = set()
                for loc in locs:
                    path = urllib.parse.urlparse(loc).path or "/"
                    path = path.rstrip("/") or "/"
                    in_map.add(path)
                    if path not in pages: serr(f"sitemap URL has no page in the folder: {loc}")
                    elif pages[path]["noindex"]: pages[path]["issues"].append(("ERROR", "noindex page is listed in sitemap.xml"))
                if site:
                    for loc in locs:
                        if not loc.startswith(site): swarn(f"sitemap URL not on {site}: {loc}")
                for route, r in pages.items():
                    if not r["noindex"] and route not in in_map: r["issues"].append(("WARN", "indexable page missing from sitemap.xml"))
            except Exception as e: serr(f"sitemap.xml does not parse: {e}")
        # Orphans: indexable pages no other page links to.
        linked = set()
        for r in results:
            for h in r.get("anchors", []):
                u = urllib.parse.urlparse(h)
                if u.netloc and site and not h.startswith(site): continue
                if u.netloc and not site: continue
                path = (u.path.rstrip("/") or "/") if u.path else None
                if path: linked.add(path)
        for route, r in pages.items():
            if route != "/" and not r["noindex"] and route not in linked: r["issues"].append(("WARN", "orphan page: no internal <a href> points to it"))

    if live:
        for rule, path in disallow_conflicts(robots, [urllib.parse.urlparse(r["page"]).path for r in results if r.get("noindex")]):
            serr(f"robots.txt 'Disallow: {rule}' blocks noindex page {path}")

    seen_t, seen_d = {}, {}
    for r in results:
        if r.get("noindex") or not r.get("title"): continue
        seen_t.setdefault(r["title"], []).append(r["page"])
        if r.get("description"): seen_d.setdefault(r["description"], []).append(r["page"])
    for t, ps in seen_t.items():
        if len(ps) > 1: swarn(f"duplicate title on {len(ps)} pages: {t!r} ({', '.join(ps[:4])})")
    for d, ps in seen_d.items():
        if len(ps) > 1: swarn(f"duplicate description on {len(ps)} pages ({', '.join(ps[:4])})")

    errors = sum(1 for r in results for s, _ in r["issues"] if s == "ERROR") + sum(1 for s, _ in site_issues if s == "ERROR")
    warns = sum(1 for r in results for s, _ in r["issues"] if s == "WARN") + sum(1 for s, _ in site_issues if s == "WARN")
    if a.json:
        for r in results: r.pop("anchors", None)
        print(json.dumps({"site": site_issues, "pages": results, "errors": errors, "warnings": warns}, indent=1))
    else:
        for r in results:
            if a.quiet and not r["issues"]: continue
            flag = " [noindex]" if r.get("noindex") else ""
            print(f"\n== {r['page']}{flag}")
            if "title" in r:
                print(f"   title: {r['title']!r}  words: {r['words']}  h1: {r['h1']}  json-ld: {', '.join(r['jsonld_types']) or '-'}")
            for s, m in r["issues"]: print(f"   {s:5} {m}")
        print("\n== site")
        for s, m in site_issues: print(f"   {s:5} {m}")
        notes = sum(1 for r in results for s, _ in r["issues"] if s == "NOTE") + sum(1 for s, _ in site_issues if s == "NOTE")
        print(f"\n{len(results)} pages, {errors} errors, {warns} warnings, {notes} notes")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
