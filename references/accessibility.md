# Accessibility and best-practice fixes Lighthouse asks for

PageSpeed shows four scores; SEO work is judged with all of them. These are the findings that came up and their fixes.

| Lighthouse audit | Cause | Fix |
| --- | --- | --- |
| `aria-prohibited-attr` / "elements use prohibited ARIA" | `aria-label` on `<p>`, `<div>`, `<span>` (not allowed on generic roles) | Put the text in a visually hidden `.sr-only` span; mark the decorative version `aria-hidden="true"` |
| `label-content-name-mismatch` | `aria-label` on a link that doesn't contain its visible text (e.g. drops the subtitle) | Remove the `aria-label`, let the name come from visible text; or make the label start with the visible text |
| `link-name` / identical links with different targets | Several "Google Play" / "Source" links | Per-item accessible names: `aria-label="Dino Launcher on Google Play"` (containing the visible text) |
| `heading-order` | Footer headings jump h2 to h4 | Use the next level (h3); style with classes, not tag choice |
| `color-contrast` | Muted/"unlit" text, small labels on tinted backgrounds | Darken to at least 4.5:1 (3:1 for 24px+ or 18.66px bold); check every state, including animated "unlit" words |
| `nested-interactive` / buttons in links | `<a><button>..</button></a>` | Style the link as a button; one interactive element |
| `image-alt` | Missing `alt` | Meaningful `alt` for content images (`"App name: what the screenshot shows"`), `alt=""` for decorative ones |
| `document-title`, `html-has-lang`, `meta-viewport` | Missing basics | See head-metadata.md; don't disable zoom (`user-scalable=no`) |
| `errors-in-console` | Hydration errors (React #418/#423), 404s for `/favicon.ico` | Regenerate the pre-render; add favicon.ico; fix missing files |
| `inspector-issues` / third-party cookies | Embedded widgets | Load embeds on interaction (facade) |
| `csp-xss`, `has-hsts`, `origin-isolation` (best-practice diagnostics) | Missing headers | Security headers in hosting.md |

General rules:

- `.sr-only { position:absolute; width:1px; height:1px; margin:-1px; padding:0; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0 }`
- Decorative text drawn with CSS `content: attr(data-*)` is not read or indexed; keep the real text in the DOM.
- Menus: `inert` on closed menu links, Escape closes and returns focus, a real `<button>` toggles.
- Respect `prefers-reduced-motion` for every animation.
- Tap targets at least 24x24 CSS px (48 recommended) with spacing.
