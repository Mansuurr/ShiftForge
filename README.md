# DragShift — local file tools

## Custom Windows build 1.1.0+files.4

This local extension is based on [llamaboi55/DragShift](https://github.com/llamaboi55/DragShift), upstream commit `88abe0cf392b80ad2db805ef12b020c76a6cf458` retrieved on 2026-10-19. It is not an official upstream release. The custom Windows package adds video, audio, experimental Datamosh and archive workflows to the original Shift-drag radial menu, with neutral matte glass.

The supplied deliverables are `DragShift-Files-Setup.exe`, `DragShift-Files-Source.zip` and the Russian `DragShift-Руководство.md`. Upstream GitHub releases do not contain these local additions. Cross-platform modules remain in the source tree; this custom distribution and its bundled engines target Windows x64.

## Start and convert

Launch DragShift once; it stays in the system tray. There is no standalone file queue or upload window.

1. Begin dragging a file in Explorer or on the desktop.
2. Press **Shift**, then drop it on a menu sector.
3. Tap **Shift** again while dragging to switch between **Convert** and **Tools**.

Choose a format in **Convert**, or an operation in **Tools**. Editors open only after choosing a tool. Several files of the same type can be dragged together. The tray icon opens its control menu, with **Settings…**, **How to use** and **Quit DragShift**. The per-user installer can add Explorer's **DragShift…** and **Send to → DragShift** entries, which also use the radial menu. Ctrl or Alt can replace Shift in Settings.

## Supported workflows

| Input | Output formats | Tools |
|---|---|---|
| Images: PNG, JPG/JPEG, WebP, HEIC/HEIF, AVIF, TIFF, BMP, GIF, ICO | PNG, JPG, WebP, HEIC, AVIF, TIFF, BMP, GIF, ICO, PDF | Compress, resize, crop, colour/light edits, annotate, redact, add background, view/remove metadata |
| Video: MP4, MKV, MOV, AVI, WebM, M4V, WMV, FLV, TS/MTS/M2TS, MPEG/MPG, 3GP, OGV, VOB | MP4, MKV, MOV, WebM, AVI, animated GIF, MP3, WAV | Trim, compress, resize, crop/rotate/mirror, speed, colour, mute, PNG frame, metadata, Datamosh, Audio extraction |
| Audio: MP3, WAV, FLAC, M4A/M4B, AAC, OGG/OGA, Opus, AIFF/AIF, WMA, APE, ALAC, AMR | MP3, WAV, FLAC, M4A, AAC, OGG, Opus, AIFF | Trim, edit, normalize, fade, compress, reverse, metadata |
| Archives: ZIP, 7Z, RAR, TAR | ZIP, 7Z, TAR | Contents, extract into a new folder |
| PDF | JPG/PNG per page, DOCX, TXT | Compress, split, rotate, merge, password protection, extract images, metadata |
| Word DOCX | PDF, TXT | Conversion |
| Text: TXT, MD, CSV, LOG, JSON, XML, HTML/HTM | PDF, DOCX | Plain-text conversion |

Available decoders and encoders determine whether a particular file is readable. Unsupported extensions have no conversion actions in the radial menu. This is not a general Office, spreadsheet, slide, OCR or 3D converter. Text formats are imported as text, without evaluating HTML, Markdown or spreadsheet formulas. Animated images opened through image conversion use their first frame; animated GIF export from video is a separate workflow.

DOCX → PDF uses Microsoft Word when available, otherwise a basic local renderer. PDF → DOCX rebuilds paragraphs and images. Complex layouts, fonts, tables, headers, charts and scanned pages may not reproduce accurately; scanned text is not recognized with OCR.

## Video and Datamosh

MP4/MKV/MOV use H.264 and AAC, WebM uses VP9 and Opus, and AVI uses MPEG-4 video. GIF exports use 12 fps and an edge up to 640 px. Video edits save a new MP4. Speed ranges from 0.25× to 4× and preserves audio pitch. The editor's frame preview shows the source; it does not render pending edits.

**Tools → Audio** extracts the first audio track from a video into any supported audio output format. **Mute** saves an MP4 without audio; **Frame** saves a full-resolution PNG.

For a psychedelic transition from the end of A to the beginning of B:

1. Open **Tools → Datamosh** on A and choose B, or select two videos together.
2. Set **Last seconds of A**, **First seconds of B** and **Transition duration**. Leave at least 0.1 seconds of clean B after the transition.
3. **Melt** is selected by default. You can also choose **Bloom**, **Fluid** or **Psychedelic**, intensity, longest edge, fps and whether to retain audio.
4. Use **Render preview** for a short 480 px export, then open it from the result notification. **Create transition** saves the full selected segments as MP4.

The bridge uses FFglitch motion-vector editing and I-frame removal, then recovers a clean B. A final FFmpeg pass produces a playable H.264 MP4. The output consists of the selected tail/head segments, not both entire videos. Audio segments are joined; silence fills a missing track when only one selected segment has audio. Datamosh is experimental: motion-rich clips tend to produce stronger artifacts, and source material affects every result.

## Audio

**Edit** combines trimming, volume in dB, pitch-preserving tempo, reverse, mono, fades, normalization, sample rate and output format. Edits save directly to **Save as**, so WAV or FLAC can be chosen without an intermediate AAC encode. The initial format follows the input when supported; otherwise it is M4A. **Compress** starts with MP3 at 128 kb/s.

Normalization measures the processed signal, then applies FFmpeg's two-pass EBU R128 `loudnorm` at −16 LUFS, −1.5 dBTP and LRA 11. Fades are included in the measurement; a volume gain follows normalization, so a positive gain can exceed that normalization peak target. Silence or material shorter than the measurement gate is exported without invalid infinite measurements.

MP3 supports up to 320 kb/s. OGG uses Vorbis VBR quality 5. WAV/AIFF use 16-bit PCM; FLAC uses lossless compression. Bitrate controls apply to MP3, M4A/AAC and Opus. Opus output uses 48 kHz; explicitly incompatible sample rates are rejected. Automatic rate selection retains the source rate when the encoder supports it. Only the first audio track is exported; cover art, video, subtitles and chapters are excluded. Reverse buffers the selected audio in memory, so trim long material before reversing it.

## Archives, outputs and cancellation

**Tools → Pack** creates one **ZIP** (default) or **7Z** archive from selected files and folders, including mixed file types and unsupported conversion extensions. Start dragging the selection, press Shift, switch to Tools with another Shift press, then drop on Pack and choose the archive format. Folders and unknown file types show the Pack tool directly. Moving the pointer over the hub never switches rings; click menus also accept deliberate hub clicks.

Folder structure, empty folders and modification times are retained. Overlapping selections are included once. Conflicting top-level names and links/junctions are rejected with an explanation. Limits are 100,000 items and 20 GiB of source data. Packing first creates a cancellable temporary copy, so enough free space for that copy and the archive is required.

The archive is saved beside the first remaining top-level selection, or in its parent's DragShift subfolder according to Settings. If that would place the result inside a selected folder, it is saved beside that folder instead. Existing results receive a numbered name. Choosing Pack for an existing archive puts that archive file into a new archive; Convert changes the format of its contents.


Archive conversion uses the local 7-Zip engine. RAR is read-only; RAR creation and encrypted archives are not supported. Contents are inspected before extraction. Unsafe paths, links, special files and colliding names are rejected. Limits are 100,000 listed entries and 20 GiB of declared uncompressed data; extraction also checks free disk space and the actual extracted tree.

Conversions and edits use **Settings → Save results**: beside the original, or in a `DragShift` subfolder. Archive extraction always creates a unique **`<name> Extracted`** folder beside the original archive. Existing results receive a numbered name rather than being replaced.

Video, audio and archive processing runs in background workers with a progress window and **Cancel**. Their batch conversions roll back results from earlier files when a later file fails or the batch is cancelled. Original files are kept. Closing a busy progress window requests cancellation. Result notifications offer **Open**, **Show** and **Undo**; Undo sends newly created results to the Recycle Bin.

All conversion engines process local files; DragShift does not upload media or download an engine during a job. **Listen to original** and result **Open** launch the system's associated app. The glass retains local background snapshots, blur and refraction, with a neutral light tint and simple controls. Snapshots stay in memory for decoration and are not saved or sent. On Windows, native acrylic is the fallback when a snapshot is unavailable. Set `DRAGSHIFT_RECORDING=1` before launch to keep windows visible to screen-recording tools.

## Run, verify and build from source

Use a Python virtual environment. The Windows dependency snapshot is in `requirements-windows-lock.txt`; the base runtime requirements are in `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-windows-lock.txt
.\.venv\Scripts\python.exe -m dragshift
```

Place FFmpeg/FFprobe, FFglitch 0.10.2 (`ffgac` and `ffedit`), and 7-Zip in `bin/`, with their notices. For a Windows 7-Zip sidecar, keep `7z.dll` beside `7z.exe`. Source archives omit these engine binaries; obtain them separately from the sources below.

Engine discovery accepts `DRAGSHIFT_FFMPEG`, `DRAGSHIFT_FFPROBE`, `DRAGSHIFT_FFGAC`, `DRAGSHIFT_FFEDIT` and `DRAGSHIFT_7Z`, then bundled `bin/` and PATH. The archive engine also checks an existing `C:\Program Files\7-Zip\7z.exe` installation.

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m dragshift --selftest
.\.venv\Scripts\python.exe -m dragshift --video-selftest
.\.venv\Scripts\python.exe -m dragshift --files-selftest
.\.venv\Scripts\python.exe -m PyInstaller DragShift.spec --noconfirm
ISCC.exe installer\DragShift.iss
```

The Inno Setup recipe creates `dist/DragShift-Setup.exe`; the delivered custom installer is named `DragShift-Files-Setup.exe`. Synthetic integration checks exercise real codecs and archive round trips when their engines are installed. Run the self-test switches on the frozen executable too when validating a package. Tests that require optional media engines skip when those engines are absent. The custom build has been verified on Windows; macOS and Linux need platform validation.

Windows logs are written to `%LOCALAPPDATA%\DragShift\log.txt`. Settings are available from the tray menu; closing an editor leaves the tray app running. A normal launch or second launch only shows a short reminder to use Shift-drag; `--quiet` launches silently.

## Engines and licenses

- [FFmpeg documentation](https://ffmpeg.org/documentation.html), [FFmpeg source](https://github.com/FFmpeg/FFmpeg), and [Gyan Windows builds](https://www.gyan.dev/ffmpeg/builds/).
- [FFglitch documentation](https://ffglitch.org/), [FFglitch 0.10 source repository](https://github.com/ramiropolla/ffglitch-core/tree/ffedit-0.10), and [0.10.2 source archive](https://ffglitch.org/pub/src/ffglitch-0.10.2.tar.xz).
- [7-Zip downloads](https://www.7-zip.org/), [7-Zip source](https://github.com/ip7z/7zip), and [license](https://www.7-zip.org/license.txt).
- Application source: upstream [MIT license](LICENSE). Bundled engines and Python dependencies retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md) before redistributing a package.
