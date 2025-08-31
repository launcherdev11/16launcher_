import json
import logging
import os
import platform
import random
import shutil
import subprocess
import traceback
import webbrowser

import requests
from PyQt5.QtCore import QSize, QTimer, Qt
from PyQt5.QtGui import QIcon, QKeySequence, QCloseEvent
from PyQt5.QtWidgets import (
    QMainWindow,
    QShortcut,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QTabWidget,
    QFrame,
    QPushButton,
    QMessageBox,
    QApplication,
    QFileDialog,
    QDialog,
    QLabel,
    QInputDialog,
    QLineEdit,
    QProgressBar,
    QComboBox,
    QToolButton,
)

from .custom_line_edit import CustomLineEdit
from .threads.launch_thread import LaunchThread
from .widgets.mod_loader_tab import ModLoaderTab
from .widgets.modpack_tab import ModpackTab
from .widgets.mods_tab import ModsTab
from .widgets.settings_tab import SettingsTab
from .widgets.splash_screen import SplashScreen
from .. import ely
from ..config import MINECRAFT_DIR, AUTHLIB_JAR_PATH, SKINS_DIR, VERSIONS, main_message, light_theme_css, dark_theme_css
from ..ely_by_skin_manager import ElyBySkinManager
from ..ely_skin_manager import ElySkinManager
from ..translator import Translator
from ..util import (
    resource_path,
    load_settings,
    save_settings,
    download_authlib_injector,
    generate_random_username,
)


def open_root_folder() -> None:
    folder = MINECRAFT_DIR

    if platform.system() == "Windows":
        subprocess.Popen(f'explorer "{folder}"')
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


def get_ely_skin(username: str) -> str | None:
    """Получает URL скина пользователя с Ely.by"""
    try:
        response = requests.get(
            f"https://skinsystem.ely.by/skins/{username}.png", allow_redirects=False
        )
        if response.status_code == 200:
            return f"https://skinsystem.ely.by/skins/{username}.png"
        return None
    except Exception as e:
        logging.error(f"Ошибка при получении скина: {e}")
        return None


class MainWindow(QMainWindow):
    __slots__ = (
        "random_name_button",
        "motd_messages",
        "ely_login_button",
        "open_folder_button",
        "start_progress_label",
        "motd_label",
        "username",
        "toggle_sidebar_button",
        "support_button",
        "telegram_button",
        "news_button",
        "settings_button",
        "quilt_tab",
        "optifine_tab",
        "fabric_tab",
        "forge_tab",
        "play_button",
        "sidebar",
        "sidebar_layout",
        "sidebar_container",
        "ely_session",
        "splash",
    )

    def __init__(self) -> None:
        self.current_theme = None
        self.change_skin_button = None
        self.start_button = None
        self.favorite_button = None
        self.version_select = None
        self.loader_select = None
        self.version_type_select = None
        self.random_name_button = None
        self.motd_messages = main_message
        self.ely_login_button = None
        self.open_folder_button = None
        self.start_progress_label = None
        self.start_progress = None
        self.motd_label = None
        self.username = None
        self.toggle_sidebar_button = None
        self.support_button = None
        self.telegram_button = None
        self.news_button = None
        self.settings_button = None
        self.quilt_tab = None
        self.optifine_tab = None
        self.fabric_tab = None
        self.forge_tab = None
        self.play_button = None
        self.sidebar = None
        self.sidebar_layout = None
        self.sidebar_container = None
        self.ely_session = None
        self.splash = SplashScreen()
        self.splash.show()
        logging.debug("Инициализация основного окна")
        self.splash.update_progress(1, "Инициализация основного окна...")
        super().__init__()

        self.splash.update_progress(2, "Установка заголовка окна...")
        self.setWindowTitle("16Launcher 1.0.2")

        self.splash.update_progress(3, "Установка размера окна...")
        self.setFixedSize(1280, 720)

        self.splash.update_progress(4, "Установка размера окна...")
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        logging.debug("Инициализация транслятора")
        self.splash.update_progress(5, "Инициализация транслятора...")
        self.translator = Translator()

        logging.debug("Загружаем настройки")
        self.splash.update_progress(6, "Загружаем настройки")
        self.settings = load_settings()

        self.splash.update_progress(7, "Загружаем сессию через ely")
        self.setup_ely_auth()

        self.splash.update_progress(19, "Устанавливаем никнейм")
        self.last_username = self.settings.get("last_username", "")

        self.splash.update_progress(20, "Постанавливаем избранные версии")
        self.favorites = self.settings.get("favorites", [])

        self.splash.update_progress(21, "Получаем последний версию")
        self.last_version = self.settings.get("last_version", "")

        self.splash.update_progress(22, "Получаем последний загрузчик")
        self.last_loader = self.settings.get("last_loader", "vanilla")

        logging.debug("Создаем UI элементы")
        self.splash.update_progress(23, "Создаем UI элементы")
        self.launch_thread = LaunchThread(self)
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)
        self.launch_thread.close_launcher_signal.connect(self.close_launcher)

        logging.debug("Добавляем горячие клавиши")
        self.splash.update_progress(24, "Добавляем горячие клавиши")
        self.ctrl_d_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message)
        self.ctrl_q_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.ctrl_q_shortcut.activated.connect(self.show_funny_message)
        self.ctrl_r_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.ctrl_r_shortcut.activated.connect(self.show_funny_message)
        self.ctrl_g_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        self.ctrl_g_shortcut.activated.connect(self.show_funny_message)

        logging.debug("Создаём основной контейнер")
        self.splash.update_progress(25, "Создаём основной экран")
        self.main_container = QWidget(self)
        self.setCentralWidget(self.main_container)
        self.main_layout = QHBoxLayout(self.main_container)
        self.main_container.setLayout(self.main_layout)

        logging.debug("Создаём боковую панель")
        self.splash.update_progress(26, "Создаём боковую панель")
        self.setup_sidebar()
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        self.tab_widget = QWidget()
        self.tab_layout = QVBoxLayout(self.tab_widget)
        self.tab_layout.setContentsMargins(15, 15, 15, 15)

        logging.debug("Создаём Game TAB")
        self.splash.update_progress(37, "Создаём Game TAB")
        self.game_tab = QWidget()
        self.setup_game_tab()

        logging.debug("Создаём Mods TAB")
        self.splash.update_progress(38, "Создаём Mods TAB")
        self.mods_tab = ModsTab(self)

        logging.debug("Создаём Modpacks TAB")
        self.splash.update_progress(39, "Создаём Modpacks TAB")
        self.modpacks_tab = ModpackTab(self)

        logging.debug("Создаём меню вкладок")
        self.splash.update_progress(40, "Создаём меню вкладок")
        self.tabs = QTabWidget()

        self.splash.update_progress(41, "Добавляем вкладку `Запуск игры`")
        self.tabs.addTab(self.game_tab, "Запуск игры")
        self.splash.update_progress(42, "Добавляем вкладку `Моды`")
        self.tabs.addTab(self.mods_tab, "Моды")
        self.splash.update_progress(43, "Добавляем вкладку `Мои сборки`")
        self.tabs.addTab(self.modpacks_tab, "Мои сборки")
        self.splash.update_progress(44, "Добавляем вкладку `Мои сборки`")
        self.splash.update_progress(45, "Добавляем меню вкладок на основную панель`")
        self.tab_layout.addWidget(self.tabs)

        logging.debug("Инициализируем вкладку загрузки")
        self.splash.update_progress(46, "Инициализируем вкладку загрузки")
        self.setup_modloader_tabs()

        self.stacked_widget.addWidget(self.tab_widget)
        logging.debug("Инициализируем вкладку настроек")
        self.splash.update_progress(52, "Инициализируем вкладку настроек")
        self.settings_tab = SettingsTab(self.translator, self)
        self.stacked_widget.addWidget(self.settings_tab)
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.currentChanged.connect(self.handle_tab_changed)

        logging.debug("Инициализируем тёмную тему")
        self.splash.update_progress(53, "Инициализируем тёмную тему")
        self.apply_dark_theme()

        self.splash.update_progress(54, "Загрузка завершена")
        self.splash.close()
        logging.debug("Инициализация завершена")
        del self.splash

    def setup_modloader_tabs(self) -> None:
        # Существующие вкладки
        logging.debug("Создаём вкладку Forge")
        self.splash.update_progress(47, "Создаём вкладку Forge")
        self.forge_tab = ModLoaderTab("forge")

        logging.debug("Создаём вкладку Fabric")
        self.splash.update_progress(48, "Создаём вкладку Fabric")
        self.fabric_tab = ModLoaderTab("fabric")

        logging.debug("Создаём вкладку OptiFine")
        self.splash.update_progress(49, "Создаём вкладку OptiFine")
        self.optifine_tab = ModLoaderTab("optifine")

        logging.debug("Создаём вкладку Quilt")
        self.splash.update_progress(50, "Создаём вкладку Quilt")
        self.quilt_tab = ModLoaderTab("quilt")

        self.splash.update_progress(51, "Добавляем вкладку на основную панель")
        self.tabs.addTab(self.quilt_tab, "Quilt")
        self.tabs.addTab(self.forge_tab, "Forge")
        self.tabs.addTab(self.fabric_tab, "Fabric")
        self.tabs.addTab(self.optifine_tab, "OptiFine")

    def setup_sidebar(self) -> None:
        """Создаёт боковую панель с возможностью сворачивания"""
        logging.debug("Создаём обёртку для панели и кнопки")
        self.splash.update_progress(27, "Создаём панели и кнопки")
        self.sidebar_container = QWidget()
        self.sidebar_layout = QHBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        logging.debug("Создаём боковую панель")
        self.splash.update_progress(28, "Создаём боковую панель")
        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.StyledPanel)
        self.sidebar.setFixedWidth(100)
        sidebar_content_layout = QVBoxLayout(self.sidebar)
        sidebar_content_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_content_layout.setSpacing(20)

        logging.debug("Создаём кнопку играть")
        self.splash.update_progress(29, "Создаём кнопку играть")
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon(resource_path("assets/play64.png")))
        self.play_button.setIconSize(QSize(64, 64))
        self.play_button.setFixedSize(75, 75)
        self.play_button.setStyleSheet("""
               QPushButton {
                   border: none;
                   background-color: transparent;
                   font-size: 14px;
                   padding: 5px;
               }
               QPushButton:hover {
                   background-color: #444444;
                   border-radius: 5px;
               }
           """)
        self.play_button.clicked.connect(self.show_game_tab)
        sidebar_content_layout.addWidget(self.play_button, alignment=Qt.AlignCenter)

        logging.debug("Создаём кнопку настроек")
        self.splash.update_progress(30, "Создаём кнопку настроек")
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(resource_path("assets/set64.png")))
        self.settings_button.setIconSize(QSize(64, 64))
        self.settings_button.setFixedSize(75, 75)
        self.settings_button.setStyleSheet(self.play_button.styleSheet())
        self.settings_button.clicked.connect(self.show_settings_tab)
        sidebar_content_layout.addWidget(self.settings_button, alignment=Qt.AlignCenter)

        logging.debug("Создаём кнопку новостей")
        self.splash.update_progress(31, "Создаём кнопку новостей")
        self.news_button = QPushButton()
        self.news_button.setIcon(QIcon(resource_path("assets/news64.png")))
        self.news_button.setIconSize(QSize(64, 64))
        self.news_button.setFixedSize(75, 75)
        self.news_button.setStyleSheet(self.play_button.styleSheet())
        self.news_button.clicked.connect(self.show_news_tab)
        sidebar_content_layout.addWidget(self.news_button, alignment=Qt.AlignCenter)

        sidebar_content_layout.addStretch()

        logging.debug("Создаём кнопку телеграмма")
        self.splash.update_progress(32, "Создаём кнопку телеграмма")
        self.telegram_button = QPushButton()
        self.telegram_button.setIcon(QIcon(resource_path("assets/tg.png")))
        self.telegram_button.setIconSize(QSize(64, 64))
        self.telegram_button.setFixedSize(75, 75)
        self.telegram_button.setStyleSheet(self.play_button.styleSheet())
        self.telegram_button.clicked.connect(
            lambda: webbrowser.open("https://t.me/of16launcher")
        )
        sidebar_content_layout.addWidget(self.telegram_button, alignment=Qt.AlignCenter)

        logging.debug("Создаём кнопку доната")
        self.splash.update_progress(33, "Создаём кнопку доната")
        self.support_button = QPushButton()
        self.support_button.setIcon(QIcon(resource_path("assets/support64.png")))
        self.support_button.setIconSize(QSize(64, 64))
        self.support_button.setFixedSize(75, 75)
        self.support_button.setStyleSheet(self.play_button.styleSheet())
        self.support_button.clicked.connect(
            lambda: webbrowser.open("https://www.donationalerts.com/r/16steyy")
        )
        sidebar_content_layout.addWidget(self.support_button, alignment=Qt.AlignCenter)

        logging.debug("Создаём Кнопку-свёртку")
        self.splash.update_progress(34, "Создаём кнопку-свёртку")
        self.toggle_sidebar_button = QPushButton()
        self.toggle_sidebar_button.setIcon(QIcon(resource_path("assets/toggle.png")))
        self.toggle_sidebar_button.setIconSize(QSize(24, 24))
        self.toggle_sidebar_button.setFixedSize(30, 30)
        self.toggle_sidebar_button.setStyleSheet("""
               QPushButton {
                   background-color: #444444;
                   color: white;
                   border: none;
                   border-top-right-radius: 5px;
                   border-bottom-right-radius: 5px;
               }
               QPushButton:hover {
                   background-color: #666666;
               }
           """)
        self.toggle_sidebar_button.clicked.connect(self.toggle_sidebar)

        logging.debug("Добавляем в основной контейнер")
        self.splash.update_progress(35, "Добавляем в основной контейнер")
        self.sidebar_layout.addWidget(self.sidebar)
        self.sidebar_layout.addWidget(self.toggle_sidebar_button)

        self.main_layout.addWidget(self.sidebar_container)

    def setup_game_tab(self) -> None:
        layout = QVBoxLayout(self.game_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.username = CustomLineEdit(self.game_tab)
        self.username.setPlaceholderText("Введите имя")
        self.username.setMinimumHeight(40)
        self.username.setText(self.last_username)

        self.username.setStyleSheet("padding-right: 80px;")
        top_row.addWidget(self.username)

        self.random_name_button = QToolButton(self.username)
        self.random_name_button.setIcon(QIcon(resource_path("assets/random.png")))
        self.random_name_button.setIconSize(QSize(45, 45))
        self.random_name_button.setCursor(Qt.PointingHandCursor)
        self.random_name_button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QToolButton:hover {
                background-color: #666;
                border-radius: 3px;
            }
        """)
        self.random_name_button.setFixedSize(60, 30)  
        self.random_name_button.clicked.connect(self.set_random_username)

        self.username.set_button(self.random_name_button)

        form_layout.addLayout(top_row)

        form_layout.addLayout(top_row)

        version_row = QHBoxLayout()
        version_row.setSpacing(10)

        self.version_type_select = QComboBox(self.game_tab)
        self.version_type_select.setMinimumHeight(45)
        self.version_type_select.setFixedWidth(250)
        self.version_type_select.addItem("Все версии")
        self.version_type_select.addItem("Избранные")
        self.version_type_select.currentTextChanged.connect(self.update_version_list)
        version_row.addWidget(self.version_type_select)

        self.loader_select = QComboBox(self.game_tab)
        self.loader_select.setMinimumHeight(45)
        self.loader_select.setFixedWidth(250)
        self.loader_select.addItem("Vanilla", "vanilla")
        self.loader_select.addItem("Forge", "forge")
        self.loader_select.addItem("Fabric", "fabric")
        self.loader_select.addItem("OptiFine", "optifine")
        self.loader_select.addItem("Quilt", "quilt")
        loader_index = self.loader_select.findData(self.last_loader)
        if loader_index >= 0:
            self.loader_select.setCurrentIndex(loader_index)
        version_row.addWidget(self.loader_select)

        self.version_select = QComboBox(self.game_tab)
        self.version_select.setMinimumHeight(45)
        self.version_select.setFixedWidth(250)
        self.version_select.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        version_row.addWidget(self.version_select)

        self.favorite_button = QPushButton("★")
        self.favorite_button.setFixedSize(45, 45)
        self.favorite_button.setCheckable(True)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        version_row.addWidget(self.favorite_button)

        form_layout.addLayout(version_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.change_skin_button = QPushButton("Сменить скин (Ely.by)")
        self.change_skin_button.setMinimumHeight(50)
        self.change_skin_button.clicked.connect(self.change_ely_skin)
        self.change_skin_button.setVisible(False)

        self.start_button = QPushButton("Играть")
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.launch_game)
        bottom_row.addWidget(self.start_button)

        self.change_skin_button = QPushButton("Сменить скин (Ely.by)")
        self.change_skin_button.setMinimumHeight(50)
        self.change_skin_button.clicked.connect(self.change_ely_skin)
        self.change_skin_button.setVisible(False)

        self.ely_login_button = QPushButton("Войти с Ely.by")
        self.ely_login_button.setMinimumHeight(50)
        self.ely_login_button.clicked.connect(self.handle_ely_login)

        bottom_row.addWidget(self.change_skin_button)
        bottom_row.addWidget(self.ely_login_button)

        self.open_folder_button = QPushButton()
        self.open_folder_button.setIcon(QIcon(resource_path(" assets/folder.png")))
        self.open_folder_button.setToolTip("Открыть папку с игрой")
        self.open_folder_button.setIconSize(QSize(24, 24))
        self.open_folder_button.setCursor(Qt.PointingHandCursor)
        self.open_folder_button.setFixedSize(50, 50)
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)
        self.open_folder_button.clicked.connect(open_root_folder)
        bottom_row.addWidget(self.open_folder_button)

        self.motd_label = QLabel()
        self.motd_label.setAlignment(Qt.AlignCenter)
        self.motd_label.setStyleSheet("""
            color: #aaaaaa; 
            font-style: italic; 
            font-size: 14px;
            background: transparent;
            padding: 5px;
        """)
        layout.addWidget(self.motd_label)
        layout.addStretch()

        self.show_message_of_the_day()

        form_layout.addLayout(bottom_row)

        layout.addLayout(form_layout)

        self.start_progress_label = QLabel(self.game_tab)
        self.start_progress_label.setVisible(False)
        layout.addWidget(self.start_progress_label)

        self.start_progress = QProgressBar(self.game_tab)
        self.start_progress.setMinimumHeight(20)
        self.start_progress.setVisible(False)
        layout.addWidget(self.start_progress)

        self.update_version_list()
        if self.last_version:
            index = self.version_select.findText(self.last_version)
            if index >= 0:
                self.version_select.setCurrentIndex(index)

        loader_index = self.loader_select.findData(self.last_loader)
        if loader_index >= 0:
            self.loader_select.setCurrentIndex(loader_index)

    def setup_ely_auth(self) -> None:
        """Проверяет сохранённую сессию"""
        try:
            self.splash.update_progress(8, "Проверяем авторизацию")
            logging.debug("Проверяем авторизацию")
            if ely.is_logged_in():
                logging.debug("Авторизация успешна")
                self.splash.update_progress(9, "Авторизация успешна")
                logging.debug("Загружаем сессию")
                self.splash.update_progress(10, "Загружаем сессию")
                self.ely_session = {
                    "username": ely.username(),
                    "uuid": ely.uuid(),
                    "token": ely.token(),
                }
                self.splash.update_progress(11, "Устанавливаем никнейм")
                self.username.setText(self.ely_session["username"])
                self.splash.update_progress(12, "Обновляем интерфейс")
                self.update_ely_ui(True)

                self.splash.update_progress(12, "Проверяем текстуру скина")
                try:
                    logging.debug("Делаем запрос к API")
                    self.splash.update_progress(13, "Делаем запрос к API")
                    texture_info = requests.get(
                        f"https://authserver.ely.by/session/profile/{self.ely_session['uuid']}",
                        headers={
                            "Authorization": f"Bearer {self.ely_session['token']}"
                        },
                    ).json()

                    if "textures" in texture_info:
                        logging.debug("Текстура найдена")
                        logging.debug("Проверяем ссылку на скин")
                        self.splash.update_progress(14, "Текстура найдена")
                        self.splash.update_progress(15, "Проверяем ссылку на скин")
                        skin_url = texture_info["textures"].get("SKIN", {}).get("url")
                        if skin_url:
                            logging.debug("Ссылка найдена")
                            logging.debug("Делаем запрос на получение данных скина")
                            self.splash.update_progress(16, "Ссылка найдена")
                            self.splash.update_progress(
                                17, "Делаем запрос на получение данных скина"
                            )
                            skin_data = requests.get(skin_url).content
                            os.makedirs(SKINS_DIR, exist_ok=True)
                            with open(
                                    os.path.join(
                                        SKINS_DIR, f"{self.ely_session['username']}.png"
                                    ),
                                    "wb",
                            ) as f:
                                self.splash.update_progress(18, "Устанавливаем скин")
                                f.write(skin_data)

                except Exception as e:
                    logging.error(f"Ошибка проверки скина: {e}")

        except Exception as e:
            logging.error(f"Ошибка загрузки сессии Ely.by: {e}")

    def retranslate_ui(self) -> None:
        """Обновляет все текстовые элементы интерфейса в соответствии с текущим языком"""
        self.setWindowTitle(self.translator.tr("window_title"))

        self.username.setPlaceholderText(self.translator.tr("username_placeholder"))
        self.random_name_button.setToolTip(
            self.translator.tr("generate_random_username")
        )

        self.version_type_select.setItemText(0, self.translator.tr("all versions"))
        self.version_type_select.setItemText(1, self.translator.tr("favorites"))

        self.loader_select.setItemText(0, self.translator.tr("vanilla"))
        self.loader_select.setItemText(1, self.translator.tr("forge"))
        self.loader_select.setItemText(2, self.translator.tr("fabric"))
        self.loader_select.setItemText(3, self.translator.tr("optifine"))

        self.start_button.setText(self.translator.tr("launch_button"))
        self.ely_login_button.setText(self.translator.tr("ely_login_button"))

    def handle_tab_changed(self, index: int) -> None:
        """Обработчик смены вкладок"""
        pass

    def update_login_button_text(self) -> None:
        self.ely_login_button.setText(
            "Выйти из Ely.by"
            if hasattr(self, "access_token") and self.access_token
            else "Войти с Ely.by"
        )

    def show_game_tab(self) -> None:
        """Переключает на вкладку с игрой"""
        self.stacked_widget.setCurrentWidget(self.game_tab)

    def toggle_theme(self) -> None:
        current_theme = getattr(self, "current_theme", "dark")
        new_theme = "light" if current_theme == "dark" else "dark"

        self.apply_theme(new_theme == "dark")

        icon_path = "assets/sun.png" if new_theme == "light" else "assets/moon.png"
        self.theme_button.setIcon(QIcon(resource_path(icon_path)))

        if hasattr(self.settings_tab, "theme_button"):
            self.settings_tab.theme_button.setIcon(QIcon(resource_path(icon_path)))
            self.settings_tab.theme_button.setText(
                "Светлая тема" if new_theme == "light" else "Тёмная тема"
            )

        self.settings["theme"] = new_theme
        save_settings(self.settings)

    def show_settings_tab(self) -> None:
        """Переключает на вкладку с настройками"""
        self.stacked_widget.setCurrentWidget(self.settings_tab)

    def show_news_tab(self) -> None:
        """Переключает на вкладку с новостями"""
        self.stacked_widget.setCurrentWidget(self.news_tab)

    def update_ely_ui(self, logged_in: bool) -> None:
        """Обновляет UI в зависимости от статуса авторизации"""
        if logged_in:
            self.ely_login_button.setVisible(False)
            self.change_skin_button.setVisible(True)
            self.change_skin_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 8px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            self.change_skin_button.setText("Управление скином")
        else:
            self.ely_login_button.setVisible(True)
            self.change_skin_button.setVisible(False)

    def handle_ely_login(self) -> None:
        """Обработчик кнопки входа/выхода"""
        if hasattr(self, "ely_session") and self.ely_session:
            self.ely_logout()
        else:
            self.ely_login()
        # Обновляем кнопку в настройках
        if hasattr(self.settings_tab, "update_logout_button_visibility"):
            self.settings_tab.update_logout_button_visibility()

    def ely_login(self) -> None:
        """Диалог ввода логина/пароля"""
        email, ok = QInputDialog.getText(
            self, "Вход", "Введите email Ely.by:", QLineEdit.Normal, ""
        )
        if not ok or not email:
            return

        password, ok = QInputDialog.getText(
            self, "Вход", "Введите пароль:", QLineEdit.Password, ""
        )
        if not ok or not password:
            return

        try:
            self.ely_session = ely.auth_password(email, password)
            self.update_ely_ui(True)
            self.username.setText(self.ely_session["username"])
            QMessageBox.information(self, "Успешно", "Авторизация прошла успешно!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            ely.write_login_data({
                "username": self.ely_session["username"],
                "uuid": self.ely_session["uuid"],
                "token": self.ely_session["token"],
                "logged_in": True,
            })

    def start_device_auth(self, dialog: QInputDialog) -> None:
        """Запуск авторизации через device code"""
        dialog.close()
        try:
            self.ely_session = ely.auth_device_code()
            self.update_ely_ui(True)
            self.username.setText(self.ely_session["username"])
            QMessageBox.information(
                self, "Успешно", f"Вы вошли как {self.ely_session['username']}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def start_credentials_auth(self, dialog: QInputDialog) -> None:
        """Запуск авторизации по логину/паролю"""
        dialog.close()
        email, ok = QInputDialog.getText(self, "Вход", "Введите email Ely.by:")
        if not (ok or email):
            return

        password, ok = QInputDialog.getText(
            self, "Вход", "Введите пароль:", QLineEdit.Password
        )
        if not (ok or password):
            return

        try:
            self.ely_session = ely.auth(email, password)
            ely.write_login_data({
                "username": self.ely_session["username"],
                "uuid": self.ely_session["uuid"],
                "token": self.ely_session["token"],
                "logged_in": True,
            })
            self.update_ely_ui(True)
            self.username.setText(self.ely_session["username"])
            QMessageBox.information(
                self, "Успешно", f"Вы вошли как {self.ely_session['username']}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def ely_logout(self) -> None:
        """Выход из аккаунта Ely.by"""
        ely.logout()
        self.ely_session = None
        self.update_ely_ui(False)
        self.username.setText("")
        # Обновляем кнопку в настройках
        if hasattr(self.settings_tab, "update_logout_button_visibility"):
            self.settings_tab.update_logout_button_visibility()
        QMessageBox.information(self, "Выход", "Вы вышли из аккаунта Ely.by")

    def open_support_tab(self) -> None:
        support_tab = QWidget()
        layout = QVBoxLayout(support_tab)

        text = QLabel(
            "Наш лаунчер абсолютно бесплатный и безопасный, если тебе нравится лаунчер, его функции, дизайн,"
            "\nты можешь поддержать разработчика ❤"
        )
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        layout.addWidget(text)
        text.setFixedSize(700, 900)

        # Кнопка "Поддержать"
        donate_button = QPushButton("Поддержать")
        donate_button.setFixedSize(200, 50)
        donate_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 16px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        donate_button.clicked.connect(
            lambda: webbrowser.open("https://www.donationalerts.com/r/16steyy")
        )
        layout.addWidget(donate_button, alignment=Qt.AlignCenter)

        layout.addStretch()

        self.stacked_widget.addWidget(support_tab)
        self.stacked_widget.setCurrentWidget(support_tab)

    def change_ely_skin(self) -> None:
        """Открывает диалог управления скином для Ely.by"""
        if not hasattr(self, "ely_session") or not self.ely_session:
            QMessageBox.warning(self, "Ошибка", "Сначала войдите в Ely.by!")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Управление скином")
        dialog.setFixedSize(400, 250)

        layout = QVBoxLayout()

        # Кнопка загрузки нового скина
        upload_btn = QPushButton("Загрузить новый скин")
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        upload_btn.clicked.connect(lambda: self.upload_new_skin(dialog))
        layout.addWidget(upload_btn)

        reset_btn = QPushButton("Сбросить скин на стандартный")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        reset_btn.clicked.connect(lambda: self.reset_ely_skin(dialog))
        layout.addWidget(reset_btn)

        # Кнопка открытия страницы управления
        manage_btn = QPushButton("Открыть страницу управления")
        manage_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
        """)
        manage_btn.clicked.connect(
            lambda: webbrowser.open(
                f"https://ely.by/skins?username={self.ely_session['username']}"
            )
        )
        layout.addWidget(manage_btn)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def upload_new_skin(self, parent_dialog: QInputDialog) -> None:
        """Загружает новый скин на Ely.by"""
        parent_dialog.close()

        # Диалог выбора файла
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите PNG-файл скина (64x64 или 64x32)", "", "PNG Images (*.png)"
        )

        if not file_path:
            return  # Пользователь отменил выбор

        # Диалог выбора типа модели
        model_type, ok = QInputDialog.getItem(
            self, "Тип модели", "Выберите тип модели:", ["classic", "slim"], 0, False
        )

        if not ok:
            return

        try:
            # Загружаем скин
            success, message = ElySkinManager.upload_skin(
                file_path, self.ely_session["token"], model_type
            )

            if success:
                # Скачиваем обновлённый скин для отображения в лаунчере
                skin_url = ElySkinManager.get_skin_url(self.ely_session["username"])
                if skin_url:
                    skin_data = requests.get(skin_url).content
                    skin_path = os.path.join(SKINS_DIR, f"{self.username.text()}.png")

                    os.makedirs(SKINS_DIR, exist_ok=True)
                    with open(skin_path, "wb") as f:
                        f.write(skin_data)

                    QMessageBox.information(self, "Успех", message)
                else:
                    QMessageBox.warning(
                        self, "Ошибка", "Не удалось получить новый скин"
                    )
            else:
                QMessageBox.critical(self, "Ошибка", message)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def reset_ely_skin(self, parent_dialog: QInputDialog) -> None:
        """Сбрасывает скин на стандартный"""
        parent_dialog.close()

        try:
            success, message = ElySkinManager.reset_skin(self.ely_session["token"])
            if success:
                # Удаляем локальную копию скина
                skin_path = os.path.join(SKINS_DIR, f"{self.username.text()}.png")
                if os.path.exists(skin_path):
                    os.remove(skin_path)

                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.critical(self, "Ошибка", message)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def update_version_list(self) -> None:
        """Обновляет список версий в зависимости от выбранного типа"""
        current_text = self.version_select.currentText()
        self.version_select.clear()

        show_only_favorites = self.version_type_select.currentText() == "Избранные"
        show_snapshots = self.settings.get("show_snapshots", False)
        for v in VERSIONS:
            if v["type"] == "release" or (show_snapshots and v["type"] == "snapshot"):
                version_id = v["id"]
                if not show_only_favorites or version_id in self.favorites:
                    self.version_select.addItem(version_id)

        if current_text and self.version_select.findText(current_text) >= 0:
            self.version_select.setCurrentText(current_text)

        self.update_favorite_button()

    def toggle_sidebar(self) -> None:
        is_visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not is_visible)
        self.toggle_sidebar_button.setIcon(
            QIcon(
                resource_path(
                    "assets/toggle_open.png"
                    if is_visible
                    else "assets/toggle_close.png"
                )
            )
        )

    def toggle_favorite(self) -> None:
        """Добавляет или удаляет версию из избранного"""
        version = self.version_select.currentText()
        if not version:
            return

        if version in self.favorites:
            self.favorites.remove(version)
        else:
            self.favorites.append(version)

        # Сохраняем изменения в настройках
        self.settings["favorites"] = self.favorites
        save_settings(self.settings)

        # Обновляем кнопку и список версий (если в режиме избранных)
        self.update_favorite_button()
        if self.version_type_select.currentText() == "Избранные":
            self.update_version_list()

    def update_favorite_button(self) -> None:
        """Обновляет состояние кнопки избранного"""
        version = self.version_select.currentText()
        if not version:
            self.favorite_button.setChecked(False)
            self.favorite_button.setEnabled(False)
            return

        self.favorite_button.setEnabled(True)
        self.favorite_button.setChecked(version in self.favorites)
        self.favorite_button.setStyleSheet(
            "QPushButton {color: %s;}"
            % ("gold" if version in self.favorites else "gray")
        )

    def get_selected_memory(self) -> int:
        """Возвращает выбранное количество памяти в мегабайтах"""
        return self.settings_tab.memory_slider.value() * 1024  

    def show_funny_message(self) -> None:
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText("💬 <i>Binobinos привет!</i>")
        QTimer.singleShot(3000, self.show_message_of_the_day)

    def load_skin(self) -> None:
        source_dialog = QDialog(self)
        source_dialog.setWindowTitle("Выберите источник скина")
        source_dialog.setFixedSize(300, 200)

        layout = QVBoxLayout()

        label = QLabel("Откуда загрузить скин?")
        layout.addWidget(label)

        local_button = QPushButton("С компьютера")
        layout.addWidget(local_button)

        elyby_button = QPushButton("С Ely.by")
        layout.addWidget(elyby_button)

        source_dialog.setLayout(layout)

        def load_from_local():
            source_dialog.close()
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Выбери PNG-файл скина", "", "PNG файлы (*.png)"
            )
            if file_path:
                try:
                    os.makedirs(SKINS_DIR, exist_ok=True)
                    dest_path = os.path.join(
                        SKINS_DIR, f"{self.username.text().strip()}.png"
                    )
                    shutil.copy(file_path, dest_path)
                    QMessageBox.information(
                        self, "Скин загружен", "Скин успешно загружен!"
                    )
                except Exception as e:
                    logging.error(f"Ошибка загрузки скина: {e}")
                    QMessageBox.critical(
                        self, "Ошибка", f"Не удалось загрузить скин: {e}"
                    )

        def load_from_elyby():
            source_dialog.close()
            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, "Ошибка", "Введите имя игрока!")
                return

            if ElyBySkinManager.download_skin(username):
                QMessageBox.information(
                    self, "Скин загружен", "Скин успешно загружен с Ely.by!"
                )
            else:
                ElyBySkinManager.authorize_and_get_skin(self, username)

        local_button.clicked.connect(load_from_local)
        elyby_button.clicked.connect(load_from_elyby)

        source_dialog.exec_()

    def load_user_data(self) -> None:
        if os.path.exists(self.user_data_path):
            try:
                with open(self.user_data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.info("⚠️ Ошибка загрузки user_data:", e)
        return {"launch_count": 0, "achievements": []}

    def save_user_data(self) -> None:
        try:
            with open(self.user_data_path, "w", encoding="utf-8") as f:
                json.dump(self.user_data, f, indent=4)
        except Exception as e:
            logging.info("⚠️ Ошибка сохранения user_data:", e)

    def increment_launch_count(self) -> None:
        self.user_data["launch_count"] += 1
        count = self.user_data["launch_count"]
        logging.info(f"🚀 Запуск №{count}")

        # Проверка достижений
        if count >= 1 and "first_launch" not in self.user_data["achievements"]:
            self.user_data["achievements"].append("first_launch")
        if count >= 5 and "five_launches" not in self.user_data["achievements"]:
            self.user_data["achievements"].append("five_launches")

        self.save_user_data()

    def set_random_username(self) -> None:
        self.username.setText(generate_random_username())

    def apply_dark_theme(self, dark_theme: bool = True) -> None:
        self.setStyleSheet(dark_theme_css if dark_theme else light_theme_css)
        self.current_theme = "dark" if dark_theme else "light"

        icon_suffix = "" if dark_theme else "_dark"

        if hasattr(self, "theme_button"):
            self.theme_button.setIcon(
                QIcon(resource_path(f"assets/sun{icon_suffix}.png"))
            )
        if hasattr(self, "settings_button"):
            self.settings_button.setIcon(
                QIcon(resource_path(f"assets/set64{icon_suffix}.png"))
            )
        if hasattr(self, "news_button"):
            self.news_button.setIcon(
                QIcon(resource_path(f"assets/news64{icon_suffix}.png"))
            )
        if hasattr(self, "telegram_button"):
            self.telegram_button.setIcon(
                QIcon(resource_path(f"assets/tg{icon_suffix}.png"))
            )
        if hasattr(self, "support_button"):
            self.support_button.setIcon(
                QIcon(resource_path(f"assets/support64{icon_suffix}.png"))
            )
        if hasattr(self, "play_button"):
            self.play_button.setIcon(
                QIcon(resource_path(f"assets/play64{icon_suffix}.png"))
            )
        if hasattr(self, "toggle_sidebar_button"):
            is_visible = self.sidebar.isVisible()
            icon_name = "toggle_open" if is_visible else "toggle_close"
            self.toggle_sidebar_button.setIcon(
                QIcon(resource_path(f"assets/{icon_name}{icon_suffix}.png"))
            )
        if hasattr(self, "random_name_button"):
            self.random_name_button.setIcon(
                QIcon(resource_path(f"assets/random{icon_suffix}.png"))
            )
        if hasattr(self, "open_folder_button"):
            self.open_folder_button.setIcon(
                QIcon(resource_path(f"assets/folder{icon_suffix}.png"))
            )
        if hasattr(self, "favorite_button"):
            # Для кнопки избранного используем цвет вместо иконки
            version = self.version_select.currentText()
            if version:
                self.favorite_button.setStyleSheet(
                    "QPushButton {color: %s;}"
                    % ("gold" if version in self.favorites else "gray")
                )
        if hasattr(self, "ely_button"):
            self.ely_button.setIcon(QIcon(resource_path("assets/account.png")))
        if hasattr(self, "skin_button"):
            self.skin_button.setIcon(QIcon(resource_path("assets/change_name.png")))

        if hasattr(self, "settings_tab") and hasattr(self.settings_tab, "theme_button"):
            self.settings_tab.theme_button.setIcon(
                QIcon(resource_path(f"assets/sun{icon_suffix}.png"))
            )

        if hasattr(self, "motd_label"):
            color = "#aaaaaa" if dark_theme else "#666666"
            self.motd_label.setStyleSheet(f"""
                color: {color}; 
                font-style: italic; 
                font-size: 14px;
                background: transparent;
                padding: 5px;
            """)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Переопределяем метод закрытия окна для сохранения настроек"""
        # Сохраняем текущий выбор
        current_version = self.version_select.currentText()
        if current_version:
            self.settings["last_version"] = current_version
            self.settings["last_loader"] = self.loader_select.currentData()
            self.settings["show_snapshots"] = (
                self.settings_tab.show_snapshots_checkbox.isChecked()
            )
            self.settings["show_motd"] = self.settings_tab.motd_checkbox.isChecked()

        self.settings["last_username"] = self.username.text().strip()
        save_settings(self.settings)
        event.accept()

    def close_launcher(self) -> None:
        """Закрывает лаунчер после запуска игры"""
        self.close()

    def launch_game(self) -> None:
        try:
            logging.info("[LAUNCHER] Starting game launch process...")

            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, "Ошибка", "Введите имя игрока!")
                return

            version = self.version_select.currentText()
            loader_type = self.loader_select.currentData()
            memory_mb = self.get_selected_memory()
            close_on_launch = self.settings_tab.close_on_launch_checkbox.isChecked()

            logging.info(
                f"[LAUNCHER] Launch parameters: "
                f"User: {username}, "
                f"Version: {version}, "
                f"Loader: {loader_type}, "
                f"Memory: {memory_mb}MB, "
                f"Close on launch: {close_on_launch}"
            )

            if not hasattr(self, "ely_session"):
                self.ely_session = None
                logging.info("[LAUNCHER] No Ely.by session found")

            skin_path = os.path.join(SKINS_DIR, f"{username}.png")
            if os.path.exists(skin_path):
                logging.info("[LAUNCHER] Found skin, copying...")
                assets_dir = os.path.join(MINECRAFT_DIR, "assets", "skins")
                os.makedirs(assets_dir, exist_ok=True)
                shutil.copy(skin_path, os.path.join(assets_dir, f"{username}.png"))

            if hasattr(self, "ely_session") and self.ely_session:
                logging.info("[LAUNCHER] Ely.by session detected, checking authlib...")
                if not os.path.exists(AUTHLIB_JAR_PATH):
                    logging.info("[LAUNCHER] Downloading authlib-injector...")
                    if not download_authlib_injector():
                        QMessageBox.critical(
                            self, "Ошибка", "Не удалось загрузить Authlib Injector"
                        )
                        return

            self.settings["last_version"] = version
            self.settings["last_loader"] = loader_type
            save_settings(self.settings)

            self.start_progress_label.setText("Подготовка к запуску...")
            self.start_progress_label.setVisible(True)
            self.start_progress.setVisible(True)
            QApplication.processEvents()  

            logging.info("[LAUNCHER] Starting launch thread...")
            self.launch_thread.launch_setup(
                version, username, loader_type, memory_mb, close_on_launch
            )
            self.launch_thread.start()

        except Exception as e:
            logging.error(f"[ERROR] Launch failed: {str(e)}")
            logging.error(f"Game launch failed: {traceback.format_exc()}")
            QMessageBox.critical(
                self, "Ошибка запуска", f"Не удалось запустить игру: {str(e)}"
            )

    def update_progress(self, current: int, total: int, text: str) -> None:
        self.start_progress.setMaximum(total)
        self.start_progress.setValue(current)
        if text:
            self.start_progress_label.setText(text)

    def state_update(self, is_running: bool) -> None:
        if is_running:
            self.start_button.setEnabled(False)
        else:
            self.start_button.setEnabled(True)
            self.start_progress_label.setVisible(False)
            self.start_progress.setVisible(False)

    def show_message_of_the_day(self) -> None:
        if hasattr(self, "motd_label") and self.settings.get("show_motd", True):
            message = random.choice(self.motd_messages)
            self.motd_label.setText(f"💬 <i>{message}</i>")
        else:
            self.motd_label.clear()
