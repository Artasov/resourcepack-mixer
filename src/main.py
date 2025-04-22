# main.py
import sys
from os.path import join
from pathlib import Path

from PyQt5 import QtWidgets

from src.mixer.ui import ResourcePackMixin

if __name__ == "__main__":
    SRC_DIR = Path(__file__).resolve().parent
    MIX_DIR = Path(join(SRC_DIR.parent, 'MixDir'))
    OUT_DIR = Path(r'C:\Users\xl\AppData\Roaming\xlmine-launcher\xlartas-client\resourcepacks\xlmine_1.20.1')

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(
        "QWidget{"
        "background-color:#222;"
        "color:#fff;"
        "} "
        "QLineEdit,QPushButton,QCheckBox{"
        "background-color:#333;"
        "color:#fff;"
        "outline:none;"
        "border:none;"
        "} "
        "QPushButton{"
        "padding: 5px 10px;"
        "} "
        "QPushButton::pressed{"
        "padding: 5px 10px;"
        "border: 2px solid #fe5;"
        "} "
        "QLineEdit,QCheckBox{"
        "padding: 4px 10px 4px 10px;"
        "} "
        "QLineEdit:focus{"
        "background-color:#333;"
        "color:#fff;"
        "outline:none;"
        "border:none;"
        "} "
        "QScrollArea,QDialog{background-color:#222;color:#fff;border:none;}"
    )
    window = ResourcePackMixin(mix_dir=MIX_DIR, out_dir=OUT_DIR)
    window.show()
    sys.exit(app.exec_())
