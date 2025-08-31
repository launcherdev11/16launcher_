import logging
import sys

from PyQt5.QtWidgets import (
    QApplication,
)

from core.config import LOG_FILE
from core.gui.main_window import MainWindow
from core.util import setup_directories


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE)
    ]
)

if __name__ == "__main__":
    logging.info("Инициализация директорий")
    setup_directories()
    logging.info("Создание приложения")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
