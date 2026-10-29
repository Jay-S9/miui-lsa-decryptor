"""Tests for the decryption engine (src/decryptor.py).

Ground truth is an independent single-shot AES-CTR implementation in this file, not the engine's own code.
Run:  pip install pycryptodome pytest   &&   python -m pytest -q
"""
import os
import sys
from pathlib import Path

import pytest
from Crypto.Cipher import AES

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import decryptor  # noqa: E402

JPEG = bytes([0xFF, 0xD8, 0xFF, 0xE0])
PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
MP4 = bytes([0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70])


def ctr(data: bytes) -> bytes:
    """Reference: AES-128-CTR with MIUI's key/IV (encrypt == decrypt in CTR mode)."""
    cipher = AES.new(decryptor.AES_KEY, AES.MODE_CTR, nonce=decryptor.AES_IV[:8],
                     initial_value=int.from_bytes(decryptor.AES_IV[8:], "big"))
    return cipher.encrypt(data)


def make_plain(magic: bytes, size: int) -> bytes:
    return (magic + os.urandom(max(0, size - len(magic))))[:size]


def write_lsa(path: Path, plain: bytes) -> Path:
    path.write_bytes(ctr(plain))
    return path


def write_lsav(path: Path, plain: bytes) -> Path:
    path.write_bytes(ctr(plain[:1024]) + plain[1024:])   # only the first 1024 bytes are encrypted
    return path


@pytest.mark.parametrize("size", [16, 17, 1000, 4096, 100_000])
def test_photo_roundtrip(tmp_path, size):
    plain = make_plain(JPEG, size)
    out = decryptor.decrypt_file(write_lsa(tmp_path / "p.hash.lsa", plain), tmp_path / "out")
    assert out.read_bytes() == plain and out.suffix == ".jpg" and out.name == "p_decrypted.jpg"


@pytest.mark.parametrize("size", [16, 1000, 1023, 1024, 1025, 5000, 100_000])
def test_video_roundtrip_around_the_header_boundary(tmp_path, size):
    plain = make_plain(MP4, size)
    out = decryptor.decrypt_file(write_lsav(tmp_path / "v.hash.lsav", plain), tmp_path / "out")
    assert out.read_bytes() == plain and out.suffix == ".mp4"


@pytest.mark.parametrize("chunk", [16, 100, 1024, 1500])
@pytest.mark.parametrize("video", [False, True])
def test_counter_continues_correctly_across_chunk_boundaries(tmp_path, monkeypatch, chunk, video):
    monkeypatch.setattr(decryptor, "CHUNK_SIZE", chunk)       # tiny chunks exercise every boundary cheaply
    plain = make_plain(MP4 if video else PNG, 5000)
    f = (write_lsav if video else write_lsa)(tmp_path / ("a.lsav" if video else "a.lsa"), plain)
    assert decryptor.decrypt_file(f, tmp_path / "out").read_bytes() == plain


@pytest.mark.parametrize("magic,ext", [(JPEG, ".jpg"), (PNG, ".png"), (MP4, ".mp4"),
                                       (bytes([0x1A, 0x45, 0xDF, 0xA3]), ".mkv"), (b"GIF89a", ".gif"),
                                       (b"\x01\x02\x03\x04\x05\x06\x07\x08", ".bin")])
def test_format_detection(tmp_path, magic, ext):
    out = decryptor.decrypt_file(write_lsa(tmp_path / "x.lsa", make_plain(magic, 64)), tmp_path / "out")
    assert out.suffix == ext


def test_existing_outputs_are_never_overwritten(tmp_path):
    """Regression: two inputs with the same base name used to overwrite each other silently."""
    a = write_lsa(tmp_path / "IMG_1.aaaa.lsa", make_plain(JPEG, 1000))
    b = write_lsa(tmp_path / "IMG_1.bbbb.lsa", make_plain(JPEG, 2000))
    out = tmp_path / "out"
    first, second = decryptor.decrypt_file(a, out), decryptor.decrypt_file(b, out)
    third = decryptor.decrypt_file(a, out)                        # running it again must not clobber either
    assert len({first, second, third}) == 3
    assert first.stat().st_size == 1000 and second.stat().st_size == 2000
    assert second.name == "IMG_1_decrypted (1).jpg"


@pytest.mark.parametrize("name,content,exc", [
    ("empty.lsa", b"", ValueError),
    ("tiny.lsav", b"x" * 15, ValueError),
    ("notes.txt", b"x" * 100, ValueError),
    ("missing.lsa", None, FileNotFoundError),
])
def test_bad_inputs_fail_with_a_clear_error(tmp_path, name, content, exc):
    p = tmp_path / name
    if content is not None:
        p.write_bytes(content)
    with pytest.raises(exc):
        decryptor.decrypt_file(p, tmp_path / "out")


def test_a_folder_named_like_an_encrypted_file_is_rejected(tmp_path):
    (tmp_path / "dir.lsa").mkdir()
    with pytest.raises(FileNotFoundError):
        decryptor.decrypt_file(tmp_path / "dir.lsa", tmp_path / "out")


def test_failure_leaves_no_partial_or_temp_files(tmp_path, monkeypatch):
    f = write_lsa(tmp_path / "a.lsa", make_plain(JPEG, 5000))
    monkeypatch.setattr(decryptor, "_detect_extension", lambda data: (_ for _ in ()).throw(RuntimeError("boom")))
    out = tmp_path / "out"
    with pytest.raises(RuntimeError):
        decryptor.decrypt_file(f, out)
    assert list(out.iterdir()) == []


def test_output_always_lands_inside_the_output_folder(tmp_path):
    f = write_lsa(tmp_path / "..evil.lsa", make_plain(JPEG, 100))
    out = tmp_path / "out"
    result = decryptor.decrypt_file(f, out)
    assert result.parent.resolve() == out.resolve()


def test_decrypt_folder_reports_each_file_and_progress(tmp_path):
    write_lsa(tmp_path / "b.lsa", make_plain(JPEG, 100))
    write_lsav(tmp_path / "a.lsav", make_plain(MP4, 100))
    (tmp_path / "bad.lsa").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_bytes(b"x" * 50)
    calls = []
    results = decryptor.decrypt_folder(tmp_path, tmp_path / "out", progress_callback=lambda i, n, name: calls.append((i, n)))
    assert [r["input"].name for r in results] == ["a.lsav", "b.lsa", "bad.lsa"]       # sorted, non-matching files skipped
    assert [r["success"] for r in results] == [True, True, False]
    assert "too small" in results[2]["error"]
    assert calls[-1] == (3, 3)
