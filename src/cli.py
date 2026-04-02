"""
cli.py — Command-Line Interface for MIUI LSA Decryptor
=======================================================
Usage:
    python cli.py <file_or_folder> [output_dir]

Examples:
    python cli.py photo.lsa
    python cli.py video.lsav ./recovered/
    python cli.py C:\\Users\\Me\\secretAlbum
    python cli.py C:\\Users\\Me\\secretAlbum C:\\Users\\Me\\Desktop\\recovered
"""

import sys
import time
from pathlib import Path

# Allow running from project root or from src/
try:
    from decryptor import decrypt_file, decrypt_folder
except ImportError:
    from src.decryptor import decrypt_file, decrypt_folder


# ---------------------------------------------------------------------------
# ANSI colour helpers (Windows 10+ supports these via cmd /v or Windows Terminal)
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


def enable_ansi_windows() -> None:
    """Enable ANSI escape codes on Windows (requires Win10 1511+)."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


def print_banner() -> None:
    banner = f"""
{CYAN}{BOLD}╔══════════════════════════════════════╗
║     MIUI LSA / LSAV  Decryptor       ║
║     Recover your Secret Album files  ║
╚══════════════════════════════════════╝{RESET}
"""
    print(banner)


def print_result(label: str, success: bool, detail: str = "") -> None:
    icon   = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
    status = f"{GREEN}OK{RESET}"  if success else f"{RED}FAILED{RESET}"
    print(f"  {icon}  {label:<45} {status}")
    if detail and not success:
        print(f"     {DIM}{detail}{RESET}")


def progress_bar(current: int, total: int, filename: str, width: int = 30) -> None:
    if total == 0:
        return
    filled = int(width * current / total)
    bar    = "█" * filled + "░" * (width - filled)
    pct    = int(100 * current / total)
    name   = filename[:35] + "…" if len(filename) > 35 else filename
    print(f"\r  [{bar}] {pct:3d}%  {name:<36}", end="", flush=True)


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def run(args: list[str]) -> int:
    """
    Entry point for the CLI. Returns exit code (0 = success, 1 = error).
    """
    enable_ansi_windows()
    print_banner()

    if not args:
        print(f"{YELLOW}Usage:{RESET}  python cli.py <file_or_folder> [output_dir]\n")
        print(f"  Decrypt a single file:    {CYAN}python cli.py photo.lsa{RESET}")
        print(f"  Decrypt a whole folder:   {CYAN}python cli.py secretAlbum/{RESET}")
        print(f"  Custom output directory:  {CYAN}python cli.py secretAlbum/ C:\\recovered{RESET}\n")
        return 1

    input_path = Path(args[0])

    if not input_path.exists():
        print(f"{RED}Error:{RESET} Path not found → {input_path}\n")
        return 1

    # ── Determine output directory ──────────────────────────────────────────
    if len(args) >= 2:
        output_dir = Path(args[1])
    elif input_path.is_dir():
        output_dir = input_path / "decrypted"
    else:
        output_dir = input_path.parent / "decrypted"

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  {DIM}Output directory:{RESET} {output_dir}\n")

    start = time.perf_counter()

    # ── Single file ─────────────────────────────────────────────────────────
    if input_path.is_file():
        if input_path.suffix.lower() not in (".lsa", ".lsav"):
            print(f"{RED}Error:{RESET} Expected a .lsa or .lsav file, got '{input_path.suffix}'\n")
            return 1
        try:
            out = decrypt_file(input_path, output_dir)
            print_result(input_path.name, True)
            print(f"\n  {GREEN}Saved →{RESET} {out}")
        except Exception as e:
            print_result(input_path.name, False, str(e))
            return 1

    # ── Folder ───────────────────────────────────────────────────────────────
    else:
        files = [
            f for f in input_path.iterdir()
            if f.suffix.lower() in (".lsa", ".lsav") and f.is_file()
        ]
        if not files:
            print(f"{YELLOW}No .lsa or .lsav files found in:{RESET} {input_path}\n")
            return 1

        print(f"  Found {BOLD}{len(files)}{RESET} encrypted file(s)\n")

        def on_progress(current, total, filename):
            if filename:
                progress_bar(current, total, filename)

        results = decrypt_folder(input_path, output_dir, progress_callback=on_progress)
        print()  # newline after progress bar
        print()

        ok      = [r for r in results if r["success"]]
        failed  = [r for r in results if not r["success"]]

        for r in results:
            name = r["input"].name
            print_result(name, r["success"], r.get("error") or "")

        elapsed = time.perf_counter() - start
        print(f"\n  ─────────────────────────────────────────────")
        print(f"  {GREEN}{len(ok)} decrypted{RESET}   {RED}{len(failed)} failed{RESET}   {DIM}{elapsed:.2f}s{RESET}")
        print(f"  Saved to → {output_dir}\n")

        return 0 if not failed else 1

    elapsed = time.perf_counter() - start
    print(f"\n  {DIM}Done in {elapsed:.3f}s{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
