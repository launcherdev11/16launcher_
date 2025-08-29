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
from minecraft_launcher_lib.utils import get_version_list
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QShortcut,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import ely
from ..config import AUTHLIB_JAR_PATH, MINECRAFT_DIR, SKINS_DIR
from ..ely_by_skin_manager import ElyBySkinManager
from ..ely_skin_manager import ElySkinManager
from ..translator import Translator
from ..util import (
    download_authlib_injector,
    generate_random_username,
    load_settings,
    resource_path,
    save_settings,
)
from .custom_line_edit import CustomLineEdit
from .threads.launch_thread import LaunchThread
from .widgets.mod_loader_tab import ModLoaderTab
from .widgets.modpack_tab import ModpackTab
from .widgets.mods_tab import ModsTab
from .widgets.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ely_session = None
        self.setWindowTitle('16Launcher 1.0.2')
        self.setFixedSize(1280, 720)
        self.setWindowIcon(QIcon(resource_path('assets/icon.ico')))
        self.translator = Translator()
        self.motd_messages = [
            'Приятной игры, легенда!',
            'Поддержи проект, если нравится ❤️',
            'Сегодня отличный день, чтобы поиграть!',
            'Ты красавчик, что запускаешь это 😎',
            'Готов к новым блокам?',
            'Эндермены советуют: всегда носишь с собой эндер-жемчуг… и зонтик!',
            'Совет от опытного шахтёра: алмазы любят тишину… и факелы!',
            'Эндермен смотрит? Не смотри в ответ!',
            'Лава опасна, но обсидиан того стоит!',
            'Сундук с сокровищем? Проверь, нет ли ТНТ!',
            'Летать на Элитрах? Помни: ремонт нужен!',
            'Зельеварение? Не перепутай ингредиенты!',
            'Лови рыбу — может, клюнет зачарованная книга!',
        ]

        # Сначала загружаем настройки
        self.settings = load_settings()
        self.setup_ely_auth()
        self.last_username = self.settings.get('last_username', '')
        self.favorites = self.settings.get('favorites', [])
        self.last_version = self.settings.get('last_version', '')
        self.last_loader = self.settings.get('last_loader', 'vanilla')

        # Затем создаем UI элементы
        self.launch_thread = LaunchThread(self)
        self.launch_thread.log_signal.connect(self.append_console_log)
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)
        self.launch_thread.close_launcher_signal.connect(self.close_launcher)

        # Добавляем хоткей Ctrl+D
        self.ctrl_d_shortcut = QShortcut(QKeySequence('Ctrl+D'), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message)

        self.ctrl_d_shortcut = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message_1)

        self.ctrl_d_shortcut = QShortcut(QKeySequence('Ctrl+R'), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message_2)

        self.ctrl_d_shortcut = QShortcut(QKeySequence('Ctrl+G'), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message_3)

        self.main_container = QWidget(self)
        self.setCentralWidget(self.main_container)

        self.main_layout = QHBoxLayout(self.main_container)
        self.main_container.setLayout(self.main_layout)

        self.setup_sidebar()
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.tab_widget = QWidget()
        self.tab_layout = QVBoxLayout(self.tab_widget)
        self.tab_layout.setContentsMargins(15, 15, 15, 15)

        # Инициализация вкладок ПЕРЕД их использованием
        self.game_tab = QWidget()  # Создаем game_tab первым
        self.setup_game_tab()  # Настраиваем содержимое

        self.mods_tab = ModsTab(self)
        self.modpacks_tab = ModpackTab(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.game_tab, 'Запуск игры')  # Теперь game_tab существует
        self.tabs.addTab(self.mods_tab, 'Моды')
        self.tabs.addTab(self.modpacks_tab, 'Мои сборки')

        self.tab_layout.addWidget(self.tabs)

        self.setup_modloader_tabs()

        self.stacked_widget.addWidget(self.tab_widget)
        self.settings_tab = SettingsTab(self.translator, self)
        self.stacked_widget.addWidget(self.settings_tab)
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.currentChanged.connect(self.handle_tab_changed)

        self.apply_dark_theme()

    def retranslate_ui(self):
        """Обновляет все текстовые элементы интерфейса в соответствии с текущим языком"""
        # Основное окно
        self.setWindowTitle(self.translator.tr('window_title'))

        # Вкладка игры
        self.username.setPlaceholderText(self.translator.tr('username_placeholder'))
        self.random_name_button.setToolTip(
            self.translator.tr('generate_random_username'),
        )

        # Версии и модлоадеры
        self.version_type_select.setItemText(0, self.translator.tr('all versions'))
        self.version_type_select.setItemText(1, self.translator.tr('favorites'))

        self.loader_select.setItemText(0, self.translator.tr('vanilla'))
        self.loader_select.setItemText(1, self.translator.tr('forge'))
        self.loader_select.setItemText(2, self.translator.tr('fabric'))
        self.loader_select.setItemText(3, self.translator.tr('optifine'))

        # Кнопки
        self.start_button.setText(self.translator.tr('launch_button'))
        self.ely_login_button.setText(self.translator.tr('ely_login_button'))
        self.change_skin_button.setText

    def handle_tab_changed(self, index):
        """Обработчик смены вкладок"""
        if self.tabs.tabText(index) == 'Моды' and not hasattr(self, 'mods_tab'):
            # Инициализируем вкладку модов только при первом открытии
            self.mods_tab = ModsTab(self)
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, self.mods_tab, 'Моды')
            self.tabs.setCurrentIndex(index)

    def setup_sidebar(self):
        """Создаёт боковую панель с возможностью сворачивания"""
        # Обёртка для панели и кнопки
        self.sidebar_container = QWidget()
        self.sidebar_layout = QHBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        # Боковая панель
        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.StyledPanel)
        self.sidebar.setFixedWidth(100)
        sidebar_content_layout = QVBoxLayout(self.sidebar)
        sidebar_content_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_content_layout.setSpacing(20)

        # Кнопка "Играть"
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon(resource_path('assets/play64.png')))
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

        # Кнопка "Настройки"
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(resource_path('assets/set64.png')))
        self.settings_button.setIconSize(QSize(64, 64))
        self.settings_button.setFixedSize(75, 75)
        self.settings_button.setStyleSheet(self.play_button.styleSheet())
        self.settings_button.clicked.connect(self.show_settings_tab)
        sidebar_content_layout.addWidget(self.settings_button, alignment=Qt.AlignCenter)

        sidebar_content_layout.addStretch()

        # Кнопка "Телеграм"
        self.telegram_button = QPushButton()
        self.telegram_button.setIcon(QIcon(resource_path('assets/tg.png')))
        self.telegram_button.setIconSize(QSize(64, 64))
        self.telegram_button.setFixedSize(75, 75)
        self.telegram_button.setStyleSheet(self.play_button.styleSheet())
        self.telegram_button.clicked.connect(
            lambda: webbrowser.open('https://t.me/of16launcher'),
        )
        sidebar_content_layout.addWidget(self.telegram_button, alignment=Qt.AlignCenter)

        # Кнопка "Поддержать"
        self.support_button = QPushButton()
        self.support_button.setIcon(QIcon(resource_path('assets/support64.png')))
        self.support_button.setIconSize(QSize(64, 64))
        self.support_button.setFixedSize(75, 75)
        self.support_button.setStyleSheet(self.play_button.styleSheet())
        self.support_button.clicked.connect(
            lambda: webbrowser.open('https://www.donationalerts.com/r/16steyy'),
        )
        sidebar_content_layout.addWidget(self.support_button, alignment=Qt.AlignCenter)

        # Кнопка-свёртка (вне панели!)
        self.toggle_sidebar_button = QPushButton()
        self.toggle_sidebar_button.setIcon(QIcon(resource_path('assets/toggle.png')))
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

        # Добавляем панель и кнопку в контейнер
        self.sidebar_layout.addWidget(self.sidebar)
        self.sidebar_layout.addWidget(self.toggle_sidebar_button)

        self.main_layout.addWidget(self.sidebar_container)

    def update_login_button_text(self):
        if hasattr(self, 'access_token') and self.access_token:
            self.ely_login_button.setText('Выйти из Ely.by')
        else:
            self.ely_login_button.setText('Войти с Ely.by')

    def show_game_tab(self):
        """Переключает на вкладку с игрой"""
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.setCurrentIndex(
            0,
        )  # Убедимся, что выбрана первая вкладка (Запуск игры)

    def toggle_theme(self):
        current_theme = getattr(self, 'current_theme', 'dark')
        new_theme = 'light' if current_theme == 'dark' else 'dark'

        # Применяем новую тему
        self.apply_theme(new_theme == 'dark')

        # Обновляем иконки во всех местах
        icon_path = 'assets/sun.png' if new_theme == 'light' else 'assets/moon.png'
        self.theme_button.setIcon(QIcon(resource_path(icon_path)))

        # Если есть кнопка в настройках, обновляем и её
        if hasattr(self.settings_tab, 'theme_button'):
            self.settings_tab.theme_button.setIcon(QIcon(resource_path(icon_path)))
            self.settings_tab.theme_button.setText(
                'Светлая тема' if new_theme == 'light' else 'Тёмная тема',
            )

        # Сохраняем выбор темы
        self.settings['theme'] = new_theme
        save_settings(self.settings)

    def show_settings_tab(self):
        """Переключает на вкладку с настройками"""
        self.stacked_widget.setCurrentIndex(1)

    def append_console_log(self, message: str):
        """Добавляет строку в консоль загрузки"""
        if hasattr(self, "console_output"):
            self.console_output.appendPlainText(message)


    def setup_game_tab(self):
        layout = QVBoxLayout(self.game_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        # Первая строка — имя игрока
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.username = CustomLineEdit(self.game_tab)
        self.username.setPlaceholderText('Введите имя')
        self.username.setMinimumHeight(40)
        self.username.setText(self.last_username)
        self.username.setStyleSheet('padding-right: 80px;')
        top_row.addWidget(self.username)

        self.random_name_button = QToolButton(self.username)
        self.random_name_button.setIcon(QIcon(resource_path('assets/random.png')))
        self.random_name_button.setIconSize(QSize(45, 45))
        self.random_name_button.setCursor(Qt.PointingHandCursor)
        self.random_name_button.setFixedSize(60, 30)
        self.random_name_button.clicked.connect(self.set_random_username)
        self.username.set_button(self.random_name_button)

        form_layout.addLayout(top_row)

        # Вторая строка — версия/модлоадер
        version_row = QHBoxLayout()
        version_row.setSpacing(10)

        self.version_type_select = QComboBox(self.game_tab)
        self.version_type_select.setMinimumHeight(45)
        self.version_type_select.setFixedWidth(250)
        self.version_type_select.addItem('Все версии')
        self.version_type_select.addItem('Избранные')
        self.version_type_select.currentTextChanged.connect(self.update_version_list)
        version_row.addWidget(self.version_type_select)

        self.loader_select = QComboBox(self.game_tab)
        self.loader_select.setMinimumHeight(45)
        self.loader_select.setFixedWidth(250)
        self.loader_select.addItem('Vanilla', 'vanilla')
        self.loader_select.addItem('Forge', 'forge')
        self.loader_select.addItem('Fabric', 'fabric')
        self.loader_select.addItem('OptiFine', 'optifine')
        self.loader_select.addItem('Quilt', 'quilt')
        loader_index = self.loader_select.findData(self.last_loader)
        if loader_index >= 0:
            self.loader_select.setCurrentIndex(loader_index)
        version_row.addWidget(self.loader_select)

        self.version_select = QComboBox(self.game_tab)
        self.version_select.setMinimumHeight(45)
        self.version_select.setFixedWidth(250)
        version_row.addWidget(self.version_select)

        self.favorite_button = QPushButton('★')
        self.favorite_button.setFixedSize(45, 45)
        self.favorite_button.setCheckable(True)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        version_row.addWidget(self.favorite_button)

        form_layout.addLayout(version_row)

        # Третья строка — кнопки
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.start_button = QPushButton('Играть')
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.launch_game)
        bottom_row.addWidget(self.start_button)

        self.change_skin_button = QPushButton('Сменить скин (Ely.by)')
        self.change_skin_button.setMinimumHeight(50)
        self.change_skin_button.setVisible(False)
        self.change_skin_button.clicked.connect(self.change_ely_skin)

        self.ely_login_button = QPushButton('Войти с Ely.by')
        self.ely_login_button.setMinimumHeight(50)
        self.ely_login_button.clicked.connect(self.handle_ely_login)

        bottom_row.addWidget(self.change_skin_button)
        bottom_row.addWidget(self.ely_login_button)

        layout.addLayout(form_layout)
        layout.addLayout(bottom_row)
        
        #консоль
        from PyQt5.QtWidgets import QPlainTextEdit, QSizePolicy
        self.console_output = QPlainTextEdit(self.game_tab)
        self.console_output.setReadOnly(True)
        self.console_output.setVisible(False)
        self.console_output.setFixedHeight(100)
        self.console_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.console_output.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #FFFFFF;
                font-family: Consolas, monospace;
                font-size: 11px;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 4px;
            }
        """)

        console_container = QVBoxLayout()
        console_container.addWidget(self.console_output)
        layout.addLayout(console_container)


        # Прогресс-бар
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



    def setup_ely_auth(self):
        """Проверяет сохранённую сессию"""
        self.ely_session = None
        try:
            if ely.is_logged_in():
                self.ely_session = {
                    'username': ely.username(),
                    'uuid': ely.uuid(),
                    'token': ely.token(),
                }
                self.username.setText(self.ely_session['username'])
                self.update_ely_ui(True)

                # Проверяем текстуру скина через authlib
                try:
                    texture_info = requests.get(
                        f'https://authserver.ely.by/session/profile/{self.ely_session["uuid"]}',
                        headers={
                            'Authorization': f'Bearer {self.ely_session["token"]}',
                        },
                    ).json()

                    if 'textures' in texture_info:
                        skin_url = texture_info['textures'].get('SKIN', {}).get('url')
                        if skin_url:
                            # Сохраняем скин локально для отображения в лаунчере
                            skin_data = requests.get(skin_url).content
                            os.makedirs(SKINS_DIR, exist_ok=True)
                            with open(
                                os.path.join(
                                    SKINS_DIR,
                                    f'{self.ely_session["username"]}.png',
                                ),
                                'wb',
                            ) as f:
                                f.write(skin_data)
                except Exception as e:
                    logging.exception(f'Ошибка проверки скина: {e}')

        except Exception as e:
            logging.exception(f'Ошибка загрузки сессии Ely.by: {e}')

    def update_ely_ui(self, logged_in):
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
            self.change_skin_button.setText('Управление скином')
        else:
            self.ely_login_button.setVisible(True)
            self.change_skin_button.setVisible(False)

    def setup_ely_auth(self):
        """Проверяет сохранённую сессию и загружает скин"""
        try:
            if ely.is_logged_in():
                self.ely_session = {
                    'username': ely.username(),
                    'uuid': ely.uuid(),
                    'token': ely.token(),
                }
                self.username.setText(self.ely_session['username'])
                self.update_ely_ui(True)

                # Загружаем скин через текстуры-прокси
                texture_url = ElySkinManager.get_skin_texture_url(
                    self.ely_session['username'],
                )
                if texture_url:
                    if ElySkinManager.download_skin(self.ely_session['username']):
                        logging.info('Скин успешно загружен')
                    else:
                        logging.warning('Не удалось загрузить скин')

        except Exception as e:
            logging.exception(f'Ошибка загрузки сессии Ely.by: {e}')

    def handle_ely_login(self):
        """Обработчик кнопки входа/выхода"""
        if hasattr(self, 'ely_session') and self.ely_session:
            self.ely_logout()
        else:
            self.ely_login()
        # Обновляем кнопку в настройках
        if hasattr(self.settings_tab, 'update_logout_button_visibility'):
            self.settings_tab.update_logout_button_visibility()

    def ely_login(self):
        """Диалог ввода логина/пароля"""
        email, ok = QInputDialog.getText(
            self,
            'Вход',
            'Введите email Ely.by:',
            QLineEdit.Normal,
            '',
        )
        if not ok or not email:
            return

        password, ok = QInputDialog.getText(
            self,
            'Вход',
            'Введите пароль:',
            QLineEdit.Password,
            '',
        )
        if not ok or not password:
            return

        try:
            self.ely_session = ely.auth_password(email, password)
            self.update_ely_ui(True)
            self.username.setText(self.ely_session['username'])
            QMessageBox.information(self, 'Успешно', 'Авторизация прошла успешно!')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
            ely.write_login_data(
                {
                    'username': self.ely_session['username'],
                    'uuid': self.ely_session['uuid'],
                    'token': self.ely_session['token'],
                    'logged_in': True,
                },
            )

    def start_device_auth(self, dialog):
        """Запуск авторизации через device code"""
        dialog.close()
        try:
            self.ely_session = ely.auth_device_code()
            self.update_ely_ui(True)
            self.username.setText(self.ely_session['username'])
            QMessageBox.information(
                self,
                'Успешно',
                f'Вы вошли как {self.ely_session["username"]}',
            )
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def start_credentials_auth(self, dialog):
        """Запуск авторизации по логину/паролю"""
        dialog.close()
        email, ok = QInputDialog.getText(self, 'Вход', 'Введите email Ely.by:')
        if not ok or not email:
            return

        password, ok = QInputDialog.getText(
            self,
            'Вход',
            'Введите пароль:',
            QLineEdit.Password,
        )
        if not ok or not password:
            return

        try:
            self.ely_session = ely.auth(email, password)
            ely.write_login_data(
                {
                    'username': self.ely_session['username'],
                    'uuid': self.ely_session['uuid'],
                    'token': self.ely_session['token'],
                    'logged_in': True,
                },
            )
            self.update_ely_ui(True)
            self.username.setText(self.ely_session['username'])
            QMessageBox.information(
                self,
                'Успешно',
                f'Вы вошли как {self.ely_session["username"]}',
            )
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def ely_logout(self):
        """Выход из аккаунта Ely.by"""
        ely.logout()
        self.ely_session = None
        self.update_ely_ui(False)
        self.username.setText('')
        # Обновляем кнопку в настройках
        if hasattr(self.settings_tab, 'update_logout_button_visibility'):
            self.settings_tab.update_logout_button_visibility()
        QMessageBox.information(self, 'Выход', 'Вы вышли из аккаунта Ely.by')

    def open_support_tab(self):
        support_tab = QWidget()
        layout = QVBoxLayout(support_tab)

        # Твой текст (можешь сам изменить потом)
        text = QLabel(
            'Наш лаунчер абсолютно бесплатный и безопасный, если тебе нравится лаунчер, его функции, дизайн,\nты можешь поддержать разработчика ❤',
        )
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        layout.addWidget(text)
        text.setFixedSize(700, 900)

        # Кнопка "Поддержать"
        donate_button = QPushButton('Поддержать')
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
            lambda: webbrowser.open('https://www.donationalerts.com/r/16steyy'),
        )
        layout.addWidget(donate_button, alignment=Qt.AlignCenter)

        layout.addStretch()

        self.stacked_widget.addWidget(support_tab)
        self.stacked_widget.setCurrentWidget(support_tab)

    def change_ely_skin(self):
        """Открывает диалог управления скином для Ely.by"""
        if not hasattr(self, 'ely_session') or not self.ely_session:
            QMessageBox.warning(self, 'Ошибка', 'Сначала войдите в Ely.by!')
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('Управление скином')
        dialog.setFixedSize(400, 250)

        layout = QVBoxLayout()

        # Кнопка загрузки нового скина
        upload_btn = QPushButton('Загрузить новый скин')
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

        # Кнопка сброса скина
        reset_btn = QPushButton('Сбросить скин на стандартный')
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
        manage_btn = QPushButton('Открыть страницу управления')
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
                f'https://ely.by/skins?username={self.ely_session["username"]}',
            ),
        )
        layout.addWidget(manage_btn)

        # Кнопка закрытия
        close_btn = QPushButton('Закрыть')
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def upload_new_skin(self, parent_dialog):
        """Загружает новый скин на Ely.by"""
        parent_dialog.close()

        # Диалог выбора файла
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Выберите PNG-файл скина (64x64 или 64x32)',
            '',
            'PNG Images (*.png)',
        )

        if not file_path:
            return  # Пользователь отменил выбор

        # Диалог выбора типа модели
        model_type, ok = QInputDialog.getItem(
            self,
            'Тип модели',
            'Выберите тип модели:',
            ['classic', 'slim'],
            0,
            False,
        )

        if not ok:
            return

        try:
            # Загружаем скин
            success, message = ElySkinManager.upload_skin(
                file_path,
                self.ely_session['token'],
                model_type,
            )

            if success:
                # Скачиваем обновлённый скин для отображения в лаунчере
                skin_url = ElySkinManager.get_skin_url(self.ely_session['username'])
                if skin_url:
                    skin_data = requests.get(skin_url).content
                    skin_path = os.path.join(SKINS_DIR, f'{self.username.text()}.png')

                    os.makedirs(SKINS_DIR, exist_ok=True)
                    with open(skin_path, 'wb') as f:
                        f.write(skin_data)

                    QMessageBox.information(self, 'Успех', message)
                else:
                    QMessageBox.warning(
                        self,
                        'Ошибка',
                        'Не удалось получить новый скин',
                    )
            else:
                QMessageBox.critical(self, 'Ошибка', message)

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def reset_ely_skin(self, parent_dialog):
        """Сбрасывает скин на стандартный"""
        parent_dialog.close()

        try:
            success, message = ElySkinManager.reset_skin(self.ely_session['token'])
            if success:
                # Удаляем локальную копию скина
                skin_path = os.path.join(SKINS_DIR, f'{self.username.text()}.png')
                if os.path.exists(skin_path):
                    os.remove(skin_path)

                QMessageBox.information(self, 'Успех', message)
            else:
                QMessageBox.critical(self, 'Ошибка', message)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def update_version_list(self):
        """Обновляет список версий в зависимости от выбранного типа"""
        current_text = self.version_select.currentText()
        self.version_select.clear()

        versions = get_version_list()
        show_only_favorites = self.version_type_select.currentText() == 'Избранные'
        show_snapshots = self.settings.get('show_snapshots', False)

        for version in versions:
            if version['type'] == 'release' or (show_snapshots and version['type'] == 'snapshot'):
                version_id = version['id']
                if not show_only_favorites or version_id in self.favorites:
                    self.version_select.addItem(version_id)

        # Восстанавливаем текущий выбор, если он доступен
        if current_text and self.version_select.findText(current_text) >= 0:
            self.version_select.setCurrentText(current_text)

        # Обновляем состояние кнопки избранного
        self.update_favorite_button()

    def toggle_sidebar(self):
        is_visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not is_visible)

        # Можно менять иконку в зависимости от состояния
        if is_visible:
            self.toggle_sidebar_button.setIcon(
                QIcon(resource_path('assets/toggle_open.png')),
            )
        else:
            self.toggle_sidebar_button.setIcon(
                QIcon(resource_path('assets/toggle_close.png')),
            )

    def toggle_favorite(self):
        """Добавляет или удаляет версию из избранного"""
        version = self.version_select.currentText()
        if not version:
            return

        if version in self.favorites:
            self.favorites.remove(version)
        else:
            self.favorites.append(version)

        # Сохраняем изменения в настройках
        self.settings['favorites'] = self.favorites
        save_settings(self.settings)

        # Обновляем кнопку и список версий (если в режиме избранных)
        self.update_favorite_button()
        if self.version_type_select.currentText() == 'Избранные':
            self.update_version_list()

    def update_favorite_button(self):
        """Обновляет состояние кнопки избранного"""
        version = self.version_select.currentText()
        if not version:
            self.favorite_button.setChecked(False)
            self.favorite_button.setEnabled(False)
            return

        self.favorite_button.setEnabled(True)
        self.favorite_button.setChecked(version in self.favorites)
        self.favorite_button.setStyleSheet(
            'QPushButton {color: %s;}' % ('gold' if version in self.favorites else 'gray'),
        )

    def get_selected_memory(self):
        """Возвращает выбранное количество памяти в мегабайтах"""
        return self.settings_tab.memory_slider.value() * 1024  # Конвертируем ГБ в МБ

    def show_funny_message(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText('💬 <i>Юля писька</i>')
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)

    def show_funny_message_1(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText('💬 <i>Еру Тукаш</i>')
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)

    def show_funny_message_2(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText('💬 <i>Sosun TheNerfi</i>')
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)

    def show_funny_message_3(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText('💬 <i>Марат педик</i>')
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)

    def load_skin(self):
        # Создаем диалоговое окно выбора источника скина
        source_dialog = QDialog(self)
        source_dialog.setWindowTitle('Выберите источник скина')
        source_dialog.setFixedSize(300, 200)

        layout = QVBoxLayout()

        label = QLabel('Откуда загрузить скин?')
        layout.addWidget(label)

        local_button = QPushButton('С компьютера')
        layout.addWidget(local_button)

        elyby_button = QPushButton('С Ely.by')
        layout.addWidget(elyby_button)

        source_dialog.setLayout(layout)

        def load_from_local():
            source_dialog.close()
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                'Выбери PNG-файл скина',
                '',
                'PNG файлы (*.png)',
            )
            if file_path:
                try:
                    os.makedirs(SKINS_DIR, exist_ok=True)
                    dest_path = os.path.join(
                        SKINS_DIR,
                        f'{self.username.text().strip()}.png',
                    )
                    shutil.copy(file_path, dest_path)
                    QMessageBox.information(
                        self,
                        'Скин загружен',
                        'Скин успешно загружен!',
                    )
                except Exception as e:
                    logging.exception(f'Ошибка загрузки скина: {e}')
                    QMessageBox.critical(
                        self,
                        'Ошибка',
                        f'Не удалось загрузить скин: {e}',
                    )

        def load_from_elyby():
            source_dialog.close()
            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, 'Ошибка', 'Введите имя игрока!')
                return

            if ElyBySkinManager.download_skin(username):
                QMessageBox.information(
                    self,
                    'Скин загружен',
                    'Скин успешно загружен с Ely.by!',
                )
            else:
                ElyBySkinManager.authorize_and_get_skin(self, username)

        local_button.clicked.connect(load_from_local)
        elyby_button.clicked.connect(load_from_elyby)

        source_dialog.exec_()

    def get_ely_skin(username):
        """Получает URL скина пользователя с Ely.by"""
        try:
            response = requests.get(
                f'https://skinsystem.ely.by/skins/{username}.png',
                allow_redirects=False,
            )
            if response.status_code == 200:
                return f'https://skinsystem.ely.by/skins/{username}.png'
            return None
        except Exception as e:
            logging.exception(f'Ошибка при получении скина: {e}')
            return None

    def reset_ely_skin(access_token):
        """Сбрасывает скин на стандартный"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.delete(
                'https://skinsystem.ely.by/upload',
                headers=headers,
            )

            if response.status_code == 200:
                return True, 'Скин сброшен на стандартный!'
            return (
                False,
                f'Ошибка сброса скина: {response.json().get("message", "Неизвестная ошибка")}',
            )
        except Exception as e:
            return False, f'Ошибка при сбросе скина: {e!s}'

    def load_user_data(self):
        if os.path.exists(self.user_data_path):
            try:
                with open(self.user_data_path, encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.info('⚠️ Ошибка загрузки user_data:', e)
        return {'launch_count': 0, 'achievements': []}

    def save_user_data(self):
        try:
            with open(self.user_data_path, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=4)
        except Exception as e:
            logging.info('⚠️ Ошибка сохранения user_data:', e)

    def increment_launch_count(self):
        self.user_data['launch_count'] += 1
        count = self.user_data['launch_count']
        logging.info(f'🚀 Запуск №{count}')

        # Проверка достижений
        if count >= 1 and 'first_launch' not in self.user_data['achievements']:
            self.user_data['achievements'].append('first_launch')
        if count >= 5 and 'five_launches' not in self.user_data['achievements']:
            self.user_data['achievements'].append('five_launches')

        self.save_user_data()

    def set_random_username(self):
        self.username.setText(generate_random_username())

    def setup_modloader_tabs(self):
        # Существующие вкладки
        self.forge_tab = ModLoaderTab('forge')
        self.tabs.addTab(self.forge_tab, 'Forge')

        self.fabric_tab = ModLoaderTab('fabric')
        self.tabs.addTab(self.fabric_tab, 'Fabric')

        self.optifine_tab = ModLoaderTab('optifine')
        self.tabs.addTab(self.optifine_tab, 'OptiFine')

        self.quilt_tab = ModLoaderTab('quilt')
        self.tabs.addTab(self.quilt_tab, 'Quilt')

    def apply_dark_theme(self, dark_theme=True):
        dark_theme_css = """
        QMainWindow {
            background-color: #2e2e2e;
        }
        QWidget {
            background-color: #2e2e2e;
            color: #f1f1f1;
        }
        QLineEdit {
            background-color: #444444;
            color: #f1f1f1;
            border: 1px solid #555555;
            padding: 10px 30px 10px 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #a1a1a1;
        }
        QPushButton {
            background-color: #444444;
            color: #f1f1f1;
            border: 1px solid #555555;
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #666666;
            transform: scale(1.1);
        }
        QPushButton:focus {
            border-color: #a1a1a1;
        }
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 0;
        }
        QToolButton:hover {
            background-color: #666;
            border-radius: 3px;
        }
        QComboBox {
            background-color: #444444;
            color: #f1f1f1;
            border: 1px solid #555555;
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid #555;
            background: #555;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: #333;
            color: #f1f1f1;
            selection-background-color: #555;
            border: 1px solid #444;
            padding: 5px;
            outline: none;
        }
        QProgressBar {
            border: 1px solid #555555;
            background-color: #333333;
            color: #f1f1f1;
        }
        QSlider::groove:horizontal {
            background: #383838;
            height: 6px;
            border-radius: 3px;
        }

        QSlider::sub-page:horizontal {
            background: #505050;
            border-radius: 3px;
        }

        QSlider::add-page:horizontal {
            background: #282828;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background: #ffffff;
            width: 16px;
            height: 16px;
            margin: -4px 0;
            border-radius: 8px;
            border: 2px solid #3a7bd5;
        }

        QSlider::handle:horizontal:hover {
            background: #f0f0f0;
        }
        QTabWidget::pane {
            border: 1px solid #444;
            background: #333;
        }
        QTabBar::tab {
            background: #444;
            color: #fff;
            padding: 8px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background: #555;
            border-color: #666;
        }
        QFrame {
            background-color: #252525;
            border-right: 1px solid #444;
        }
        QScrollBar:vertical {
            border: none;
            background: #2e2e2e;
            width: 12px;
            margin: 0px 0px 0px 0px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #777777;
        }
        """

        vertical_slider_style = """
        QSlider::groove:vertical {
            background: #383838;
            width: 8px;
            border-radius: 4px;
            margin: 4px 0;
        }

        QSlider::sub-page:vertical {
            background: qlineargradient(x1:0, y1:1, x2:0, y2:0,
                stop:0 #3a7bd5, stop:1 #00d2ff);
            border-radius: 4px;
        }

        QSlider::handle:vertical {
            background: #ffffff;
            width: 20px;
            height: 20px;
            margin: 0 -6px;
            border-radius: 10px;
            border: 2px solid #3a7bd5;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
    """

        light_theme_css = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QWidget {
            background-color: #f5f5f5;
            color: #333333;
        }
        QLineEdit {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 10px 30px 10px 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #66afe9;
        }
        QPushButton {
            background-color: #e0e0e0;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
            transform: scale(1.1);
        }
        QPushButton:focus {
            border-color: #66afe9;
        }
        QToolButton {
            background-color: transparent;
            border: none;
            padding: 0;
        }
        QToolButton:hover {
            background-color: #d0d0d0;
            border-radius: 3px;
        }
        QComboBox {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 10px;
            border-radius: 10px;
            font-size: 14px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid #cccccc;
            background: #e0e0e0;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #333333;
            selection-background-color: #e0e0e0;
            border: 1px solid #cccccc;
            padding: 5px;
            outline: none;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            background-color: #ffffff;
            color: #333333;
        }
        QSlider::groove:horizontal {
            background: #e0e0e0;
            height: 6px;
            border-radius: 3px;
            border: 1px solid #cccccc;
        }
        QSlider::handle:horizontal {
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                    stop:0 #f0f0f0, stop:0.5 #d0d0d0, stop:1 #f0f0f0);
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
            border: 1px solid #aaaaaa;
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #3a7bd5, stop:1 #00d2ff);
            border-radius: 3px;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            background: #ffffff;
        }
        QTabBar::tab {
            background: #e0e0e0;
            color: #333333;
            padding: 8px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            border-color: #cccccc;
        }
        QFrame {
            background-color: #f0f0f0;
            border-right: 1px solid #cccccc;
        }
        QScrollBar:vertical {
            border: none;
            background: #f5f5f5;
            width: 12px;
            margin: 0px 0px 0px 0px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #c0c0c0;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #a0a0a0;
        }
        """

        # Применяем выбранную тему
        self.setStyleSheet(dark_theme_css if dark_theme else light_theme_css)
        self.current_theme = 'dark' if dark_theme else 'light'

        # Меняем иконки в зависимости от темы
        icon_suffix = '' if dark_theme else '_dark'

        # Обновляем иконки кнопок, если они существуют
        if hasattr(self, 'theme_button'):
            self.theme_button.setIcon(
                QIcon(resource_path(f'assets/sun{icon_suffix}.png')),
            )
        if hasattr(self, 'settings_button'):
            self.settings_button.setIcon(
                QIcon(resource_path(f'assets/set64{icon_suffix}.png')),
            )

        if hasattr(self, 'telegram_button'):
            self.telegram_button.setIcon(
                QIcon(resource_path(f'assets/tg{icon_suffix}.png')),
            )
        if hasattr(self, 'support_button'):
            self.support_button.setIcon(
                QIcon(resource_path(f'assets/support64{icon_suffix}.png')),
            )
        if hasattr(self, 'play_button'):
            self.play_button.setIcon(
                QIcon(resource_path(f'assets/play64{icon_suffix}.png')),
            )
        if hasattr(self, 'toggle_sidebar_button'):
            is_visible = self.sidebar.isVisible()
            icon_name = 'toggle_open' if is_visible else 'toggle_close'
            self.toggle_sidebar_button.setIcon(
                QIcon(resource_path(f'assets/{icon_name}{icon_suffix}.png')),
            )
        if hasattr(self, 'random_name_button'):
            self.random_name_button.setIcon(
                QIcon(resource_path(f'assets/random{icon_suffix}.png')),
            )
        if hasattr(self, 'open_folder_button'):
            self.open_folder_button.setIcon(
                QIcon(resource_path(f'assets/folder{icon_suffix}.png')),
            )
        if hasattr(self, 'favorite_button'):
            # Для кнопки избранного используем цвет вместо иконки
            version = self.version_select.currentText()
            if version:
                self.favorite_button.setStyleSheet(
                    'QPushButton {color: %s;}' % ('gold' if version in self.favorites else 'gray'),
                )
        if hasattr(self, 'ely_button'):
            # Для кнопки Ely.by используем стандартную иконку
            self.ely_button.setIcon(QIcon(resource_path('assets/account.png')))
        if hasattr(self, 'skin_button'):
            # Для кнопки скина используем стандартную иконку
            self.skin_button.setIcon(QIcon(resource_path('assets/change_name.png')))

        # Обновляем иконки в настройках
        if hasattr(self, 'settings_tab'):
            if hasattr(self.settings_tab, 'theme_button'):
                self.settings_tab.theme_button.setIcon(
                    QIcon(resource_path(f'assets/sun{icon_suffix}.png')),
                )

        # Обновляем цвет MOTD-сообщения
        if hasattr(self, 'motd_label'):
            color = '#aaaaaa' if dark_theme else '#666666'
            self.motd_label.setStyleSheet(f"""
                color: {color};
                font-style: italic;
                font-size: 14px;
                background: transparent;
                padding: 5px;
            """)

    def closeEvent(self, event):
        """Переопределяем метод закрытия окна для сохранения настроек"""
        # Сохраняем текущий выбор
        current_version = self.version_select.currentText()
        if current_version:
            self.settings['last_version'] = current_version
            self.settings['last_loader'] = self.loader_select.currentData()
            self.settings['show_snapshots'] = self.settings_tab.show_snapshots_checkbox.isChecked()
            self.settings['show_motd'] = self.settings_tab.motd_checkbox.isChecked()

        self.settings['last_username'] = self.username.text().strip()
        save_settings(self.settings)
        event.accept()

    def close_launcher(self):
        """Закрывает лаунчер после запуска игры"""
        self.close()

    def launch_game(self):
        try:
            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, 'Ошибка', 'Введите имя игрока!')
                return

            version = self.version_select.currentText()
            loader_type = self.loader_select.currentData()
            memory_mb = self.get_selected_memory()
            close_on_launch = self.settings_tab.close_on_launch_checkbox.isChecked()

            # Сохраняем последние настройки
            self.settings['last_version'] = version
            self.settings['last_loader'] = loader_type
            save_settings(self.settings)

            # Показываем консоль только при запуске
            if self.settings.get("enable_console", False):
                self.console_output.clear()
                self.console_output.setVisible(True)

            # Показываем прогресс
            self.start_progress_label.setText('Подготовка к запуску...')
            self.start_progress_label.setVisible(True)
            self.start_progress.setVisible(True)
            QApplication.processEvents()

            # Запускаем поток
            self.launch_thread.launch_setup(
                version, username, loader_type, memory_mb, close_on_launch
            )
            self.launch_thread.start()

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка запуска', str(e))


    def update_progress(self, current, total, text):
        self.start_progress.setMaximum(total)
        self.start_progress.setValue(current)
        if text:
            self.start_progress_label.setText(text)

    def state_update(self, is_running):
        if is_running:
            self.start_button.setEnabled(False)
        else:
            self.start_button.setEnabled(True)
            self.start_progress_label.setVisible(False)
            self.start_progress.setVisible(False)

            # Если консоль включена и включено "убирать после запуска"
            if self.settings.get("enable_console", False) and \
            self.settings.get("hide_console_after_launch", False):
                self.console_output.setVisible(False)

    def show_message_of_the_day(self):
        if hasattr(self, 'motd_label') and self.settings.get('show_motd', True):
            message = random.choice(self.motd_messages)
            self.motd_label.setText(f'💬 <i>{message}</i>')
        else:
            self.motd_label.clear()

    def open_root_folder(self):
        # Используем глобальную переменную MINECRAFT_DIR, которая содержит путь к папке игры
        folder = MINECRAFT_DIR

        if platform.system() == 'Windows':
            subprocess.Popen(f'explorer "{folder}"')
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])
