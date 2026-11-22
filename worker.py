import threading
import uuid
import os
import shutil
import zipfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yt_dlp


STALE_AGE_SECONDS = 10 * 60
SUPPORTED_CACHE = {"ts": 0, "list": []}
CACHE_TTL_SECONDS = 60 * 60 * 24


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
DEFAULT_DOWNLOAD_FOLDER = BASE_DIR / "downloads"
DEFAULT_DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def resolve_ffmpeg(custom_path: str | None = None) -> str | None:
    if custom_path:
        p = Path(custom_path)
        if p.is_file():
            return str(p.resolve())
    local = BASE_DIR / "ffmpeg.exe"
    if local.is_file():
        return str(local)
    return shutil.which("ffmpeg")


FFMPEG_PATH = resolve_ffmpeg()


def resolve_deno() -> str | None:
    deno = BASE_DIR / "deno.exe"
    return str(deno) if deno.is_file() else None


SUBTITLE_EXTS = {".srt", ".vtt", ".ass", ".ssa", ".lrc", ".mpl"}


def parse_custom_ydl_args(args_str: str) -> dict:
    """Parse a space-separated string of CLI-style yt-dlp flags into an options dict."""
    if not args_str.strip():
        return {}
    try:
        import shlex
        from yt_dlp.options import create_parser
        parser = create_parser()
        defaults, _ = parser.parse_args([])
        custom, _ = parser.parse_known_args(shlex.split(args_str))
        result = {}
        for key in vars(defaults):
            dv = getattr(defaults, key)
            cv = getattr(custom, key)
            if cv != dv:
                result[key] = cv
        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Options dataclass
# ---------------------------------------------------------------------------

@dataclass
class DownloadOptions:
    url: str = ""
    format_type: str = "mp4"
    format_code: str | None = None
    playlist: bool = False
    output_dir: str | None = None
    filename_template: str | None = None
    cookies_file: str | None = None
    proxy: str | None = None
    embed_thumbnail: bool = False
    subtitles: bool = False
    subtitle_langs: str = "en"
    audio_quality: str = "192"
    concurrent_fragments: int = 1
    download_archive: str | None = None
    custom_ffmpeg_path: str | None = None
    restrict_filenames: bool = False
    no_overwrites: bool = False
    player_client: str | None = None
    custom_ydl_args: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def requires_ffmpeg(opts: DownloadOptions) -> bool:
    if opts.format_type == "mp3":
        return True
    if opts.format_code:
        return False
    if opts.format_type in ("mp4", "best"):
        return True
    return False


def find_file_by_id(download_id: str, folder: Path) -> str | None:
    try:
        files = [fn for fn in os.listdir(folder) if fn.startswith(download_id)]
        if not files:
            return None
        main = [fn for fn in files if Path(fn).suffix.lower() not in SUBTITLE_EXTS]
        if main:
            files = main
        zips = [fn for fn in files if fn.lower().endswith(".zip")]
        return sorted(zips)[0] if zips else sorted(files)[0]
    except FileNotFoundError:
        return None


def find_all_files_by_id(download_id: str, folder: Path) -> list[str]:
    try:
        return sorted(
            fn for fn in os.listdir(folder) if fn.startswith(download_id)
        )
    except FileNotFoundError:
        return []


def package_playlist_into_zip(download_id: str, folder: Path) -> str | None:
    matching = [
        p for p in folder.iterdir()
        if p.is_file() and p.name.startswith(download_id) and p.suffix.lower() != ".zip"
    ]
    if not matching:
        return None
    archive = folder / f"{download_id}.zip"
    try:
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in sorted(matching):
                zf.write(fp, arcname=fp.name)
        for fp in matching:
            try:
                fp.unlink(missing_ok=True)
            except Exception:
                pass
        return archive.name
    except Exception:
        return None


def cleanup_stale_files(folder: Path | None = None, age: int = STALE_AGE_SECONDS):
    folder = folder or DEFAULT_DOWNLOAD_FOLDER
    now = __import__("time").time()
    for fn in os.listdir(folder):
        full = folder / fn
        try:
            if full.is_file() and (now - full.stat().st_mtime) > age:
                full.unlink(missing_ok=True)
        except Exception:
            continue


def get_supported_extractors():
    try:
        from yt_dlp.extractor import gen_extractors
        names = []
        for ie in gen_extractors():
            name = getattr(ie, "IE_NAME", None)
            if name:
                names.append(name)
        return sorted(set(names))
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Idle file cleaner thread
# ---------------------------------------------------------------------------

def _start_cleaner():
    def loop():
        while True:
            __import__("time").sleep(CACHE_TTL_SECONDS)
            try:
                cleanup_stale_files()
            except Exception:
                pass
    t = threading.Thread(target=loop, daemon=True)
    t.start()


_start_cleaner()


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

class DownloadWorker:
    def __init__(self):
        self._lock = threading.Lock()
        self._progress: dict[str, dict] = {}

    # -- progress api -------------------------------------------------------

    def get_progress(self, download_id: str) -> dict | None:
        with self._lock:
            info = self._progress.get(download_id)
            return dict(info) if info else None

    def pop_progress(self, download_id: str) -> dict | None:
        with self._lock:
            return self._progress.pop(download_id, None)

    # -- start --------------------------------------------------------------

    def start_download(self, opts: DownloadOptions) -> str:
        download_id = str(uuid.uuid4())
        t = threading.Thread(
            target=self._run_download,
            args=(opts, download_id),
            daemon=True,
        )
        t.start()
        return download_id

    def _update(self, download_id: str, **kwargs):
        with self._lock:
            if download_id in self._progress:
                self._progress[download_id].update(kwargs)

    # -- the actual download -------------------------------------------------

    def _run_download(self, opts: DownloadOptions, download_id: str):
        # figure out which folder to use
        if opts.output_dir:
            out_folder = Path(opts.output_dir)
        else:
            out_folder = DEFAULT_DOWNLOAD_FOLDER
        out_folder.mkdir(parents=True, exist_ok=True)

        with self._lock:
            self._progress[download_id] = {
                "percent": 0,
                "status": "processing",
                "filename": None,
                "error": None,
                "playlist": opts.playlist,
            }

        # -- progress hook --------------------------------------------------
        def progress_hook(d):
            try:
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    percent = int((downloaded / total) * 100) if total else 0
                    self._update(download_id, percent=percent, status="downloading")
                elif d.get("status") == "finished":
                    self._update(download_id, percent=100, status="merging")
            except Exception:
                pass

        # -- ffmpeg check ----------------------------------------------------
        ffmpeg = resolve_ffmpeg(opts.custom_ffmpeg_path)
        if requires_ffmpeg(opts) and not ffmpeg:
            self._update(
                download_id,
                percent=0,
                status="error",
                error="ffmpeg not found. Install ffmpeg or place ffmpeg.exe alongside the app, "
                      "or set a custom path in Advanced settings.",
            )
            return

        # -- build yt-dlp opts ----------------------------------------------
        filename_tmpl = opts.filename_template or "%(title)s.%(ext)s"
        outtmpl = str(out_folder / f"{download_id}_{filename_tmpl}")

        ydl_opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "verbose": False,
            "progress_hooks": [progress_hook],
            "noplaylist": not opts.playlist,
            "outtmpl": outtmpl,
            "restrictfilenames": opts.restrict_filenames,
            "nooverwrites": opts.no_overwrites,
        }

        if ffmpeg:
            ydl_opts["ffmpeg_location"] = ffmpeg

        if opts.cookies_file:
            ydl_opts["cookiefile"] = opts.cookies_file

        if opts.proxy:
            ydl_opts["proxy"] = opts.proxy

        if opts.download_archive:
            ydl_opts["download_archive"] = opts.download_archive

        if opts.concurrent_fragments > 1:
            ydl_opts["concurrent_fragments"] = opts.concurrent_fragments

        if opts.player_client and opts.player_client not in ("default", ""):
            clients = [c.strip() for c in opts.player_client.split(",") if c.strip() and c not in ("default", "")]
            if clients:
                ydl_opts.setdefault("extractor_args", {})
                ydl_opts["extractor_args"]["youtube"] = {
                    "player_client": clients
                }

        custom = parse_custom_ydl_args(opts.custom_ydl_args)
        if custom:
            if opts.filename_template:
                custom.pop("outtmpl", None)
                custom.pop("output", None)
            ydl_opts.update(custom)

        # -- format / post-processing ---------------------------------------
        if opts.format_code:
            ydl_opts["format"] = opts.format_code
        elif opts.format_type == "mp3":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": opts.audio_quality,
                }],
            })
        elif opts.format_type == "best":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        else:
            ydl_opts.update({
                "format": "bv*+ba/best",
                "merge_output_format": "mp4",
            })

        # -- subtitles -------------------------------------------------------
        if opts.subtitles:
            ydl_opts.setdefault("subtitlesformat", "srt")
            ydl_opts.setdefault("subtitleslangs", [opts.subtitle_langs])
            ydl_opts.setdefault("writesubtitles", True)
            ydl_opts.setdefault("writeautomaticsub", True)

        # -- thumbnail -------------------------------------------------------
        if opts.embed_thumbnail:
            ydl_opts.setdefault("writethumbnail", True)
            pp = ydl_opts.setdefault("postprocessors", [])
            # EmbedThumbnail must come after FFmpegExtractAudio if used
            if not any(p.get("key") == "EmbedThumbnail" for p in pp):
                pp.append({"key": "EmbedThumbnail"})
            ydl_opts["embedthumbnail"] = True

        # -- javascript runtime ----------------------------------------------
        deno = resolve_deno()
        if deno:
            ydl_opts["js_executable"] = deno

        # -- run -------------------------------------------------------------
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([opts.url])

            if opts.playlist:
                filename = package_playlist_into_zip(download_id, out_folder)
            else:
                filename = find_file_by_id(download_id, out_folder)

            self._update(
                download_id,
                percent=100,
                status="completed",
                filename=filename,
                output_dir=str(out_folder.resolve()),
            )
        except Exception as e:
            self._update(download_id, percent=0, status="error", error=str(e))

    # -- fetch formats -------------------------------------------------------

    def fetch_formats(self, url: str, playlist_enabled: bool = False,
                      player_client: str | None = None,
                      custom_ydl_args: str = "") -> dict:
        ydl_opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "verbose": False,
            "noplaylist": not playlist_enabled,
        }
        ffmpeg = resolve_ffmpeg()
        if ffmpeg:
            ydl_opts["ffmpeg_location"] = ffmpeg

        deno = resolve_deno()
        if deno:
            ydl_opts["js_executable"] = deno

        if player_client and player_client not in ("default", ""):
            clients = [c.strip() for c in player_client.split(",") if c.strip() and c not in ("default", "")]
            if clients:
                ydl_opts.setdefault("extractor_args", {})
                ydl_opts["extractor_args"]["youtube"] = {
                    "player_client": clients
                }

        custom = parse_custom_ydl_args(custom_ydl_args)
        if custom:
            ydl_opts.update(custom)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if isinstance(info, dict) and info.get("_type") == "playlist":
                entries = info.get("entries") or []
                first = next((e for e in entries if e), None)
                if first:
                    info = first

            formats = []
            for f in info.get("formats", []):
                formats.append({
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f.get("resolution"),
                    "format_note": f.get("format_note"),
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                    "fps": f.get("fps"),
                    "tbr": f.get("tbr"),
                })

            return {"title": info.get("title"), "formats": formats}
        except Exception as e:
            return {"error": str(e)}

    # -- file helpers --------------------------------------------------------

    def get_file_path(self, download_id: str, output_dir: str | None = None) -> str | None:
        folder = Path(output_dir) if output_dir else DEFAULT_DOWNLOAD_FOLDER
        fn = find_file_by_id(download_id, folder)
        if not fn:
            return None
        p = folder / fn
        return str(p) if p.is_file() else None

    def remove_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
