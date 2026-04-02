"""
gui.py — MIUI LSA Decryptor · Modern Desktop App
==================================================
Built with CustomTkinter for a clean, modern dark UI.
Replaces the old tkinter version entirely.

Run:
    python src/gui.py
    python src/gui.py path/to/file.lsav       <- pre-loads from context menu
    python src/gui.py path/to/secretAlbum/    <- pre-loads whole folder
"""

import sys
import os
import threading
import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog

try:
    from decryptor import decrypt_file
except ImportError:
    from src.decryptor import decrypt_file

# ── Theme ──────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT      = "#00E5B0"
ACCENT_DARK = "#00B589"
BG          = "#080B0F"
SURFACE     = "#0E1318"
SURFACE2    = "#141C24"
BORDER      = "#1E2A35"
TEXT        = "#E2EBF0"
TEXT2       = "#7A96A8"
SUCCESS     = "#22D47A"
ERROR       = "#FF4D6A"
WARNING     = "#FFB020"


# ── File row ───────────────────────────────────────────────────────────────
class FileRow(ctk.CTkFrame):
    STATUS_COLORS  = {"ready": TEXT2, "decrypting": WARNING, "done": SUCCESS, "error": ERROR}
    STATUS_LABELS  = {"ready": "READY", "decrypting": "DECRYPTING…", "done": "DONE  ✓", "error": "ERROR"}

    def __init__(self, master, file_path: Path, on_remove, **kwargs):
        super().__init__(master, fg_color=SURFACE2, corner_radius=8, **kwargs)
        self.file_path = file_path
        self._status   = "ready"

        ext      = file_path.suffix.lower().lstrip(".")
        size_b   = file_path.stat().st_size
        size_str = f"{size_b/1024:.0f} KB" if size_b < 1024*1024 else f"{size_b/1024/1024:.1f} MB"
        badge_fg = ACCENT if ext == "lsa" else WARNING

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f".{ext}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=badge_fg, fg_color=SURFACE, corner_radius=4,
            width=44, height=22,
        ).grid(row=0, column=0, padx=(10,8), pady=11)

        name = file_path.name
        if len(name) > 52: name = name[:24] + "…" + name[-20:]
        ctk.CTkLabel(self, text=name,
            font=ctk.CTkFont(size=12), text_color=TEXT, anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=11)

        ctk.CTkLabel(self, text=size_str,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=TEXT2, width=64,
        ).grid(row=0, column=2, padx=8, pady=11)

        self._status_lbl = ctk.CTkLabel(self, text="READY",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT2, width=100,
        )
        self._status_lbl.grid(row=0, column=3, padx=8, pady=11)

        self._rm = ctk.CTkButton(self, text="✕", width=28, height=24,
            fg_color="transparent", hover_color=SURFACE,
            text_color=TEXT2, font=ctk.CTkFont(size=13),
            command=lambda: on_remove(self),
        )
        self._rm.grid(row=0, column=4, padx=(0,8), pady=11)

    def set_status(self, s: str):
        self._status = s
        self._status_lbl.configure(
            text=self.STATUS_LABELS.get(s, s.upper()),
            text_color=self.STATUS_COLORS.get(s, TEXT2),
        )
        if s != "ready": self._rm.configure(state="disabled")

    @property
    def status(self): return self._status


# ── Main App ───────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self, preload_paths=None):
        super().__init__()
        self._rows: list[FileRow] = []
        self._setup_window()
        self._build_ui()
        if preload_paths:
            self.after(300, lambda: self._load_paths(preload_paths))

    def _setup_window(self):
        self.title("LSA Decryptor")
        self.geometry("720x660")
        self.minsize(620, 540)
        self.configure(fg_color=BG)
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 720) // 2
        y = (self.winfo_screenheight() - 660) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(24,0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="LSA Decryptor",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(hdr, text="v2.0",
            font=ctk.CTkFont(family="Consolas", size=11), text_color=TEXT2,
        ).grid(row=0, column=1, sticky="w", padx=(8,0), pady=(6,0))

        ctk.CTkLabel(hdr,
            text="Recover encrypted Xiaomi Secret Album photos & videos",
            font=ctk.CTkFont(size=12), text_color=TEXT2,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2,0))

        ctk.CTkFrame(self, height=1, fg_color=BORDER).grid(
            row=1, column=0, sticky="ew", padx=28, pady=(16,0))

        # ── Drop zone ───────────────────────────────────────────────────────
        dz = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=12,
            border_width=1, border_color=BORDER)
        dz.grid(row=2, column=0, sticky="ew", padx=28, pady=(16,0))
        dz.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(dz, text="⬇",
            font=ctk.CTkFont(size=28), text_color=ACCENT,
        ).grid(row=0, column=0, pady=(28,4))

        ctk.CTkLabel(dz, text="Drop .lsa or .lsav files here",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT,
        ).grid(row=1, column=0)

        ctk.CTkLabel(dz, text="Photos (.lsa) and videos (.lsav) both supported",
            font=ctk.CTkFont(size=11), text_color=TEXT2,
        ).grid(row=2, column=0, pady=(2,12))

        brow = ctk.CTkFrame(dz, fg_color="transparent")
        brow.grid(row=3, column=0, pady=(0,24))

        for i, (label, cmd) in enumerate([
            ("Browse files", self._browse_files),
            ("📁  Add folder", self._browse_folder),
        ]):
            ctk.CTkButton(brow, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=SURFACE2, hover_color=BORDER,
                text_color=TEXT, border_width=1, border_color=BORDER,
                width=130, height=34, corner_radius=8,
                command=cmd,
            ).grid(row=0, column=i, padx=(0 if i else 0, 8 if i==0 else 0))

        # ── File list ────────────────────────────────────────────────────────
        lc = ctk.CTkFrame(self, fg_color="transparent")
        lc.grid(row=3, column=0, sticky="nsew", padx=28, pady=(12,0))
        lc.grid_columnconfigure(0, weight=1)
        lc.grid_rowconfigure(1, weight=1)

        self._count_lbl = ctk.CTkLabel(lc, text="No files loaded",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=TEXT2, anchor="w",
        )
        self._count_lbl.grid(row=0, column=0, sticky="w", pady=(0,6))

        self._scroll = ctk.CTkScrollableFrame(lc, fg_color=SURFACE,
            corner_radius=10, border_width=1, border_color=BORDER)
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        self._empty_lbl = ctk.CTkLabel(self._scroll,
            text="Files you add will appear here",
            font=ctk.CTkFont(size=12), text_color=TEXT2)
        self._empty_lbl.grid(row=0, column=0, pady=32)

        # ── Bottom bar ───────────────────────────────────────────────────────
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.grid(row=4, column=0, sticky="ew", padx=28, pady=(12,0))
        bot.grid_columnconfigure(0, weight=1)

        out_row = ctk.CTkFrame(bot, fg_color="transparent")
        out_row.grid(row=0, column=0, sticky="ew", pady=(0,10))
        out_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(out_row, text="Output:",
            font=ctk.CTkFont(size=12), text_color=TEXT2, width=52,
        ).grid(row=0, column=0, sticky="w")

        self._out_var = ctk.StringVar(value=str(Path.home() / "Desktop" / "lsa_decrypted"))
        ctk.CTkEntry(out_row, textvariable=self._out_var,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=SURFACE2, border_color=BORDER,
            text_color=TEXT, height=32,
        ).grid(row=0, column=1, sticky="ew", padx=(6,6))

        ctk.CTkButton(out_row, text="Browse",
            font=ctk.CTkFont(size=11),
            fg_color=SURFACE2, hover_color=BORDER,
            text_color=TEXT2, border_width=1, border_color=BORDER,
            width=70, height=32, corner_radius=6,
            command=self._browse_output,
        ).grid(row=0, column=2)

        act = ctk.CTkFrame(bot, fg_color="transparent")
        act.grid(row=1, column=0, sticky="ew")
        act.grid_columnconfigure(0, weight=1)

        self._decrypt_btn = ctk.CTkButton(act, text="Decrypt Files",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_DARK, text_color="#000000",
            height=44, corner_radius=10, state="disabled",
            command=self._start_decryption,
        )
        self._decrypt_btn.grid(row=0, column=0, sticky="ew", padx=(0,10))

        ctk.CTkButton(act, text="Clear",
            font=ctk.CTkFont(size=13),
            fg_color=SURFACE2, hover_color=BORDER,
            text_color=TEXT2, border_width=1, border_color=BORDER,
            width=80, height=44, corner_radius=10,
            command=self._clear_all,
        ).grid(row=0, column=1)

        self._progress = ctk.CTkProgressBar(bot, height=3,
            fg_color=BORDER, progress_color=ACCENT, corner_radius=99)
        self._progress.grid(row=2, column=0, sticky="ew", pady=(10,4))
        self._progress.set(0)
        self._progress.grid_remove()

        self._status_lbl = ctk.CTkLabel(bot, text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=TEXT2, anchor="w")
        self._status_lbl.grid(row=3, column=0, sticky="w")
        self._status_lbl.grid_remove()

        # Footer
        ctk.CTkFrame(self, height=1, fg_color=BORDER).grid(
            row=5, column=0, sticky="ew", padx=28, pady=(12,0))
        ftr = ctk.CTkFrame(self, fg_color="transparent")
        ftr.grid(row=6, column=0, sticky="ew", padx=28, pady=(8,16))
        ftr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ftr,
            text="🔒  Your files never leave this machine — all decryption is local",
            font=ctk.CTkFont(size=11), text_color=TEXT2,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(ftr, text="Open source  ·  MIT License",
            font=ctk.CTkFont(size=10), text_color=BORDER,
        ).grid(row=0, column=1, sticky="e")

    # ── File management ──────────────────────────────────────────────────────
    def _load_paths(self, paths):
        for p in paths:
            if p.is_dir():
                for f in sorted(p.iterdir()):
                    if f.suffix.lower() in (".lsa", ".lsav") and f.is_file():
                        self._add_row(f)
            elif p.suffix.lower() in (".lsa", ".lsav") and p.is_file():
                self._add_row(p)
        self._refresh()

    def _add_row(self, path: Path):
        if any(r.file_path == path for r in self._rows): return
        row = FileRow(self._scroll, path, on_remove=self._remove_row)
        row.grid(row=len(self._rows), column=0, sticky="ew", padx=8, pady=(6,0))
        self._scroll.grid_columnconfigure(0, weight=1)
        self._rows.append(row)

    def _remove_row(self, row: FileRow):
        row.destroy()
        self._rows.remove(row)
        for i, r in enumerate(self._rows):
            r.grid(row=i, column=0, sticky="ew", padx=8, pady=(6,0))
        self._refresh()

    def _clear_all(self):
        for r in list(self._rows): r.destroy()
        self._rows.clear()
        self._progress.set(0)
        self._progress.grid_remove()
        self._status_lbl.configure(text="")
        self._status_lbl.grid_remove()
        self._refresh()

    def _refresh(self):
        n = len(self._rows)
        if n == 0:
            self._empty_lbl.grid()
            self._count_lbl.configure(text="No files loaded", text_color=TEXT2)
            self._decrypt_btn.configure(state="disabled")
        else:
            self._empty_lbl.grid_remove()
            self._count_lbl.configure(
                text=f"{n} file{'s' if n!=1 else ''} ready", text_color=ACCENT)
            has_pending = any(r.status == "ready" for r in self._rows)
            self._decrypt_btn.configure(state="normal" if has_pending else "disabled")

    # ── Browse ───────────────────────────────────────────────────────────────
    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="Select .lsa or .lsav files",
            filetypes=[("MIUI encrypted files", "*.lsa *.lsav"), ("All files", "*.*")])
        if paths: self._load_paths([Path(p) for p in paths])

    def _browse_folder(self):
        f = filedialog.askdirectory(title="Select folder with .lsa / .lsav files")
        if f: self._load_paths([Path(f)])

    def _browse_output(self):
        f = filedialog.askdirectory(title="Select output folder")
        if f: self._out_var.set(f)

    # ── Decryption ───────────────────────────────────────────────────────────
    def _start_decryption(self):
        pending = [r for r in self._rows if r.status == "ready"]
        if not pending: return
        out_dir = Path(self._out_var.get())
        out_dir.mkdir(parents=True, exist_ok=True)
        self._decrypt_btn.configure(state="disabled", text="Decrypting…")
        self._progress.set(0)
        self._progress.grid()
        self._status_lbl.grid()
        threading.Thread(target=self._run, args=(pending, out_dir), daemon=True).start()

    def _run(self, rows, out_dir):
        total = len(rows)
        ok = fail = 0
        for i, row in enumerate(rows):
            self.after(0, lambda r=row: r.set_status("decrypting"))
            self.after(0, lambda n=i, f=row.file_path: (
                self._progress.set(n/total),
                self._status_lbl.configure(text=f"Processing: {f.name}")))
            try:
                decrypt_file(row.file_path, out_dir)
                ok += 1
                self.after(0, lambda r=row: r.set_status("done"))
            except Exception as e:
                fail += 1
                self.after(0, lambda r=row: r.set_status("error"))
                print(f"Error: {row.file_path.name} — {e}")
        self.after(0, lambda: self._done(ok, fail, out_dir))

    def _done(self, ok, fail, out_dir):
        self._progress.set(1)
        msg = f"Done — {ok} decrypted" + (f", {fail} failed" if fail else "")
        self._status_lbl.configure(
            text=msg, text_color=SUCCESS if not fail else WARNING)
        self._decrypt_btn.configure(state="normal", text="Decrypt Files")
        self._refresh()
        if ok > 0:
            try:
                if sys.platform == "win32": os.startfile(out_dir)
                elif sys.platform == "darwin": subprocess.Popen(["open", out_dir])
                else: subprocess.Popen(["xdg-open", out_dir])
            except Exception: pass


# ── Entry ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    preload = [Path(p) for p in sys.argv[1:] if Path(p).exists()] if len(sys.argv) > 1 else []
    App(preload_paths=preload or None).mainloop()
