"""Exercise bundled engines and radial editor routing in the frozen app."""
import tempfile
import time
import zipfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from . import audio, archives, video


def selftest():
    from .video_check import selftest as video_selftest
    if video_selftest() != 0:
        return 1
    try:
        with tempfile.TemporaryDirectory(prefix="dragshift-files-check-") as folder:
            base = Path(folder)
            sound = base / "audio.wav"
            video.capture([video.executable("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                "sine=frequency=440:duration=2", "-ar", "44100", "-y", str(sound)])
            for target in audio.TARGETS:
                result = audio.convert_audio(sound, target)[0]
                assert audio.probe(result).duration > 1.9
            edited = audio.transform(sound, target="FLAC", normalize=True, mono=True,
                                     speed=2, fade_in=.1, fade_out=.1)[0]
            info = audio.probe(edited)
            assert .9 < info.duration < 1.1 and info.channels == 1 and info.codec == "flac"
            source = base / "archive.zip"
            with zipfile.ZipFile(source, "w") as z:
                z.writestr("folder/hello.txt", "DragShift test")
            for target in archives.TARGETS:
                result = archives.convert_archive(source, target)[0]
                extracted = archives.extract(result)[0]
                assert (extracted / "folder" / "hello.txt").read_text() == "DragShift test"
            from .app import DragShiftApp
            from .audio_tools import AudioToolWindow
            from .archive_tools import ArchiveContentsWindow
            from .radial import RadialMenu
            menu = RadialMenu(lambda paths: DragShiftApp.build_rings(None, paths), lambda paths: "1 audio file")
            menu._load([str(sound)])
            assert "FLAC" in {item.label for item in menu.items}
            menu.next_ring()
            assert "Normalize" in {item.label for item in menu.items}
            assert not hasattr(DragShiftApp, "open_converter")
            windows = [AudioToolWindow([str(sound)], lambda *_: None),
                       ArchiveContentsWindow(str(source), lambda *_: None)]
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                QApplication.processEvents()
                if windows[0].info is not None and windows[1].table.rowCount():
                    break
                time.sleep(.01)
            assert windows[0].primary_btn.isEnabled() and windows[1].table.rowCount() == 1
            for window in windows:
                window.close()
            menu.close()
            QApplication.processEvents()
        print("FILES SELFTEST OK · audio, loudness, archives, radial workflow, video and Datamosh", flush=True)
        return 0
    except Exception:
        import traceback
        traceback.print_exc()
        print("FILES SELFTEST FAILED", flush=True)
        return 1
