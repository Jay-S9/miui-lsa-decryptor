# Third-party notices

The hosted web version serves these files itself, so a visitor's browser never has to contact another site to load them.

| Component | Version | Licence | Where | Source |
|---|---|---|---|---|
| [JSZip](https://stuk.github.io/jszip/) | 3.10.1 | MIT OR GPL-3.0-or-later (used here under MIT) | `vendor/jszip-3.10.1.min.js` | npm package `jszip@3.10.1`, `dist/jszip.min.js` |
| [Syne](https://gitlab.com/bonjour-monde/fonderie/syne-typeface) | via Fontsource | SIL Open Font License 1.1 | `fonts/syne-latin-*.woff2` | npm package `@fontsource/syne` |
| [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) | via Fontsource | SIL Open Font License 1.1 | `fonts/jetbrains-mono-latin-*.woff2` | npm package `@fontsource/jetbrains-mono` |

Font licence texts are in [`fonts/OFL-LICENSES.txt`](fonts/OFL-LICENSES.txt).

## Integrity of the vendored JSZip file

```
sha256  acc7e41455a80765b5fd9c7ee1b8078a6d160bbbca455aeae854de65c947d59e  vendor/jszip-3.10.1.min.js
```

Check it with `sha256sum vendor/jszip-3.10.1.min.js` (Linux/macOS) or `Get-FileHash vendor\jszip-3.10.1.min.js -Algorithm SHA256` (PowerShell).
To upgrade JSZip: fetch the new version from npm, replace the file, rename it with the new version number (the filename is cached forever), and update this table and `index.html`/`vercel.json`.

## Analytics

The hosted site uses [Vercel Web Analytics](https://vercel.com/docs/analytics) for anonymous page-view counts. Its script is served from this site's own domain (`/_vercel/insights/script.js`).
