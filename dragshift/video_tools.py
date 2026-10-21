"""Video editors and cancellable progress windows in DragShift's glass style."""
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSlider, QSpinBox, QVBoxLayout, QWidget)

from . import datamosh, report, video
from .tools import ToolWindow, section, slider, slider_row
from .theme import BORDER, ERROR, HOVER, MUTED, SELECTED, TEXT
from .util import UserError, keep, release
from .window import GlassWindow

VIDEO_STYLE = f"""
QDoubleSpinBox, QPlainTextEdit {{ color: {TEXT}; background-color: #ffffff;
 border: 1px solid {BORDER}; border-radius: 6px; padding: 5px 8px; }}
QDoubleSpinBox QLineEdit {{ color: {TEXT}; background-color: #ffffff; border: none; }}
QDoubleSpinBox:focus, QComboBox:focus, QPushButton:focus {{ border-color: {TEXT}; }}
QProgressBar {{ color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px;
 background: {HOVER}; text-align: center; min-height: 24px; }}
QProgressBar::chunk {{ background: {SELECTED}; border-radius: 5px; }}
QLabel#videoError {{ color: {ERROR}; }}
"""
SPIN_STYLE = (f"QDoubleSpinBox {{background-color:#ffffff;color:{TEXT};border:1px solid {BORDER};"
              f"border-radius:6px;padding:5px 28px 5px 8px;}} QLineEdit {{background-color:#ffffff;color:{TEXT};border:none;}}"
              f"QDoubleSpinBox:disabled, QLineEdit:disabled {{color:{MUTED};background-color:{HOVER};}}")


class _LookupSignals(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)
    finished = Signal(object)


class _Lookup(QRunnable):
    def __init__(self, serial, fn):
        super().__init__()
        self.serial, self.fn = serial, fn
        self.sig = _LookupSignals()

    def run(self):
        try:
            self.sig.done.emit(self.serial, self.fn())
        except Exception as e:
            self.sig.failed.emit(self.serial, str(e))
        finally:
            self.sig.finished.emit(self)


class _AsyncTools(ToolWindow):
    """Only Qt slots touch widgets; lookup jobs own no GUI objects."""
    def __init__(self, title, paths, notify, size):
        super().__init__(title, paths, notify, size)
        self.setStyleSheet(self.styleSheet() + VIDEO_STYLE)
        self._serial = 0
        self._callbacks = {}
        self.error = QLabel()
        self.error.setObjectName("videoError")
        self.error.setWordWrap(True)
        self.error.setAccessibleName("Video error")

    def lookup(self, fn, callback, failure=None):
        self._serial += 1
        job = _Lookup(self._serial, fn)
        self._callbacks[job.serial] = (callback, failure)
        job.sig.done.connect(self._lookup_done)
        job.sig.failed.connect(self._lookup_failed)
        job.sig.finished.connect(release)
        QThreadPool.globalInstance().start(keep(job))
        return job.serial

    @Slot(int, object)
    def _lookup_done(self, serial, value):
        callbacks = self._callbacks.pop(serial, None)
        if callbacks:
            callbacks[0](value)

    @Slot(int, str)
    def _lookup_failed(self, serial, message):
        callbacks = self._callbacks.pop(serial, None)
        if callbacks:
            if callbacks[1]:
                callbacks[1](message)
            else:
                self.error.setText(message)

    def closeEvent(self, e):
        self._callbacks.clear()
        super().closeEvent(e)


def _seconds(value=0.):
    spin = QDoubleSpinBox()
    spin.setStyleSheet(SPIN_STYLE)
    spin.setRange(0, 1_000_000)
    spin.setDecimals(3)
    spin.setSingleStep(.1)
    spin.setSuffix(" s")
    spin.setValue(value)
    return spin


def _field(form: QFormLayout, label: str, widget):
    widget.setAccessibleName(label.replace("&", ""))
    form.addRow(label, widget)


def _preview_label():
    label = QLabel("Reading video…")
    label.setAlignment(Qt.AlignCenter)
    label.setMinimumHeight(110)
    label.setMaximumHeight(180)
    label.setAccessibleName("Video frame preview")
    return label


def _show_frame(label, data):
    pix = QPixmap()
    if pix.loadFromData(data):
        label.setPixmap(pix.scaled(max(240, label.width()), 176, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        label.setText("Frame preview unavailable")


def _scroll_panel(form, note=None):
    content = QWidget()
    content.setObjectName("mediaForm")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 4, 0)
    layout.addLayout(form)
    if note:
        layout.addWidget(note)
    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.viewport().setObjectName("mediaViewport")
    scroll.setStyleSheet("QScrollArea, QWidget#mediaForm, QWidget#mediaViewport { background: transparent; border: none; }")
    scroll.viewport().setAutoFillBackground(False)
    content.setAutoFillBackground(False)
    scroll.setMinimumHeight(170)
    scroll.setWidget(content)
    return scroll


class VideoToolWindow(_AsyncTools):
    def __init__(self, paths, notify, mode="Edit"):
        super().__init__(f"Video · {mode}", paths, notify, (740, 730 if mode == "Edit" else 560))
        self.tool_name = mode
        self.mode = mode
        self.info = None
        self.preview_serial = 0
        self.details = QLabel("Reading video information…")
        self.details.setObjectName("dim")
        self.details.setWordWrap(True)
        self.body.addWidget(self.details)
        self.preview = _preview_label()
        self.body.addWidget(self.preview)
        self.scrub = QSlider(Qt.Horizontal)
        self.scrub.setRange(0, 1000)
        self.scrub.setAccessibleName("Preview position")
        self.scrub.setEnabled(False)
        self.timestamp = QLabel("00:00.000")
        self.timestamp.setMinimumWidth(90)
        row = QHBoxLayout()
        row.addWidget(self.scrub, 1)
        row.addWidget(self.timestamp)
        self.body.addLayout(row)
        self._preview_timer = QTimer(self, interval=220, singleShot=True)
        self._preview_timer.timeout.connect(self.load_frame)
        self.scrub.valueChanged.connect(self._scrub_changed)
        self.form = QFormLayout()
        self.form.setHorizontalSpacing(18)
        self.form.setVerticalSpacing(10)
        if mode == "Trim":
            self.start_time, self.end_time = _seconds(), _seconds()
            _field(self.form, "&Start", self.start_time)
            _field(self.form, "&End", self.end_time)
            self.start_time.valueChanged.connect(self._start_preview)
        elif mode in ("Compress", "Resize"):
            self.max_side = QSpinBox()
            self.max_side.setRange(16, 7680)
            self.max_side.setValue(1280)
            self.max_side.setSuffix(" px")
            _field(self.form, "&Longest edge (no upscale)", self.max_side)
            if mode == "Compress":
                self.quality = QComboBox()
                for text, value in [("High quality", 23), ("Balanced", 28), ("Smaller file", 33), ("Smallest file", 38)]:
                    self.quality.addItem(text, value)
                self.quality.setCurrentIndex(1)
                _field(self.form, "&Compression", self.quality)
        elif mode == "Edit":
            self.rotation = QComboBox()
            for angle in (0, 90, 180, 270):
                self.rotation.addItem(f"{angle}° clockwise", angle)
            self.crop = QComboBox()
            for text, ratio in [("Keep original", None), ("Square · 1:1", 1), ("Landscape · 16:9", 16/9),
                                ("Portrait · 9:16", 9/16), ("Classic · 4:3", 4/3)]:
                self.crop.addItem(text, ratio)
            self.flip = QCheckBox("Mirror horizontally")
            self.speed = QDoubleSpinBox()
            self.speed.setStyleSheet(SPIN_STYLE)
            self.speed.setRange(.25, 4)
            self.speed.setSingleStep(.25)
            self.speed.setValue(1)
            self.speed.setSuffix(" ×")
            _field(self.form, "&Rotation", self.rotation)
            _field(self.form, "Centre &crop", self.crop)
            _field(self.form, "&Speed (audio pitch preserved)", self.speed)
            self.form.addRow("", self.flip)
            for key, label, lo, hi, value in [("brightness", "Brightness", -50, 50, 0),
                    ("contrast", "Contrast", 10, 300, 100), ("saturation", "Saturation", 0, 300, 100)]:
                s = slider(lo, hi, value)
                s.setAccessibleName(label)
                setattr(self, key, s)
                value_label = QLabel(str(value))
                s.valueChanged.connect(value_label.setNum)
                layout = QHBoxLayout()
                layout.addWidget(s, 1)
                layout.addWidget(value_label)
                self.form.addRow(label, layout)
        elif mode == "Frame":
            self.frame_time = _seconds()
            _field(self.form, "&Frame position", self.frame_time)
            self.frame_time.valueChanged.connect(self._frame_time_changed)
        elif mode == "Metadata":
            self.metadata = QPlainTextEdit()
            self.metadata.setReadOnly(True)
            self.metadata.setMaximumHeight(140)
            self.metadata.setAccessibleName("Video metadata")
            self.form.addRow(self.metadata)
        elif mode == "Mute":
            hint = QLabel("Save a new MP4 without an audio track.")
            hint.setWordWrap(True)
            self.form.addRow(hint)
        self.body.addWidget(_scroll_panel(self.form), 1)
        note = QLabel("Edits save a new MP4. The original stays unchanged." if mode != "Frame"
                      else "Save the selected frame as a full-resolution PNG.")
        note.setWordWrap(True)
        note.setObjectName("dim")
        self.body.addWidget(note)
        if len(self.paths) > 1:
            batch = QLabel(f"Settings apply to all {len(self.paths)} videos. Preview shows the first.")
            batch.setWordWrap(True)
            self.body.addWidget(batch)
        if mode == "Edit":
            hint = QLabel("Frame preview shows the source. Changes are applied when saving.")
            hint.setObjectName("dim")
            self.body.addWidget(hint)
        self.body.addWidget(self.error)
        text = "Save PNG" if mode == "Frame" else "Save without metadata" if mode == "Metadata" else "Save MP4"
        self.body.addLayout(self.footer(text, self.save))
        self.primary_btn.setEnabled(False)
        path = self.path
        self.lookup(lambda: (video.probe(path), video.preview_bytes(path)), self._loaded)

    def _loaded(self, data):
        self.info, frame = data
        i = self.info
        self.details.setText(f"{i.width} × {i.height} · {video.time_text(i.duration)} · {i.fps:.2f} fps · "
                             f"{i.codec.upper()} · {'Audio' if i.has_audio else 'No audio'}")
        _show_frame(self.preview, frame)
        self.primary_btn.setEnabled(True)
        self.scrub.setEnabled(True)
        if self.mode == "Trim":
            self.start_time.setMaximum(i.duration)
            self.end_time.setMaximum(i.duration)
            self.end_time.setValue(i.duration)
        if self.mode == "Frame":
            self.frame_time.setMaximum(max(0, i.duration - 1 / i.fps))
        if self.mode in ("Compress", "Resize"):
            self.max_side.setValue(min(1280, max(i.width, i.height)))
        if self.mode == "Metadata":
            self.metadata.setPlainText("\n".join(f"{k}: {v}" for k, v in i.tags.items()) or "No descriptive metadata")

    def _scrub_changed(self, value):
        if self.info:
            at = min(self.info.duration - 1 / self.info.fps, value / 1000 * self.info.duration)
            self.timestamp.setText(video.time_text(at))
            if self.mode == "Frame":
                self.frame_time.blockSignals(True)
                self.frame_time.setValue(at)
                self.frame_time.blockSignals(False)
            self._preview_timer.start()

    def _start_preview(self, value):
        if self.info:
            self.scrub.setValue(round(value / self.info.duration * 1000))

    def _frame_time_changed(self, value):
        self._start_preview(value)

    def load_frame(self):
        if not self.info:
            return
        at = min(self.info.duration - 1 / self.info.fps, self.scrub.value() / 1000 * self.info.duration)
        path = self.path
        self.preview_serial += 1
        serial = self.preview_serial
        def show(data):
            if serial == self.preview_serial:
                _show_frame(self.preview, data)
        self.lookup(lambda: video.preview_bytes(path, at), show, lambda msg: self.preview.setText("Frame preview unavailable"))

    def validate(self):
        self.error.clear()
        if self.info is None:
            return False
        if self.mode == "Trim":
            try:
                video.validate_range(self.info, self.start_time.value(), self.end_time.value())
            except UserError as e:
                self.error.setText(str(e))
                self.start_time.setFocus()
                return False
        return True

    def save(self):
        if not self.validate():
            return
        opts = {"label": self.mode + ("med" if self.mode == "Trim" else "")}
        if self.mode == "Trim":
            opts.update(start=self.start_time.value(), end=self.end_time.value())
        elif self.mode in ("Compress", "Resize"):
            opts["max_side"] = self.max_side.value()
            if self.mode == "Compress":
                opts["crf"] = self.quality.currentData()
        elif self.mode == "Edit":
            opts.update(rotation=self.rotation.currentData(), crop_ratio=self.crop.currentData(),
                flip=self.flip.isChecked(), speed=self.speed.value(), brightness=self.brightness.value()/100,
                contrast=self.contrast.value()/100, saturation=self.saturation.value()/100)
        elif self.mode == "Mute":
            opts["mute"] = True
        elif self.mode == "Metadata":
            opts["strip_metadata"] = True
        paths = list(self.paths)
        if self.mode == "Frame":
            at = self.frame_time.value()
            fn = lambda p: video.snapshot(p, at)
        else:
            fn = lambda p: video.transform(p, **opts)
        self.run(lambda: video.batch(paths, fn), "Processing video…")


class DatamoshWindow(_AsyncTools):
    tool_name = "Datamosh"

    def __init__(self, paths, notify):
        super().__init__("Datamosh · A → B", paths[:2], notify, (800, 740))
        self.first_info = self.second_info = None
        self.second_path = self.paths[1] if len(self.paths) > 1 else None
        self._second_serial = 0
        intro = QLabel("Carry the last image of A into B's motion, then return to a clean B.")
        intro.setWordWrap(True)
        self.body.addWidget(intro)
        previews = QHBoxLayout()
        self.previews = []
        self.names = []
        for title in ("A · END OF FIRST VIDEO", "B · START OF SECOND VIDEO"):
            col = QVBoxLayout()
            col.addWidget(section(title))
            name = QLabel("Choose a second video…" if self.previews else self.path.name)
            name.setWordWrap(True)
            name.setObjectName("dim")
            col.addWidget(name)
            frame = _preview_label()
            col.addWidget(frame)
            previews.addLayout(col, 1)
            self.previews.append(frame)
            self.names.append(name)
        self.body.addLayout(previews)
        choose = QPushButton("Choose second video…")
        choose.clicked.connect(self.choose_second)
        self.body.addWidget(choose)
        self.form = QFormLayout()
        self.form.setVerticalSpacing(8)
        self.tail, self.head, self.duration = _seconds(4), _seconds(6), _seconds(2)
        self.tail.setMinimum(.2)
        self.head.setMinimum(.2)
        self.duration.setMinimum(.1)
        self.preset = QComboBox()
        self.preset.addItems(datamosh.PRESETS)
        self.preset.setCurrentText("Melt")
        self.strength = slider(1, 100, 65)
        strength_row = QHBoxLayout()
        strength_value = QLabel("65")
        strength_value.setMinimumWidth(28)
        self.strength.valueChanged.connect(strength_value.setNum)
        self.strength.setAccessibleName("Datamosh intensity")
        strength_row.addWidget(self.strength)
        strength_row.addWidget(strength_value)
        self.resolution = QComboBox()
        for px in (360, 720, 1080, 1440, 2160):
            self.resolution.addItem(f"{px} px · longest edge", px)
        self.resolution.setCurrentIndex(1)
        self.fps = QComboBox()
        for fps in (24, 25, 30, 60):
            self.fps.addItem(f"{fps} fps", fps)
        self.fps.setCurrentIndex(2)
        _field(self.form, "&Last seconds of A", self.tail)
        _field(self.form, "&First seconds of B", self.head)
        _field(self.form, "&Transition duration", self.duration)
        _field(self.form, "&Preset", self.preset)
        self.form.addRow("Intensity", strength_row)
        _field(self.form, "&Resolution", self.resolution)
        _field(self.form, "Frame rate", self.fps)
        self.audio = QCheckBox("Keep audio from both selected segments")
        self.audio.setChecked(True)
        self.form.addRow("", self.audio)
        self.note = QLabel("FFglitch motion vectors + keyframe removal · Export: MP4\n"
            "Motion-rich footage gives stronger results. B returns cleanly after the transition.\n"
            "Preview renders a short 480 px excerpt; open it from the result notification.")
        self.note.setObjectName("dim")
        self.note.setWordWrap(True)
        self.body.addWidget(_scroll_panel(self.form, self.note), 1)
        self.body.addWidget(self.error)
        self.preview_btn = QPushButton("Render preview")
        self.preview_btn.clicked.connect(lambda: self.save(preview=True))
        self.body.addLayout(self.footer("Create transition", self.save, extra_buttons=(self.preview_btn,)))
        self.primary_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        first = self.path
        def load_first():
            info = video.probe(first)
            return info, video.preview_bytes(first, max(0, info.duration - .15))
        self.lookup(load_first, self._first_loaded)
        if self.second_path:
            self.load_second(self.second_path)

    def _first_loaded(self, data):
        self.first_info, frame = data
        self.tail.setMaximum(self.first_info.duration)
        self.tail.setValue(min(4, self.first_info.duration))
        self.names[0].setText(f"{self.path.name} · {video.time_text(self.first_info.duration)}")
        _show_frame(self.previews[0], frame)
        self._enable()

    def choose_second(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose video B", str(self.path.parent), video.VIDEO_FILTER)
        if path:
            self.load_second(Path(path))

    def load_second(self, path):
        self._second_serial += 1
        serial = self._second_serial
        self.second_path = Path(path)
        self.second_info = None
        self.error.clear()
        self.names[1].setText(self.second_path.name)
        self.previews[1].setText("Reading video…")
        self._enable()
        def loaded(data):
            if serial != self._second_serial:
                return
            self.second_info, frame = data
            self.names[1].setText(f"{path.name} · {video.time_text(self.second_info.duration)}")
            self.head.setMaximum(self.second_info.duration)
            self.head.setValue(min(6, self.second_info.duration))
            self.duration.setValue(min(2, max(.1, self.second_info.duration / 2)))
            _show_frame(self.previews[1], frame)
            self._enable()
        self.lookup(lambda: (video.probe(path), video.preview_bytes(path)), loaded)

    def _enable(self):
        enabled = self.first_info is not None and self.second_info is not None
        self.primary_btn.setEnabled(enabled)
        self.preview_btn.setEnabled(enabled)

    def validate(self):
        self.error.clear()
        if not self.first_info or not self.second_info:
            return False
        if self.duration.value() > self.head.value() - .1:
            self.error.setText("The transition must end at least 0.1 seconds before the selected B segment ends.")
            self.duration.setFocus()
            return False
        try:
            video.executable("ffgac")
            video.executable("ffedit")
        except UserError as e:
            self.error.setText(str(e))
            return False
        return True

    def save(self, checked=False, *, preview=False):
        if not self.validate():
            return
        opts = dict(tail=self.tail.value(), head=self.head.value(), duration=self.duration.value(),
            strength=self.strength.value(), preset=self.preset.currentText(),
            max_side=self.resolution.currentData(), audio=self.audio.isChecked(), fps=self.fps.currentData())
        if preview:
            opts.update(tail=min(opts["tail"], 1.5), duration=min(opts["duration"], 3), max_side=480)
            opts["head"] = min(opts["head"], opts["duration"] + .75)
        a, b = self.path, self.second_path
        fn = lambda: datamosh.transition(a, b, **opts)
        if self.submit:
            self.submit("tool:Datamosh", [str(a), str(b)], fn, "Creating Datamosh transition…",
                        ("Preview · " if preview else "") + opts["preset"])
            if not preview:
                self.close()
        else:
            # Standalone test harnesses still get the same processing behaviour.
            outs = fn()
            self.notify("tool:Datamosh", [str(a), str(b)], outs, opts["preset"])


class _RenderSignals(QObject):
    done = Signal(object)
    failed = Signal(str, bool)
    progress = Signal(float, str)


class _Render(QRunnable):
    def __init__(self, action, srcs, fn, extra):
        super().__init__()
        self.action, self.srcs, self.fn, self.extra = action, srcs, fn, extra
        self.sig = _RenderSignals()
        self.control = video.Control(progress=self.sig.progress.emit)

    def run(self):
        try:
            with video.job_context(self.control):
                outs = self.fn()
                # Once published, cancellation must not hide a completed result.
                result = report.summarize(self.action, self.srcs, outs, self.extra)
            self.sig.done.emit(result)
        except video.Cancelled as e:
            self.sig.failed.emit(str(e), True)
        except Exception as e:
            traceback.print_exc()
            self.sig.failed.emit(str(e), False)


class VideoProgressWindow(GlassWindow):
    def __init__(self, action, srcs, fn, on_done, extra=""):
        super().__init__("File processing", size=(580, 260))
        self.setStyleSheet(self.styleSheet() + VIDEO_STYLE)
        self.busy = False
        self.on_done = on_done
        self.job = _Render(action, srcs, fn, extra)
        self.job.sig.done.connect(self._done)
        self.job.sig.failed.connect(self._failed)
        self.job.sig.progress.connect(self._progress)
        self.status = QLabel("Preparing…")
        self.status.setWordWrap(True)
        self.body.addWidget(self.status)
        self.detail = QLabel(" → ".join(Path(p).name for p in srcs))
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.addWidget(self.detail)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setAccessibleName("Video export progress")
        self.body.addWidget(self.bar)
        self.button = QPushButton("Cancel")
        self.button.clicked.connect(self.cancel_work)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.button)
        self.body.addLayout(row)

    def start(self, pool=None):
        if self.busy:
            return
        self.busy = True
        (pool or QThreadPool.globalInstance()).start(keep(self.job))

    @Slot(float, str)
    def _progress(self, value, text):
        self.bar.setValue(round(value * 100))
        self.status.setText(text)

    @Slot(object)
    def _done(self, result):
        release(self.job)
        self.busy = False
        self.on_done(result)
        self.close()

    @Slot(str, bool)
    def _failed(self, message, cancelled):
        release(self.job)
        self.busy = False
        self.status.setText("Cancelled" if cancelled else "Couldn't finish")
        self.detail.setText(message)
        self.button.setText("Close")
        self.button.setEnabled(True)

    def cancel_work(self):
        if self.busy:
            self.job.control.cancel.set()
            self.button.setText("Cancelling…")
            self.button.setEnabled(False)
        else:
            self.close()

    def closeEvent(self, e):
        if self.busy:
            self.cancel_work()
            e.ignore()
        else:
            super().closeEvent(e)
