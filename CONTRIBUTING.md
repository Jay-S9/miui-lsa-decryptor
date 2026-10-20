# Contributing to MIUI LSA Decryptor

Thanks for helping improve the tool. Here's how to contribute effectively.

---

## Reporting a file that won't decrypt

Open an issue and include:
- File extension (`.lsa` or `.lsav`)
- File size in KB/MB
- Your device model (e.g. Redmi Note 12)
- Your MIUI/HyperOS version (Settings → About phone)
- Whether the web version and desktop version both fail, or just one

**Do not attach the encrypted file itself** — your private photos stay private.

---

## Reporting a bug

Include:
- What you did
- What you expected to happen
- What actually happened
- OS version and Python version (for desktop app issues)
- Any error message shown

---

## Adding support for a new file variant

If you've found a `.lsa` or `.lsav` file that uses a different key:

1. Extract the key from your Gallery APK:
   ```bash
   adb pull /product/priv-app/MIUIGalleryGlobal/MIUIGalleryGlobal.apk
   keytool -printcert -rfc -jarfile MIUIGalleryGlobal.apk
   ```
2. Decode the PEM certificate to hex and take bytes [0:16]
3. Open an issue with the key hex and your device/Gallery version

---

## Code contributions

1. Fork the repo
2. Create a branch: `git checkout -b fix/your-fix-name`
3. Make your changes
4. Test with at least one real `.lsa` or `.lsav` file
5. Open a pull request describing what changed and why

### Code style
- Python: follow existing style (type hints, docstrings on public functions)
- JS (web app): vanilla JS only, no frameworks
- Keep decryption logic in `src/decryptor.py` — don't duplicate it in `gui.py` or `cli.py`

---

## Questions

Open an issue or email [solanki9jay@email.com](mailto:solanki9jay@email.com).
