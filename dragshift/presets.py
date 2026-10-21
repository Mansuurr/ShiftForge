"""User-defined format shortcuts shown as a third radial-menu ring."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from .settings import DEFAULTS, Settings
from .window import GlassWindow

CATEGORIES = [
    ("image", "Изображения"),
    ("video", "Видео"),
    ("audio", "Аудио"),
    ("document", "Документы"),
    ("archive", "Архивы"),
]
TARGETS = {
    "image": ["JPG", "PNG", "WEBP", "HEIC", "TIFF", "AVIF", "BMP", "PDF", "ICO", "GIF"],
    "video": ["MP4", "MKV", "MOV", "WEBM", "AVI", "GIF", "MP3", "WAV"],
    "audio": ["MP3", "WAV", "FLAC", "M4A", "AAC", "OGG", "OPUS", "AIFF"],
    "document": ["PDF", "DOCX", "TXT", "JPG", "PNG"],
    "archive": ["ZIP", "7Z", "TAR"],
}


def category_matches(preset_category: str, actual: str) -> bool:
    return preset_category == actual or preset_category == "document" and actual in ("pdf", "docx", "text")


def for_category(settings: Settings, actual: str, available: list[str]) -> list[dict]:
    allowed = set(available)
    result = []
    for preset in settings.get("presets"):
        if not isinstance(preset, dict):
            continue
        name = str(preset.get("name", "")).strip()
        target = str(preset.get("target", "")).upper()
        if name and target in allowed and category_matches(str(preset.get("category", "")), actual):
            result.append({"name": name, "category": preset.get("category"), "target": target})
    return result


class PresetDialog(QDialog):
    def __init__(self, parent=None, preset: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Пресет формата")
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit((preset or {}).get("name", ""))
        self.category = QComboBox()
        for value, label in CATEGORIES:
            self.category.addItem(label, value)
        self.target = QComboBox()
        form.addRow("Название", self.name)
        form.addRow("Тип файлов", self.category)
        form.addRow("Формат", self.target)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.category.currentIndexChanged.connect(self._targets)
        wanted_category = (preset or {}).get("category", "image")
        self.category.setCurrentIndex(max(0, self.category.findData(wanted_category)))
        self._targets()
        wanted_target = (preset or {}).get("target", "")
        if wanted_target:
            self.target.setCurrentIndex(max(0, self.target.findText(wanted_target)))

    def _targets(self):
        current = self.target.currentText()
        self.target.clear()
        self.target.addItems(TARGETS[self.category.currentData()])
        if current in TARGETS[self.category.currentData()]:
            self.target.setCurrentText(current)

    def value(self) -> dict:
        name = self.name.text().strip() or f"{self.category.currentText()} · {self.target.currentText()}"
        return {"name": name, "category": self.category.currentData(), "target": self.target.currentText()}


class PresetsWindow(GlassWindow):
    changed = Signal()

    def __init__(self, settings: Settings):
        super().__init__("Пресеты форматов", size=(650, 500))
        self.settings = settings
        note = QLabel("Пресеты появляются отдельным кругом рядом с «Форматами» и «Инструментами».")
        note.setWordWrap(True)
        note.setObjectName("dim")
        self.body.addWidget(note)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Название", "Тип", "Формат"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_selected)
        self.body.addWidget(self.table, 1)
        row = QHBoxLayout()
        add = QPushButton("Добавить")
        add.clicked.connect(self.add_preset)
        edit = QPushButton("Изменить")
        edit.clicked.connect(self.edit_selected)
        remove = QPushButton("Удалить")
        remove.clicked.connect(self.remove_selected)
        reset = QPushButton("Вернуть стандартные")
        reset.clicked.connect(self.reset_defaults)
        for button in (add, edit, remove, reset):
            row.addWidget(button)
        row.addStretch(1)
        done = QPushButton("Готово")
        done.setObjectName("primary")
        done.clicked.connect(self.close)
        row.addWidget(done)
        self.body.addLayout(row)
        self.refresh()

    def presets(self) -> list[dict]:
        return list(self.settings.get("presets"))

    def refresh(self):
        labels = dict(CATEGORIES)
        values = self.presets()
        self.table.setRowCount(len(values))
        for row, preset in enumerate(values):
            for col, text in enumerate((preset.get("name", ""), labels.get(preset.get("category"), ""),
                                        preset.get("target", ""))):
                item = QTableWidgetItem(str(text))
                item.setData(Qt.UserRole, row)
                self.table.setItem(row, col, item)

    def _save(self, values: list[dict]):
        self.settings.set("presets", values)
        self.refresh()
        self.changed.emit()

    def add_preset(self):
        dialog = PresetDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._save(self.presets() + [dialog.value()])

    def edit_selected(self, *_):
        row = self.table.currentRow()
        values = self.presets()
        if not 0 <= row < len(values):
            return
        dialog = PresetDialog(self, values[row])
        if dialog.exec() == QDialog.Accepted:
            values[row] = dialog.value()
            self._save(values)

    def remove_selected(self):
        row = self.table.currentRow()
        values = self.presets()
        if 0 <= row < len(values):
            del values[row]
            self._save(values)

    def reset_defaults(self):
        self._save([dict(item) for item in DEFAULTS["presets"]])
