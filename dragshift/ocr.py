"""Offline text recognition through the OCR engine built into Windows."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from .convert import open_image
from .util import UserError, sibling


async def _recognize_file(path: Path) -> str:
    try:
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage import FileAccessMode, StorageFile
    except ImportError as error:  # pragma: no cover - exercised by non-Windows CI
        raise UserError("OCR доступен в Windows 10/11 и не установлен в этой сборке.") from error

    source = await StorageFile.get_file_from_path_async(str(path.resolve()))
    stream = await source.open_async(FileAccessMode.READ)
    try:
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            raise UserError("В Windows не установлен язык для распознавания текста.")
        result = await engine.recognize_async(bitmap)
        return result.text.strip()
    finally:
        stream.close()


def extract_text(src: str | Path) -> list[Path]:
    """Recognize an image locally and save UTF-8 text next to the original."""
    source = Path(src)
    if os.name != "nt":
        raise UserError("Распознавание текста в этой сборке поддерживается только в Windows.")
    try:
        image = open_image(source).convert("RGB")
    except Exception as error:
        raise UserError("Не удалось открыть изображение для распознавания текста.") from error

    # Normalizing to PNG lets the Windows engine handle HEIC/AVIF/TIFF through
    # Pillow and avoids OCR limits on extremely large camera originals.
    limit = 7000
    if max(image.size) > limit:
        image.thumbnail((limit, limit))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix="shiftforge-ocr-", suffix=".png", delete=False) as file:
            temporary = Path(file.name)
        image.save(temporary, "PNG")
        text = asyncio.run(_recognize_file(temporary))
    except UserError:
        raise
    except Exception as error:
        raise UserError(f"Windows не смог распознать текст: {error}") from error
    finally:
        image.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    if not text:
        raise UserError("Текст на изображении не найден.")
    output = sibling(source, "OCR", ".txt")
    output.write_text(text + "\n", encoding="utf-8")
    return [output]
