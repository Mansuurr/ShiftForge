"""Local archive conversion and safe extraction using the installed 7-Zip CLI.

Archives are copied into an isolated temporary workspace before inspection, so
the inspected bytes are the bytes extracted. Sources are never modified.
"""
from __future__ import annotations

import contextlib
import os
import re
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from . import video
from .util import UserError

TARGETS = ["ZIP", "7Z", "TAR"]
INPUT_EXTENSIONS = {".zip", ".7z", ".rar", ".tar"}
MAX_ENTRIES = 100_000
MAX_EXTRACTED_BYTES = 20 * 1024 ** 3
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.I)


@dataclass(frozen=True)
class ArchiveEntry:
    name: str
    size: int
    is_dir: bool


def executable() -> str:
    """Explicit override, bundled sidecar, installed Windows 7-Zip, then PATH."""
    override = os.environ.get("DRAGSHIFT_7Z")
    roots = [Path(sys.executable).parent] if getattr(sys, "frozen", False) else []
    roots.append(Path(__file__).resolve().parent.parent)
    suffix = ".exe" if os.name == "nt" else ""
    candidates = ([Path(override)] if override else [])
    candidates += [root / "bin" / ("7z" + suffix) for root in roots]
    candidates.append(Path(r"C:\Program Files\7-Zip\7z.exe"))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    found = shutil.which("7z") or shutil.which("7zz")
    if found:
        return found
    raise UserError("7-Zip was not found. Install 7-Zip, set DRAGSHIFT_7Z, or put 7z.exe in DragShift/bin.")


def _source(src) -> Path:
    video.check_cancel()
    source = Path(src).resolve()
    if not source.is_file():
        raise UserError("The selected archive was moved or deleted. Choose the file again.")
    if source.suffix.lower() not in INPUT_EXTENSIONS:
        raise UserError("Unsupported archive format. Choose ZIP, 7Z, RAR or TAR.")
    return source


def _safe_name(name: str) -> str:
    normalized = name.replace("\\", "/").rstrip("/")
    if (not normalized or name.startswith(("/", "\\")) or PureWindowsPath(name).drive
            or any(ord(char) < 32 or char in '<>:"|?*' for char in normalized)):
        raise UserError("This archive contains an unsafe file path.")
    parts = normalized.split("/")
    if any(part in ("", ".", "..") or part.endswith((".", " ")) or _RESERVED.match(part) for part in parts):
        raise UserError("This archive contains an unsafe file path.")
    return "/".join(parts)


def _records(raw: bytes) -> list[dict[str, str]]:
    try:
        text = raw.decode("utf-8-sig", "strict")
    except UnicodeError as error:
        raise UserError("The archive contains unreadable file names.") from error
    records = []
    current = {}
    for line in text.splitlines():
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, separator, value = line.partition(" = ")
        if not separator or not key or key in current:
            raise UserError("The archive listing is ambiguous or contains unsafe file names.")
        current[key] = value
    if current:
        records.append(current)
    return records


def entries(src) -> list[ArchiveEntry]:
    source = _source(src)
    try:
        raw = video.capture([executable(), "l", "-slt", "-ba", "-sccUTF-8",
                             "-t" + source.suffix[1:].lower(), "--", str(source)])
    except video.Cancelled:
        raise
    except UserError as error:
        raise UserError("Couldn't read this archive. It may be damaged, encrypted or unsupported.\n" + str(error).split("\n", 1)[-1]) from error
    records = _records(raw)
    if len(records) > MAX_ENTRIES:
        raise UserError(f"This archive contains too many entries (limit: {MAX_ENTRIES:,}).")
    result = []
    seen = {}
    total = 0
    for record in records:
        video.check_cancel()
        # Reject links before extraction, including Unix modes stored in ZIP.
        for key, value in record.items():
            lower = key.lower()
            if ((lower in ("symbolic link", "hard link") and value)
                    or ("reparse" in lower and value not in ("", "-", "0"))
                    or (lower == "alternate stream" and value == "+")):
                raise UserError("Links and alternate streams in archives are not supported.")
        attributes = record.get("Attributes", "") + " " + record.get("Mode", "")
        if re.search(r"(?:^|\s)[bclps][rwxstST-]{9}(?:\s|$)", attributes):
            raise UserError("Links and special files in archives are not supported.")
        if record.get("Encrypted") == "+":
            raise UserError("Password-protected archives are not supported.")
        try:
            name = _safe_name(record["Path"])
            size = int(record["Size"] or "0")
            if size < 0:
                raise ValueError
        except (KeyError, ValueError) as error:
            raise UserError("The archive contains invalid file information.") from error
        is_dir = record.get("Folder") == "+" or attributes.lstrip().startswith("D") or bool(re.search(r"(?:^|\s)d[rwxstST-]{9}", attributes))
        key = name.casefold()
        if key in seen:
            raise UserError("The archive contains colliding file names.")
        seen[key] = is_dir
        result.append(ArchiveEntry(name, size, is_dir))
        if not is_dir:
            total += size
        if total > MAX_EXTRACTED_BYTES:
            raise UserError(f"This archive is too large to extract safely (limit: {MAX_EXTRACTED_BYTES // 1024 ** 3} GB).")
    for entry in result:
        parts = entry.name.casefold().split("/")
        if any(seen.get("/".join(parts[:i])) is False for i in range(1, len(parts))):
            raise UserError("The archive contains colliding file and directory paths.")
    return result


def _run(args, **kwargs):
    try:
        return video.run_process(args, parse_progress=False, **kwargs)
    except video.Cancelled:
        raise
    except UserError as error:
        raise UserError("Archive processing failed. The original archive is unchanged.\n" + str(error).split("\n", 1)[-1]) from error


def _audit(folder: Path, members: list[ArchiveEntry]):
    """Check the actual tree before making any result visible to the user."""
    expected = {entry.name.casefold(): entry for entry in members}
    files = set()
    count = total = 0
    for current, directories, filenames in os.walk(folder, followlinks=False):
        for name in directories + filenames:
            video.check_cancel()
            path = Path(current) / name
            info = path.lstat()
            if (stat.S_ISLNK(info.st_mode) or info.st_nlink > 1 and not stat.S_ISDIR(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                    or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))):
                raise UserError("Links and special files in archives are not supported.")
            relative = _safe_name(path.relative_to(folder).as_posix()).casefold()
            count += 1
            if count > MAX_ENTRIES:
                raise UserError("This archive creates too many files and folders.")
            if stat.S_ISREG(info.st_mode):
                member = expected.get(relative)
                if member is None or member.is_dir or info.st_size != member.size:
                    raise UserError("The extracted files do not match the archive listing.")
                files.add(relative)
                total += info.st_size
                if total > MAX_EXTRACTED_BYTES:
                    raise UserError("This archive is too large to extract safely.")
    if files != {entry.name.casefold() for entry in members if not entry.is_dir}:
        raise UserError("The archive could not be extracted completely.")
    if any(not (folder / entry.name).is_dir() for entry in members if entry.is_dir):
        raise UserError("The archive could not be extracted completely.")


@contextlib.contextmanager
def _contents(source: Path):
    with tempfile.TemporaryDirectory(prefix=".~archive-", dir=source.parent) as name:
        workspace = Path(name)
        snapshot = workspace / ("input" + source.suffix.lower())
        with source.open("rb") as original, snapshot.open("xb") as copied:
            while chunk := original.read(1024 * 1024):
                video.check_cancel()
                copied.write(chunk)
        members = entries(snapshot)
        required = sum(entry.size for entry in members if not entry.is_dir)
        if shutil.disk_usage(workspace).free < required + 64 * 1024 ** 2:
            raise UserError("There is not enough free disk space to extract this archive.")
        folder = workspace / "contents"
        folder.mkdir()
        _run([executable(), "x", "-y", "-bd", "-bb0", "-sccUTF-8", "-aos",
              "-t" + source.suffix[1:].lower(), "-o" + str(folder), "--", str(snapshot)],
             message="Extracting archive…", offset=.05, span=.45)
        _audit(folder, members)
        yield folder


def extract(src) -> list[Path]:
    source = _source(src)
    with _contents(source) as folder:
        video.check_cancel()
        with video._publish_lock:
            base = source.with_name(source.stem + " Extracted")
            destination = base
            counter = 0
            while destination.exists():
                counter += 1
                destination = base.with_name(f"{base.name} ({counter})")
            # Windows directory rename atomically refuses an existing target.
            try:
                os.rename(folder, destination)
            except FileExistsError as error:
                raise UserError("Another program created this output folder. Please try again.") from error
    return [destination]


def convert_archive(src, target: str) -> list[Path]:
    target = target.upper()
    if target not in TARGETS:
        raise UserError("Unsupported archive export format. Choose ZIP, 7Z or TAR.")
    source = _source(src)
    with _contents(source) as folder:
        with video.export_path(source, ext="." + target.lower()) as (temporary, outputs):
            # 7-Zip creates the archive itself; an empty pre-created file is invalid.
            temporary.unlink()
            args = [executable(), "a", "-t" + target.lower(), "-y", "-bd", "-bb0", "-sccUTF-8"]
            if target != "TAR":
                args += ["-mx=5"]
            _run(args + ["--", str(temporary), "*"], cwd=folder,
                 message=f"Packing archive as {target}…", offset=.5, span=.45)
    return outputs
