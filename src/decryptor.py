"""
decryptor.py — MIUI LSA/LSAV Decryption Engine
================================================
MIUI Gallery encrypts photos/videos placed in its "Secret Album" using
AES-128 in CTR mode. This module implements the full decryption logic.

How the encryption works:
  - Key:  First 16 bytes of the MIUI Gallery APK's signing certificate
          (converted from Base64 PEM → raw bytes).
  - IV:   Hardcoded byte sequence embedded in the Gallery app source.
  - Mode: AES-128-CTR (counter mode — no padding needed, stream cipher).

Photo files (.lsa):  Entire file is encrypted.
Video files (.lsav): Only the first 1024 bytes (the media header) are
                     encrypted. The rest of the video payload is stored
                     in plain bytes — this keeps seek/play performance
                     fast on the phone.

After decryption we inspect the first few bytes ("magic bytes") to
determine the original file format (JPEG, PNG, or MP4) and write the
output with the correct extension.

Robustness guarantees (this module is used on untrusted, possibly huge files):
  - Files are processed in fixed-size chunks, so memory use stays small
    no matter how large the input is (a 4 GB video needs the same RAM as a 4 KB one).
  - Output is written to a temporary ".part" file and only renamed into place
    when decryption has fully succeeded — a failure never leaves a truncated
    or half-written file behind.
  - An existing file is never overwritten: if "photo_decrypted.jpg" exists, the
    next output is "photo_decrypted (1).jpg", and so on.
  - Output names are built from the input's base name only and are always
    created inside the chosen output directory.
"""

import os
import tempfile
from pathlib import Path
from Crypto.Cipher import AES


# ---------------------------------------------------------------------------
# Cryptographic constants
# These come from the MIUI Gallery APK signing certificate and source code.
# ---------------------------------------------------------------------------

# The IV is a hardcoded byte sequence found in the MIUI Gallery app source.
# Each integer is a signed byte — we convert to unsigned with & 0xFF.
_RAW_IV: list[int] = [17, 19, 33, 35, 49, 51, 65, 67, 81, 83, 97, 102, 103, 104, 113, 114]
AES_IV: bytes = bytes(b & 0xFF for b in _RAW_IV)

# The key is the first 16 bytes of the Gallery APK certificate (Base64 → hex).
# Certificate starts: MIIEbDCCA1S... → base64-decoded → 3082046c30820354...
# We take bytes [0:16] of that raw DER data.
AES_KEY: bytes = bytes.fromhex("3082046c30820354a003020102020900")

# Only the first 1024 bytes of a video file are encrypted.
LSAV_HEADER_SIZE: int = 1024

# Anything smaller than one AES block cannot be a real encrypted media file.
MIN_FILE_SIZE: int = 16

# Read/decrypt this many bytes at a time (bounded memory use).
CHUNK_SIZE: int = 1024 * 1024


# ---------------------------------------------------------------------------
# Magic byte signatures → file extensions
# Every file format starts with a unique sequence of bytes. We use this
# to figure out what the decrypted data actually is.
# ---------------------------------------------------------------------------

MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (bytes([0xFF, 0xD8, 0xFF]),             ".jpg"),   # JPEG
    (bytes([0x89, 0x50, 0x4E, 0x47]),       ".png"),   # PNG
    (bytes([0x00, 0x00, 0x00, 0x18, 0x66]), ".mp4"),   # MP4 (ftyp box)
    (bytes([0x00, 0x00, 0x00, 0x20, 0x66]), ".mp4"),   # MP4 variant
    (bytes([0x00, 0x00, 0x00, 0x1C, 0x66]), ".mp4"),   # MP4 variant
    (bytes([0x1A, 0x45, 0xDF, 0xA3]),       ".mkv"),   # Matroska/WebM
    (bytes([0x47, 0x49, 0x46]),             ".gif"),   # GIF
]


def _detect_extension(data: bytes) -> str:
    """Return the correct file extension by checking magic bytes."""
    for signature, ext in MAGIC_SIGNATURES:
        if data[:len(signature)] == signature:
            return ext
    # MP4 fallback: byte 4-7 is often 'ftyp'
    if len(data) > 8 and data[4:8] == b"ftyp":
        return ".mp4"
    return ".bin"  # Unknown — keep raw binary


def _build_aes_cipher() -> AES:
    """
    Create an AES-128-CTR cipher object.

    CTR mode needs an integer counter, not just an IV. The MIUI app
    reconstructs the counter by interpreting the 16-byte IV as two
    64-bit big-endian integers (nonce + counter). We replicate that here.
    """
    # Interpret the 16-byte IV as: [8-byte nonce][8-byte initial counter]
    nonce   = AES_IV[:8]
    counter = int.from_bytes(AES_IV[8:], byteorder="big")

    # PyCryptodome's CTR mode takes nonce + initial_value
    return AES.new(
        AES_KEY,
        AES.MODE_CTR,
        nonce=nonce,
        initial_value=counter,
    )


def _output_stem(input_path: Path) -> str:
    """Base name for the output: the original name with the key-hash part removed."""
    stem = Path(input_path.stem.split(".")[0]).name      # .name guarantees no path components
    return stem or "file"


def _unique_path(output_dir: Path, stem: str, ext: str) -> Path:
    """First free '<stem>_decrypted<ext>', '<stem>_decrypted (1)<ext>', ... — never overwrites."""
    candidate = output_dir / f"{stem}_decrypted{ext}"
    n = 1
    while candidate.exists():
        candidate = output_dir / f"{stem}_decrypted ({n}){ext}"
        n += 1
    return candidate


def _decrypt_stream(input_path: Path, output_dir: Path, encrypted_prefix: int | None) -> Path:
    """
    Decrypt `input_path` chunk by chunk into `output_dir`.

    Args:
        encrypted_prefix: number of leading bytes that are encrypted, or None if the
                          whole file is (photos). Bytes after the prefix are copied as-is.
    """
    size = input_path.stat().st_size
    if size < MIN_FILE_SIZE:
        raise ValueError("File too small — not a valid .lsa/.lsav file")

    output_dir.mkdir(parents=True, exist_ok=True)
    cipher = _build_aes_cipher()
    remaining = encrypted_prefix                      # None = everything is encrypted
    ext = None

    tmp = tempfile.NamedTemporaryFile(dir=output_dir, prefix=".lsa_", suffix=".part", delete=False)
    tmp_path = Path(tmp.name)
    try:
        with open(input_path, "rb") as src, tmp:
            while True:
                chunk = src.read(CHUNK_SIZE)
                if not chunk:
                    break
                if remaining is None:
                    out = cipher.decrypt(chunk)
                else:
                    n = min(remaining, len(chunk))
                    out = (cipher.decrypt(chunk[:n]) + chunk[n:]) if n else chunk
                    remaining -= n
                if ext is None:                       # first chunk tells us the real format
                    ext = _detect_extension(out)
                tmp.write(out)
        final = _unique_path(output_dir, _output_stem(input_path), ext or ".bin")
        os.replace(tmp_path, final)                   # atomic: the file appears complete or not at all
        return final
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def decrypt_lsa(input_path: Path, output_dir: Path) -> Path:
    """
    Decrypt a .lsa photo file.

    The entire file is AES-encrypted. It is decrypted in chunks, the image
    format is detected from the magic bytes, and the result is saved.

    Args:
        input_path:  Path to the .lsa encrypted file.
        output_dir:  Directory where the decrypted file will be saved.

    Returns:
        Path to the decrypted output file.
    """
    return _decrypt_stream(input_path, output_dir, encrypted_prefix=None)


def decrypt_lsav(input_path: Path, output_dir: Path) -> Path:
    """
    Decrypt a .lsav video file.

    Only the first 1024 bytes (the container header) are encrypted.
    The rest of the video payload is stored in plaintext. We decrypt
    only the header and copy the untouched body after it, in chunks.

    Args:
        input_path:  Path to the .lsav encrypted file.
        output_dir:  Directory where the decrypted file will be saved.

    Returns:
        Path to the decrypted output file.
    """
    return _decrypt_stream(input_path, output_dir, encrypted_prefix=LSAV_HEADER_SIZE)


def decrypt_file(input_path: Path, output_dir: Path) -> Path:
    """
    Dispatch decryption based on file extension.

    Args:
        input_path:  .lsa or .lsav file to decrypt.
        output_dir:  Directory for the output file.

    Returns:
        Path to the decrypted output file.

    Raises:
        ValueError: If the file extension is not .lsa or .lsav, or the file is too small.
        FileNotFoundError: If the input does not exist or is not a regular file.
    """
    input_path, output_dir = Path(input_path), Path(output_dir)
    if not input_path.is_file():
        raise FileNotFoundError(f"File not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == ".lsa":
        return decrypt_lsa(input_path, output_dir)
    elif suffix == ".lsav":
        return decrypt_lsav(input_path, output_dir)
    else:
        raise ValueError(f"Unsupported file type: '{suffix}'. Expected .lsa or .lsav")


def decrypt_folder(folder_path: Path, output_dir: Path,
                   progress_callback=None) -> list[dict]:
    """
    Decrypt all .lsa and .lsav files in a folder (non-recursive).

    Args:
        folder_path:       Directory containing encrypted files.
        output_dir:        Directory for decrypted outputs.
        progress_callback: Optional callable(current, total, filename)
                           called after each file — used by the GUI.

    Returns:
        List of result dicts: {"input", "output", "success", "error"}
    """
    files = sorted(
        f for f in folder_path.iterdir()
        if f.suffix.lower() in (".lsa", ".lsav") and f.is_file()
    )

    results = []
    for i, file in enumerate(files):
        if progress_callback:
            progress_callback(i, len(files), file.name)
        try:
            out = decrypt_file(file, output_dir)
            results.append({"input": file, "output": out, "success": True, "error": None})
        except Exception as e:
            results.append({"input": file, "output": None, "success": False, "error": str(e)})

    if progress_callback:
        progress_callback(len(files), len(files), "")

    return results
