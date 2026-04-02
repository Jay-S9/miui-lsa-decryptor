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
"""

import os
import struct
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


def decrypt_lsa(input_path: Path, output_dir: Path) -> Path:
    """
    Decrypt a .lsa photo file.

    The entire file is AES-encrypted. We decrypt it in one pass,
    detect the image format from the magic bytes, and save it.

    Args:
        input_path:  Path to the .lsa encrypted file.
        output_dir:  Directory where the decrypted file will be saved.

    Returns:
        Path to the decrypted output file.
    """
    encrypted_data = input_path.read_bytes()
    cipher = _build_aes_cipher()
    decrypted_data = cipher.decrypt(encrypted_data)

    ext = _detect_extension(decrypted_data)
    stem = input_path.stem.split(".")[0]           # strip md5 hash from filename
    output_path = output_dir / f"{stem}_decrypted{ext}"

    output_path.write_bytes(decrypted_data)
    return output_path


def decrypt_lsav(input_path: Path, output_dir: Path) -> Path:
    """
    Decrypt a .lsav video file.

    Only the first 1024 bytes (the container header) are encrypted.
    The rest of the video payload is stored in plaintext. We decrypt
    only the header and stitch it back onto the untouched body.

    Args:
        input_path:  Path to the .lsav encrypted file.
        output_dir:  Directory where the decrypted file will be saved.

    Returns:
        Path to the decrypted output file.
    """
    raw = input_path.read_bytes()

    encrypted_header = raw[:LSAV_HEADER_SIZE]
    video_body       = raw[LSAV_HEADER_SIZE:]       # already plaintext

    cipher = _build_aes_cipher()
    decrypted_header = cipher.decrypt(encrypted_header)

    # Pad header back to 1024 bytes if the file was smaller (edge case)
    if len(raw) < LSAV_HEADER_SIZE:
        decrypted_data = decrypted_header
    else:
        decrypted_data = decrypted_header + video_body

    ext = _detect_extension(decrypted_data)
    stem = input_path.stem.split(".")[0]
    output_path = output_dir / f"{stem}_decrypted{ext}"

    output_path.write_bytes(decrypted_data)
    return output_path


def decrypt_file(input_path: Path, output_dir: Path) -> Path:
    """
    Dispatch decryption based on file extension.

    Args:
        input_path:  .lsa or .lsav file to decrypt.
        output_dir:  Directory for the output file.

    Returns:
        Path to the decrypted output file.

    Raises:
        ValueError: If the file extension is not .lsa or .lsav.
        FileNotFoundError: If the input file does not exist.
    """
    if not input_path.exists():
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
    files = [
        f for f in folder_path.iterdir()
        if f.suffix.lower() in (".lsa", ".lsav") and f.is_file()
    ]

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
