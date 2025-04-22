import os
import shutil
import filecmp
import pickle
from pathlib import Path

from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import Image

from src.mixer.services.mixing_map import load_texture_map, build_texture_map


class ResourcePackMixin(QtWidgets.QMainWindow):
    def __init__(self, mix_dir: Path, out_dir: Path):
        super().__init__()
        self.mix_dir = mix_dir
        self.output_dir = out_dir
        self.pkl_path = mix_dir / "mix_map.pkl"
        os.makedirs(self.mix_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self.texture_map = {}
        self._setup_ui()
        self._start_map_loading()

    def _setup_ui(self):
        self.setWindowTitle("Resource Pack Mixer")
        self.resize(800, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)

        hbox = QtWidgets.QHBoxLayout()
        self.rescan_button = QtWidgets.QPushButton("Пересоздать карту")
        self.rescan_button.clicked.connect(self._on_rescan_clicked)
        hbox.addWidget(self.rescan_button)
        hbox.addStretch()
        vbox.addLayout(hbox)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        vbox.addWidget(scroll)

        self.list_widget = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.list_widget)
        scroll.setWidget(self.list_widget)

    def _start_map_loading(self):
        if self.pkl_path.exists():
            self.texture_map = load_texture_map(self.mix_dir, self.pkl_path)
            self._populate_rows()
        else:
            self._show_loading_dialog()
            QtCore.QTimer.singleShot(100, self._build_map_async)

    def _build_map_async(self):
        self.texture_map = build_texture_map(self.mix_dir)
        with open(self.pkl_path, "wb") as f:
            pickle.dump(self.texture_map, f)
        self._populate_rows()
        self._close_loading_dialog()

    def _show_loading_dialog(self):
        self.loading_dialog = QtWidgets.QDialog(self)
        self.loading_dialog.setWindowTitle("Сканирование ресурсов")
        self.loading_dialog.setModal(True)
        layout = QtWidgets.QVBoxLayout(self.loading_dialog)
        layout.addWidget(QtWidgets.QLabel("Идёт сканирование MixDir..."))
        bar = QtWidgets.QProgressBar()
        bar.setRange(0, 0)
        layout.addWidget(bar)
        self.loading_dialog.resize(300, 100)
        self.loading_dialog.show()

    def _close_loading_dialog(self):
        if hasattr(self, "loading_dialog"):
            self.loading_dialog.accept()
            del self.loading_dialog

    def _on_rescan_clicked(self):
        if self.pkl_path.exists():
            try:
                os.remove(self.pkl_path)
            except:
                pass
        self._clear_rows()
        self._start_map_loading()

    def _clear_rows(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _populate_rows(self):
        self._clear_rows()
        for rel_path, entries in sorted(self.texture_map.items()):
            self._add_row(rel_path, entries)
        self.list_layout.addStretch()

    def _load_pixmap(self, filepath: str) -> QtGui.QPixmap:
        try:
            img = Image.open(filepath).convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QtGui.QImage(data, img.width, img.height, QtGui.QImage.Format_RGBA8888)
            return QtGui.QPixmap.fromImage(qimg)
        except Exception:
            reader = QtGui.QImageReader(filepath)
            image = reader.read()
            return QtGui.QPixmap.fromImage(image)

    def _add_row(self, rel_path: str, entries):
        row = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setAlignment(QtCore.Qt.AlignLeft)

        label = QtWidgets.QLabel(rel_path)
        label.setFixedWidth(300)
        hbox.addWidget(label)

        group = QtWidgets.QButtonGroup(self)
        group.setExclusive(True)

        dst_file = Path(self.output_dir) / rel_path
        for pack_name, full in entries:
            btn = QtWidgets.QToolButton()
            pixmap = self._load_pixmap(str(full)).scaled(
                48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            btn.setIcon(QtGui.QIcon(pixmap))
            btn.setIconSize(QtCore.QSize(48, 48))
            btn.setCheckable(True)
            btn.setToolTip(pack_name)
            btn.setProperty("full_path", str(full))
            btn.setProperty("rel_path", rel_path)
            btn.toggled.connect(self._on_texture_selected)
            if dst_file.exists() and filecmp.cmp(str(full), str(dst_file), shallow=False):
                btn.setChecked(True)
            group.addButton(btn)
            hbox.addWidget(btn)

        self.list_layout.addWidget(row)

    def _on_texture_selected(self, checked: bool):
        btn = self.sender()
        full = Path(btn.property("full_path"))
        rel = btn.property("rel_path")
        dst = Path(self.output_dir) / rel
        if checked:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, dst)
        else:
            if dst.exists():
                dst.unlink()
