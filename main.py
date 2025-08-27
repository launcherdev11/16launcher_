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
    logging.info("Создание Загрузчика")
    splash = SplashScreen()
    steps = [
        (20, "Загрузка настроек..."),
        (40, "Проверка обновлений..."),
        (60, "Загрузка списка версий..."),
        (80, "Инициализация интерфейса..."),
        (100, "Готово!"),
    ]
    logging.info("Показ загрузчика")
    splash.show()
    logging.info("Обновление статуса загрузчика")
    splash.update_progress(10, "Загрузка основных компонентов...")
    logging.info("Создание основного окна")
    window = MainWindow()

    for value, message in steps:
        time.sleep(0.5)
        splash.update_progress(value, message)

    splash.close()
    window.show()

    sys.exit(app.exec_())
