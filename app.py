import tkinter as tk
import os
from tkinter import filedialog
from pathlib import Path
import threading
import shutil
import webbrowser

import customtkinter as ctk

from worker import (
    DownloadWorker,
    DownloadOptions,
    get_supported_extractors,
    cleanup_stale_files,
    find_all_files_by_id,
    FFMPEG_PATH,
    DEFAULT_DOWNLOAD_FOLDER,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CONFIG_DIR / "settings.txt"
DISCLAIMER_FILE = CONFIG_DIR / ".disclaimer_accepted"


def format_bytes(n: int | None) -> str:
    if n is None:
        return ""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


HELP_TEXTS: dict[str, str] = {
    "Best": (
        "Downloads the highest-quality video+audio stream available.\n"
        "Keeps the original container (WebM, MKV, etc.) without forcing MP4.\n"
        "Does not require ffmpeg for most streams."
    ),
    "MP4": (
        "Downloads the best video and merges it with the best audio\n"
        "into an MP4 container using ffmpeg.\n"
        "Best for maximum device / player compatibility."
    ),
    "MP3": (
        "Extracts audio only and converts to MP3.\n"
        "Requires ffmpeg. Quality is set in Advanced > Audio."
    ),
    "Playlist": (
        "Downloads every video in a playlist, channel, or series.\n"
        "All files are packaged into a single ZIP archive."
    ),
    "Load Formats": (
        "Fetches every available quality / format option for the URL.\n"
        "Lets you pick a specific resolution, codec, or format ID\n"
        "instead of relying on automatic selection."
    ),
    "Download folder": (
        "Directory where downloaded files are temporarily stored\n"
        "before you choose a final save location.\n"
        "Defaults to a 'downloads' folder next to the app."
    ),
    "Filename template": (
        "Pattern for naming downloaded files.\n"
        "Common variables:\n"
        "  %(title)s  — video title\n"
        "  %(id)s     — video ID\n"
        "  %(ext)s    — file extension\n"
        "  %(resolution)s — resolution label\n"
        "Example: %(title)s-%(id)s.%(ext)s"
    ),
    "Restrict filenames": (
        "Removes special characters, spaces, and non-ASCII characters\n"
        "from filenames. Safe for older filesystems and scripts."
    ),
    "Don't overwrite existing files": (
        "If a file with the same name already exists in the output folder,\n"
        "skip the download instead of overwriting it."
    ),
    "Proxy URL": (
        "HTTP, HTTPS, or SOCKS proxy for all connections.\n"
        "Format: http://user:pass@host:port\n"
        "        socks5://host:1080"
    ),
    "Concurrent fragments": (
        "Number of fragments to download in parallel for DASH/hls streams.\n"
        "Higher values can speed up downloads but use more bandwidth.\n"
        "Default: 1"
    ),
    "Cookies file": (
        "Path to a Netscape-format cookies.txt file.\n"
        "Use this to access member-only, age-restricted, or\n"
        "subscription content you have access to in your browser."
    ),
    "Download archive": (
        "A text file that tracks which video IDs have been downloaded.\n"
        "Useful for incremental downloads — skips already-downloaded videos."
    ),
    "MP3 quality": (
        "Bitrate for MP3 audio extraction.\n"
        "128 = smaller file, lower quality\n"
        "192 = good balance\n"
        "320 = highest quality, largest file"
    ),
    "Download subtitles": (
        "Downloads subtitle tracks in the specified languages.\n"
        "Includes both manual and auto-generated subtitles."
    ),
    "Subtitle language(s)": (
        "Language codes for subtitle downloads.\n"
        "Examples: en, fr, de, es, ja\n"
        "Separate multiple with commas: en,fr,es"
    ),
    "Embed thumbnail": (
        "Embeds the video thumbnail into the downloaded file's metadata.\n"
        "Works with MP4/MKV and some audio formats."
    ),
    "Custom ffmpeg path": (
        "Path to a specific ffmpeg.exe if it is not on your system PATH.\n"
        "The app also looks for ffmpeg.exe in its own folder."
    ),
    "YouTube player client": (
        "Which YouTube player client to use for requests.\n"
        "If videos show as 'not available', try 'android' or 'ios'.\n"
        "Leave default for yt-dlp's default behavior."
    ),
    "Custom yt-dlp args": (
        "Extra CLI flags passed directly to yt-dlp.\n"
        "Separate with spaces. Example:\n"
        "  --no-mtime --limit-rate 2M --retries 10\n"
        "Flags that conflict with app settings are ignored."
    ),
}


class HelpPopup(ctk.CTkToplevel):
    def __init__(self, parent, title: str, text: str):
        super().__init__(parent)
        self.title(f"Help — {title}")
        self.geometry("480x260")
        self.minsize(400, 180)
        self.resizable(True, True)
        self.transient(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        box = ctk.CTkTextbox(self, wrap="word", font=("Segoe UI", 12))
        box.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        box.insert("0.0", text)
        box.configure(state="disabled")

        btn = ctk.CTkButton(self, text="OK", command=self.destroy, width=100)
        btn.grid(row=1, column=0, pady=(0, 12))


class DisclaimerPopup(ctk.CTkToplevel):
    def __init__(self, parent, on_close):
        super().__init__(parent)
        self._on_close = on_close
        self.title("Disclaimer")
        self.geometry("520x360")
        self.minsize(480, 300)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        text = (
            "This tool downloads video and audio from third-party websites.\n\n"
            "By using this software you agree that:\n"
            "  \u2022 You should only download content you have the legal right to access.\n"
            "  \u2022 You are responsible for complying with the terms of service\n"
            "    of the websites you use this tool with.\n"
            "  \u2022 This tool is provided as-is, without any warranty.\n"
            "  \u2022 The developers are not responsible for how you use this software \n"
            "    or any trouble you get into by using it, legal or otherwise.\n\n"
            "Downloading copyrighted material without permission may violate\n"
            "copyright laws in your jurisdiction. Use at your own risk!"
        )

        box = ctk.CTkTextbox(self, wrap="word", font=("Segoe UI", 12))
        box.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="nsew")
        box.insert("0.0", text)
        box.configure(state="disabled")

        self._dont_show = tk.BooleanVar(value=False)
        cb = ctk.CTkCheckBox(
            self, text="Don't show this again",
            variable=self._dont_show,
        )
        cb.grid(row=1, column=0, padx=16, pady=(4, 8), sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=(0, 14))
        ctk.CTkButton(btn_frame, text="I Understand", command=self._accept).pack()

    def _accept(self):
        accepted = self._dont_show.get()
        self._on_close(accepted)
        self.destroy()


class DownloadApp(ctk.CTk):
    WIDTH = 1000
    HEIGHT = 720

    def __init__(self):
        super().__init__()
        self.title("Video Downloader")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(880, 620)
        self.resizable(True, True)

        self.worker = DownloadWorker()
        self._current_download_id: str | None = None
        self._poll_job: str | None = None
        self._selected_format_id: str | None = None

        # persistable settings
        self._output_dir = tk.StringVar(value=str(DEFAULT_DOWNLOAD_FOLDER))
        self._cookies_file = tk.StringVar(value="")
        self._proxy = tk.StringVar(value="")
        self._custom_ffmpeg = tk.StringVar(value="")
        self._filename_template = tk.StringVar(value="%(title)s.%(ext)s")
        self._audio_quality = tk.StringVar(value="192")
        self._subtitle_langs = tk.StringVar(value="en")
        self._concurrent = tk.StringVar(value="1")
        self._archive_file = tk.StringVar(value="")
        self._embed_thumb = tk.BooleanVar(value=False)
        self._subs = tk.BooleanVar(value=False)
        self._restrict = tk.BooleanVar(value=False)
        self._no_overwrite = tk.BooleanVar(value=False)
        self._save_folder = tk.StringVar(value="")
        self._use_save_folder = tk.BooleanVar(value=False)
        self._player_client = tk.StringVar(value="default")
        self._custom_ydl_args = tk.StringVar(value="")

        # ------------------------------------------------------------------
        # Layout: main content (left) + site panel (right)
        # ------------------------------------------------------------------
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._main_scroll = ctk.CTkScrollableFrame(content, fg_color="transparent")
        self._main_scroll.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)
        self._main_scroll.grid_columnconfigure(0, weight=1)

        # site panel (right side)
        self._site_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self._site_frame.grid(row=0, column=1, sticky="ns")
        self._site_frame.grid_propagate(False)
        self._build_site_panel()

        # build the main content
        self._build_main_content()

        self._load_settings()
        self.after(1000, lambda: cleanup_stale_files())

        # show disclaimer if not yet accepted
        self.after(500, self._check_disclaimer)

    # ======================================================================
    # Disclaimer
    # ======================================================================

    def _check_disclaimer(self):
        if DISCLAIMER_FILE.is_file():
            return
        DisclaimerPopup(self, self._on_disclaimer_closed)

    def _on_disclaimer_closed(self, dont_show_again: bool):
        if dont_show_again:
            try:
                DISCLAIMER_FILE.parent.mkdir(parents=True, exist_ok=True)
                DISCLAIMER_FILE.write_text("accepted", encoding="utf-8")
            except Exception:
                pass

    # ======================================================================
    # Main content (single scrollable page)
    # ======================================================================

    def _build_main_content(self):
        s = self._main_scroll
        row = 0

        # -- title --
        ctk.CTkLabel(s, text="Video Downloader", font=("Segoe UI", 22, "bold")).grid(
            row=row, column=0, pady=(0, 16), sticky="w"
        )
        row += 1

        # -- URL --
        ctk.CTkLabel(s, text="URL", anchor="w").grid(
            row=row, column=0, padx=2, pady=(0, 2), sticky="w"
        )
        row += 1
        self.url_entry = ctk.CTkEntry(s, placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self._start_download())
        self._setup_paste_menu(self.url_entry)
        row += 1

        # -- Format + Playlist row --
        fmt_frame = ctk.CTkFrame(s, fg_color="transparent")
        fmt_frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        row += 1

        ctk.CTkLabel(fmt_frame, text="Format:").pack(side="left", padx=(0, 10))

        self._fmt_var = tk.StringVar(value="best")
        for val, lbl in [("best", "Best"), ("mp4", "MP4"), ("mp3", "MP3")]:
            rb = ctk.CTkRadioButton(fmt_frame, text=lbl, variable=self._fmt_var, value=val)
            rb.pack(side="left", padx=(0, 8))
            self._bind_help(rb, lbl)

        ctk.CTkLabel(fmt_frame, text="    ").pack(side="left")
        self._playlist_var = tk.BooleanVar(value=False)
        cb = ctk.CTkCheckBox(fmt_frame, text="Playlist", variable=self._playlist_var)
        cb.pack(side="left")
        self._bind_help(cb, "Playlist")

        # -- Title + format preview --
        self._title_label = ctk.CTkLabel(s, text="", wraplength=700, anchor="w", justify="left")
        self._title_label.grid(row=row, column=0, sticky="w", pady=(2, 2))
        row += 1

        # -- Inline format list (hidden until loaded) --
        self._format_container = ctk.CTkFrame(s, fg_color="transparent")
        self._format_container.grid(row=row, column=0, sticky="ew", pady=(2, 4))
        self._format_container.grid_columnconfigure(0, weight=1)
        self._format_container.grid_remove()
        self._format_list_frame: ctk.CTkScrollableFrame | None = None
        self._format_radio_var = tk.StringVar(value="")
        self._format_row_count = 0
        row += 1

        # -- Buttons --
        btn_frame = ctk.CTkFrame(s, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew", pady=(6, 8))
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)
        row += 1

        self._load_btn = ctk.CTkButton(btn_frame, text="Load Formats", command=self._load_formats)
        self._load_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._bind_help(self._load_btn, "Load Formats")

        self._dl_btn = ctk.CTkButton(btn_frame, text="Download", command=self._start_download)
        self._dl_btn.grid(row=0, column=1, padx=4, sticky="ew")

        self._cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", state="disabled",
            fg_color="#dc2626", hover_color="#b91c1c", command=self._cancel_download
        )
        self._cancel_btn.grid(row=0, column=2, padx=(4, 0), sticky="ew")

        # -- Progress --
        self._prog_frame = ctk.CTkFrame(s, fg_color="transparent")
        self._prog_frame.grid(row=row, column=0, sticky="ew", pady=(4, 2))
        self._prog_frame.grid_columnconfigure(0, weight=1)
        self._prog_frame.grid_remove()
        row += 1

        self._prog_bar = ctk.CTkProgressBar(self._prog_frame)
        self._prog_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._prog_bar.set(0)

        self._prog_pct = ctk.CTkLabel(self._prog_frame, text="0%", anchor="w")
        self._prog_pct.grid(row=1, column=0, sticky="w")

        # -- Status --
        self._status_textbox = ctk.CTkTextbox(
            s, height=28, wrap="word", font=("Segoe UI", 12),
            activate_scrollbars=False,
        )
        self._status_textbox.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        self._status_textbox.insert("0.0", "Ready.")
        self._status_textbox.configure(state="disabled")
        row += 1

        # -- ffmpeg warning --
        self._ffmpeg_warn_frame = ctk.CTkFrame(s, fg_color="transparent")
        self._ffmpeg_warn_frame.grid(row=row, column=0, sticky="ew", pady=(4, 0))
        self._ffmpeg_warn_frame.grid_columnconfigure(0, weight=1)
        self._ffmpeg_warn_frame.grid_remove()
        row += 1

        self._ffmpeg_label = ctk.CTkLabel(
            self._ffmpeg_warn_frame, text="", text_color="#f87171", anchor="w", wraplength=600
        )
        self._ffmpeg_label.grid(row=0, column=0, sticky="w")

        self._ffmpeg_btn = ctk.CTkButton(
            self._ffmpeg_warn_frame, text="Install ffmpeg", width=110, height=26,
            fg_color="#d97706", hover_color="#b45309",
            font=("Segoe UI", 11), command=self._show_ffmpeg_help,
        )
        self._ffmpeg_btn.grid(row=0, column=1, padx=(8, 0))

        if not FFMPEG_PATH:
            self._ffmpeg_label.configure(
                text="ffmpeg not found. MP3 and MP4 formats require ffmpeg."
            )
            self._ffmpeg_warn_frame.grid()

        # -- separator --
        ctk.CTkFrame(s, height=1, fg_color="#374151").grid(
            row=row, column=0, sticky="ew", pady=(14, 8)
        )
        row += 1

        # -- Advanced options (collapsible) --
        self._build_advanced_section(s, row)

    # ======================================================================
    # Help system
    # ======================================================================

    def _bind_help(self, widget: ctk.CTkBaseClass | ctk.CTkCheckBox, key: str):
        text = HELP_TEXTS.get(key)
        if not text:
            return

        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Help", command=lambda: HelpPopup(self, key, text))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu, add=True)
        widget.bind("<Button-2>", show_menu, add=True)

    # ======================================================================
    # Advanced (collapsible)
    # ======================================================================

    def _build_advanced_section(self, parent: ctk.CTkFrame, start_row: int):
        self._adv_visible = False
        adv_header = ctk.CTkFrame(parent, fg_color="transparent")
        adv_header.grid(row=start_row, column=0, sticky="ew", pady=(4, 4))
        adv_header.grid_columnconfigure(0, weight=1)

        self._adv_toggle_btn = ctk.CTkButton(
            adv_header, text="+  Advanced Options", anchor="w",
            fg_color="transparent", hover_color=("#d1d5db", "#2d3a4f"),
            text_color=("#1f2937", "#e5e7eb"), font=("Segoe UI", 13, "bold"),
            command=self._toggle_advanced,
        )
        self._adv_toggle_btn.grid(row=0, column=0, sticky="ew")

        self._adv_body = ctk.CTkFrame(parent, fg_color="transparent")
        self._adv_body.grid(row=start_row + 1, column=0, sticky="ew", pady=(0, 8))
        self._adv_body.grid_columnconfigure(1, weight=1)
        self._adv_body.grid_remove()

        self._build_advanced_body(self._adv_body)

    def _toggle_advanced(self):
        self._adv_visible = not self._adv_visible
        if self._adv_visible:
            self._adv_body.grid()
            self._adv_toggle_btn.configure(text="\u2212  Advanced Options")
        else:
            self._adv_body.grid_remove()
            self._adv_toggle_btn.configure(text="+  Advanced Options")

    def _build_advanced_body(self, parent: ctk.CTkFrame):
        r = 0

        def section(title: str):
            nonlocal r
            ctk.CTkLabel(
                parent, text=title, font=("Segoe UI", 12, "bold"), text_color="#3b82f6"
            ).grid(row=r, column=0, columnspan=3, pady=(10, 4), sticky="w")
            r += 1

        def picker(label: str, var: tk.StringVar, btn_text: str, filetypes=None, help_key: str | None = None):
            nonlocal r
            lbl = ctk.CTkLabel(parent, text=label)
            lbl.grid(row=r, column=0, padx=(0, 8), pady=3, sticky="w")
            if help_key:
                self._bind_help(lbl, help_key)

            entry = ctk.CTkEntry(parent, textvariable=var)
            entry.grid(row=r, column=1, padx=(0, 6), pady=3, sticky="ew")
            self._setup_paste_menu(entry)

            def browse():
                if filetypes:
                    fp = filedialog.askopenfilename(filetypes=filetypes)
                else:
                    fp = filedialog.askdirectory()
                if fp:
                    var.set(fp)

            ctk.CTkButton(parent, text=btn_text, width=70, height=28, command=browse,
                          font=("Segoe UI", 11)).grid(row=r, column=2, pady=3)
            r += 1

        def entry_row(label: str, var: tk.StringVar, width=200, placeholder="", help_key: str | None = None):
            nonlocal r
            lbl = ctk.CTkLabel(parent, text=label)
            lbl.grid(row=r, column=0, padx=(0, 8), pady=3, sticky="w")
            if help_key:
                self._bind_help(lbl, help_key)

            entry = ctk.CTkEntry(parent, textvariable=var, width=width, placeholder_text=placeholder)
            entry.grid(row=r, column=1, padx=(0, 6), pady=3, sticky="w")
            self._setup_paste_menu(entry)
            r += 1

        def check_row(label: str, var: tk.BooleanVar, help_key: str | None = None):
            nonlocal r
            cb = ctk.CTkCheckBox(parent, text=label, variable=var)
            cb.grid(row=r, column=1, sticky="w", pady=2)
            if help_key:
                self._bind_help(cb, help_key)
            r += 1

        def option_row(label: str, var: tk.StringVar, values: list[str], width=120, help_key: str | None = None):
            nonlocal r
            lbl = ctk.CTkLabel(parent, text=label)
            lbl.grid(row=r, column=0, padx=(0, 8), pady=3, sticky="w")
            if help_key:
                self._bind_help(lbl, help_key)

            ctk.CTkOptionMenu(parent, values=values, variable=var, width=width).grid(
                row=r, column=1, sticky="w", pady=3
            )
            r += 1

        section("Output")
        picker("Download folder", self._output_dir, "Browse", help_key="Download folder")
        entry_row("Filename template", self._filename_template, placeholder="%(title)s.%(ext)s",
                  help_key="Filename template")
        ctk.CTkLabel(
            parent, text="Use %(title)s, %(id)s, %(ext)s, %(resolution)s, etc.",
            font=("Segoe UI", 10), text_color="#6b7280"
        ).grid(row=r, column=1, sticky="w")
        r += 1
        check_row("Restrict filenames (ASCII, no spaces)", self._restrict,
                  help_key="Restrict filenames")
        check_row("Don't overwrite existing files", self._no_overwrite,
                  help_key="Don't overwrite existing files")
        check_row("Always save to this folder (skip save dialog)", self._use_save_folder)

        def on_toggle_save_folder():
            if self._use_save_folder.get():
                save_folder_entry.configure(state="normal")
                save_folder_btn.configure(state="normal")
            else:
                save_folder_entry.configure(state="disabled")
                save_folder_btn.configure(state="disabled")

        self._use_save_folder.trace_add("write", lambda *_: on_toggle_save_folder())

        save_folder_frame = ctk.CTkFrame(parent, fg_color="transparent")
        save_folder_frame.grid(row=r, column=0, columnspan=3, sticky="ew", pady=2)
        r += 1

        ctk.CTkLabel(save_folder_frame, text="Save folder").pack(side="left", padx=(0, 8))

        save_folder_entry = ctk.CTkEntry(
            save_folder_frame, textvariable=self._save_folder
        )
        save_folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def browse_save_folder():
            fp = filedialog.askdirectory()
            if fp:
                self._save_folder.set(fp)

        save_folder_btn = ctk.CTkButton(
            save_folder_frame, text="Browse", width=70, height=28,
            command=browse_save_folder, font=("Segoe UI", 11),
        )
        save_folder_btn.pack(side="left")

        # initial state
        if not self._use_save_folder.get():
            save_folder_entry.configure(state="disabled")
            save_folder_btn.configure(state="disabled")

        section("Network")
        entry_row("Proxy URL", self._proxy, placeholder="http://user:pass@host:port",
                  help_key="Proxy URL")
        entry_row("Concurrent fragments", self._concurrent, width=80,
                  help_key="Concurrent fragments")
        option_row("YouTube player client", self._player_client,
                   ["default", "android", "ios", "android,ios", "tv", "web",
                    "web_embedded", "tv_embedded"],
                   help_key="YouTube player client")

        section("Authentication")
        picker("Cookies file", self._cookies_file, "Browse",
               filetypes=[("Netscape cookies", "*.txt"), ("All files", "*.*")],
               help_key="Cookies file")
        picker("Download archive", self._archive_file, "Browse",
               filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
               help_key="Download archive")

        section("Audio")
        option_row("MP3 quality (kbps)", self._audio_quality, ["128", "192", "256", "320"],
                   help_key="MP3 quality")

        section("Subtitles & Thumbnails")
        check_row("Download subtitles", self._subs, help_key="Download subtitles")
        entry_row("Subtitle language(s)", self._subtitle_langs, width=120, placeholder="en",
                  help_key="Subtitle language(s)")
        ctk.CTkLabel(
            parent, text="Comma-separated (en, fr, de...)",
            font=("Segoe UI", 10), text_color="#6b7280"
        ).grid(row=r, column=1, sticky="w")
        r += 1
        check_row("Embed thumbnail in file", self._embed_thumb, help_key="Embed thumbnail")

        section("FFmpeg")
        picker("Custom ffmpeg path", self._custom_ffmpeg, "Browse",
               filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
               help_key="Custom ffmpeg path")

        section("Extra")
        entry_row("Custom yt-dlp args", self._custom_ydl_args, width=300,
                  placeholder="--no-mtime --limit-rate 1M",
                  help_key="Custom yt-dlp args")
        ctk.CTkLabel(
            parent, text="Space-separated CLI flags passed directly to yt-dlp.",
            font=("Segoe UI", 10), text_color="#6b7280"
        ).grid(row=r, column=1, sticky="w")
        r += 1

        # Save
        ctk.CTkFrame(parent, height=1, fg_color="#374151").grid(
            row=r, column=0, columnspan=3, sticky="ew", pady=10
        )
        r += 1

        btn_save = ctk.CTkButton(
            parent, text="Save Settings", command=self._save_settings,
            fg_color="#059669", hover_color="#047857"
        )
        btn_save.grid(row=r, column=1, pady=(0, 6), sticky="ew")
        r += 1

        self._adv_status = ctk.CTkLabel(parent, text="", anchor="w")
        self._adv_status.grid(row=r, column=1, sticky="w")

    # ======================================================================
    # Site panel (right side)
    # ======================================================================

    def _build_site_panel(self):
        ctk.CTkLabel(
            self._site_frame, text="Supported Sites",
            font=("Segoe UI", 13, "bold")
        ).pack(padx=10, pady=(14, 4), anchor="w")

        self._site_count = ctk.CTkLabel(
            self._site_frame, text="Loading...", font=("Segoe UI", 10)
        )
        self._site_count.pack(padx=10, pady=(0, 6), anchor="w")

        self._site_search_var = tk.StringVar(value="")
        self._site_search_var.trace_add("write", lambda *_: self._filter_sites_text())
        ctk.CTkEntry(
            self._site_frame, placeholder_text="Search...",
            textvariable=self._site_search_var
        ).pack(padx=10, pady=(0, 6), fill="x")

        self._site_textbox = ctk.CTkTextbox(
            self._site_frame, wrap="none", font=("Consolas", 11)
        )
        self._site_textbox.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        self._site_textbox.configure(state="disabled")

        # click to copy
        self._site_textbox.bind("<Button-1>", self._on_site_click)

        self._all_sites: list[str] = []
        self._load_sites_async()

    def _load_sites_async(self):
        def work():
            sites = get_supported_extractors()
            self.after(0, self._on_sites_loaded, sites)
        threading.Thread(target=work, daemon=True).start()

    def _on_sites_loaded(self, sites: list[str]):
        self._all_sites = sites
        self._site_count.configure(text=f"{len(sites):,} sites")
        self._populate_site_textbox(sites)

    def _populate_site_textbox(self, sites: list[str]):
        self._site_textbox.configure(state="normal")
        self._site_textbox.delete("0.0", "end")
        self._site_textbox.insert("0.0", "\n".join(sites))
        self._site_textbox.configure(state="disabled")

    def _filter_sites_text(self):
        q = self._site_search_var.get().strip().lower()
        if not q:
            self._site_count.configure(text=f"{len(self._all_sites):,} sites")
            self._populate_site_textbox(self._all_sites)
            return
        filtered = [s for s in self._all_sites if q in s.lower()]
        self._site_count.configure(text=f"{len(filtered):,} sites")
        self._populate_site_textbox(filtered)

    def _on_site_click(self, event):
        try:
            idx = self._site_textbox.index(f"@{event.x},{event.y}")
            line = self._site_textbox.get(f"{idx} linestart", f"{idx} lineend").strip()
            if line:
                self.clipboard_clear()
                self.clipboard_append(line)
                self._set_status(f"Copied: {line}")
        except Exception:
            pass

    # ======================================================================
    # Settings persistence
    # ======================================================================

    def _save_settings(self):
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                f"output_dir={self._output_dir.get()}",
                f"cookies_file={self._cookies_file.get()}",
                f"proxy={self._proxy.get()}",
                f"custom_ffmpeg={self._custom_ffmpeg.get()}",
                f"filename_template={self._filename_template.get()}",
                f"audio_quality={self._audio_quality.get()}",
                f"subtitle_langs={self._subtitle_langs.get()}",
                f"concurrent={self._concurrent.get()}",
                f"archive_file={self._archive_file.get()}",
                f"embed_thumb={self._embed_thumb.get()}",
                f"subtitles={self._subs.get()}",
                f"restrict={self._restrict.get()}",
                f"no_overwrite={self._no_overwrite.get()}",
                f"save_folder={self._save_folder.get()}",
                f"use_save_folder={self._use_save_folder.get()}",
                f"player_client={self._player_client.get()}",
                f"custom_ydl_args={self._custom_ydl_args.get()}",
            ]
            CONFIG_FILE.write_text("\n".join(lines), encoding="utf-8")
            self._adv_status.configure(text="Settings saved.", text_color="#4ade80")
        except Exception as e:
            self._adv_status.configure(text=f"Save failed: {e}", text_color="#f87171")
        self.after(3000, lambda: self._adv_status.configure(text=""))

    def _load_settings(self):
        try:
            if not CONFIG_FILE.is_file():
                return
            for line in CONFIG_FILE.read_text("utf-8").splitlines():
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                var_map = {
                    "output_dir": self._output_dir, "cookies_file": self._cookies_file,
                    "proxy": self._proxy, "custom_ffmpeg": self._custom_ffmpeg,
                    "filename_template": self._filename_template,
                    "audio_quality": self._audio_quality, "subtitle_langs": self._subtitle_langs,
                    "concurrent": self._concurrent, "archive_file": self._archive_file,
                    "save_folder": self._save_folder,
                    "player_client": self._player_client,
                    "custom_ydl_args": self._custom_ydl_args,
                }
                bool_map = {
                    "embed_thumb": self._embed_thumb, "subtitles": self._subs,
                    "restrict": self._restrict, "no_overwrite": self._no_overwrite,
                    "use_save_folder": self._use_save_folder,
                }
                if k in var_map:
                    var_map[k].set(v)
                elif k in bool_map:
                    bool_map[k].set(v == "True")
        except Exception:
            pass

    # ======================================================================
    # UI helpers
    # ======================================================================

    def _setup_paste_menu(self, entry: ctk.CTkEntry):
        menu = tk.Menu(self, tearoff=False)

        def do_paste():
            try:
                text = self.clipboard_get()
                entry.insert("insert", text)
            except tk.TclError:
                pass

        menu.add_command(label="Paste", command=do_paste)
        menu.add_command(label="Cut", command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: entry.event_generate("<<Copy>>"))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        entry.bind("<Button-3>", show_menu)
        entry.bind("<Button-2>", show_menu)

    def _set_busy(self, busy: bool):
        self._load_btn.configure(state="disabled" if busy else "normal")
        self._dl_btn.configure(state="disabled" if busy else "normal")
        self.url_entry.configure(state="disabled" if busy else "normal")
        self._cancel_btn.configure(state="normal" if busy else "disabled")

    def _show_ffmpeg_help(self):
        msg = (
            "ffmpeg is required for MP4, Best, and MP3 downloads.\n\n"
            "To install:\n"
            "  1. Download ffmpeg from:\n"
            "     https://ffmpeg.org/download.html\n"
            "  2. Extract the zip and place ffmpeg.exe in:\n"
            f"     {CONFIG_DIR}\n"
            "  3. Or add the folder containing ffmpeg.exe to your PATH.\n\n"
            "You can also set a custom path in Advanced > FFmpeg."
        )
        popup = ctk.CTkToplevel(self)
        popup.title("Install ffmpeg")
        popup.geometry("480x300")
        popup.minsize(440, 260)
        popup.resizable(True, True)
        popup.transient(self)
        popup.grab_set()

        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            popup, text="ffmpeg not found", font=("Segoe UI", 15, "bold"), anchor="w"
        ).grid(row=0, column=0, padx=16, pady=(14, 4), sticky="w")

        box = ctk.CTkTextbox(popup, wrap="word", font=("Segoe UI", 12))
        box.grid(row=1, column=0, padx=16, pady=4, sticky="nsew")
        box.insert("0.0", msg)
        box.configure(state="disabled")

        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=(4, 14))

        ctk.CTkButton(
            btn_frame, text="Open Download Page",
            command=lambda: [webbrowser.open("https://ffmpeg.org/download.html"), popup.destroy()]
        ).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="OK", command=popup.destroy).pack(side="left", padx=4)

    def _set_status(self, msg: str, is_error: bool = False):
        self._status_textbox.configure(state="normal")
        self._status_textbox.delete("0.0", "end")
        self._status_textbox.insert("0.0", msg)
        self._status_textbox.configure(
            state="disabled",
            text_color="#f87171" if is_error else "#a0aec0",
        )

    # ======================================================================
    # Load formats
    # ======================================================================

    def _load_formats(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Enter a URL first.", True)
            return
        self._set_busy(True)
        self._set_status("Loading formats...")
        self._load_btn.configure(text="Loading...")

        def work():
            result = self.worker.fetch_formats(
                url, self._playlist_var.get(),
                player_client=self._player_client.get().strip(),
                custom_ydl_args=self._custom_ydl_args.get().strip(),
            )
            self.after(0, self._on_formats_result, result)

        threading.Thread(target=work, daemon=True).start()

    def _on_formats_result(self, result: dict):
        self._set_busy(False)
        self._load_btn.configure(text="Load Formats")

        if "error" in result:
            self._set_status(result["error"], True)
            return

        title = result.get("title", "")
        formats = result.get("formats", [])

        self._title_label.configure(text=f"Title: {title}" if title else "")

        if not formats:
            self._set_status("No formats found.", True)
            return

        self._show_format_list(formats)
        self._set_status(f"{len(formats)} formats loaded. Select one or use default.")

    def _show_format_list(self, formats: list[dict]):
        if self._format_list_frame:
            self._format_list_frame.destroy()

        self._format_container.grid()
        self._format_radio_var.set("")

        header_frame = ctk.CTkFrame(self._format_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        header_frame.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            header_frame, text="Select quality (or leave default):",
            font=("Segoe UI", 12, "bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
            header_frame, text="Clear", width=60, height=24,
            command=self._clear_format_selection,
            fg_color="#4b5563", hover_color="#6b7280", font=("Segoe UI", 10),
        )
        clear_btn.grid(row=0, column=5, padx=(6, 4))

        close_btn = ctk.CTkButton(
            header_frame, text="\u2716", width=32, height=24,
            command=self._close_format_list,
            fg_color="#6b7280", hover_color="#dc2626", font=("Segoe UI", 10),
        )
        close_btn.grid(row=0, column=6, padx=(0, 0))

        self._format_list_frame = ctk.CTkScrollableFrame(
            self._format_container, height=200
        )
        self._format_list_frame.grid(row=1, column=0, sticky="ew")
        self._format_list_frame.grid_columnconfigure(4, weight=1)

        hdr = ctk.CTkFrame(self._format_list_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, 2))
        hdr.grid_columnconfigure((1, 2, 3, 4), weight=1)
        for ci, txt in enumerate(["", "ID", "Resolution", "Codec", "Size"]):
            ctk.CTkLabel(
                hdr, text=txt, font=("Segoe UI", 10, "bold"), anchor="w"
            ).grid(row=0, column=ci, padx=4, sticky="w")

        display = formats[:500]
        for idx, f in enumerate(display):
            fid = f.get("format_id", "")
            row_frame = ctk.CTkFrame(self._format_list_frame, fg_color="transparent")
            row_frame.grid(row=idx + 1, column=0, columnspan=5, sticky="ew", pady=1)
            row_frame.grid_columnconfigure((1, 2, 3, 4), weight=1)

            rb = ctk.CTkRadioButton(
                row_frame, text="", variable=self._format_radio_var, value=fid, width=20,
                command=self._on_format_picked,
            )
            rb.grid(row=0, column=0, padx=(0, 4))

            ctk.CTkLabel(row_frame, text=fid, anchor="w", font=("Consolas", 11)).grid(
                row=0, column=1, padx=4, sticky="w"
            )

            res = f.get("resolution") or f.get("format_note") or ""
            ctk.CTkLabel(row_frame, text=res, anchor="w").grid(
                row=0, column=2, padx=4, sticky="w"
            )

            codec = " ".join(filter(None, [f.get("vcodec", ""), f.get("acodec", "")]))
            if not codec:
                codec = f.get("ext", "")
            ctk.CTkLabel(row_frame, text=codec, anchor="w").grid(
                row=0, column=3, padx=4, sticky="w"
            )

            sz = format_bytes(f.get("filesize"))
            ctk.CTkLabel(row_frame, text=sz, anchor="w").grid(
                row=0, column=4, padx=4, sticky="w"
            )

    def _on_format_picked(self):
        self._selected_format_id = self._format_radio_var.get() or None
        if self._selected_format_id:
            self._set_status(f"Format selected: {self._selected_format_id}")
        else:
            self._set_status("Using default quality.")

    def _clear_format_selection(self):
        self._format_radio_var.set("")
        self._selected_format_id = None
        self._set_status("Using default quality.")

    def _close_format_list(self):
        self._clear_format_selection()
        self._format_container.grid_remove()
        self._title_label.configure(text="")

    # ======================================================================
    # Download
    # ======================================================================

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Enter a URL first.", True)
            return

        if self._current_download_id:
            self._set_status("A download is already in progress.", True)
            return

        try:
            concurrent = int(self._concurrent.get())
            if concurrent < 1:
                concurrent = 1
        except ValueError:
            concurrent = 1

        opts = DownloadOptions(
            url=url,
            format_type=self._fmt_var.get(),
            format_code=self._selected_format_id,
            playlist=self._playlist_var.get(),
            output_dir=self._output_dir.get().strip() or None,
            filename_template=self._filename_template.get().strip() or None,
            cookies_file=self._cookies_file.get().strip() or None,
            proxy=self._proxy.get().strip() or None,
            embed_thumbnail=self._embed_thumb.get(),
            subtitles=self._subs.get(),
            subtitle_langs=self._subtitle_langs.get().strip() or "en",
            audio_quality=self._audio_quality.get(),
            concurrent_fragments=concurrent,
            download_archive=self._archive_file.get().strip() or None,
            custom_ffmpeg_path=self._custom_ffmpeg.get().strip() or None,
            restrict_filenames=self._restrict.get(),
            no_overwrites=self._no_overwrite.get(),
            player_client=self._player_client.get().strip() or None,
            custom_ydl_args=self._custom_ydl_args.get().strip(),
        )

        self._set_busy(True)
        self._current_download_id = self.worker.start_download(opts)

        self._prog_frame.grid()
        self._prog_bar.set(0)
        self._prog_pct.configure(text="0%")
        self._set_status("Starting download...")
        self._poll_progress()

    def _cancel_download(self):
        if self._current_download_id:
            self.worker.pop_progress(self._current_download_id)
            self._current_download_id = None
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        self._set_busy(False)
        self._prog_frame.grid_remove()
        self._set_status("Download cancelled.")

    def _poll_progress(self):
        did = self._current_download_id
        if not did:
            return

        info = self.worker.get_progress(did)
        if not info:
            self._finish_download(None)
            return

        pct = info.get("percent", 0)
        self._prog_bar.set(pct / 100.0)
        self._prog_pct.configure(text=f"{pct}%")
        status = info.get("status", "")

        if status in ("downloading", "merging"):
            label = "Merging..." if status == "merging" else "Downloading..."
            self._set_status(f"{label} {pct}%")
            self._poll_job = self.after(400, self._poll_progress)
        elif status == "processing":
            self._set_status("Processing...")
            self._poll_job = self.after(400, self._poll_progress)
        elif status == "completed":
            self._prog_bar.set(1.0)
            self._prog_pct.configure(text="100%")
            self._set_status("Download complete!")
            fp = self.worker.get_file_path(did, info.get("output_dir"))
            self._finish_download(
                fp,
                output_dir=info.get("output_dir"),
                download_id=did,
            )
        elif status == "error":
            self._finish_download(None, error=info.get("error", "Download failed."))

    def _finish_download(self, file_path: str | None, error: str | None = None,
                         output_dir: str | None = None, download_id: str | None = None):
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        self._current_download_id = None
        self._set_busy(False)
        self._prog_frame.grid_remove()

        if error:
            self._set_status(error, True)
        elif file_path:
            if self._use_save_folder.get():
                folder = self._save_folder.get().strip()
                if folder:
                    self._save_all_to_folder(file_path, output_dir, download_id, folder)
                else:
                    self._set_status("Save folder is set but path is empty.", True)
            else:
                self._prompt_save_file(file_path)
        else:
            self._set_status("File not found after download.", True)

    # ======================================================================
    # Save file dialog
    # ======================================================================

    def _prompt_save_file(self, source_path: str):
        src = Path(source_path)
        suggested = src.name
        parts = suggested.split("_", 1)
        if len(parts) == 2 and len(parts[0]) == 36:
            suggested = parts[1]

        dest = filedialog.asksaveasfilename(
            initialfile=suggested,
            defaultextension=src.suffix,
            filetypes=[
                (f"{src.suffix.upper()} files", f"*{src.suffix}"),
                ("All files", "*.*"),
            ],
        )
        if dest:
            try:
                shutil.copy2(source_path, dest)
                self._set_status(f"Saved to: {dest}")
            except Exception as e:
                self._set_status(f"Failed to save file: {e}", True)
        else:
            self._set_status("Download complete. File not saved.")
        self.worker.remove_file(source_path)

    def _save_all_to_folder(self, source_main_path: str,
                            output_dir: str | None,
                            download_id: str | None,
                            save_folder: str):
        dst_root = Path(save_folder)
        try:
            dst_root.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._set_status(f"Cannot create save folder: {e}", True)
            return

        # find all files associated with this download
        out_folder = Path(output_dir) if output_dir else DEFAULT_DOWNLOAD_FOLDER
        all_names = find_all_files_by_id(download_id or "", out_folder) if download_id else [Path(source_main_path).name]

        copied = 0
        errors: list[str] = []
        for fn in all_names:
            src = out_folder / fn
            if not src.is_file():
                continue
            dst = dst_root / fn
            parts = fn.split("_", 1)
            if len(parts) == 2 and len(parts[0]) == 36:
                dst = dst_root / parts[1]
            if dst.exists() and self._no_overwrite.get():
                continue
            try:
                shutil.copy2(str(src), str(dst))
                copied += 1
            except Exception as e:
                errors.append(f"{fn}: {e}")
            finally:
                try:
                    src.unlink(missing_ok=True)
                except Exception:
                    pass

        if errors:
            self._set_status(f"Saved {copied} file(s) to {dst_root} — errors: {'; '.join(errors)}", True)
        else:
            self._set_status(f"Saved {copied} file(s) to: {dst_root}")


def run():
    app = DownloadApp()
    app.mainloop()
