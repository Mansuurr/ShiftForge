"""Inspect archive members without extracting or opening their files."""
from PySide6.QtWidgets import QHeaderView, QPushButton, QTableWidget, QTableWidgetItem

from . import archives
from .util import human_size
from .video_tools import _AsyncTools


class ArchiveContentsWindow(_AsyncTools):
    def __init__(self, path, notify):
        super().__init__("Archive contents", [path], notify, (760, 580))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAccessibleName("Files inside the selected archive")
        self.body.addWidget(self.table, 1)
        self.body.addWidget(self.error)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        self.body.addWidget(close)
        path = self.path
        self.lookup(lambda: archives.entries(path), self._loaded)

    def _loaded(self, items):
        self.table.setRowCount(len(items))
        for row, entry in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(entry.name + ("/" if entry.is_dir else "")))
            self.table.setItem(row, 1, QTableWidgetItem("Folder" if entry.is_dir else human_size(entry.size)))
