# main.py
import sys
from os.path import join
from pathlib import Path

from PyQt5 import QtWidgets

from src.mixer.ui import ResourcePackMixin

if __name__ == "__main__":
    SRC_DIR = Path(__file__).resolve().parent
    MIX_DIR = Path(join(SRC_DIR.parent, 'MixDir'))
    OUT_DIR = Path(join(SRC_DIR.parent, 'OutDir'))

    app = QtWidgets.QApplication(sys.argv)
    window = ResourcePackMixin(mix_dir=MIX_DIR, out_dir=OUT_DIR)
    window.show()
    sys.exit(app.exec_())
