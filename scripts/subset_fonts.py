"""Self-host Google Fonts, cut down to what the site uses.

    pip install fonttools brotli
    python3 subset_fonts.py                  # uses the CONFIG block below
    python3 subset_fonts.py --html index.html other.html --out assets/fonts

What it does (each step measured on a real site):
- Downloads the families from Google Fonts (no render-blocking third-party CSS, no HTML -> CSS -> font chain).
- Trims each variable font to the axis ranges in AXES (Google Sans Flex 117 KB -> 54 KB).
- Keeps only the characters in LATIN for the "latin" file; "math"/"symbols" files stay as separate faces that a
  browser fetches only when a page uses such a character (unicode-range).
- Icon font (Material Symbols): only the glyphs named in ICONS (3.1 MB -> ~5 KB).
- Writes content-hashed files (serve them with Cache-Control: public, max-age=31536000, immutable).
- Rewrites the block between <!-- fonts:start --> and <!-- fonts:end --> in each HTML file with:
    a preload for the font that draws the LCP text, inline @font-face rules (no CSS request),
    and a <template id="late-fonts"> holding families nothing in the first screen uses, which the page adds after
    first paint (templates/after-fcp-loader.html).
Add the markers to your <head> once:  <!-- fonts:start --><!-- fonts:end -->
To add an icon, add its name to ICONS and re-run. Re-run after changing weights or families.
"""
import argparse, hashlib, io, os, re, urllib.request
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

# ---------------------------------------------------------------- CONFIG: edit for each site
# Google Fonts CSS2 URLs for the text families, exactly as the site used them (ask only for weights/axes in use).
TEXT_CSS = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400..700&display=swap",
    # "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;1,9..144,500&display=swap",
]
# Material Symbols glyphs the site uses (empty list = no icon font). Find them with:
#   grep -oh 'data-icon="[a-z_0-9]*"' -r src | sort -u      (or whatever your icon component renders)
ICONS = []
ICON_FAMILY = "Material+Symbols+Rounded"  # or Material+Symbols+Outlined / Sharp
ICON_AXES = "opsz,wght,FILL,GRAD@24,400,0..1,0"
# Axis ranges the site uses, per family slug (lowercase, spaces -> dashes). Families not listed are kept as served.
AXES = {
    "inter": {"wght": (400, 700)},
    # "google-sans-flex": {"wdth": (62, 100), "wght": (400, 700)},
}
LATIN = ("U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+02C6,U+02DA,U+02DC,U+2013-2014,"
         "U+2018-201E,U+2022,U+2026,U+2039-203A,U+20AC,U+2122")
SUBSETS = {"latin", "math", "symbols"}  # add "latin-ext", "cyrillic", ... if the content needs them
LATE = set()            # family slugs nothing in the first screen uses, e.g. {"fraunces"}
PRELOAD = "inter-latin"  # "<family-slug>-<subset>" of the font that draws the LCP text ("" for none)
OUT = "assets/fonts"     # folder on disk
URL_PREFIX = "/assets/fonts/"  # how pages reference it
HTML = ["index.html"]    # files whose fonts:start/end block is rewritten
# ----------------------------------------------------------------

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"  # woff2 + unicode-range


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read()


def trim(raw, family, sub):
    font = TTFont(io.BytesIO(raw))
    if family in AXES and "fvar" in font:
        font = instancer.instantiateVariableFont(font, AXES[family])
        buf = io.BytesIO(); font.flavor = None; font.save(buf); buf.seek(0); font = TTFont(buf)
    opts = subset.Options()
    opts.flavor = "woff2"; opts.layout_features = ["*"]; opts.hinting = False
    opts.desubroutinize = True; opts.name_IDs = ["*"]; opts.notdef_outline = True
    s = subset.Subsetter(opts)
    s.populate(unicodes=subset.parse_unicodes(LATIN) if sub == "latin" else list(font.getBestCmap()))
    s.subset(font)
    buf = io.BytesIO(); font.flavor = "woff2"; font.save(buf)
    return buf.getvalue()


def main():
    global OUT, HTML
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", nargs="*"); ap.add_argument("--out")
    a = ap.parse_args()
    HTML = a.html or HTML; OUT = a.out or OUT

    blocks = []
    for url in TEXT_CSS:
        blocks += re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", get(url).decode(), re.S)
    if ICONS:
        icon_css = (f"https://fonts.googleapis.com/css2?family={ICON_FAMILY}:{ICON_AXES}"
                    f"&icon_names={','.join(sorted(set(ICONS)))}&display=swap")
        blocks.append(("icons", re.search(r"@font-face \{.*?\}", get(icon_css).decode(), re.S).group(0)))

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".woff2"):
            os.remove(os.path.join(OUT, f))
    faces, late, names, total = [], [], {}, 0
    for sub, block in blocks:
        if sub not in SUBSETS and sub != "icons":
            continue
        url = re.search(r"url\((.*?)\)", block).group(1)
        family = re.search(r"font-family: '([^']+)'", block).group(1).lower().replace(" ", "-")
        if url not in names:
            data = get(url)
            if sub != "icons":
                data = trim(data, family, sub)
            names[url] = f"{family}-{sub}-{hashlib.sha1(data).hexdigest()[:8]}.woff2"
            with open(os.path.join(OUT, names[url]), "wb") as f:
                f.write(data)
            total += len(data)
            print(f"{names[url]}  {len(data) // 1024} KB")
        block = block.replace(url, URL_PREFIX + names[url])
        if sub == "latin":
            block = re.sub(r"unicode-range:[^;]*;", "unicode-range: " + LATIN.replace(",", ", ") + ";", block)
        if sub == "icons":
            block = block.replace("font-display: block", "font-display: swap")  # hide ligature text with a class instead (templates/fallback-fonts.css)
        (late if family in LATE else faces).append(re.sub(r"\s*\n\s*", " ", block).replace("{ ", "{").replace("; }", ";}"))
    print(f"total {total // 1024} KB in {len(names)} files")

    preload = next((n for n in names.values() if PRELOAD and n.startswith(PRELOAD + "-")), None)
    new = ("<!-- fonts:start -->\n"
           + (f'<link rel="preload" as="font" type="font/woff2" href="{URL_PREFIX}{preload}" crossorigin>\n' if preload else "")
           + "<style>\n" + "\n".join(faces) + "\n</style>\n"
           + ('<template id="late-fonts"><style>\n' + "\n".join(late) + "\n</style></template>\n" if late else "")
           + "<!-- fonts:end -->")
    for path in HTML:
        html = open(path, encoding="utf-8").read()
        html, n = re.subn(r"<!-- fonts:start -->.*?<!-- fonts:end -->", lambda m: new, html, flags=re.S)
        if n != 1:
            raise SystemExit(f"{path}: add <!-- fonts:start --><!-- fonts:end --> to <head> first")
        open(path, "w", encoding="utf-8").write(html)
        print(f"updated {path}")
    if PRELOAD and not preload:
        print(f"warning: no file matched PRELOAD={PRELOAD!r}; names are " + ", ".join(names.values()))


if __name__ == "__main__":
    main()
