# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

- Use GitHub's private reporting: the repository's **Security** tab → **Report a vulnerability**.
- Or email **solanki9jay@email.com** with a description and, if possible, steps to reproduce.

Please do not attach real private photos or videos — a synthetic file is enough to show a problem.

Supported: the latest release and the `main` branch.

## What this project tries to guarantee

1. **A malicious or malformed file never runs code and never crashes the tool.** File names and messages are always rendered as plain text, never as HTML.
2. **Your files stay on your device.** The web version decrypts inside your browser tab; the desktop app and CLI never use the network.
3. **What you download is what was built.** Releases are built by a GitHub Actions workflow with least-privilege permissions and pinned actions, and publish a SHA-256 checksum next to the `.exe`.

## How that is enforced

| Area | Measure |
|---|---|
| Rendering | File rows are built with `createElement` + `textContent`; no HTML is ever built from file names. |
| Content-Security-Policy | `script-src` allows only this site (no `'unsafe-inline'`); no inline scripts or event handlers exist. `object-src`, `base-uri`, `form-action` and `frame-ancestors` are `'none'`. |
| Network | `app.js` contains no `fetch`/XHR/WebSocket/`sendBeacon` calls. `connect-src` is limited to this site. |
| Third parties | JSZip and fonts are served from this site (see `THIRD_PARTY_NOTICES.md`). |
| Resource limits | Web version: at most 500 queued files, photos up to 150 MB, ZIP memory budget. Videos are not loaded into memory. Desktop/CLI process files in 1 MiB chunks. |
| Output safety | The Python engine writes to a temporary file and renames it on success, never overwrites an existing file, and keeps outputs inside the chosen folder. |
| Release pipeline | Build job is read-only; only the publish job can write to the release. Actions are pinned to commit SHAs. |

## Verify the privacy claim yourself

Open the web version, press **F12 → Network**, then select and decrypt a file. After the page has loaded, no request carrying your data is made. You can also read `app.js` — it is a single, short, unminified file.

## Known limitations

- `style-src` still allows `'unsafe-inline'` because the page uses inline styles.
- The hosted page loads Vercel's analytics script (served from this site's domain). The app never hands files to it, and the policy restricts where the page can connect, but it is third-party code.
- The Windows build installs `pycryptodome`, `customtkinter` and `pyinstaller` without pinned versions.
- The MIUI encryption key is public and identical for all devices (see README). This tool does not weaken anything that was not already recoverable by anyone with the Gallery app.
