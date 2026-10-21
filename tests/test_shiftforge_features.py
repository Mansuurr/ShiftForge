import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from dragshift import theme
from dragshift.presets import for_category
from dragshift.watchfolders import WatchFolderManager, resolved_target


class FakeSettings:
    def __init__(self, values):
        self.values = values

    def get(self, key):
        return self.values[key]


def test_dark_and_light_styles_are_distinct():
    try:
        theme.set_mode("light")
        light = theme.qss()
        theme.set_mode("dark")
        dark = theme.qss()
        assert light != dark
        assert "#171918" in dark and "#f1f3ef" in dark
    finally:
        theme.set_mode("light")


def test_presets_are_filtered_by_type_and_available_target():
    settings = FakeSettings({"presets": [
        {"name": "Web", "category": "image", "target": "WEBP"},
        {"name": "Video", "category": "video", "target": "MP4"},
        {"name": "Document", "category": "document", "target": "PDF"},
    ]})
    assert [p["name"] for p in for_category(settings, "image", ["WEBP", "PNG"])] == ["Web"]
    assert [p["name"] for p in for_category(settings, "docx", ["PDF", "TXT"])] == ["Document"]


def test_magic_folder_waits_for_a_stable_new_file(qt_session, tmp_path):
    settings = FakeSettings({"watch_folders": [{"path": str(tmp_path), "target": "AUTO"}]})
    manager = WatchFolderManager(settings)
    converted = []
    manager.convert_requested.connect(lambda path, target: converted.append((path, target)))
    source = tmp_path / "new.png"
    Image.new("RGB", (20, 20), "white").save(source)
    manager._scan(str(tmp_path.resolve()))
    manager.timer.stop()
    for _ in range(3):
        manager._poll()
    assert converted == [(str(source.resolve()), "WEBP")]
    assert resolved_target(tmp_path / "already.webp", "AUTO") is None


@pytest.mark.skipif(os.name != "nt", reason="Windows built-in OCR")
def test_windows_ocr_writes_local_text(tmp_path):
    from dragshift.ocr import extract_text
    source = tmp_path / "words.png"
    image = Image.new("RGB", (760, 180), "white")
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 58)
    ImageDraw.Draw(image).text((25, 48), "HELLO 123", fill="black", font=font)
    image.save(source)
    output = extract_text(source)[0]
    text = output.read_text(encoding="utf-8").upper()
    assert output.name == "words OCR.txt"
    assert "HELLO" in text and "123" in text
