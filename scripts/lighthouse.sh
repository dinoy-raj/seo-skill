#!/usr/bin/env bash
# Repeated mobile Lighthouse runs with a min/median/max summary. One run is noise; compare ranges.
#   bash lighthouse.sh https://example.com/ [runs=5] [mobile|desktop]
# Needs Node. Uses $CHROME_PATH, else Playwright's Chromium if found, else the system Chrome.
# Reports land in ./lighthouse-reports/<host>-<n>.json (open in https://googlechrome.github.io/lighthouse/viewer/).
set -euo pipefail
URL=${1:?usage: lighthouse.sh URL [runs] [mobile|desktop]}
RUNS=${2:-5}
FORM=${3:-mobile}
if [ -z "${CHROME_PATH:-}" ]; then
  for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome /opt/pw-browsers/chromium; do [ -x "$c" ] && CHROME_PATH=$c && break; done
  [ -z "${CHROME_PATH:-}" ] && CHROME_PATH=$(node -e "try{console.log(require('playwright').chromium.executablePath())}catch(e){}" 2>/dev/null || true)
fi
[ -n "${CHROME_PATH:-}" ] && export CHROME_PATH
OUT=lighthouse-reports; mkdir -p "$OUT"
HOST=$(echo "$URL" | sed -E 's#https?://##; s#[/:?&=]+#_#g; s#_$##')
PRESET=(); [ "$FORM" = desktop ] && PRESET=(--preset=desktop)
for i in $(seq 1 "$RUNS"); do
  npx -y lighthouse@12 "$URL" --quiet --output=json --output-path="$OUT/$HOST-$i.json" \
    --chrome-flags="--headless=new --no-sandbox" "${PRESET[@]}" >/dev/null 2>&1 || echo "run $i failed"
done
node - "$OUT" "$HOST" "$RUNS" <<'JS'
const fs = require('fs'), [dir, host, runs] = process.argv.slice(2);
const rows = [];
for (let i = 1; i <= +runs; i++) { try { rows.push(JSON.parse(fs.readFileSync(`${dir}/${host}-${i}.json`, 'utf8'))); } catch (e) {} }
if (!rows.length) { console.error('no reports'); process.exit(1); }
const stat = f => { const v = rows.map(f).filter(x => x != null).sort((a, b) => a - b); return v.length ? [v[0], v[v.length >> 1], v[v.length - 1]] : ['-', '-', '-']; };
const cat = k => r => r.categories[k] && Math.round(r.categories[k].score * 100);
const ms = k => r => r.audits[k] && r.audits[k].numericValue;
const lines = [
  ['performance', stat(cat('performance'))], ['accessibility', stat(cat('accessibility'))],
  ['best-practices', stat(cat('best-practices'))], ['seo', stat(cat('seo'))],
  ['LCP s', stat(ms('largest-contentful-paint')).map(x => typeof x === 'number' ? (x / 1000).toFixed(2) : x)],
  ['FCP s', stat(ms('first-contentful-paint')).map(x => typeof x === 'number' ? (x / 1000).toFixed(2) : x)],
  ['TBT ms', stat(ms('total-blocking-time')).map(x => typeof x === 'number' ? Math.round(x) : x)],
  ['CLS', stat(ms('cumulative-layout-shift')).map(x => typeof x === 'number' ? x.toFixed(3) : x)],
  ['Speed Index s', stat(ms('speed-index')).map(x => typeof x === 'number' ? (x / 1000).toFixed(2) : x)],
  ['bytes KB', stat(ms('total-byte-weight')).map(x => typeof x === 'number' ? Math.round(x / 1024) : x)],
];
console.log(`${rows.length} runs of ${rows[0].finalDisplayedUrl}\n${'metric'.padEnd(16)}min      median   max`);
for (const [k, [a, m, z]] of lines) console.log(k.padEnd(16) + String(a).padEnd(9) + String(m).padEnd(9) + z);
const last = rows[rows.length - 1];
const lcpEl = last.audits['largest-contentful-paint-element'];
const item = lcpEl && lcpEl.details && (lcpEl.details.items[0]?.items?.[0]?.node || lcpEl.details.items[0]?.node);
if (item) console.log('\nLCP element: ' + (item.snippet || item.selector));
const failing = Object.values(last.audits).filter(a => a.score !== null && a.score < 0.9 && a.scoreDisplayMode !== 'informative' && a.scoreDisplayMode !== 'notApplicable' && a.scoreDisplayMode !== 'manual');
if (failing.length) { console.log('\nAudits below 90 (last run):'); for (const a of failing) console.log(`  ${a.id}: ${a.title}${a.displayValue ? ' (' + a.displayValue + ')' : ''}`); }
JS
