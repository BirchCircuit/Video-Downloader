# Video Downloader — Documentation

## Overview

This app lets you download videos and music from YouTube, Vimeo, TikTok, Twitter/X, Facebook, Instagram, and hundreds of other websites.

It works by using `yt-dlp` (a powerful download tool) with a simple graphical interface — no command line needed.

---

## Quick Start — How to Download Your First Video

1. **Paste a video URL** into the big text box at the top (e.g. `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
2. **Choose a format** — Best, MP4, or MP3 (see format descriptions below)
3. Click **Download**
4. After the download finishes, a **Save As** window pops up — pick where to save the file

That's it. For most videos, nothing else needs to be changed.

---

## Download Formats — Which One Should I Pick?

### Best (recommended for most people)
Downloads the highest quality video+audio available. Keeps whatever container format the site uses (WebM, MKV, MP4, etc.). Usually does NOT need ffmpeg.

**Use this when:** You want the best quality without worrying about settings.

### MP4
Downloads the best video and best audio separately, then merges them into an MP4 file. Requires ffmpeg (see FFmpeg section).

**Use this when:** You need a file that plays on any device (TV, phone, game console, etc.).

### MP3
Extracts only the audio and converts it to MP3 format. Requires ffmpeg. Quality can be set in Advanced > Audio.

**Use this when:** You only want the music/sound from a video.

### Playlist
Downloads every video in a playlist, channel, or series. All files are packaged into a single ZIP archive. If you use this setting, make sure to monitor the downloads as it can sometimes download beyond the playlist.

**Use this when:** You want to download an entire YouTube playlist or channel.

### Load Formats
Fetches every available quality option for the URL and lets you pick a specific one (e.g. 720p vs 1080p, different codecs).

**Use this when:** You want to choose a specific resolution or format that the automatic selection might not pick.

---

## The Main Screen — What Everything Does

### URL Box
Paste the video link here. Press **Enter** or click **Download** to start.

### Format Buttons (Best / MP4 / MP3)
Select what kind of file you want. **Right-click** any button for a short explanation.

### Playlist Checkbox
Turn this on if the URL is a playlist or channel and you want to download everything.

### Title Label
After clicking "Load Formats", shows the video title.

### Format List
After clicking "Load Formats", shows all available quality options. Pick one, or leave it to use the default.

### Download Button
Starts the download with your chosen settings.

### Cancel Button
Stops the current download. Only enabled while a download is running.

### Progress Bar & Percentage
Shows how far along the download is.

### Status Text
Shows messages about what's happening. **You can select and copy text from here** — useful for sharing error messages.

### Supported Sites Panel (right side)
Lists every website the app can download from. Type in the search box to filter. Click any site name to copy it.

---

## Advanced Settings (Click "+ Advanced Options")

### Output Settings

#### Download folder
Where the app puts files temporarily while downloading. You normally don't need to change this — the app asks where to save when done.

**If you check** "Always save to this folder" below, this becomes the final destination instead, and you won't get a Save As prompt.

#### Filename template
Controls how downloaded files are named. Use these variables:

| Variable | What it does | Example |
|---|---|---|
| `%(title)s` | Video title | `Rick Astley - Never Gonna Give You Up` |
| `%(id)s` | Video ID | `dQw4w9WgXcQ` |
| `%(ext)s` | File extension | `mp4` |
| `%(resolution)s` | Video resolution | `1080p` |

Default: `%(title)s.%(ext)s` — just the video title with the right extension.

#### Restrict filenames
Removes special characters, spaces, and non-English letters. Makes filenames safe for older systems or scripts.

Example: `Rick Astley - Never Gonna Give You Up.mp4` becomes `Rick_Astley_-_Never_Gonna_Give_You_Up.mp4`

#### Don't overwrite existing files
If a file with the same name already exists where you're saving, the app skips the download instead of overwriting it.

#### Always save to this folder (skip save dialog)
When checked, the app won't ask "Save As" after downloading. It automatically copies the file (and any subtitles) to the folder you choose below.

**How to use:**
1. Check the box
2. Click **Browse** and pick a folder
3. Future downloads go there automatically

### Network Settings

#### Proxy URL
Lets you route downloads through a proxy server. Useful if:
- A video is blocked in your country
- Your network has download restrictions

Format: `http://user:pass@host:port` or `socks5://host:1080`

#### Concurrent fragments
For DASH and HLS streams (adaptive streaming), this controls how many pieces download at once. Higher numbers = faster downloads but use more bandwidth.

- **1** (default): Slow but steady
- **3-5**: Faster on good connections
- **10+**: Only if you have very fast internet

#### YouTube player client
YouTube serves different versions of videos to different devices. This setting lets you pick which "client" to pretend to be.

| Option | When to use |
|---|---|
| **default** | Normal videos. Use this for most downloads. |
| **android** | If a video says "not available" with default. Gives lower quality (max 360p). |
| **ios** | Better quality than android. Currently blocked for some videos. |
| **android,ios** | Best of both worlds — android for access, ios for quality. |
| **tv** | For smart TV streams. Often DRM-protected. |

**Tip:** If a video shows "This video is not available", try `android` first. If quality is too low, try `android,ios`.

### Authentication Settings

#### Cookies file
This is the most important setting for accessing restricted content.

**What it does:** Tells YouTube "I'm a real logged-in user" so you can download:
- Age-restricted videos ("Sign in to confirm your age")
- Member-only or subscription content
- Private videos you have access to

**How to get a cookies file:**
1. Install a browser extension that exports cookies (search for "get cookies.txt LOCALLY")
2. Go to YouTube and sign in to your account
3. Use the extension to export cookies to a `cookies.txt` file
4. In the app, click **Browse** under "Cookies file" and select that file

#### Download archive
A text file that keeps track of which videos you've already downloaded. When you run a playlist or channel download again, it skips anything already in the archive.

**How to use:**
1. Click **Browse** and pick a location for the archive file (e.g. `downloaded.txt`)
2. Done. The app adds video IDs to this file automatically as they download.

### Audio Settings

#### MP3 quality (kbps)
Only matters when downloading as MP3. Higher = better quality but larger files.

| Setting | Quality | Approx size per minute |
|---|---|---|
| 128 kbps | Radio quality | ~1 MB |
| 192 kbps | Good balance | ~1.5 MB |
| 256 kbps | High quality | ~2 MB |
| 320 kbps | Maximum quality | ~2.5 MB |

### Subtitles & Thumbnails Settings

#### Download subtitles
Downloads subtitle tracks for the video. The app saves both manual subtitles (uploaded by creators) and auto-generated ones (YouTube's automatic captions).

#### Subtitle language(s)
Which languages to download subtitles for. Use language codes separated by commas.

Common codes: `en` (English), `fr` (French), `de` (German), `es` (Spanish), `ja` (Japanese), `ko` (Korean), `pt` (Portuguese)

Example: `en,fr,es` downloads English, French, and Spanish subtitles.

#### Embed thumbnail
Embeds the video's thumbnail image directly into the file's metadata. Works with MP4, MKV, and some audio formats.

When you view the file in your computer's file explorer, the video may show the thumbnail as its icon.

### FFmpeg Settings

#### What is ffmpeg?
FFmpeg is a free program that processes video and audio. The app needs it for:
- Merging video + audio into MP4 files
- Converting to MP3
- Some "Best" format downloads

The app looks for `ffmpeg.exe` in its own folder automatically. You only need to set this if it's installed somewhere else.

#### Custom ffmpeg path
If you have ffmpeg installed in a different location, click **Browse** and point to `ffmpeg.exe`.

### Extra Settings

#### Custom yt-dlp args
For advanced users. Lets you pass extra command-line flags directly to yt-dlp.

**Common uses:**

| Goal | What to type |
|---|---|
| Don't update file timestamps | `--no-mtime` |
| Limit download speed | `--limit-rate 5M` (5 MB/s) |
| More retries on failure | `--retries 15` |
| Skip downloads on errors | `--ignore-errors` |
| Write video info as JSON | `--write-info-json` |
| Combine flags | `--no-mtime --limit-rate 2M --retries 10` |

**How it works:** The app parses these flags using yt-dlp's own command-line parser, so anything you'd type on a command line should work here. Flags that conflict with app settings (like output template) are ignored.

---

## Other Features

### Deno Integration (automatic)
If `deno.exe` is in the app folder, it's automatically used as the JavaScript engine for solving YouTube's puzzles. This helps when YouTube changes its player code and yt-dlp needs to figure out the new signatures.

You don't need to do anything — just keep `deno.exe` next to the app and it works silently in the background.

### Right-Click Help
**Right-click** on almost any setting label or control to see a short explanation of what it does.

### Right-Click Paste Menu
**Right-click** in any text field for a menu with Paste, Cut, and Copy options.

### Status Text is Copyable
The status bar at the bottom shows progress and error messages. You can **select the text** with your mouse and **copy it (Ctrl+C)** to share error messages for troubleshooting.

### Temporary File Cleanup
Files in the download folder are automatically deleted after 10 minutes if they weren't saved. The app also cleans up old files when it starts.

### Settings Auto-Save
Settings are saved to `settings.txt` next to the app when you click **Save Settings**. They load automatically the next time you open the app.

---

## Common Errors — What They Mean and How to Fix Them

### "This video is not available"

**What it means:** YouTube blocked the app's request. The video might still exist — YouTube is just refusing to serve it to automated tools.

**Try this first:**
1. Go to **Advanced > Network > YouTube player client**
2. Change it from "default" to **`android`**
3. Try downloading again

**If quality is too low (360p):**
- Change the player client to **`android,ios`** instead
- This combines android's access with ios's higher quality

**If still failing:**
- The video may be truly unavailable (removed, private, or geo-blocked)
- Try opening the video URL in your browser to check

### "This video is DRM protected"

**What it means:** Either this video is encrypted or more often just the higher quality versions are encrypted. YouTube protects them so only official apps can play them.

**Can I fix this?** No. The app can only download the unencrypted 360p version if available (see YouTube player client). This is a hard limit that no setting can bypass. It's common on music videos from major labels.

### "ffmpeg not found"

**What it means:** The app needs ffmpeg for MP4, MP3, or Best downloads, but can't find it.

**Fix:**
1. Download ffmpeg from https://ffmpeg.org/download.html
2. Extract the zip file
3. Place `ffmpeg.exe` (and optionally `ffprobe.exe`) in the same folder as the app
4. Restart the app

Or set a custom path in **Advanced > FFmpeg > Custom ffmpeg path**.

### "Requested format is not available"

**What it means:** The format you selected (or the default one) doesn't exist for this video.

**Fix:**
1. Click **Load Formats** to see what's actually available
2. Pick a different format from the list
3. Or try changing the **YouTube player client** setting

### "Sign in to confirm your age"

**What it means:** The video is age-restricted. YouTube requires a logged-in account to access it.

**Fix:** Provide cookies from a logged-in YouTube account:
1. Install the get "cookies.txt LOCALLY" extension in your browser
2. Sign in to YouTube
3. Export cookies to a file
4. In the app, set **Advanced > Authentication > Cookies file** to that file

### "Private video"

**What it means:** The video is set to private by the uploader. You can only access it if you're logged into the YouTube account that has permission.

**Fix:** Same as above — use a cookies file from the account that has access.

### "Video unavailable"

**What it means:** The video has been removed by the uploader or by YouTube. It no longer exists.

**Fix:** Open the URL in your browser to confirm. If it's really gone, there's nothing to download.

### Download stuck at 0%

**What it means:** The download started but isn't making progress.

**Possible causes and fixes:**

| Cause | What to do |
|---|---|
| Slow internet | Add `--limit-rate 5M` in **Custom yt-dlp args** |
| Network restriction | Set a **Proxy URL** |
| Large file | Increase **Concurrent fragments** to 3-5 |
| YouTube throttling | Try a different **YouTube player client** |

### Low quality (only 360p available)

**What it means:** The current player client only offers low-resolution streams.

**Fix:** 
1. Go to **Advanced > Network > YouTube player client**
2. If it's set to `android`, change it to **`android,ios`** or **`default`**
3. Try downloading again

---

## File Locations

| File | Purpose |
|---|---|
| `app.py` | Main application code (UI window) |
| `worker.py` | Download engine (yt-dlp integration) |
| `settings.txt` | Saved settings (auto-loaded on startup) |
| `downloads/` | Temporary download folder |
| `_pycache_/` | This folder stores pre-compiled versions of your code so Python programs start up and run faster |
| `deno.exe` | JavaScript runtime (auto-detected) |
| `ffmpeg.exe` | Video/audio processor (auto-detected) |
| `ffprobe.exe` | Media analyzer (used by ffmpeg) |
| `.disclaimer_accepted` | A file created to remember if you have accepted the disclaimer |
| `Video downloader instructions.pdf` | Instructions on how to install and basic use |
| `DOCUMENTATION.md` | This file in a standard format for open-source project documentation (needs a special reader) |
| `DOCUMENTATION.pdf` | This file in an accessible format |

---

## Tips & Tricks

- **Download multiple videos:** Paste a playlist or channel URL and check the **Playlist** box. Everything downloads into a single ZIP file.
- **Compare formats:** Click **Load Formats** before downloading to see all available resolutions, codecs, and file sizes.
- **Save time:** Enable **"Always save to this folder"** to skip the Save As prompt on every download.
- **Subtitle languages:** To download all available subtitles, use `-` as the language code (yt-dlp special value).
- **Avoid duplicates:** Use **Download archive** to track which videos you've already downloaded.
- **Watch for DRM:** Music videos from major labels (Universal, Sony, Warner) are often DRM-protected at higher qualities. Only 360p will be available.
