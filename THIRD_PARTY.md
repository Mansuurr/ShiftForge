# Third-party engines and local Windows build

DragShift's application source remains under the upstream MIT license in LICENSE.
The source contribution contains no engine binaries. DragShift discovers optional
engines locally and runs them as separate command-line programs. The versions
below describe the tested private Windows package, not an official upstream release.

## FFglitch 0.10.2

Copyright 2017–2024 Ramiro Polla and the FFmpeg contributors. GPL, as indicated
by the supplied binaries' `-version` output (`--enable-gpl`).

- Project and documentation: https://ffglitch.org/
- Original Windows distribution: https://ffglitch.org/pub/bin/win64/ffglitch-0.10.2-windows-x86_64.zip
- Corresponding complete source archive: https://ffglitch.org/pub/src/ffglitch-0.10.2.tar.xz
- Source repository and license: https://github.com/ramiropolla/ffglitch-core/tree/ffedit-0.10

`assets/datamosh.js` is original code for this DragShift extension, based on the
documented FFglitch 0.10.2 motion-vector API. No third-party effect scripts were copied.

## FFmpeg / FFprobe

This computer's Gyan full static FFmpeg build is copied as a sidecar to make the
installed custom build independent of PATH. Version: 2026-06-04-git-c27a3b12e3.
Its build configuration enables GPL and version 3. FFmpeg and FFprobe are GPLv3
in this configuration; they remain independent executables.

- Project, licensing and source: https://ffmpeg.org/legal.html
- FFmpeg source revision: https://github.com/FFmpeg/FFmpeg/tree/c27a3b12e3
- Build provider, build configuration and external library source links: https://www.gyan.dev/ffmpeg/builds/
- GPLv3 license: https://www.gnu.org/licenses/gpl-3.0.html

This is a private local custom build, not an upstream DragShift release.
Before redistributing the bundled engines, provide the complete corresponding
source and notices required by their licenses, including configured external libraries.

## 7-Zip

The existing Windows installation's `7z.exe` and `7z.dll` are included as separate
archive-engine sidecars with their original license notice. The core is LGPL 2.1+
with BSD components and an unRAR restriction. This application reads RAR and never
creates RAR files.

- Source: https://github.com/ip7z/7zip
- Formats and downloads: https://www.7-zip.org/
- License: https://www.7-zip.org/license.txt

## Python dependencies

PySide6 / Qt (LGPLv3), PyMuPDF (AGPLv3), Pillow (HPND), pillow-heif, NumPy,
python-docx and pywin32 retain their respective upstream licenses. Their versions
are recorded in requirements-windows-lock.txt. PyInstaller also collects package
metadata and available license files in the frozen distribution.
