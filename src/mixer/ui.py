import os
import shutil
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore


class ResourcePackMixin(QtWidgets.QMainWindow):
    def __init__(self, mix_dir: Path, out_dir: Path):
        super().__init__()
        self.mix_dir = mix_dir
        self.output_dir = out_dir
        os.makedirs(self.mix_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self._setup_ui()
        self._load_textures()

    def _setup_ui(self):
        self.setWindowTitle("Resource Pack Mixer")
        self.resize(800, 600)

        # центральный виджет и главный лэйаут
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout()
        central.setLayout(main_layout)

        # скроллируемая область
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)

        # контейнер для строк
        self.list_widget = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout()
        self.list_widget.setLayout(self.list_layout)
        scroll.setWidget(self.list_widget)

    def _load_textures(self):
        if not self.mix_dir.is_dir():
            QtWidgets.QMessageBox.critical(self, "Ошибка",
                                           f"Папка MixDir не найдена:\n{self.mix_dir}")
            return

        texture_map: dict[str, list[tuple[str, Path]]] = {}
        # перебираем каждый ресурс-пак
        for pack_dir in sorted(self.mix_dir.iterdir()):
            if not pack_dir.is_dir():
                continue
            pack_name = pack_dir.name
            for root, _, files in os.walk(pack_dir):
                root_path = Path(root)
                parts = set(root_path.parts)
                # только внутри assets/.../textures
                if "assets" not in parts or "textures" not in parts:
                    continue
                for fname in files:
                    if not fname.lower().endswith(".png"):
                        continue
                    full = root_path / fname
                    rel = full.relative_to(pack_dir)
                    rel_str = str(rel).replace("\\", "/")
                    texture_map.setdefault(rel_str, []).append((pack_name, full))

        # добавляем строки в UI
        for rel_path in sorted(texture_map.keys()):
            variants = texture_map[rel_path]
            self._add_row(rel_path, variants)

        # отступ внизу, чтобы последний элемент не прилипал
        self.list_layout.addStretch()

    def _add_row(self, rel_path: str, entries: list[tuple[str, Path]]):
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout()
        row_layout.setAlignment(QtCore.Qt.AlignLeft)
        row.setLayout(row_layout)

        # метка с путём внутри пакета
        label = QtWidgets.QLabel(rel_path)
        label.setFixedWidth(300)
        row_layout.addWidget(label)

        # группируем кнопки, чтобы выбор был эксклюзивным
        group = QtWidgets.QButtonGroup(self)
        group.setExclusive(True)

        for pack_name, full in entries:
            btn = QtWidgets.QToolButton()
            # загружаем изображение через QImageReader, чтобы избежать libpng-ошибок
            reader = QtGui.QImageReader(str(full))
            image = reader.read()
            pixmap = QtGui.QPixmap.fromImage(image).scaled(
                48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            btn.setIcon(QtGui.QIcon(pixmap))
            btn.setIconSize(QtCore.QSize(48, 48))
            btn.setCheckable(True)
            btn.setToolTip(pack_name)
            btn.setProperty("full_path", str(full))
            btn.setProperty("rel_path", rel_path)
            btn.toggled.connect(self._on_texture_selected)
            group.addButton(btn)
            row_layout.addWidget(btn)

        self.list_layout.addWidget(row)

    def _on_texture_selected(self, checked: bool):
        btn = self.sender()
        rel = btn.property("rel_path")
        dst = Path(self.output_dir) / rel

        if checked:
            src = Path(btn.property("full_path"))
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            if dst.exists():
                dst.unlink()
