# MIUI LSA Decryptor

**Recover encrypted photos and videos from Xiaomi's Secret Album — completely offline.**

MIUI Gallery's "Secret Album" feature encrypts every photo and video you move into it, saving them as `.lsa` (photos) and `.lsav` (videos) files. This tool reverses that encryption and gives you back your original JPEGs, PNGs, and MP4s — no account needed, no internet, no cloud.

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
├── src/
│   ├── decryptor.py      ← Core AES decryption engine
│   ├── gui.py            ← Drag-and-drop desktop GUI (CustomTkinter)
│   └── cli.py            ← Command-line interface
├── install/
│   └── install.bat       ← Windows context menu installer
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Disclaimer

This tool is for **personal data recovery only** — to help you access your own photos and videos. The encryption keys are embedded in a publicly distributed APK and are identical for all users; no credentials or accounts are bypassed. Use responsibly.

---

## License

MIT — see [LICENSE](LICENSE).
