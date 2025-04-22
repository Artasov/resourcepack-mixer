import filecmp
import os
import pickle
import shutil
from pathlib import Path

from PIL import Image
from PyQt5 import QtWidgets, QtGui, QtCore

from src.mixer.services.mixing_map import load_texture_map, build_texture_map


class ClickableWidget(QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class PixmapButton(QtWidgets.QToolButton):
    orig_pixmap: QtGui.QPixmap

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orig_pixmap = QtGui.QPixmap()


class PreviewDialog(QtWidgets.QDialog):
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.close()


class ResourcePackMixin(QtWidgets.QMainWindow):
    def __init__(self, mix_dir: Path, out_dir: Path):
        super().__init__()
        self.mix_dir = mix_dir
        self.output_dir = out_dir
        self.pkl_path = mix_dir / "mix_map.pkl"
        os.makedirs(self.mix_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self.texture_map: dict[str, list[tuple[str, Path]]] = {}
        self.search_matches: list[int] = []
        self.search_index: int = 0

        self._setup_ui()
        self._start_map_loading()

    def _setup_ui(self):
        self.setWindowTitle("Resource Pack Mixer")
        self.resize(900, 700)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)
        vbox.setSpacing(5)
        vbox.setContentsMargins(5, 5, 5, 5)

        # поиск и фильтр
        hbox_search = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Поиск…")
        self.search_input.returnPressed.connect(self._on_search)
        hbox_search.addWidget(self.search_input)

        self.search_button = QtWidgets.QPushButton("Поиск")
        self.search_button.clicked.connect(self._on_search_button)
        hbox_search.addWidget(self.search_button)

        self.prev_button = QtWidgets.QPushButton("↑")
        self.prev_button.setFixedWidth(30)
        self.prev_button.clicked.connect(self._on_search_prev)
        hbox_search.addWidget(self.prev_button)

        self.next_button = QtWidgets.QPushButton("↓")
        self.next_button.setFixedWidth(30)
        self.next_button.clicked.connect(self._on_search_next)
        hbox_search.addWidget(self.next_button)

        self.filter_checkbox = QtWidgets.QCheckBox("Показывать только не выбранные")
        self.filter_checkbox.stateChanged.connect(self._populate_rows)
        hbox_search.addWidget(self.filter_checkbox)
        hbox_search.addStretch()
        vbox.addLayout(hbox_search)

        # пересоздание карты
        hbox_rescan = QtWidgets.QHBoxLayout()
        self.rescan_button = QtWidgets.QPushButton("Пересоздать карту")
        self.rescan_button.clicked.connect(self._on_rescan_clicked)
        hbox_rescan.addWidget(self.rescan_button)
        hbox_rescan.addStretch()
        vbox.addLayout(hbox_rescan)

        # список текстур
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        vbox.addWidget(self.scroll_area)

        self.list_widget = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.list_widget)
        self.list_layout.setAlignment(QtCore.Qt.AlignTop)
        self.list_layout.setSpacing(2)
        self.list_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_area.setWidget(self.list_widget)

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
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Сканирование ресурсов")
        dlg.setModal(True)
        layout = QtWidgets.QVBoxLayout(dlg)
        layout.addWidget(QtWidgets.QLabel("Идёт сканирование MixDir…"))
        bar = QtWidgets.QProgressBar()
        bar.setRange(0, 0)
        layout.addWidget(bar)
        dlg.resize(300, 100)
        self.loading_dialog = dlg
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
        self.rel_list = sorted(self.texture_map.keys())
        for rel in self.rel_list:
            if self.filter_checkbox.isChecked() and (Path(self.output_dir) / rel).exists():
                continue
            entries = self.texture_map[rel]
            self._add_row(rel, entries)
        self.list_layout.addStretch()

    def _on_search(self):
        term = self.search_input.text().lower()
        self.search_matches = []
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            w = item.widget()
            if not w:
                continue
            rel = w.property("rel_path")
            if term in rel.lower():
                self.search_matches.append(i)
        if self.search_matches:
            self.search_index = 0
            self._scroll_to_match()

    def _on_search_next(self):
        if not self.search_matches:
            return
        self.search_index = (self.search_index + 1) % len(self.search_matches)
        self._scroll_to_match()

    def _on_search_prev(self):
        if not self.search_matches:
            return
        self.search_index = (self.search_index - 1) % len(self.search_matches)
        self._scroll_to_match()

    def _on_search_button(self):
        if not self.search_matches:
            self._on_search()
        else:
            self._on_search_next()

    def _scroll_to_match(self):
        idx = self.search_matches[self.search_index]
        item = self.list_layout.itemAt(idx)
        w = item.widget()
        if w:
            self.scroll_area.ensureWidgetVisible(w)

    def _load_pixmap(self, filepath: str) -> QtGui.QPixmap:
        try:
            img = Image.open(filepath).convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QtGui.QImage(data, img.width, img.height, QtGui.QImage.Format_RGBA8888)
            return QtGui.QPixmap.fromImage(qimg)
        except:
            reader = QtGui.QImageReader(filepath)
            return QtGui.QPixmap.fromImage(reader.read())

    def _add_row(self, rel_path: str, entries):
        row_name = rel_path.replace('assets/minecraft/', '').replace('textures/', '')
        print(f'Render row: {rel_path}')
        row = ClickableWidget()
        row.setContentsMargins(0, 0, 0, 10)
        row.setProperty("rel_path", rel_path)
        row.setProperty("entries", entries)
        row.clicked.connect(lambda rp=rel_path, e=entries: self._open_preview(rp, e))
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setAlignment(QtCore.Qt.AlignLeft)
        hbox.setContentsMargins(0, 0, 0, 0)

        label = QtWidgets.QLabel(row_name)
        label.setFixedWidth(300)
        hbox.addWidget(label)

        group = QtWidgets.QButtonGroup(self)
        group.setExclusive(True)

        dst_file = Path(self.output_dir) / rel_path
        for pack_name, full in entries:
            btn = QtWidgets.QToolButton()
            pix = self._load_pixmap(str(full)).scaled(
                48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            btn.setIcon(QtGui.QIcon(pix))
            btn.setStyleSheet(
                "background-color:#333;"
                "color:#fff;"
                "outline:none;"
                "border:none;"
            )
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

    def _open_preview(self, rel_path: str, entries):
        dlg = PreviewDialog(self)
        dlg.setWindowTitle(rel_path)
        layout = QtWidgets.QVBoxLayout(dlg)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        content = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout(content)
        hbox.setAlignment(QtCore.Qt.AlignLeft)
        content.setLayout(hbox)
        scroll.setWidget(content)
        dlg.resize(600, 200)
        dlg._btns: list[PixmapButton] = []
        for pack_name, full in entries:
            btn = PixmapButton()
            pixmap = self._load_pixmap(str(full))
            btn.orig_pixmap = pixmap
            btn.setIcon(QtGui.QIcon(pixmap))
            btn.setIconSize(QtCore.QSize(pixmap.width(), pixmap.height()))
            btn.setToolTip(pack_name)
            hbox.addWidget(btn)
            dlg._btns.append(btn)

        def on_resize(event):
            new_h = dlg.height() - 50
            size = min(new_h, 512)
            for b in dlg._btns:
                p = b.orig_pixmap.scaled(size, size,
                                         QtCore.Qt.KeepAspectRatio,
                                         QtCore.Qt.SmoothTransformation)
                b.setIcon(QtGui.QIcon(p))
                b.setIconSize(QtCore.QSize(p.width(), p.height()))
            super(QtWidgets.QDialog, dlg).resizeEvent(event)

        dlg.resizeEvent = on_resize
        dlg.exec_()
