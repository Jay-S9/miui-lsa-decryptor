# MIUI LSA Decryptor

miui-lsa-decryptor is a free, open-source, offline tool that decrypts .lsa and .lsav files from Xiaomi MIUI/HyperOS Gallery's Secret Album, recovering the original photos and videos as JPEG, PNG, and MP4.

> **Note:** This tool is intended for recovering your own photos and videos
> from your own device's Secret Album. It does not bypass phone locks,
> passwords, or any other security — it only decrypts `.lsa`/`.lsav` files
> you already have access to. See [Disclaimer](#disclaimer) below for full details.

**Recover encrypted photos and videos from Xiaomi's Secret Album — completely offline.**

MIUI Gallery's "Secret Album" feature encrypts every photo and video you move into it, saving them as `.lsa` (photos) and `.lsav` (videos) files. This tool reverses that encryption and gives you back your original JPEGs, PNGs, and MP4s — no account needed, no internet, no cloud.

**☕ Support the project:** [ko-fi.com/jays9](https://ko-fi.com/jays9) — if this tool recovered your photos, a coffee is always appreciated.

- **Wide device coverage** — works on Xiaomi, Redmi, and POCO devices running MIUI 12 through HyperOS 2, since all three brands share the same MIUI Gallery Secret Album encryption scheme
  
---

## Features

| | |
|---|---|
| **Fully offline** | Decryption happens on your machine. Your files never leave it. |
| **Both file types** | Handles `.lsa` photos and `.lsav` videos from MIUI Secret Album |
| **Batch processing** | Drop an entire `secretAlbum/` folder and process everything at once |
| **GUI + CLI + Context menu** | Three ways to use it — pick what suits you |
| **Auto format detection** | Detects JPEG, PNG, MP4, MKV, GIF from magic bytes automatically |
| **Lossless** | Files come out bit-for-bit identical to the originals. No re-encoding. |

---

## How to find your encrypted files

Connect your Xiaomi phone via USB → enable **File Transfer** mode → navigate to:

```
Internal Storage → MIUI → Gallery → cloud → secretAlbum
```

Files look like: `3e751332435bfad27569ca4efed1b602.lsa` (hashed names, no extension you'd recognise). Copy the whole `secretAlbum/` folder to your PC before running this tool.

---

## Installation

**Requirements:** Python 3.8+ · Windows 10/11 (GUI & context menu) · macOS/Linux (CLI)

```bash
git clone https://github.com/Jay-S9/miui-lsa-decryptor
cd miui-lsa-decryptor
pip install -r requirements.txt
```

---

## Usage

### GUI (recommended)

```bash
python src/gui.py
```

Drag and drop your `.lsa` / `.lsav` files or an entire folder into the window. Choose your output directory and click **Decrypt Files**. The output folder opens automatically when done.

### CLI

```bash
# Single file
python src/cli.py photo.lsa

# Single file with custom output folder
python src/cli.py video.lsav C:\Users\Me\Desktop\recovered

# Entire secretAlbum folder
python src/cli.py C:\Users\Me\secretAlbum

# Folder with custom output
python src/cli.py C:\Users\Me\secretAlbum C:\recovered
```

### Windows Context Menu

Right-click any `.lsa` or `.lsav` file directly in File Explorer:

1. Run `install\install.bat` as Administrator
2. Right-click any `.lsa` or `.lsav` file → **"Decrypt with LSA Decryptor"**

> **Note:** The installer requires Python in your system `PATH`. During Python installation, check "Add Python to PATH".

---

## How it works

### The encryption scheme

MIUI Gallery uses **AES-128 in CTR mode** with two fixed values:

**Key** — The first 16 bytes of the MIUI Gallery APK's signing certificate (DER-encoded). You can extract this yourself:

```bash
# 1. Find the Gallery APK on your device
adb shell pm path com.miui.gallery

# 2. Pull it to your PC
adb pull /product/priv-app/MIUIGalleryGlobal/MIUIGalleryGlobal.apk

# 3. Print the certificate
keytool -printcert -rfc -jarfile MIUIGalleryGlobal.apk
```

The PEM output starts `MIIEbDCCA1S...` — Base64-decode it, and bytes `[0:16]` of the raw DER are the key.

**IV** — A hardcoded byte sequence in the Gallery app source:
```python
[17, 19, 33, 35, 49, 51, 65, 67, 81, 83, 97, 102, 103, 104, 113, 114]
```

Because both values are the same for everyone using the same Gallery version, the same key unlocks every Secret Album on every Xiaomi device.

### Photos vs videos

`.lsa` **(photos):** The entire file is encrypted. We decrypt all of it.

`.lsav` **(videos):** Only the first **1024 bytes** (the container header) are encrypted. The video payload is stored in plaintext — encrypting gigabytes of video on a phone would make playback unbearably slow. We decrypt the header only and splice it back onto the untouched body.

### Format detection

After decryption, the output is raw bytes with no extension. We read the first few bytes and compare them against known **magic byte signatures**:

| Format | Magic bytes |
|--------|------------|
| JPEG | `FF D8 FF` |
| PNG | `89 50 4E 47` |
| MP4 | `00 00 00 xx 66 74 79 70` (`ftyp` box) |
| MKV/WebM | `1A 45 DF A3` |
| GIF | `47 49 46` |

The file is saved with the correct extension automatically.

---

## Project structure

```
miui-lsa-decryptor/
├── .github/workflows/
│   └── build-exe.yml     ← Auto-builds Windows EXE on every release
├── assets/               ← Screenshots
├── install/
│   └── install.bat       ← Windows context menu installer
├── src/
│   ├── decryptor.py      ← Core AES decryption engine
│   ├── gui.py            ← Drag-and-drop desktop GUI (CustomTkinter)
│   └── cli.py            ← Command-line interface
├── build.spec            ← PyInstaller config
├── index.html            ← Web version (deploy to Vercel)
├── robots.txt
├── sitemap.xml
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Troubleshooting — File Won't Decrypt

Most decryption failures happen because Xiaomi ships different regional Gallery APK builds (Global, China, EU, India) — and each may use a slightly different signing certificate, meaning a different key.

### Step 1 — Check if the default key is yours

The default key in this tool (`3082046c30820354a003020102020900`) comes from the **Global** MIUI Gallery build. Run a quick check:

```bash
# The MD5 of the default key is:
3e751332435bfad27569ca4efed1b602

# Your .lsa filenames contain the MD5 of the key used to encrypt them.
# If your files are named like:
3e751332435bfad27569ca4efed1b602.lsa   ← default key, will decrypt fine
a1b2c3d4e5f6...something_else.lsa      ← different key, follow Step 2
```

### Step 2 — Extract your own key from your device

```bash
# 1. Find the Gallery APK path on your phone
adb shell pm path com.miui.gallery

# 2. Pull it to your PC (path may vary by device)
adb pull /product/priv-app/MIUIGalleryGlobal/MIUIGalleryGlobal.apk
# or for China builds:
adb pull /system/app/MIUIGallery/MIUIGallery.apk

# 3. Print the signing certificate in PEM format
keytool -printcert -rfc -jarfile MIUIGalleryGlobal.apk
```

The output looks like this:

```
-----BEGIN CERTIFICATE-----
MIIEbDCCA1SgAwIBAgIJAOVSqOy5ARt8MA0GCSqGSIb3DQEBBQUAMIGAMQswCQYD
VQQGEwJDTjEQMA4GA1UECBMHQmVpamluZzEQMA4GA1UEBxMHQmVpamluZzEPMA0G
...
-----END CERTIFICATE-----
```

### Step 3 — Convert certificate to your key

```python
import base64

# Paste the full base64 content between BEGIN/END CERTIFICATE here:
cert_b64 = """
MIIEbDCCA1SgAwIBAgIJAOVSqOy5ARt8...
"""

# Decode and take first 16 bytes
cert_bytes = base64.b64decode(cert_b64.replace("\n", "").strip())
your_key = cert_bytes[:16].hex()
print("Your key:", your_key)
```

### Step 4 — Use your key

Open `src/decryptor.py` and replace the `AES_KEY` line:

```python
# Replace this line:
AES_KEY: bytes = bytes.fromhex("3082046c30820354a003020102020900")

# With your extracted key:
AES_KEY: bytes = bytes.fromhex("your_key_hex_here")
```

### Common failure scenarios

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Output is garbled / random bytes | Wrong key (regional build) | Follow Steps 2–4 above |
| File decrypts but has `.bin` extension | Unusual format (HEIF, 3GP) | Rename to `.heic` or `.3gp` and try |
| Very small output file | File was already corrupted before encryption | Nothing to fix — data is gone |
| `FileNotFoundError` | Wrong path or file moved | Check the path and try again |

Still stuck? [Open a Discussion](https://github.com/Jay-S9/miui-lsa-decryptor/discussions) with your device model and MIUI/HyperOS version.

---

## Быстрый старт (Russian / Русский)

Для пользователей Xiaomi, Redmi и POCO — инструмент для расшифровки файлов `.lsa` и `.lsav` из «Секретного альбома» MIUI/HyperOS Gallery.

**Как найти файлы:**

Подключите телефон через USB → выберите **Передача файлов** → откройте:

```
Внутренняя память → MIUI → Gallery → cloud → secretAlbum
```

Файлы имеют хеш-имена вида `3e751332435bfad27569ca4efed1b602.lsav` — это нормально.

**Использование (без установки):** [miui-lsa-decryptor.vercel.app](https://miui-lsa-decryptor.vercel.app)

**Скачать приложение для Windows:** [Последний релиз](https://github.com/Jay-S9/miui-lsa-decryptor/releases/latest)

---

## 快速入门 (Chinese / 中文)

适用于小米、红米和 POCO 用户 — 解密 MIUI/HyperOS 相册保险箱中的 `.lsa` 和 `.lsav` 文件。

**如何找到加密文件：**

通过 USB 连接手机 → 选择**文件传输**模式 → 导航至：

```
手机内部存储 → MIUI → Gallery → cloud → secretAlbum
```

文件名为哈希格式，例如 `3e751332435bfad27569ca4efed1b602.lsav` — 这是正常的。

**网页版（无需安装）：** [miui-lsa-decryptor.vercel.app](https://miui-lsa-decryptor.vercel.app)

**Windows 桌面版下载（无需 Python）：** [最新版本](https://github.com/Jay-S9/miui-lsa-decryptor/releases/latest)

---

## Disclaimer

This tool is for **personal data recovery only** — to help you access your own photos and videos. The encryption keys are embedded in a publicly distributed APK and are identical for all users; no credentials or accounts are bypassed. Use responsibly.

---

## FAQ

**Is this safe? Do my files get uploaded anywhere?**
No. Everything runs locally on your machine (or entirely in-browser via the
hosted version). Your photos and videos never leave your device.

**Does this work on Redmi and POCO phones, not just Xiaomi?**
Yes. Redmi and POCO both run MIUI/HyperOS with the same Gallery app and the
same encryption scheme, so this tool works identically on all three brands.

**Do I need my phone connected while decrypting?**
No. Copy the `.lsa`/`.lsav` files to your computer first — the phone isn't
needed during decryption itself.

**Is this free?**
Yes, fully free and open source (MIT license). No per-file or per-MB charges.

**What MIUI/HyperOS versions does this support?**
Any version where MIUI Gallery uses AES-128-CTR with the key derived from
the Gallery APK's signing certificate — this has been consistent from
MIUI 12 through HyperOS 2.

**My file won't decrypt / looks corrupted. What do I do?**
Open an issue with the file's size and your MIUI Gallery version — most
failures are due to a Gallery APK signing-key mismatch across regional
builds (Global vs. China vs. EU).

---

## License

MIT — see [LICENSE](LICENSE).
