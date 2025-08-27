import logging
import sys
import time

from PyQt5.QtWidgets import (
    QApplication,
)

from core.config import LOG_FILE
from core.gui.main_window import MainWindow
from core.gui.widgets.splash_screen import SplashScreen
from core.util import setup_directories


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stderr),  # Вывод в консоль
        logging.FileHandler(LOG_FILE)  # Запись в файл
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
