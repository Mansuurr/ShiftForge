"""Watched ("magic") folders that convert newly dropped files locally."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QPushButton, QTableWidget, QTableWidgetItem)

from .settings import Settings
from .util import category
from .window import GlassWindow

TARGET_OPTIONS = ["AUTO", "JPG", "PNG", "WEBP", "PDF", "DOCX", "TXT", "MP4", "MKV",
                  "MOV", "WEBM", "GIF", "MP3", "WAV", "FLAC", "M4A", "ZIP", "7Z", "TAR"]
AUTO_TARGETS = {"image": "WEBP", "video": "MP4", "audio": "MP3", "docx": "PDF",
                "text": "PDF", "archive": "ZIP"}
ALIASES = {"JPEG": "JPG", "TIF": "TIFF", "AIF": "AIFF", "OGA": "OGG", "M4B": "M4A"}


def resolved_target(path: str | Path, requested: str) -> str | None:
    cat = category(path)
    target = AUTO_TARGETS.get(cat) if requested == "AUTO" else requested.upper()
    if not target:
        return None
    current = ALIASES.get(Path(path).suffix.lstrip(".").upper(), Path(path).suffix.lstrip(".").upper())
    return None if current == target else target


class WatchFolderManager(QObject):
    convert_requested = Signal(str, str)

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self._changed)
        self.known: dict[str, set[str]] = {}
        self.targets: dict[str, str] = {}
        self.pending: dict[str, tuple[int, int, int, str]] = {}
        self.timer = QTimer(self, interval=700)
        self.timer.timeout.connect(self._poll)
        self.reload()

    @staticmethod
    def _files(folder: str) -> set[str]:
        try:
            return {str(item.resolve()) for item in Path(folder).iterdir() if item.is_file()}
        except OSError:
            return set()

    def reload(self):
        old = self.watcher.directories()
        if old:
            self.watcher.removePaths(old)
        self.known.clear()
        self.targets.clear()
        for rule in self.settings.get("watch_folders"):
            try:
                folder = str(Path(rule["path"]).resolve())
                target = str(rule.get("target", "AUTO")).upper()
            except (KeyError, TypeError):
                continue
            if Path(folder).is_dir():
                self.targets[folder] = target if target in TARGET_OPTIONS else "AUTO"
                self.known[folder] = self._files(folder)
        if self.targets:
            self.watcher.addPaths(list(self.targets))

    def _changed(self, folder: str):
        QTimer.singleShot(350, lambda f=folder: self._scan(f))

    def _scan(self, folder: str):
        if folder not in self.targets:
            return
        current = self._files(folder)
        new = current - self.known.get(folder, set())
        self.known[folder] = current
        for path in new:
            target = resolved_target(path, self.targets[folder])
            if target is not None and category(path) is not None:
                self.pending[path] = (-1, -1, 0, target)
        if self.pending and not self.timer.isActive():
            self.timer.start()

    def _poll(self):
        for path, (last_size, last_mtime, stable, target) in list(self.pending.items()):
            try:
                stat = Path(path).stat()
            except OSError:
                self.pending.pop(path, None)
                continue
            same = stat.st_size == last_size and stat.st_mtime_ns == last_mtime
            stable = stable + 1 if same else 0
            if stable >= 2:
                self.pending.pop(path, None)
                self.convert_requested.emit(path, target)
            else:
                self.pending[path] = (stat.st_size, stat.st_mtime_ns, stable, target)
        if not self.pending:
            self.timer.stop()


class WatchFoldersWindow(GlassWindow):
    changed = Signal()

    def __init__(self, settings: Settings):
        super().__init__("Волшебные папки", size=(760, 510))
        self.settings = settings
        note = QLabel("Новые файлы в этих папках преобразуются автоматически. AUTO выбирает WebP, MP4, MP3, PDF или ZIP по типу файла.")
        note.setWordWrap(True)
        note.setObjectName("dim")
        self.body.addWidget(note)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Папка", "Формат"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.body.addWidget(self.table, 1)
        row = QHBoxLayout()
        add = QPushButton("Добавить папку")
        add.clicked.connect(self.add_folder)
        remove = QPushButton("Удалить")
        remove.clicked.connect(self.remove_selected)
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        done = QPushButton("Готово")
        done.setObjectName("primary")
        done.clicked.connect(self.close)
        row.addWidget(done)
        self.body.addLayout(row)
        self.refresh()

    def rules(self) -> list[dict]:
        return list(self.settings.get("watch_folders"))

    def refresh(self):
        rules = self.rules()
        self.table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            item = QTableWidgetItem(str(rule.get("path", "")))
            item.setData(Qt.UserRole, row)
            self.table.setItem(row, 0, item)
            combo = QComboBox()
            combo.addItems(TARGET_OPTIONS)
            combo.setCurrentText(str(rule.get("target", "AUTO")).upper())
            combo.currentTextChanged.connect(lambda target, index=row: self._set_target(index, target))
            self.table.setCellWidget(row, 1, combo)

    def _save(self, rules: list[dict]):
        self.settings.set("watch_folders", rules)
        self.changed.emit()

    def _set_target(self, row: int, target: str):
        rules = self.rules()
        if 0 <= row < len(rules) and rules[row].get("target") != target:
            rules[row]["target"] = target
            self._save(rules)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите волшебную папку")
        if not folder:
            return
        path = str(Path(folder).resolve())
        rules = self.rules()
        if not any(str(Path(rule.get("path", "")).resolve()) == path for rule in rules):
            rules.append({"path": path, "target": "AUTO"})
            self._save(rules)
            self.refresh()

    def remove_selected(self):
        row = self.table.currentRow()
        rules = self.rules()
        if 0 <= row < len(rules):
            del rules[row]
            self._save(rules)
            self.refresh()
