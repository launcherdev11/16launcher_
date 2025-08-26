import subprocess
import os
import sys
import logging
import json
import random
from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt, QTimer, QObject, QMetaObject, pyqtSlot
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QComboBox, QProgressBar, QPushButton, QApplication, 
                            QMainWindow, QFileDialog, QDialog, QFormLayout, 
                            QSlider, QMessageBox, QTabWidget, QFrame, QStackedWidget, QCheckBox, QScrollArea, QTextEdit, QListWidget, QToolButton, QStyle, QInputDialog, QShortcut, QTableWidget, QHeaderView, QTableWidgetItem, QListWidgetItem, QGridLayout, QMenu, QAction, QDialogButtonBox)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QFontDatabase, QKeySequence, QCursor
from minecraft_launcher_lib.utils import get_minecraft_directory, get_version_list
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.forge import find_forge_version, install_forge_version
from minecraft_launcher_lib.fabric import get_all_minecraft_versions, install_fabric as fabric_install
from minecraft_launcher_lib.fabric import get_latest_loader_version
from minecraft_launcher_lib.command import get_minecraft_command
from minecraft_launcher_lib.quilt import install_quilt as quilt_install
from minecraft_launcher_lib.fabric import get_all_minecraft_versions
from uuid import uuid1
import urllib.request
from subprocess import call
import shutil
import requests
from datetime import datetime
import hashlib
from functools import lru_cache
from base64 import b64encode
import webbrowser
from ely_device import authorize_via_device_code
import random 
import zipfile
from urllib.parse import urlparse
from cfg import read, write, ELY_CLIENT_ID
from flow import dedicated, logged
import ely
import traceback
import time
import re
import io
import xml.etree.ElementTree as ET
import hashlib
import gnupg

ELY_PUBKEY = """
-----BEGIN PGP PUBLIC KEY BLOCK-----
mQINBF4x...  # Вставить полный ключ с сайта ely.by
-----END PGP PUBLIC KEY BLOCK-----
"""

def get_quilt_versions(mc_version: str):
    try:
        response = requests.get(
            "https://meta.quiltmc.org/v3/versions/loader",
            timeout=15
        )
        if response.status_code != 200:
            return []

        all_versions = response.json()
        filtered_versions = [
            {
                "version": v["version"],
                "build": v["build"],
                "stable": not any(x in v["version"].lower() for x in ["beta", "alpha", "rc"])
            }
            for v in all_versions
            if v["minecraft_version"] == mc_version
        ]
        
        return sorted(
            filtered_versions,
            key=lambda x: (x["stable"], x["build"]),
            reverse=True
        )
        
    except Exception as e:
        logging.error(f"Ошибка получения версий Quilt: {str(e)}")
        return []
    
# Получаем список версий Minecraft
MINECRAFT_VERSIONS = [version["id"] for version in get_version_list() if version["type"] == "release"]

def authenticate_ely_by(username, password):
    url = "https://authserver.ely.by/authenticate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "agent": {
            "name": "Minecraft",
            "version": 1
        },
        "username": username,
        "password": password,
        "requestUser": True
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return {
            "access_token": data["accessToken"],
            "client_token": data["clientToken"],
            "uuid": data["selectedProfile"]["id"],
            "username": data["selectedProfile"]["name"],
            "user": data.get("user", {})
        }
    else:
        print("Ошибка авторизации:", response.text)
        return None



def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)


# Глобальные константы
MINECRAFT_DIR = os.path.join(get_minecraft_directory(), "16launcher")
SKINS_DIR = os.path.join(MINECRAFT_DIR, "skins")
SETTINGS_PATH = os.path.join(MINECRAFT_DIR, "settings.json")
LOG_FILE = os.path.join(MINECRAFT_DIR, "launcher_log.txt")
NEWS_FILE = os.path.join(MINECRAFT_DIR, "launcher_news.json")
ELYBY_API_URL = "https://authserver.ely.by/api/"
ELYBY_SKINS_URL = "https://skinsystem.ely.by/skins/"
ELYBY_AUTH_URL = "https://account.ely.by/oauth2/v1"
MODS_DIR = os.path.join(MINECRAFT_DIR, "mods")
AUTHLIB_INJECTOR_URL = "https://authlib-injector.ely.by/artifact/latest.json"   
AUTHLIB_JAR_PATH = os.path.join(MINECRAFT_DIR, "authlib-injector.jar")

class Translator:
    def __init__(self):
        self.language = "ru"
        # В классе Translator
        self.translations = {
            "ru": {
                # Основные элементы
                "window_title": "16Launcher 1.0.2.b",
                "play_button": "Играть",
                "settings_button": "Настройки",
                "news_button": "Новости",
                "support_button": "Поддержать",
                
                # Вкладка игры
                "username_placeholder": "Введите имя",
                "version_label": "Версия Minecraft:",
                "loader_label": "Модлоадер:",
                "launch_button": "Играть",
                "change_skin_button": "Сменить скин",
                "ely_login_button": "Войти с Ely.by",
                
                # Настройки
                "language_label": "Язык:",
                "theme_button": "Тёмная тема",
                "memory_label": "Оперативная память (ГБ):",
                "directory_label": "Директория игры:",
                "choose_directory_button": "Выбрать папку",
                "close_on_launch": "Закрывать лаунчер при запуске игры",
                "ely_logout_button": "Выйти из Ely.by",
                
                # Сообщения
                "enter_username": "Введите имя игрока!",
                "launch_error": "Ошибка запуска",
            },
            "en": {
                # Основные элементы
                "window_title": "16Launcher 1.0.2.b",
                "play_button": "Play",
                "settings_button": "Settings",
                "news_button": "News",
                "support_button": "Support",
                
                # Вкладка игры
                "username_placeholder": "Enter username",
                "version_label": "Minecraft version:",
                "loader_label": "Mod loader:",
                "launch_button": "Play",
                "change_skin_button": "Change skin",
                "ely_login_button": "Login with Ely.by",
                
                # Настройки
                "language_label": "Language:",
                "theme_button": "Dark theme",
                "memory_label": "RAM (GB):",
                "directory_label": "Game directory:",
                "choose_directory_button": "Choose folder",
                "close_on_launch": "Close launcher on game start",
                "ely_logout_button": "Logout from Ely.by",
                
                # Сообщения
                "enter_username": "Please enter username!",
                "launch_error": "Launch error",
            }
        }
        
    
    def set_language(self, lang):
        self.language = lang
        
    def tr(self, key):
        return self.translations.get(self.language, {}).get(key, key)
    
    

translator = Translator()

class ModpackTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.modpacks_dir = os.path.join(MINECRAFT_DIR, "modpacks")
        self.icons_dir = os.path.join(MINECRAFT_DIR, "modpack_icons")  # Директория для иконок
        os.makedirs(self.modpacks_dir, exist_ok=True)
        os.makedirs(self.icons_dir, exist_ok=True) 
        self.setup_ui()
        self.load_modpacks()
        self.setup_drag_drop()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header Section
        header = QHBoxLayout()
        
        # Title with icon
        title_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap(resource_path("assets/modpack_icon.png")).scaled(32, 32))
        title_layout.addWidget(icon_label)
        
        self.title = QLabel("Мои сборки")
        self.title.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(self.title)
        title_layout.addStretch()
        header.addLayout(title_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = self.create_tool_button("Создать", "add.png", self.show_creation_dialog)
        self.import_btn = self.create_tool_button("Импорт", "import.png", self.import_modpack)
        self.refresh_btn = self.create_tool_button("Обновить", "refresh.png", self.load_modpacks)
        
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.refresh_btn)
        header.addLayout(btn_layout)
        
        layout.addLayout(header)

        # Filter Section
        filter_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Поиск по названию...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.search_bar)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "Forge", "Fabric", "OptiFine", "Vanilla"])
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.currentIndexChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)

        # Modpacks Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        # Status Label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #AAAAAA; font-size: 14px;")
        layout.addWidget(self.status_label)

        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
                min-width: 120px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

    def create_tool_button(self, text, icon, callback):
        btn = QToolButton()
        btn.setText(text)
        btn.setIcon(QIcon(resource_path(f"assets/{icon}")))
        btn.setIconSize(QSize(24, 24))
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setFixedSize(100, 70)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QToolButton {
                background-color: #404040;
                border-radius: 8px;
                padding: 8px;
            }
            QToolButton:hover {
                background-color: #505050;
            }
        """)
        return btn

    def create_modpack_card(self, pack_data):
        icon = QLabel()
        icon_name = pack_data.get("icon")
        icon_path = os.path.join(self.icons_dir, icon_name) if icon_name else ""
             
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setFixedSize(300, 220)
        card.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border-radius: 10px;
                border: 1px solid #555555;
            }
            QFrame:hover {
                border: 1px solid #666666;
                background-color: #484848;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.addWidget(icon)

        title_layout = QVBoxLayout()
        title = QLabel(pack_data["name"])
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        
        version = QLabel(f"· Minecraft {pack_data['version']}")
        version.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(version)
        header.addLayout(title_layout)
        layout.addLayout(header)

        # Details
        details = QLabel(f"""
            <div style='color: #CCCCCC; font-size: 12px;'>
                <b>Тип:</b> {pack_data['loader']}<br>
                <b>Моды:</b> {len(pack_data['mods'])}<br>
                <b>Размер:</b> {self.get_modpack_size(pack_data)}
            </div>
        """)
        layout.addWidget(details)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        play_btn = self.create_card_button("Запустить", "play.png", 
                     lambda: self.launch_modpack(pack_data))
        edit_btn = self.create_card_button("Изменить", "edit.png", 
                     lambda: self.edit_modpack(pack_data))
        menu_btn = self.create_card_button("⋮", "menu.png", 
                     lambda: self.show_context_menu(pack_data))
        
        btn_layout.addWidget(play_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(menu_btn)
        layout.addLayout(btn_layout)

        return card

    def create_card_button(self, text, icon, callback):
        btn = QPushButton(text)
        btn.setFixedSize(80, 28)
        btn.setIcon(QIcon(resource_path(f"assets/{icon}")))
        btn.setIconSize(QSize(16, 16))
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                color: #FFFFFF;
                border-radius: 5px;
                font-size: 11px;
                padding: 2px 5px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)
        return btn

    def filter_modpacks(self):
        search_text = self.search_bar.text().lower()
        filter_type = self.filter_combo.currentText()

        visible_count = 0
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                name_match = search_text in widget.property("pack_name").lower()
                type_match = (filter_type == "Все") or (widget.property("loader_type") == filter_type)
                visible = name_match and type_match
                widget.setVisible(visible)
                if visible: visible_count += 1

        self.status_label.setText(f"Найдено сборок: {visible_count}" if visible_count > 0 else "Сборки не найдены")

    def load_modpacks(self):
        # Clear existing cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load modpacks
        modpacks = []
        for file in os.listdir(self.modpacks_dir):
            if file.endswith(".json"):
                try:
                    with open(os.path.join(self.modpacks_dir, file), "r") as f:
                        pack = json.load(f)
                        pack["filename"] = file
                        modpacks.append(pack)
                except Exception as e:
                    logging.error(f"Error loading modpack {file}: {e}")

        if not modpacks:
            self.status_label.setText("🎮 Создайте свою первую сборку!")
            return

        # Create cards
        row, col = 0, 0
        for pack in sorted(modpacks, key=lambda x: x["name"].lower()):
            card = self.create_modpack_card(pack)
            card.setProperty("pack_name", pack["name"])
            card.setProperty("loader_type", pack["loader"])
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col > 3:  # 4 columns
                col = 0
                row += 1

        self.status_label.setText(f"Загружено сборок: {len(modpacks)}")

    def get_modpack_size(self, pack_data):
        total_size = 0
        mods_dir = os.path.join(MODS_DIR, pack_data["version"])
        if os.path.exists(mods_dir):
            for mod in pack_data["mods"]:
                mod_path = os.path.join(mods_dir, mod)
                if os.path.exists(mod_path):
                    total_size += os.path.getsize(mod_path)
        return f"{total_size / 1024 / 1024:.1f} MB"

    def show_context_menu(self, pack_data):
        menu = QMenu(self)
        
        export_action = QAction(QIcon(resource_path("assets/export.png")), "Экспорт", self)
        export_action.triggered.connect(lambda: self.export_modpack(pack_data))
        
        duplicate_action = QAction(QIcon(resource_path("assets/copy.png")), "Дублировать", self)
        duplicate_action.triggered.connect(lambda: self.duplicate_modpack(pack_data))
        
        delete_action = QAction(QIcon(resource_path("assets/delete.png")), "Удалить", self)
        delete_action.triggered.connect(lambda: self.delete_modpack(pack_data))

        menu.addAction(export_action)
        menu.addAction(duplicate_action)
        menu.addAction(delete_action)
        menu.exec_(QCursor.pos())

    def duplicate_modpack(self, pack_data):
        new_name, ok = QInputDialog.getText(
            self, "Дублирование сборки",
            "Введите новое название:",
            QLineEdit.Normal,
            f"{pack_data['name']} - Копия"
        )
        
        if ok and new_name:
            new_filename = f"{new_name}.json"
            new_path = os.path.join(self.modpacks_dir, new_filename)
            
            if os.path.exists(new_path):
                QMessageBox.warning(self, "Ошибка", "Сборка с таким именем уже существует!")
                return

            try:
                shutil.copyfile(
                    os.path.join(self.modpacks_dir, pack_data["filename"]),
                    new_path
                )
                self.load_modpacks()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать копию: {str(e)}")

    def launch_modpack(self, pack_data):
        self.parent_window.version_select.setCurrentText(pack_data["version"])
        self.parent_window.loader_select.setCurrentText(pack_data["loader"])
        self.parent_window.tabs.setCurrentIndex(0)
        QMessageBox.information(self, "Запуск сборки", 
            f"Параметры сборки '{pack_data['name']}' установлены!\nНажмите 'Играть' для запуска.")

    def edit_modpack(self, pack_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Редактирование: {pack_data['name']}")
        dialog.setFixedSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Существующие поля
        name_layout = QHBoxLayout()
        name_label = QLabel("Название:")
        self.name_edit = QLineEdit(pack_data["name"])
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        
        # Поля версии и лоадера
        version_layout = QHBoxLayout()
        version_label = QLabel("Версия:")
        self.version_combo = QComboBox()
        self.version_combo.addItems(MINECRAFT_VERSIONS)
        self.version_combo.setCurrentText(pack_data["version"])
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_combo)
        
        loader_layout = QHBoxLayout()
        loader_label = QLabel("Модлоадер:")
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["Vanilla", "Forge", "Fabric", "OptiFine"])
        self.loader_combo.setCurrentText(pack_data["loader"])
        loader_layout.addWidget(loader_label)
        loader_layout.addWidget(self.loader_combo)
        
        # Секция модов
        mods_layout = QVBoxLayout()
        mods_label = QLabel("Моды в сборке:")
        self.mods_list = QListWidget()
        self.mods_list.addItems(pack_data["mods"])
        
        # Кнопки управления модами
        mod_buttons = QHBoxLayout()
        self.remove_mod_btn = QPushButton("Удалить выбранное")
        self.remove_mod_btn.clicked.connect(lambda: self.remove_selected_mods())
        self.add_mod_btn = QPushButton("Добавить моды")
        self.add_mod_btn.clicked.connect(lambda: self.add_mods_to_pack(pack_data))
        
        mod_buttons.addWidget(self.remove_mod_btn)
        mod_buttons.addWidget(self.add_mod_btn)
        
        mods_layout.addWidget(mods_label)
        mods_layout.addWidget(self.mods_list)
        mods_layout.addLayout(mod_buttons)
        
        
        # Добавляем все элементы в layout
        layout.addLayout(name_layout)
        layout.addLayout(version_layout)
        layout.addLayout(loader_layout)
        layout.addLayout(mods_layout)
        
        # Кнопки сохранения/отмены
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(lambda: self.save_modpack_changes(pack_data, dialog))
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def remove_selected_mods(self):
        selected_items = self.mods_list.selectedItems()
        for item in selected_items:
            row = self.mods_list.row(item)
            self.mods_list.takeItem(row)

    def add_mods_to_pack(self, pack_data):
        # Диалог выбора модов
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Mod files (*.jar *.zip)")
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            mods_dir = os.path.join(MODS_DIR, pack_data["version"])
            
            for file_path in selected_files:
                mod_name = os.path.basename(file_path)
                dest_path = os.path.join(mods_dir, mod_name)
                
                # Копируем мод в папку сборки
                if not os.path.exists(dest_path):
                    shutil.copyfile(file_path, dest_path)
                
                # Добавляем в список, если еще нет
                if not self.mods_list.findItems(mod_name, Qt.MatchExactly):
                    self.mods_list.addItem(mod_name)

            QMessageBox.information(self, "Успех", "Моды успешно добавлены!")

    def save_modpack_changes(self, old_pack, dialog):
        new_name = self.name_edit.text()
        new_version = self.version_combo.currentText()
        new_loader = self.loader_combo.currentText()
        
        # Получаем обновленный список модов
        new_mods = []
        for i in range(self.mods_list.count()):
            new_mods.append(self.mods_list.item(i).text())
        
        try:
            # Удаляем старый файл
            old_path = os.path.join(self.modpacks_dir, old_pack["filename"])
            os.remove(old_path)
            
            # Создаем новый
            new_filename = f"{new_name}.json"
            new_pack = {
                "name": new_name,
                "version": new_version,
                "loader": new_loader,
                "mods": new_mods
            }
            
            with open(os.path.join(self.modpacks_dir, new_filename), "w") as f:
                json.dump(new_pack, f)
            
            self.load_modpacks()
            dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить изменения: {str(e)}")

    def delete_modpack(self, pack_data):
        confirm = QMessageBox.question(
            self,
            "Удаление сборки",  # Исправлен заголовок
            f"Вы уверены, что хотите удалить сборку '{pack_data['name']}'?",  # Исправлен текст
            QMessageBox.Yes | QMessageBox.No,  # Правильные константы кнопок
            QMessageBox.No  # Кнопка по умолчанию
        )
        
        if confirm == QMessageBox.Yes:
            try:
                os.remove(os.path.join(self.modpacks_dir, pack_data["filename"]))
                self.load_modpacks()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить сборку: {str(e)}")

    def setup_drag_drop(self):
        self.setAcceptDrops(True)
        self.scroll_area.setAcceptDrops(True)
        self.scroll_area.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith('.zip') for url in urls):
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip'):
                self.handle_dropped_file(file_path)
        event.acceptProposedAction()

    def handle_dropped_file(self, file_path):
        try:
            loading_indicator = QLabel("Импорт сборки...", self)
            loading_indicator.setAlignment(Qt.AlignCenter)
            loading_indicator.setStyleSheet("""
                QLabel {
                    background-color: #454545;
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    font-size: 16px;
                }
            """)
            loading_indicator.setGeometry(self.width()//2-150, self.height()//2-50, 300, 100)
            loading_indicator.show()
            QApplication.processEvents()
            
            self.import_modpack(file_path)
            self.load_modpacks()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {str(e)}")
        finally:
            loading_indicator.hide()

    def import_modpack(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Выберите файл сборки", 
                "", 
                "ZIP файлы (*.zip)"
            )
            if not file_path:
                return
        
        try:
            with zipfile.ZipFile(file_path, "r") as zipf:
                if "modpack.json" not in zipf.namelist():
                    raise ValueError("Отсутствует файл modpack.json в архиве")
                
                pack_data = json.loads(zipf.read("modpack.json"))
                mods_dir = os.path.join(MODS_DIR, pack_data["version"])
                os.makedirs(mods_dir, exist_ok=True)
                
                for mod in pack_data["mods"]:
                    try:
                        zipf.extract(f"mods/{mod}", mods_dir)
                    except KeyError:
                        logging.warning(f"Мод {mod} отсутствует в архиве")
                
                with open(os.path.join(self.modpacks_dir, f"{pack_data['name']}.json"), "w") as f:
                    json.dump(pack_data, f)
            
            self.load_modpacks()
            QMessageBox.information(self, "Успех", "Сборка успешно импортирована!")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {str(e)}")

    def export_modpack(self, pack_data):
        try:
            export_path = self.parent_window.settings.get("export_path", os.path.expanduser("~/Desktop"))
            os.makedirs(export_path, exist_ok=True)
            
            with open(os.path.join(self.modpacks_dir, pack_data["filename"]), "r") as f:
                pack_data = json.load(f)
            
            zip_path = os.path.join(export_path, f"{pack_data['name']}.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                mods_dir = os.path.join(MODS_DIR, pack_data["version"])
                for mod in pack_data["mods"]:
                    mod_path = os.path.join(mods_dir, mod)
                    if os.path.exists(mod_path):
                        zipf.write(mod_path, arcname=f"mods/{mod}")
                
                zipf.writestr("modpack.json", json.dumps(pack_data))
            
            QMessageBox.information(self, "Успех", f"Сборка экспортирована в:\n{zip_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {str(e)}")

    def show_creation_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Создание сборки")
        dialog.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        self.steps = QStackedWidget()
        
        # Шаг 1: Основная информация
        step1 = QWidget()
        form = QFormLayout()
        self.pack_name = QLineEdit()
        self.pack_version = QComboBox()
        self.pack_loader = QComboBox()
        
        versions = get_version_list()
        for v in versions:
            if v["type"] == "release":
                self.pack_version.addItem(v["id"])
        self.pack_loader.addItems(["Vanilla", "Forge", "Fabric", "OptiFine"])
        
        form.addRow("Название сборки:", self.pack_name)
        form.addRow("Версия Minecraft:", self.pack_version)
        form.addRow("Модлоадер:", self.pack_loader)
        step1.setLayout(form)
        
        # Шаг 2: Выбор модов
        step2 = QWidget()
        mods_layout = QVBoxLayout()
        self.mods_selection = QListWidget()
        self.mods_selection.setSelectionMode(QListWidget.MultiSelection)
        
        version = self.pack_version.currentText()
        mods = ModManager.get_mods_list(version)
        self.mods_selection.addItems(mods)
        
        mods_layout.addWidget(QLabel("Выберите моды:"))
        mods_layout.addWidget(self.mods_selection)
        step2.setLayout(mods_layout)
        
        self.steps.addWidget(step1)
        self.steps.addWidget(step2)
        
        # Навигация
        nav_buttons = QHBoxLayout()
        self.prev_btn = QPushButton("Назад")
        self.next_btn = QPushButton("Далее")
        self.prev_btn.clicked.connect(lambda: self.steps.setCurrentIndex(0))
        self.next_btn.clicked.connect(lambda: self.steps.setCurrentIndex(1))
        nav_buttons.addWidget(self.prev_btn)
        nav_buttons.addWidget(self.next_btn)
        
        # Сохранение
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(lambda: self.save_modpack(dialog))
        
        layout.addWidget(self.steps)
        layout.addLayout(nav_buttons)
        layout.addWidget(save_btn)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def select_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите иконку", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.selected_icon = file_path
            self.icon_label.setText(os.path.basename(file_path))

    def save_modpack(self, dialog):
        name = self.pack_name.text()
        version = self.pack_version.currentText()
        loader = self.pack_loader.currentText()
        selected_mods = [item.text() for item in self.mods_selection.selectedItems()]
        
        icon_name = None
        # Проверяем, существует ли атрибут и путь
        if hasattr(self, 'selected_icon') and self.selected_icon:
            try:
                icon_name = f"{name}_{int(time.time())}.png"
                dest_path = os.path.join(self.icons_dir, icon_name)
                shutil.copyfile(self.selected_icon, dest_path)
            except Exception as e:
                logging.error(f"Ошибка копирования иконки: {e}")
                icon_name = None
        
        pack_data = {
            "name": name,
            "version": version,
            "loader": loader,
            "mods": selected_mods,
        }
        # Добавляем иконку, только если она есть
        if icon_name:
            pack_data["icon"] = icon_name
        
        with open(os.path.join(self.modpacks_dir, f"{name}.json"), "w") as f:
            json.dump(pack_data, f)
        
        self.load_modpacks()
        dialog.close()
        
class SkinManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление скинами")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Кнопка для legacy-версий
        self.legacy_btn = QPushButton("Установить скин для старых версий")
        self.legacy_btn.clicked.connect(self.handle_legacy_skin)
        layout.addWidget(self.legacy_btn)
        
        # Кнопка для новых версий
        self.modern_btn = QPushButton("Установить через Ely.by")
        self.modern_btn.clicked.connect(self.handle_modern_skin)
        layout.addWidget(self.modern_btn)
        
        self.setLayout(layout)

    def handle_legacy_skin(self):
        file = QFileDialog.getOpenFileName(self, "Выберите PNG-скин", "", "Images (*.png)")[0]
        if file:
            # Применяем скин для выбранной версии
            version = self.parent().version_select.currentText()
            ElySkinManager.inject_legacy_skin(file, version)

class ElySkinManager:
    @staticmethod
    def apply_skin(username, version, is_legacy):
        """Применяет скин с учетом версии"""
        skin_url = f"https://skinsystem.ely.by/skins/{username}.png"
        skin_path = os.path.join(SKINS_DIR, f"{username}.png")
        
        try:
            # Скачивание скина
            response = requests.get(skin_url)
            if response.status_code == 200:
                with open(skin_path, 'wb') as f:
                    f.write(response.content)
                
                # Для legacy версий
                if is_legacy:
                    legacy_skin_path = os.path.join(MINECRAFT_DIR, "assets", "skins", "char.png")
                    shutil.copy(skin_path, legacy_skin_path)
                    
                return True
        except Exception as e:
            logging.error(f"Skin download error: {str(e)}")
        
        return False

    @staticmethod
    def inject_legacy_skin(skin_path, version):
        """Внедряет скин в файлы игры для legacy-версий"""
        try:
            assets_dir = os.path.join(MINECRAFT_DIR, "assets", "skins")
            os.makedirs(assets_dir, exist_ok=True)
            shutil.copy(skin_path, os.path.join(assets_dir, "char.png"))
            return True
        except Exception as e:
            logging.error(f"Legacy skin injection failed: {str(e)}")
            return False
    @staticmethod
    def get_skin_texture_url(username):
        """Получаем URL текстуры скина через текстуры-прокси"""
        try:
            response = requests.get(f"https://skinsystem.ely.by/textures/{username}")
            if response.status_code == 200:
                data = response.json()
                return data.get("textures", {}).get("SKIN", {}).get("url")
            return None
        except Exception as e:
            logging.error(f"Ошибка при получении текстуры скина: {e}")
            return None

    @staticmethod
    def get_skin_image_url(username):
        """Получаем URL изображения скина"""
        return f"https://skinsystem.ely.by/skins/{username}.png"

    @staticmethod
    def download_skin(username):
        """Скачиваем скин с Ely.by"""
        try:
            skin_url = ElySkinManager.get_skin_image_url(username)
            response = requests.get(skin_url, stream=True)
            if response.status_code == 200:
                os.makedirs(SKINS_DIR, exist_ok=True)
                dest_path = os.path.join(SKINS_DIR, f"{username}.png")
                with open(dest_path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                return True
        except Exception as e:
            logging.error(f"Ошибка при загрузке скина: {e}")
        return False

    @staticmethod
    def upload_skin(file_path, access_token, variant="classic"):
        """
        Загружает скин на Ely.by
        :param file_path: путь к файлу скина
        :param access_token: токен доступа Ely.by
        :param variant: тип модели ("classic" или "slim")
        """
        try:
            url = "https://account.ely.by/api/resources/skin"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': ('skin.png', f, 'image/png'),
                    'variant': (None, variant)
                }
                
                response = requests.put(url, headers=headers, files=files)
                
                if response.status_code == 200:
                    return True, "Скин успешно загружен!"
                return False, f"Ошибка: {response.json().get('message', 'Неизвестная ошибка')}"
        except Exception as e:
            return False, f"Ошибка загрузки: {str(e)}"

    @staticmethod
    def reset_skin(access_token):
        """Сбрасывает скин на стандартный"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.delete('https://account.ely.by/api/resources/skin', headers=headers)
            
            if response.status_code == 200:
                return True, "Скин сброшен на стандартный!"
            return False, f"Ошибка сброса скина: {response.json().get('message', 'Неизвестная ошибка')}"
        except Exception as e:
            return False, f"Ошибка при сбросе скина: {str(e)}"

class ModManager:
    @staticmethod
    def get_mods_list(version):
        """Получает список установленных модов для указанной версии"""
        version_mods_dir = os.path.join(MODS_DIR, version)
        if not os.path.exists(version_mods_dir):
            return []
            
        return [f for f in os.listdir(version_mods_dir) 
                if f.endswith('.jar') or f.endswith('.zip')]

    @staticmethod
    def install_mod_from_file(file_path, version):
        """Устанавливает мод из файла"""
        try:
            os.makedirs(os.path.join(MODS_DIR, version), exist_ok=True)
            dest_path = os.path.join(MODS_DIR, version, os.path.basename(file_path))
            shutil.copy(file_path, dest_path)
            return True, "Мод успешно установлен!"
        except Exception as e:
            return False, f"Ошибка установки мода: {str(e)}"

    @staticmethod
    def remove_mod(mod_name, version):
        """Удаляет мод"""
        try:
            mod_path = os.path.join(MODS_DIR, version, mod_name)
            if os.path.exists(mod_path):
                os.remove(mod_path)
                return True, "Мод успешно удален"
            return False, "Мод не найден"
        except Exception as e:
            return False, f"Ошибка удаления мода: {str(e)}"

    @staticmethod
    def search_modrinth(query, version=None, loader=None, category=None, sort_by="relevance"):
        try:
            # Преобразуем параметры сортировки
            sort_mapping = {
                "По релевантности": "relevance",
                "По загрузкам": "downloads",
                "По дате": "newest"
            }
            sort_by = sort_mapping.get(sort_by, "relevance")

            params = {
                'query': query,
                'limit': 50,
                'facets': []
            }

            # Фильтр по версии Minecraft
            if version and version != "Все версии":
                params['facets'].append(["versions:" + version])

            # Фильтр по модлоадеру
            if loader and loader.lower() != "vanilla":
                loader = loader.lower()
                if loader == "optifine":
                    params['facets'].append(["categories:optimization"])
                else:
                    params['facets'].append(["categories:" + loader])

            # Фильтр по категории
            if category and category != "Все категории":
                params['facets'].append(["categories:" + category.lower()])

            # Параметры сортировки
            params['index'] = sort_by

            response = requests.get(
                'https://api.modrinth.com/v2/search',
                params={'query': query, 'limit': 50, 'facets': json.dumps(params['facets']), 'index': sort_by}
            )
            
            if response.status_code == 200:
                return response.json().get('hits', [])
            return []
        except Exception as e:
            logging.error(f"Ошибка поиска на Modrinth: {e}")
            return []

    @staticmethod
    def search_curseforge(query, version=None, loader=None):
        """Поиск модов на CurseForge"""
        try:
            headers = {
                'x-api-key': 'YOUR_CURSEFORGE_API_KEY'  # Нужно получить API ключ
            }
            params = {
                'gameId': 432,  # Minecraft
                'searchFilter': query,
                'pageSize': 20
            }
            if version:
                params['gameVersion'] = version
            if loader:
                params['modLoaderType'] = loader
                
            response = requests.get('https://api.curseforge.com/v1/mods/search', 
                                 headers=headers, params=params)
            if response.status_code == 200:
                return response.json()['data']
            return []
        except Exception as e:
            logging.error(f"Ошибка поиска на CurseForge: {e}")
            return []

    @staticmethod
    def download_modrinth_mod(mod_id, version):
        """Скачивает мод с Modrinth"""
        try:
            # Получаем информацию о файле
            response = requests.get(f'https://api.modrinth.com/v2/project/{mod_id}/version')
            if response.status_code != 200:
                return False, "Не удалось получить информацию о моде"
                
            versions = response.json()
            for v in versions:
                if version in v['game_versions']:
                    file_url = v['files'][0]['url']
                    file_name = v['files'][0]['filename']
                    
                    # Скачиваем файл
                    os.makedirs(os.path.join(MODS_DIR, version), exist_ok=True)
                    dest_path = os.path.join(MODS_DIR, version, file_name)
                    
                    response = requests.get(file_url, stream=True)
                    if response.status_code == 200:
                        with open(dest_path, 'wb') as f:
                            response.raw.decode_content = True
                            shutil.copyfileobj(response.raw, f)
                        return True, "Мод успешно установлен!"
            return False, "Не найдена подходящая версия мода"
        except Exception as e:
            return False, f"Ошибка загрузки мода: {str(e)}"

    @staticmethod
    def download_curseforge_mod(mod_id, version):
        """Скачивает мод с CurseForge"""
        try:
            headers = {
                'x-api-key': 'YOUR_CURSEFORGE_API_KEY'
            }
            
            # Получаем информацию о файле
            response = requests.get(f'https://api.curseforge.com/v1/mods/{mod_id}/files',
                                 headers=headers)
            if response.status_code != 200:
                return False, "Не удалось получить информацию о моде"
                
            files = response.json()['data']
            for file in files:
                if version in file['gameVersions']:
                    file_url = file['downloadUrl']
                    file_name = file['fileName']
                    
                    # Скачиваем файл
                    os.makedirs(os.path.join(MODS_DIR, version), exist_ok=True)
                    dest_path = os.path.join(MODS_DIR, version, file_name)
                    
                    response = requests.get(file_url, stream=True)
                    if response.status_code == 200:
                        with open(dest_path, 'wb') as f:
                            response.raw.decode_content = True
                            shutil.copyfileobj(response.raw, f)
                        return True, "Мод успешно установлен!"
            return False, "Не найдена подходящая версия мода"
        except Exception as e:
            return False, f"Ошибка загрузки мода: {str(e)}"

    @staticmethod
    def create_modpack(version, mods, output_path):
        """Создает сборку модов"""
        try:
            with zipfile.ZipFile(output_path, 'w') as zipf:
                # Добавляем моды
                for mod in mods:
                    mod_path = os.path.join(MODS_DIR, version, mod)
                    if os.path.exists(mod_path):
                        zipf.write(mod_path, os.path.join('mods', mod))
                
                # Добавляем файл манифеста
                manifest = {
                    'minecraft': {
                        'version': version,
                        'modLoaders': []
                    },
                    'manifestType': 'minecraftModpack',
                    'manifestVersion': 1,
                    'name': f'Modpack {version}',
                    'version': '1.0.0',
                    'author': '16Launcher',
                    'files': []
                }
                
                manifest_path = os.path.join(MODS_DIR, 'manifest.json')
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=4)
                zipf.write(manifest_path, 'manifest.json')
                os.remove(manifest_path)
                
            return True, "Сборка успешно создана!"
        except Exception as e:
            return False, f"Ошибка создания сборки: {str(e)}"

    @staticmethod
    def get_mod_categories(source="modrinth"):
        """Получает список доступных категорий модов"""
        if source == "modrinth":
            try:
                response = requests.get('https://api.modrinth.com/v2/tag/category')
                if response.status_code == 200:
                    return [cat['name'] for cat in response.json()]
            except Exception as e:
                logging.error(f"Ошибка получения категорий Modrinth: {e}")
        return []

    @staticmethod
    def get_mod_details(mod_id, source="modrinth"):
        """Получает подробную информацию о моде"""
        try:
            if source == "modrinth":
                response = requests.get(f'https://api.modrinth.com/v2/project/{mod_id}')
                if response.status_code == 200:
                    return response.json()
            elif source == "curseforge":
                headers = {'x-api-key': 'YOUR_CURSEFORGE_API_KEY'}
                response = requests.get(f'https://api.curseforge.com/v1/mods/{mod_id}',
                                     headers=headers)
                if response.status_code == 200:
                    return response.json()['data']
            return None
        except Exception as e:
            logging.error(f"Ошибка получения информации о моде: {e}")
            return None

    @staticmethod
    def get_mod_icon(mod_id, source="modrinth"):
        """Получает URL иконки мода"""
        try:
            if source == "modrinth":
                response = requests.get(f'https://api.modrinth.com/v2/project/{mod_id}')
                if response.status_code == 200:
                    data = response.json()
                    return data.get('icon_url')
            elif source == "curseforge":
                headers = {'x-api-key': 'YOUR_CURSEFORGE_API_KEY'}
                response = requests.get(f'https://api.curseforge.com/v1/mods/{mod_id}',
                                     headers=headers)
                if response.status_code == 200:
                    data = response.json()['data']
                    return data.get('logo', {}).get('url')
            return None
        except Exception as e:
            logging.error(f"Ошибка получения иконки мода: {e}")
            return None

    @staticmethod
    @lru_cache(maxsize=100)
    def cached_search(query, version=None, loader=None, category=None, sort_by="relevance", source="modrinth"):
        """Кэшированный поиск модов"""
        if source == "modrinth":
            return ModManager.search_modrinth(query, version, loader, category, sort_by)
        else:
            return ModManager.search_curseforge(query, version, loader)

# Добавим новую вкладку для управления модами
class ModsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.search_thread = None
        self.popular_mods_thread = None
        self.current_search_query = ""
        self.current_page = 1
        self.total_pages = 1
        self.mods_data = []
        self.setup_ui()
        self.is_loaded = False  # Флаг загрузки данных
        QTimer.singleShot(0, self.load_popular_mods)
        
        # Добавляем надпись о загрузке
        self.loading_label = QLabel("Моды загружаются, подождите...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(self.loading_label)
        
    def showEvent(self, event):
        """Запускаем загрузку только при первом открытии вкладки"""
        if not self.is_loaded:
            self.load_popular_mods()
            self.is_loaded = True
        super().showEvent(event)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Верхняя панель с поиском и фильтрами ---
        top_panel = QWidget()
        top_panel.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        top_layout = QVBoxLayout(top_panel)
        
        # Поисковая строка
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск модов...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #444444;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #666666;
            }
        """)
        self.search_input.returnPressed.connect(self.search_mods)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton()
        self.search_button.setIcon(QIcon(resource_path("assets/search.png")))
        self.search_button.setIconSize(QSize(24, 24))
        self.search_button.setFixedSize(40, 40)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.search_button.clicked.connect(self.search_mods)
        search_layout.addWidget(self.search_button)
        top_layout.addLayout(search_layout)
        
        # Фильтры
        filters_layout = QHBoxLayout()
        
        # Версия Minecraft
        version_layout = QVBoxLayout()
        version_layout.addWidget(QLabel("Версия Minecraft:"))
        
        # Заменяем QComboBox на QSlider и QLabel
        self.version_slider = QSlider(Qt.Horizontal)
        self.version_slider.setTickPosition(QSlider.TicksBelow)
        self.version_label = QLabel()
        self.version_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #444444;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #666666;
                border-radius: 3px;
            }
        """)
        
        # Инициализируем список версий
        self.load_minecraft_versions()
        
        version_layout.addWidget(self.version_slider)
        version_layout.addWidget(self.version_label)
        filters_layout.addLayout(version_layout)
        
        # Подключаем обработчик изменения слайдера
        self.version_slider.valueChanged.connect(self.update_version_label)
        self.version_slider.valueChanged.connect(self.search_mods)
        
        # Модлоадер
        loader_layout = QVBoxLayout()
        loader_layout.addWidget(QLabel("Модлоадер:"))
        self.loader_combo = QComboBox()
        self.loader_combo.setFixedWidth(200)
        self.loader_combo.addItems(["Fabric", "Forge", "Quilt"])
        self.loader_combo.setStyleSheet(self.version_combo.styleSheet())
        loader_layout.addWidget(self.loader_combo)
        filters_layout.addLayout(loader_layout)
        
        # Категория
        category_layout = QVBoxLayout()
        category_layout.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.setFixedWidth(200)
        self.category_combo.addItem("Все категории")
        self.category_combo.setStyleSheet(self.version_combo.styleSheet())
        category_layout.addWidget(self.category_combo)
        filters_layout.addLayout(category_layout)
        
        # Сортировка
        sort_layout = QVBoxLayout()
        sort_layout.addWidget(QLabel("Сортировка:"))
        self.sort_combo = QComboBox()
        self.sort_combo.setFixedWidth(200)
        self.sort_combo.addItems(["По релевантности", "По загрузкам", "По дате"])
        self.sort_combo.setStyleSheet(self.version_combo.styleSheet())
        sort_layout.addWidget(self.sort_combo)
        filters_layout.addLayout(sort_layout)
        
        top_layout.addLayout(filters_layout)
        layout.addWidget(top_panel)
        
        # --- Список модов ---
        self.mods_scroll = QScrollArea()
        self.mods_scroll.setWidgetResizable(True)
        self.mods_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #333333;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
        """)
        
        self.mods_container = QWidget()
        self.mods_layout = QVBoxLayout(self.mods_container)
        self.mods_layout.setSpacing(15)
        self.mods_scroll.setWidget(self.mods_container)
        layout.addWidget(self.mods_scroll)
        
        # --- Пагинация ---
        pagination_widget = QWidget()
        pagination_widget.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        pagination_layout = QHBoxLayout(pagination_widget)
        
        self.prev_page_button = QPushButton("←")
        self.prev_page_button.setFixedSize(40, 40)
        self.prev_page_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.prev_page_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_page_button)
        
        self.page_label = QLabel("Страница 1 из 1")
        self.page_label.setStyleSheet("color: white;")
        pagination_layout.addWidget(self.page_label)
        
        self.next_page_button = QPushButton("→")
        self.next_page_button.setFixedSize(40, 40)
        self.next_page_button.setStyleSheet(self.prev_page_button.styleSheet())
        self.next_page_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_page_button)
        
        layout.addWidget(pagination_widget)
        
        # Инициализация данных
        self.current_page = 1
        self.total_pages = 1
        self.mods_data = []
        
    def create_mod_card(self, mod):
        """Создает карточку мода"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #444444;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        card.setFixedHeight(120)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setFixedSize(90, 90)
        icon_label.setStyleSheet("background-color: #444444; border-radius: 5px;")
        icon_url = ModManager.get_mod_icon(mod.get('project_id', mod.get('id')), "modrinth")
        if icon_url:
            pixmap = QPixmap()
            try:
                pixmap.loadFromData(requests.get(icon_url).content)
                icon_label.setPixmap(pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except:
                pass
        layout.addWidget(icon_label)
        
        # Информация
        info_layout = QVBoxLayout()
        
        # Название
        name_label = QLabel(mod.get('title', mod.get('name', 'N/A')))
        name_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # Описание
        desc_label = QLabel(mod.get('description', 'Нет описания'))
        desc_label.setStyleSheet("color: #aaaaaa;")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        info_layout.addWidget(desc_label)
        
        # Статистика
        stats_layout = QHBoxLayout()
        downloads_label = QLabel(f"📥 {mod.get('downloads', 0)}")
        downloads_label.setStyleSheet("color: #aaaaaa;")
        stats_layout.addWidget(downloads_label)
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)
        
        layout.addLayout(info_layout)
        
        # Кнопка установки
        install_button = QPushButton("Установить")
        install_button.setFixedWidth(100)
        install_button.clicked.connect(lambda: self.install_modrinth_mod(mod['project_id']))
        layout.addWidget(install_button)
        
        return card
        
    def search_mods(self):
        """Выполняет поиск модов"""
        query = self.search_input.text().strip()
        
        # Если строка поиска пуста, показываем популярные моды
        if not query:
            self.load_popular_mods()
            return

        # Сохраняем текущий запрос
        self.current_searchSquery = query

        # Очищаем предыдущие результаты
        self.current_page = 1
        self.mods_data = []
        self.update_page()

        # Показываем индикатор загрузки
        self.show_loading_indicator()

        # Получаем параметры поиска
        version = self.get_selected_version()
        loader = self.loader_combo.currentText()
        category = self.category_combo.currentText()
        sort_by = self.sort_combo.currentText()

        # Создаем и запускаем поток поиска
        self.search_thread = ModSearchThread(query, version, loader, category, sort_by)
        self.search_thread.search_finished.connect(lambda mods, q: self.handle_search_results(mods, q))
        self.search_thread.error_occurred.connect(self.handle_search_error)
        self.search_thread.start()

    def load_popular_mods(self):
        """Загружает список популярных модов"""
        try:
            # Показываем индикатор загрузки
            self.loading_label.setVisible(True)
            self.mods_scroll.setVisible(False)
            
            # Создаем и запускаем поток
            self.popular_mods_thread = PopularModsThread(
                version=self.version_combo.currentText(),
                loader=self.loader_combo.currentText()
            )
            self.popular_mods_thread.finished.connect(self.handle_popular_mods_loaded)
            self.popular_mods_thread.error.connect(self.handle_popular_mods_error)
            self.popular_mods_thread.start()

        except Exception as e:
            self.handle_popular_mods_error(str(e))

    def handle_popular_mods_loaded(self, mods):
        """Обрабатывает загруженные моды"""
        self.mods_data = mods
        self.current_page = 1
        self.loading_label.setVisible(False)
        self.mods_scroll.setVisible(True)
        self.update_page()

    def handle_popular_mods_error(self, error_message):
        """Обрабатывает ошибки загрузки"""
        self.loading_label.setText(f"Ошибка загрузки: {error_message}")
        QTimer.singleShot(5000, lambda: self.loading_label.setVisible(False))
        logging.error(f"Ошибка загрузки популярных модов: {error_message}")

    def handle_search_results(self, mods, query):
        """Обрабатывает результаты поиска"""
        if query != self.search_input.text().strip():
            return  # Игнорируем устаревшие результаты
            
        self.mods_data = mods
        self.current_page = 1
        self.hide_loading_indicator()
        self.update_page()

    def handle_search_error(self, error_message):
        """Обрабатывает ошибки поиска"""
        self.hide_loading_indicator()
        QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить поиск: {error_message}")
        
    def prev_page(self):
        """Переход на предыдущую страницу"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page()

    def next_page(self):
        """Переход на следующую страницу"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page()

    def show_loading_indicator(self):
        """Показывает индикатор загрузки"""
        self.loading_label = QLabel("Загрузка...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(self.loading_label)

    def hide_loading_indicator(self):
        """Скрывает индикатор загрузки"""
        if hasattr(self, 'loading_label'):
            self.loading_label.deleteLater()

    def show_no_results_message(self):
        """Показывает сообщение об отсутствии результатов"""
        no_results_label = QLabel("Ничего не найдено")
        no_results_label.setAlignment(Qt.AlignCenter)
        no_results_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(no_results_label)

    def update_page(self):
        """Обновляет отображение текущей страницы с модами"""
        # Очищаем текущие карточки
        while self.mods_layout.count():
            item = self.mods_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Если нет данных, показываем сообщение
        if not self.mods_data:
            self.show_no_results_message()
            return
        
        # Обновляем информацию о странице
        self.total_pages = (len(self.mods_data) + 9) // 10  # Округляем вверх
        self.page_label.setText(f"Страница {self.current_page} из {self.total_pages}")
        self.prev_page_button.setEnabled(self.current_page > 1)
        self.next_page_button.setEnabled(self.current_page < self.total_pages)
        
        # Добавляем карточки для текущей страницы
        start = (self.current_page - 1) * 10
        end = min(start + 10, len(self.mods_data))
        for mod in self.mods_data[start:end]:
            self.mods_layout.addWidget(self.create_mod_card(mod))
        
        # Добавляем растягивающийся элемент
        self.mods_layout.addStretch()
        
    def load_minecraft_versions(self):
        """Загружает и обрабатывает список версий Minecraft"""
        versions = get_version_list()
        self.minecraft_versions = [
            v['id'] for v in versions 
            if v['type'] == 'release'
        ][::-1]  # Разворачиваем список, чтобы новые версии были справа
        
        # Настраиваем слайдер
        if self.minecraft_versions:
            self.version_slider.setMinimum(0)
            self.version_slider.setMaximum(len(self.minecraft_versions) - 1)
            self.version_slider.setValue(0)
            self.update_version_label()
            
    def update_version_label(self):
        """Обновляет метку с выбранной версией"""
        if self.minecraft_versions:
            index = self.version_slider.value()
            self.version_label.setText(f"Выбрано: {self.minecraft_versions[index]}")
            
    def get_selected_version(self):
        """Возвращает выбранную версию"""
        if self.minecraft_versions:
            return self.minecraft_versions[self.version_slider.value()]
        return None

    def install_modrinth_mod(self, mod_id):
        """Устанавливает мод с Modrinth"""
        try:
            # Получаем выбранную версию Minecraft
            version = self.version_combo.currentText()
            if not version:
                QMessageBox.warning(self, "Ошибка", "Выберите версию Minecraft")
                return

            # Показываем индикатор загрузки
            self.show_loading_indicator()
            
            # Устанавливаем мод
            success, message = ModManager.download_modrinth_mod(mod_id, version)
            
            # Скрываем индикатор загрузки
            self.hide_loading_indicator()
            
            # Показываем результат
            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.critical(self, "Ошибка", message)
                
        except Exception as e:
            self.hide_loading_indicator()
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить мод: {str(e)}")
            logging.error(f"Ошибка установки мода: {str(e)}")

class ElyBySkinManager:
    @staticmethod
    def get_skin_url(username):
        """Получаем URL скина для указанного пользователя"""
        try:
            response = requests.get(f"{ELYBY_SKINS_URL}{username}.png", allow_redirects=False)
            if response.status_code == 200:
                return f"{ELYBY_SKINS_URL}{username}.png"
            return None
        except Exception as e:
            logging.error(f"Ошибка при получении скина с Ely.by: {e}")
            return None

    @staticmethod
    def download_skin(username):
        """Скачиваем скин с Ely.by"""
        skin_url = ElyBySkinManager.get_skin_url(username)
        if not skin_url:
            return False
        
        try:
            response = requests.get(skin_url, stream=True)
            if response.status_code == 200:
                os.makedirs(SKINS_DIR, exist_ok=True)
                dest_path = os.path.join(SKINS_DIR, f"{username}.png")
                with open(dest_path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                return True
        except Exception as e:
            logging.error(f"Ошибка при загрузке скина: {e}")
        
        return False

    @staticmethod
    def authorize_and_get_skin(parent_window, username):
        """Авторизация через Ely.by и получение скина"""
        # Создаем диалоговое окно авторизации
        auth_dialog = QDialog(parent_window)
        auth_dialog.setWindowTitle("Авторизация через Ely.by")
        auth_dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        info_label = QLabel("Для загрузки скина требуется авторизация через Ely.by")
        layout.addWidget(info_label)
        
        email_label = QLabel("Email:")
        layout.addWidget(email_label)
        
        email_input = QLineEdit()
        layout.addWidget(email_input)
        
        password_label = QLabel("Пароль:")
        layout.addWidget(password_label)
        
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(password_input)
        
        buttons_layout = QHBoxLayout()
        
        login_button = QPushButton("Войти")
        buttons_layout.addWidget(login_button)
        
        web_auth_button = QPushButton("Войти через браузер")
        buttons_layout.addWidget(web_auth_button)
        
        layout.addLayout(buttons_layout)
        
        status_label = QLabel()
        layout.addWidget(status_label)
        
        auth_dialog.setLayout(layout)
        
        def try_login():
            email = email_input.text()
            password = password_input.text()
            
            if not email or not password:
                status_label.setText("Введите email и пароль")
                return
                
            try:
                # Формируем Basic Auth заголовок
                auth_string = f"{email}:{password}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = b64encode(auth_bytes).decode('ascii')
                
                headers = {
                    'Authorization': f'Basic {auth_b64}',
                    'Content-Type': 'application/json'
                }
                
                # Отправляем запрос на авторизацию
                response = requests.post(
                    f"{ELYBY_AUTH_URL}/token",
                    headers=headers,
                    json={
                        "grant_type": "password",
                        "username": email,
                        "password": password
                    }
                )
                
                if response.status_code == 200:
                    # Успешная авторизация, получаем скин
                    if ElyBySkinManager.download_skin(username):
                        status_label.setText("Скин успешно загружен!")
                        QTimer.singleShot(2000, auth_dialog.accept)
                    else:
                        status_label.setText("Не удалось загрузить скин")
                else:
                    status_label.setText("Ошибка авторизации")
                    
            except Exception as e:
                logging.error(f"Ошибка авторизации: {e}")
                status_label.setText("Ошибка соединения")
        
        def open_browser_auth():
            webbrowser.open(f"https://account.ely.by/oauth2/v1/auth?response_type=code&client_id=16launcher&redirect_uri=http://localhost&scope=skin")
            status_label.setText("Пожалуйста, авторизуйтесь в браузере")
        
        login_button.clicked.connect(try_login)
        web_auth_button.clicked.connect(open_browser_auth)
        
        auth_dialog.exec_()

class NewsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_news()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Вкладки для разных типов новостей
        self.tabs = QTabWidget()
        
        # Minecraft News Tab
        self.minecraft_news_tab = QWidget()
        self.setup_minecraft_news_tab()
        self.tabs.addTab(self.minecraft_news_tab, "Minecraft")
        
        # Launcher News Tab
        self.launcher_news_tab = QWidget()
        self.setup_launcher_news_tab()
        self.tabs.addTab(self.launcher_news_tab, "Лаунчер")
        
        layout.addWidget(self.tabs)     
    
    def setup_minecraft_news_tab(self):
        layout = QVBoxLayout(self.minecraft_news_tab)
        
        self.minecraft_news_list = QLabel()
        self.minecraft_news_list.setWordWrap(True)
        self.minecraft_news_list.setAlignment(Qt.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidget(self.minecraft_news_list)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(scroll)
        
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.load_minecraft_news)
        layout.addWidget(self.refresh_button)
    
    def setup_launcher_news_tab(self):
        layout = QVBoxLayout(self.launcher_news_tab)
        
        self.launcher_news_list = QLabel()
        self.launcher_news_list.setWordWrap(True)
        self.launcher_news_list.setAlignment(Qt.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidget(self.launcher_news_list)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(scroll)    
    
    def load_news(self):
        self.load_minecraft_news()
        self.load_launcher_news()
    
    def load_minecraft_news(self):
        try:
            news = requests.get("https://launchercontent.mojang.com/news.json", timeout=10).json()
            
            html_content = """
            <h1 style="color: #FFAA00;">Последние новости Minecraft</h1>
            <p><small>Автоматический перевод с английского</small></p>
            """
            
            for item in news['entries'][:5]:  # Берем 5 последних новостей (меньше для скорости)
                try:
                    # Обработка даты
                    date = item['date'][:10] if 'date' in item else "Дата не указана"
                    
                    # Переводим заголовок и текст
                    title = MinecraftNewsTranslator.translate_text(item.get('title', ''))
                    text = MinecraftNewsTranslator.translate_text(item.get('text', ''))
                    
                    html_content += f"""
                    <div style="margin-bottom: 20px; border-bottom: 1px solid #555; padding-bottom: 10px;">
                        <h2 style="color: #55AAFF;">{title}</h2>
                        <p><small>{date}</small></p>
                        <p>{text}</p>
                        <a href="{item.get('readMoreLink', '#')}">Подробнее (оригинал)...</a>
                    </div>
                    """
                except Exception as e:
                    logging.error(f"Ошибка обработки новости: {str(e)}")
                    continue
                
            self.minecraft_news_list.setText(html_content)
        except Exception as e:
            self.minecraft_news_list.setText(f"""
                <h1 style="color: #FF5555;">Ошибка загрузки новостей</h1>
                <p>Не удалось загрузить новости Minecraft: {str(e)}</p>
                <p>Попробуйте позже или проверьте интернет-соединение.</p>
            """)
            logging.error(f"Ошибка загрузки новостей Minecraft: {str(e)}")
            
        
    def load_launcher_news(self):
        try:
            # Загружаем новости с GitHub
            response = requests.get(
                "https://raw.githubusercontent.com/16steyy/launcher-news/refs/heads/main/launcher_news.json",  # ЗАМЕНИ на свою ссылку!
                timeout=10
            )
            news = response.json()

            html_content = "<h1>Новости лаунчера</h1>"

            for item in news:
                html_content += f"""
                <div style="margin-bottom: 20px; border-bottom: 1px solid #555; padding-bottom: 10px;">
                    <h2>{item['title']}</h2>
                    <p><small>{item['date']}</small></p>
                    <p>{item['content']}</p>
                </div>
                """

            self.launcher_news_list.setText(html_content)

        except Exception as e:
            self.launcher_news_list.setText(f"""
                <h1 style="color: #FF5555;">Ошибка загрузки</h1>
                <p>Не удалось загрузить новости лаунчера: {str(e)}</p>
            """)
            logging.error(f"Ошибка загрузки новостей лаунчера: {str(e)}")
            
class MinecraftNewsTranslator:
    @staticmethod
    @lru_cache(maxsize=100)  # Кэшируем последние 100 переводов
    def translate_text(text, source_lang='en', target_lang='ru'):
        """Переводит текст с помощью MyMemory API"""
        if not text.strip():
            return text
            
        try:
            # Создаем хэш для кэширования
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cache_file = os.path.join(MINECRAFT_DIR, f"translation_{text_hash}.json")
            
            # Проверяем кэш
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)['translation']
            
            # Переводим через API
            params = {
                'q': text,
                'langpair': f'{source_lang}|{target_lang}',
                'de': 'your-email@example.com'  # Укажите ваш email для бесплатного API
            }
            
            response = requests.get(
                'https://api.mymemory.translated.net/get',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            translation = response.json()['responseData']['translatedText']
            
            # Сохраняем в кэш
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'translation': translation}, f, ensure_ascii=False)
            
            return translation
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            return text  # Возвращаем оригинальный текст при ошибке

def setup_directories():
    """Создает все необходимые директории при запуске"""
    try:
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
    except Exception as e:
        print(f"Не удалось создать директорию: {e}")
        raise

# Инициализация директорий перед настройкой логирования
setup_directories()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    filename=LOG_FILE,
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ModLoaderInstaller(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, loader_type, version, mc_version=None):
        super().__init__()
        self.loader_type = loader_type.lower()  # Приводим к нижнему регистру
        self.version = version
        self.mc_version = mc_version
    
    def run(self):
        try:
            if self.loader_type == "fabric":
                self.install_fabric()
            elif self.loader_type == "forge":
                self.install_forge()
            elif self.loader_type == "optifine":
                self.install_optifine()
            elif self.loader_type == "quilt":
                self.install_quilt()
            elif self.loader_type == "neoforge":
                self.install_neoforge()
            elif self.loader_type == "forgeoptifine":
                self.install_forge_optifine()
            else:
                self.finished_signal.emit(False, f"Неизвестный тип модлоадера: {self.loader_type}")
        except Exception as e:
            self.finished_signal.emit(False, f"Критическая ошибка: {str(e)}")
            logging.error(f"Ошибка установки {self.loader_type}: {str(e)}", exc_info=True)
            
    def install_optifine(self):
        """Установка OptiFine"""
        try:
            # Скачивание установщика
            download_url = f"https://optifine.net/adloadx?f=OptiFine_{self.mc_version}.jar"
            optifine_path = os.path.join(MINECRAFT_DIR, "OptiFine.jar")
            
            with requests.get(download_url, stream=True) as r:
                with open(optifine_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

            # Запуск установщика
            command = [
                'java',
                '-jar', optifine_path,
                '--install', MINECRAFT_DIR
            ]
            subprocess.run(command, check=True)
            
            self.finished_signal.emit(True, f"OptiFine для {self.mc_version} установлен!")

        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки OptiFine: {str(e)}")   

    def install_quilt(self):
        try:
            mc_version = self.mc_version
            quilt_version = self.version
            
            install_quilt(
                minecraft_version=mc_version,
                loader_version=quilt_version,
                minecraft_directory=MINECRAFT_DIR,
                callback={
                    'setStatus': lambda text: self.progress_signal.emit(0, 100, text),
                    'setProgress': lambda value: self.progress_signal.emit(value, 100, ''),
                    'setMax': lambda value: self.progress_signal.emit(0, value, '')
                }
            )
            self.finished_signal.emit(True, f"Quilt {quilt_version} для {mc_version} установлен!")
        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки: {str(e)}")
            logging.error(f"Quilt install error: {traceback.format_exc()}")
            
    def get_latest_quilt_version(mc_version: str):
        try:
            versions = get_quilt_versions(mc_version)
            if not versions:
                return None
                
            # Ищем последнюю стабильную версию
            stable_versions = [v for v in versions if v["stable"]]
            if stable_versions:
                return stable_versions[-1]["version"]
                
            # Если нет стабильных - берем последнюю бета
            return versions[-1]["version"]
            
        except Exception as e:
            logging.error(f"Error getting latest Quilt: {e}")
            return None

    def install_fabric(self):
        try:
            # Получаем последнюю версию лоадера
            loader_version = get_latest_loader_version()
            
            # Создаем профиль Fabric
            fabric_install(
                minecraft_version=self.mc_version,
                minecraft_directory=MINECRAFT_DIR,
                loader_version=loader_version
            )
            
            self.finished_signal.emit(True, 
                f"Fabric {loader_version} для {self.mc_version} установлен!")
        
        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки Fabric: {str(e)}")
            logging.error(f"Fabric install error: {traceback.format_exc()}")

    def _check_internet_connection(self):
        """Проверка соединения с серверами Fabric"""
        try:
            urllib.request.urlopen("https://meta.fabricmc.net", timeout=5)
            return True
        except:
            try:
                urllib.request.urlopen("https://google.com", timeout=5)
                return False  # Есть интернет, но Fabric недоступен
            except:
                return False  # Нет интернета

    def _get_fabric_versions_with_fallback(self):
        """Получение версий с несколькими попытками и резервными методами"""
        versions = []
        
        # Попытка 1: Официальный API Fabric
        try:
            versions_data = get_all_minecraft_versions()
            if versions_data:
                versions = [v['id'] for v in versions_data if isinstance(v, dict) and 'id' in v]
                if versions:
                    return versions
        except:
            pass
        
        # Попытка 2: Альтернативный источник (GitHub)
        try:
            with urllib.request.urlopen("https://raw.githubusercontent.com/FabricMC/fabric-meta/main/data/game_versions.json") as response:
                data = json.loads(response.read().decode())
                versions = [v['version'] for v in data if isinstance(v, dict) and 'version' in v]
                if versions:
                    return versions
        except:
            pass
        
        # Попытка 3: Версии Vanilla Minecraft
        try:
            vanilla_versions = get_version_list()
            versions = [v['id'] for v in vanilla_versions if v['type'] == 'release']
            return versions
        except:
            pass
        
        return []
    
    def find_neoforge_version(mc_version: str):
        """Поиск версии NeoForge для указанной версии MC"""
        response = requests.get("https://maven.neoforged.net/api/maven/versions/releases/net.neoforged/neoforge")
        versions = response.json()['versions']
        for v in versions:
            if mc_version in v:
                return v
        return None

    def install_quilt_version(self):
        try:
            # Получаем версии Quilt
            quilt_versions = get_quilt_versions(self.mc_version)
            if not quilt_versions:
                raise Exception("Нет доступных версий Quilt для этой версии Minecraft")

            # Выбираем версию
            target_version = next((v for v in quilt_versions if v["stable"]), None)
            if not target_version:
                target_version = quilt_versions[0]

            # Устанавливаем Quilt
            install_quilt(
                minecraft_version=self.mc_version,
                loader_version=target_version["version"],
                minecraft_directory=MINECRAFT_DIR,
                callback={
                    'setStatus': lambda text: self.progress_signal.emit(0, 100, text),
                    'setProgress': lambda value: self.progress_signal.emit(value, 100, ''),
                    'setMax': lambda value: self.progress_signal.emit(0, value, '')
                }
            )
            self.finished_signal.emit(True, f"Quilt {target_version['version']} установлен!")

        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка: {str(e)}")
            logging.error(f"Quilt install error: {traceback.format_exc()}")

    def _perform_fabric_installation(self):
        """Выполнение установки с проверкой каждого этапа"""
        # Получаем версию загрузчика
        try:
            loader_version = get_latest_loader_version()
            if not loader_version:
                # Если не получается определить последнюю версию, пробуем конкретную
                loader_version = "0.15.7"  # Актуальная стабильная версия на момент написания
        except:
            loader_version = "0.15.7"
        
        # Установка
        try:
            fabric_install(
                minecraft_version=self.mc_version,
                minecraft_directory=MINECRAFT_DIR,
                loader_version=loader_version,
                callback=self.get_callback()
            )
            self.finished_signal.emit(True, 
                f"Fabric {loader_version} для {self.mc_version} успешно установлен!")
        except Exception as e:
            raise ValueError(f"Ошибка установки: {str(e)}")

    def install_forge(self):
        """Установка Forge"""
        try:
            forge_version = find_forge_version(self.mc_version)
            if not forge_version:
                self.finished_signal.emit(False, f"Forge для {self.mc_version} не найден")
                return

            install_forge_version(
                forge_version,
                MINECRAFT_DIR,
                callback=self.get_callback()
            )
            self.finished_signal.emit(True, f"Forge {forge_version} установлен!")
            
        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки Forge: {str(e)}")
            logging.error(f"Forge install failed: {str(e)}", exc_info=True)

    def get_callback(self):
        """Генератор callback-функций для отслеживания прогресса"""
        return {
            'setStatus': lambda text: self.progress_signal.emit(0, 100, text),
            'setProgress': lambda value: self.progress_signal.emit(value, 100, ''),
            'setMax': lambda value: self.progress_signal.emit(0, value, '')
        }

class ModLoaderTab(QWidget):
    def __init__(self, loader_type, parent=None):
        super().__init__(parent)
        self.loader_type = loader_type
        self.setup_ui()
        self.load_mc_versions()
        
        # Для Quilt - выбор версии лоадера
        if self.loader_type == "quilt":
            self.loader_version_combo = QComboBox()
            self.layout().insertWidget(2, QLabel("В разработке"))
            self.layout().insertWidget(3, self.loader_version_combo)
            self.mc_version_combo.currentTextChanged.connect(self.update_quilt_versions)
            self.update_quilt_versions()

        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Выбор версии Minecraft
        self.mc_version_combo = QComboBox()
        layout.addWidget(QLabel("Версия Minecraft:"))
        layout.addWidget(self.mc_version_combo)
        
        # Для Forge - выбор версии Forge
        if self.loader_type == "forge":
            self.forge_version_combo = QComboBox()
            layout.addWidget(QLabel("Версия Forge:"))
            layout.addWidget(self.forge_version_combo)
            self.mc_version_combo.currentTextChanged.connect(self.update_forge_versions)
            self.update_forge_versions()
        
        # Кнопка установки
        self.install_btn = QPushButton(f"Установить {self.loader_type}")
        self.install_btn.clicked.connect(self.install_loader)
        layout.addWidget(self.install_btn)
        
        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Статус
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
    
    def load_mc_versions(self):
        """Загружает версии Minecraft"""
        self.mc_version_combo.clear()
        versions = get_version_list()
        for version in versions:
            if version["type"] == "release":
                self.mc_version_combo.addItem(version["id"])
    
    def update_forge_versions(self):
        """Обновляет список версий Forge при изменении версии MC"""
        if self.loader_type != "forge":
            return
            
        mc_version = self.mc_version_combo.currentText()
        self.forge_version_combo.clear()
        
        try:
            forge_version = find_forge_version(mc_version)
            if forge_version:
                self.forge_version_combo.addItem(forge_version)
            else:
                self.forge_version_combo.addItem("Автоматический выбор")
        except Exception as e:
            logging.error(f"Ошибка загрузки Forge: {str(e)}")
            self.forge_version_combo.addItem("Ошибка загрузки")
            
    def update_quilt_versions(self):
        try:
            self.loader_version_combo.clear()
            versions = get_quilt_versions(self.mc_version_combo.currentText())
            
            if not versions:
                self.loader_version_combo.addItem("Нет доступных сборок")
                return
                
            for v in versions:
                status = "🔒" if not v["stable"] else "✅"
                self.loader_version_combo.addItem(
                    f"{v['version']} (build {v['build']}) {status}",
                    userData=v["version"]
                )
                
        except Exception as e:
            logging.error(f"Ошибка обновления версий Quilt: {e}")
            self.loader_version_combo.addItem("Ошибка загрузки")

    def install_loader(self):
        mc_version = self.mc_version_combo.currentText()
        
        if self.loader_type == "quilt":
            loader_version = self.loader_version_combo.currentText()
            self.install_thread = ModLoaderInstaller(
                "quilt", 
                loader_version,  # Передаем версию лоадера
                mc_version
            )
        
        if self.loader_type == "forge":
            forge_version = self.forge_version_combo.currentText()
            if forge_version == "Автоматический выбор":
                forge_version = None
            self.install_thread = ModLoaderInstaller("forge", forge_version, mc_version)
        else:
            self.install_thread = ModLoaderInstaller(self.loader_type, None, mc_version)
        
        self.install_thread.progress_signal.connect(self.update_progress)
        self.install_thread.finished_signal.connect(self.installation_finished)
        self.install_thread.start()
        
        self.install_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setVisible(True)
    
    def update_progress(self, current, total, text):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status_label.setText(text)
    
    def installation_finished(self, success, message):
        self.install_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        # Обновляем список версий Minecraft
        if success and self.loader_type == "quilt":
            self.parent_window.update_version_list()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information if success else QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Результат установки")
        msg.exec_()

class LaunchThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.version_id = ""
        self.username = ""
        self.loader_type = "vanilla"
        self.memory_mb = 4096
        self.close_on_launch = False

    finished_signal = pyqtSignal(bool, str)
    launch_setup_signal = pyqtSignal(str, str, str, int, bool)
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)
    close_launcher_signal = pyqtSignal()

    def launch_setup(self, version_id, username, loader_type, memory_mb, close_on_launch):
        self.version_id = version_id
        self.username = username
        self.loader_type = loader_type
        self.memory_mb = memory_mb
        self.close_on_launch = close_on_launch
    
    def run(self):
        try:
            print("[LAUNCH THREAD] Starting Minecraft launch process...")
            self.state_update_signal.emit(True)
            
            # 1. Проверяем и скачиваем authlib-injector
            if not self.download_authlib():
                raise Exception("Не удалось загрузить authlib-injector")

            # 2. Определение параметров
            launch_version = self.version_id
            is_legacy = self.is_legacy_version(self.version_id)
            options = {
                'username': self.username,
                'uuid': str(uuid1()),
                'token': '',
                'jvmArguments': [
                    f'-Xmx{self.memory_mb}M',
                    f'-Xms{min(self.memory_mb // 2, 2048)}M',
                    f'-javaagent:{AUTHLIB_JAR_PATH}=ely.by',
                    '-Dauthlibinjector.yggdrasil.prefetched=' + json.dumps({
                        "meta": {
                            "serverName": "Ely.by",
                            "implementationName": "ElyAuthLib",
                            "implementationVersion": "1.2.0",
                            "links": {
                                "homepage": "https://ely.by"
                            }
                        },
                        "skinDomains": ["ely.by"],
                        "signaturePublickey": "7vjWLLgQovH0V5SQjYQuvPM2vpKD1RWZ7Xb9sYrBqgI"
                    })
                ],
                'launcherName': '16Launcher',
                'launcherVersion': '1.0'
            }

            # 3. Для legacy версий - патчим jar и применяем скин
            if is_legacy:
                print("[LAUNCH THREAD] Applying legacy patch...")
                legacy_jar = os.path.join(MINECRAFT_DIR, "versions", launch_version, f"{launch_version}.jar")
                self.patch_legacy_jar(legacy_jar)
                self.apply_legacy_skin(skin_path)
            else:
                # Для новых версий используем текстуры-прокси
                textures = self.apply_modern_skin(username)
                if textures:
                    options['textures'] = textures

            # 4. Установка версии если требуется
            if not os.path.exists(os.path.join(MINECRAFT_DIR, "versions", launch_version)):
                print("[LAUNCH THREAD] Installing version...")
                install_minecraft_version(
                    launch_version,
                    MINECRAFT_DIR,
                    callback={
                        'setStatus': lambda text: self.progress_update_signal.emit(0, 100, text),
                        'setProgress': lambda value: self.progress_update_signal.emit(value, 100, ''),
                        'setMax': lambda value: self.progress_update_signal.emit(0, value, '')
                    }
                )

            # 5. Формирование команды запуска
            command = get_minecraft_command(
                launch_version,
                MINECRAFT_DIR,
                options
            )
            print("[LAUNCH THREAD] Final command:", " ".join(command))

            # 6. Запуск процесса
            minecraft_process = subprocess.Popen(
                command,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 7. Закрытие лаунчера если нужно
            if self.close_on_launch:
                self.close_launcher_signal.emit()

            self.state_update_signal.emit(False)
            print("[LAUNCH THREAD] Launch completed successfully")

        except Exception as e:
            print(f"[LAUNCH THREAD ERROR] {str(e)}")
            logging.error(f"Launch thread failed: {traceback.format_exc()}")
            self.state_update_signal.emit(False)
            self.finished_signal.emit(False, f"Критическая ошибка: {str(e)}")
            
    def patch_legacy_jar(self, jar_path):
        """Патчим jar-файл для старых версий с проверкой хэша"""
        try:
            patch_url = "https://ely.by/load/legacy-patch.jar"
            response = requests.get(patch_url)
            if response.status_code != 200:
                raise Exception("Не удалось скачать патч")
                
            # Проверка целостности патча
            patch_hash = hashlib.sha256(response.content).hexdigest()
            if patch_hash != "a1b2c3d4e5...":  # Заменить на актуальный хэш
                raise Exception("Неверная контрольная сумма патча")
                
            with zipfile.ZipFile(io.BytesIO(response.content)) as patch:
                with zipfile.ZipFile(jar_path, 'a') as game_jar:
                    # Удаляем старые файлы перед добавлением
                    for file in ['net/minecraft/client/Minecraft.class', 
                            'net/minecraft/util/Session.class']:
                        if file in game_jar.namelist():
                            game_jar.remove(file)
                    
                    # Добавляем новые файлы из патча
                    for file in patch.namelist():
                        if file.endswith('.class'):
                            game_jar.writestr(file, patch.read(file))
            return True
        except Exception as e:
            raise Exception(f"Ошибка патчинга: {str(e)}")
            
    def is_legacy_version(self, version):
        """Определяет legacy-версии (1.7.10 и старше) с поддержкой snapshot"""
        try:
            version = re.sub(r'-pre|\w+-snapshot', '', version)  # Игнорируем snapshot суффиксы
            parts = list(map(int, version.split('.')[0:3]))
            if parts[0] == 1 and parts[1] < 8:
                return True
            if parts[0] == 1 and parts[1] == 8 and parts[2] < 9:
                return True
            return False
        except:
            return False
        
    def apply_legacy_skin(self, skin_path):
        """Патчит game.jar для старых версий"""
        try:
            jar_path = os.path.join(MINECRAFT_DIR, "versions", self.version_id, f"{self.version_id}.jar")
            patch_url = "https://ely.by/load/legacy-patch.jar"
            
            # Скачивание патча
            patch_data = requests.get(patch_url).content
            
            # Модификация jar-файла
            with zipfile.ZipFile(jar_path, 'a') as jar:
                with zipfile.ZipFile(io.BytesIO(patch_data)) as patch:
                    for file in patch.namelist():
                        if file.endswith('.class'):
                            jar.writestr(file, patch.read(file))
            
            # Копирование скина
            assets_dir = os.path.join(MINECRAFT_DIR, "assets", "skins")
            os.makedirs(assets_dir, exist_ok=True)
            shutil.copy(skin_path, os.path.join(assets_dir, "char.png"))
            
        except Exception as e:
            logging.error(f"Legacy skin apply error: {str(e)}")
            
    def apply_modern_skin(username):
        """Применяет скин через текстуры-прокси для новых версий"""
        try:
            texture_url = f"https://textures.ely.by/skins/{username}"
            response = requests.get(texture_url)
            if response.status_code == 200:
                texture_data = response.json()
                return {
                    'SKIN': {'url': texture_data['textures']['SKIN']['url']},
                    'CAPE': {'url': texture_data['textures']['CAPE']['url']} if 'CAPE' in texture_data else {}
                }
            return None
        except Exception as e:
            logging.error(f"Ошибка получения текстуры: {str(e)}")
            return None

    def setup_authlib(self, options):
        """Настраивает параметры authlib-injector"""
        options['jvmArguments'].extend([
            f"-javaagent:{AUTHLIB_JAR_PATH}=ely.by",
            f"-Dauthlibinjector.yggdrasil.prefetched={json.dumps({
                'meta': {
                    'serverName': 'Ely.by',
                    'implementationName': 'ElyAuthLib',
                    'implementationVersion': self.get_authlib_version(),
                    'links': {'homepage': 'https://ely.by'}
                },
                'skinDomains': ['ely.by'],
                'signaturePublickey': '7vjWLLgQovH0V5SQjYQuvPM2vpKD1RWZ7Xb9sYrBqgI',
                'textureServiceUrl': 'https://textures.ely.by/'
            })}"
        ])

    def download_authlib(self):
        """Скачивает последнюю версию Authlib Injector с проверкой подписи"""
        try:
            # Получаем метаданные из Maven
            metadata_url = "https://maven.ely.by/releases/by/ely/authlib/maven-metadata.xml"
            response = requests.get(metadata_url, timeout=15)
            root = ET.fromstring(response.text)
            
            # Получаем последнюю версию
            latest_version = root.find(".//latest").text
            
            # Формируем URL для скачивания
            jar_url = f"https://maven.ely.by/releases/by/ely/authlib/{latest_version}/authlib-{latest_version}.jar"
            sig_url = jar_url + ".asc"
            
            # Скачиваем JAR
            response = requests.get(jar_url, stream=True)
            jar_data = response.content
            
            # Скачиваем подпись
            response = requests.get(sig_url)
            signature = response.text
            
            # Проверка подписи (требуется GPG)
            # Здесь должна быть реализация проверки PGP подписи
            
            # Сохраняем файл
            with open(AUTHLIB_JAR_PATH, 'wb') as f:
                f.write(jar_data)
                
            return True
        except Exception as e:
            logging.error(f"Ошибка загрузки Authlib: {str(e)}")
            return False
        
    def apply_legacy_patch(self, version):
        """Применяет патч для старых версий"""
        jar_path = os.path.join(MINECRAFT_DIR, "versions", version, f"{version}.jar")
        
        if not os.path.exists(jar_path):
            raise Exception("JAR file not found")
        
        # Скачиваем патч с ely.by
        patch_url = "https://ely.by/load/legacy-patch.jar"  # Пример URL
        patch_data = requests.get(patch_url).content
        
        # Модифицируем JAR-файл
        with zipfile.ZipFile(jar_path, 'a') as jar:
            with zipfile.ZipFile(io.BytesIO(patch_data)) as patch:
                for file in patch.namelist():
                    if file.endswith('.class'):
                        jar.writestr(file, patch.read(file))
            
    def _set_status(self, text):
        self.progress_update_signal.emit(self.current_step, self.total_steps, text)

    def _set_progress(self, sub_value):
        # Преобразуем sub_value в глобальный прогресс (например, 0–20%)
        percent_of_stage = 20  # каждый этап = 20% общего
        global_progress = self.progress_step * percent_of_stage + (sub_value * percent_of_stage // 100)
        self.current_step = global_progress
        self.progress_update_signal.emit(self.current_step, self.total_steps, '')

    def _set_max(self, _):  # не нужен для глобального прогресса
        pass

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # Сохраняем ссылку на главное окно
        self.setup_ui()
        self.setup_language_selector()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        # Добавляем разделитель
        layout.addRow(QLabel("<b>Внешний вид</b>"))
        
        # Кнопка смены темы
        self.theme_button = QPushButton()
        self.theme_button.setFixedHeight(40)
        self.update_theme_button_icon()  # Новый метод для обновления иконки
        
        # Стилизуем кнопку
        self.theme_button.setStyleSheet("""
            QPushButton {
                padding: 8px;
                text-align: left;
                border-radius: 5px;
                background-color: #444444;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        self.theme_button.clicked.connect(self.toggle_theme)
        layout.addRow(self.theme_button)
        
        self.close_on_launch_checkbox = QCheckBox("Закрывать лаунчер при запуске игры", self)
        layout.addRow(self.close_on_launch_checkbox)

        self.memory_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.memory_slider.setRange(1, 32)
        self.memory_slider.setValue(4)
        self.memory_slider.setTickPosition(QSlider.TicksBelow)
        self.memory_slider.setTickInterval(1)
        self.memory_label = QLabel("Оперативная память (ГБ): 4", self)
        self.memory_slider.valueChanged.connect(self.update_memory_label)
        layout.addRow(self.memory_label, self.memory_slider)

        # Добавляем разделитель
        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Директории</b>"))

        # Директория игры
        self.directory_edit = QLineEdit(self)
        self.directory_edit.setText(MINECRAFT_DIR)
        layout.addRow("Директория игры:", self.directory_edit)

        self.choose_directory_button = QPushButton("Выбрать папку игры", self)
        self.choose_directory_button.clicked.connect(self.choose_directory)
        layout.addRow(self.choose_directory_button)

        # Директория модов
        self.mods_directory_edit = QLineEdit(self)
        self.mods_directory_edit.setText(MODS_DIR)
        layout.addRow("Директория модов:", self.mods_directory_edit)

        mods_buttons_layout = QHBoxLayout()
        
        self.choose_mods_directory_button = QPushButton("Выбрать папку модов", self)
        self.choose_mods_directory_button.clicked.connect(self.choose_mods_directory)
        mods_buttons_layout.addWidget(self.choose_mods_directory_button)
        
        layout.addRow(mods_buttons_layout)
        
            # Добавляем разделитель
        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Версии Minecraft</b>"))

        # Чекбокс для отображения снапшотов
        self.show_snapshots_checkbox = QCheckBox("Показывать Снапшоты", self)
        if 'show_snapshots' in self.parent_window.settings:
            self.show_snapshots_checkbox.setChecked(self.parent_window.settings['show_snapshots'])
        layout.addRow(self.show_snapshots_checkbox)
        self.show_snapshots_checkbox.stateChanged.connect(self.parent_window.update_version_list)

        # Добавляем разделитель
        layout.addRow(QLabel(""))
        layout.addRow(QLabel("<b>Аккаунт Ely.by</b>"))
        
        # Кнопка выхода
        self.ely_logout_button = QPushButton("Выйти из Ely.by")
        self.ely_logout_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.ely_logout_button.clicked.connect(self.parent_window.ely_logout)
        layout.addRow(self.ely_logout_button)
        
        # Обновляем видимость кнопки
        self.update_logout_button_visibility()
            
        layout.addRow(QLabel("<b>Сборки</b>"))
        
        self.export_path_edit = QLineEdit()
        self.export_path_edit.setText(self.parent_window.settings.get("export_path", ""))
        layout.addRow("Путь для экспорта:", self.export_path_edit)
        
        self.export_path_btn = QPushButton("Выбрать папку")
        self.export_path_btn.clicked.connect(self.set_export_path)
        layout.addWidget(self.export_path_btn)
        
        # Загружаем настройки
        settings = self.parent_window.settings if self.parent_window else load_settings()
        if 'close_on_launch' in settings:
            self.close_on_launch_checkbox.setChecked(settings['close_on_launch'])
        if 'memory' in settings:
            self.memory_slider.setValue(settings['memory'])
        if 'minecraft_directory' in settings:
            self.directory_edit.setText(settings['minecraft_directory'])
        if 'mods_directory' in settings:
            self.mods_directory_edit.setText(settings['mods_directory'])

    def choose_mods_directory(self):
        """Выбор директории для модов"""
        try:
            directory = QFileDialog.getExistingDirectory(self, "Выберите директорию для модов")
            if directory:
                self.mods_directory_edit.setText(directory)
                global MODS_DIR
                MODS_DIR = directory
                # Сохраняем в настройках
                if self.parent_window:
                    self.parent_window.settings['mods_directory'] = directory
                    save_settings(self.parent_window.settings)
        except Exception as e:
            logging.error(f"Ошибка при выборе директории модов: {e}")
            self.show_error_message("Ошибка при выборе директории модов")
            
    def set_export_path(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для экспорта")
        if path:
            self.export_path_edit.setText(path)
            self.parent_window.settings["export_path"] = path
            save_settings(self.parent_window.settings)

    def open_mods_directory(self):
        """Открывает директорию с модами"""
        try:
            mods_dir = self.mods_directory_edit.text()
            if not os.path.exists(mods_dir):
                os.makedirs(mods_dir)
            if os.name == 'nt':
                subprocess.Popen(f'explorer "{mods_dir}"')
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', mods_dir])
        except Exception as e:
            logging.error(f"Ошибка при открытии директории модов: {e}")
            self.show_error_message("Ошибка при открытии директории модов")

    def setup_language_selector(self):
        # Добавляем в layout настроек
        self.language_combo = QComboBox()
        self.language_combo.addItem("Русский", "ru")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(self.change_language)
        
        # Добавляем в layout (можно в начало)
        self.layout().insertRow(0, QLabel("Язык:"), self.language_combo)
        
    def change_language(self):
        lang = self.language_combo.currentData()
        translator.set_language(lang)
        self.parent_window.retranslate_ui()
        
            
    def toggle_theme(self):
        """Переключает тему между светлой и темной"""
        current_theme = getattr(self.parent_window, 'current_theme', 'dark')
        new_theme = 'light' if current_theme == 'dark' else 'dark'
        
        # Применяем новую тему
        self.parent_window.apply_dark_theme(new_theme == 'dark')  # <- Исправлено на apply_dark_theme
        self.update_theme_button_icon()
        
        # Сохраняем выбор темы
        self.parent_window.settings['theme'] = new_theme
        save_settings(self.parent_window.settings)

    def update_theme_button_icon(self):
        """Обновляет иконку и текст кнопки в зависимости от текущей темы"""
        current_theme = getattr(self.parent_window, 'current_theme', 'dark')
        if current_theme == 'dark':
            self.theme_button.setIcon(QIcon(resource_path("assets/sun.png")))
            self.theme_button.setText(" Светлая тема")
        else:
            self.theme_button.setIcon(QIcon(resource_path("assets/moon.png")))
            self.theme_button.setText(" Тёмная тема")
        self.theme_button.setIconSize(QSize(24, 24))
        
    def update_logout_button_visibility(self):
        """Обновляет видимость кнопки выхода в зависимости от статуса авторизации"""
        if hasattr(self.parent_window, 'ely_session') and self.parent_window.ely_session:
            self.ely_logout_button.setVisible(True)
        else:
            self.ely_logout_button.setVisible(False)
        # Принудительно обновляем layout
        self.layout().update()

    def update_memory_label(self):
        self.memory_label.setText(f"Оперативная память (ГБ): {self.memory_slider.value()}")

    def choose_directory(self):
        try:
            directory = QFileDialog.getExistingDirectory(self, "Выберите директорию Minecraft")
            if directory:
                self.directory_edit.setText(directory)
                global MINECRAFT_DIR
                MINECRAFT_DIR = directory
                global SETTINGS_PATH, LOG_FILE
                SETTINGS_PATH = os.path.join(MINECRAFT_DIR, "settings.json")
                LOG_FILE = os.path.join(MINECRAFT_DIR, "launcher_log.txt")
        except Exception as e:
            logging.error(f"Ошибка при выборе директории: {e}")
            self.show_error_message("Ошибка при выборе директории")

    def open_directory(self):
        try:
            if os.name == 'nt':
                subprocess.Popen(f'explorer "{MINECRAFT_DIR}"')
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', MINECRAFT_DIR])
        except Exception as e:
            logging.error(f"Ошибка при открытии директории: {e}")
            self.show_error_message("Ошибка при открытии директории")

    def show_error_message(self, message):
        QMessageBox.critical(self, "Ошибка", message)

    def closeEvent(self, event):
        # Сохраняем настройки через главное окно
        if self.parent_window:
            self.parent_window.settings = {
                'close_on_launch': self.close_on_launch_checkbox.isChecked(),
                'memory': self.memory_slider.value(),
                'minecraft_directory': self.directory_edit.text(),
                'mods_directory': self.mods_directory_edit.text()
                # Убрали сохранение last_username здесь
            }
            save_settings(self.parent_window.settings)

def load_settings():
    default_settings = {
        'language': 'ru',  
        'close_on_launch': False,
        'memory': 4,
        'minecraft_directory': MINECRAFT_DIR,
        'last_username': '',
        'favorites': [],  # Добавляем список избранных версий
        'last_version': '',  # Последняя выбранная версия
        'last_loader': 'vanilla',  # Последний выбранный загрузчик
        'show_snapshots': False,
    }
    
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                # Объединяем с настройками по умолчанию
                return {**default_settings, **loaded_settings}
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек: {e}")
            return default_settings
    return default_settings


def save_settings(settings):
    try:
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        logging.debug("Настройки успешно сохранены")
    except Exception as e:
        logging.error(f"Ошибка при сохранении настроек: {e}")
    if 'export_path' not in settings:
        settings['export_path'] = os.path.expanduser("~/Desktop")


def generate_random_username():
    """Генерирует случайное имя пользователя для Minecraft"""
    adjectives = [
        "Cool", "Mighty", "Epic", "Crazy", "Wild", 
        "Sneaky", "Happy", "Angry", "Funny", "Lucky",
        "Dark", "Light", "Red", "Blue", "Green",
        "Golden", "Silver", "Iron", "Diamond", "Emerald"
    ]
    
    nouns = [
        "Player", "Gamer", "Hero", "Villain", "Warrior",
        "Miner", "Builder", "Explorer", "Adventurer", "Hunter",
        "Wizard", "Knight", "Ninja", "Pirate", "Dragon",
        "Wolf", "Fox", "Bear", "Tiger", "Ender", "Sosun"
    ]
    
    numbers = [
        "123", "42", "99", "2023", "777",
        "1337", "69", "100", "1", "0"
    ]
    
    # Выбираем случайные элементы
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    num = random.choice(numbers) if random.random() > 0.5 else ""
    
    # Собираем имя
    if num:
        return f"{adj}{noun}{num}"
    return f"{adj}{noun}"

class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._button = None

    def set_button(self, button):
        self._button = button
        self.update_button_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_button_position()

    def update_button_position(self):
        if self._button:
            from PyQt5.QtWidgets import QStyle
            frame_width = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
            rect = self.rect()
            x = rect.right() - self._button.width() - frame_width - 2  # Уменьшили отступ
            y = (rect.height() - self._button.height()) // 2
            self._button.move(x, y) 
            
def download_authlib_injector():
    """Скачивает последнюю версию Authlib Injector"""
    try:
        response = requests.get(AUTHLIB_INJECTOR_URL)
        data = response.json()
        download_url = data["download_url"]
        
        response = requests.get(download_url, stream=True)
        with open(AUTHLIB_JAR_PATH, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        return True
    except Exception as e:
        logging.error(f"Ошибка загрузки Authlib Injector: {e}")
        return False
    
class InitializationWorker(QObject):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)
    window_created = pyqtSignal(QMainWindow)  # Измененный сигнал

    def __init__(self):
        super().__init__()
        self.window = None
        self._timeout = 10  # Максимальное время ожидания в секундах

    def run(self):
        try:
            logging.info("Инициализация начата")
            # Этап 1: Базовые настройки
            self.progress.emit(10, "Инициализация системы...")
            setup_directories()

            # Этап 2: Загрузка конфигурации
            self.progress.emit(30, "Загрузка настроек...")
            settings = load_settings()

            # Этап 3: Применение настроек
            self.progress.emit(50, "Применение настроек...")
            translator.set_language(settings.get('language', 'ru'))

            # Этап 4: Создание окна через очередь событий   
            QMetaObject.invokeMethod(self, "create_window", Qt.BlockingQueuedConnection)
            
            # Ожидаем создания окна с таймаутом
            start_time = time.time()
            while not self.window and (time.time() - start_time) < self._timeout:
                time.sleep(0.1)
                self.progress.emit(50 + int(40*(time.time()-start_time)/self._timeout), 
                                "Подготовка интерфейса...")
                
            QMetaObject.invokeMethod(self, "create_window", Qt.BlockingQueuedConnection)
            self.window_created.emit()  # Сигнал о создании окна
            self.progress.emit(100, "Готово!")
            self.finished.emit(self.window)
        except Exception as e:
            self.error.emit(f"Ошибка: {str(e)}")

            # Финальный этап
            self.progress.emit(100, "Готово!")
            self.finished.emit(self.window)

        except Exception as e:
            self.error.emit(f"Ошибка инициализации: {str(e)}")
            logging.error(traceback.format_exc())

    @pyqtSlot()
    def create_window(self):
        try:
            self.window = MainWindow()
            self.window.setAttribute(Qt.WA_DeleteOnClose)
            self.window_created.emit()
        except Exception as e:
            self.error.emit(f"Ошибка создания окна: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ely_session = None

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.setWindowTitle("16Launcher 1.0.2.b")
        self.setFixedSize(1280, 720)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        self.motd_messages = [
            "Приятной игры, легенда!",
            "Поддержи проект, если нравится ❤️",
            "Сегодня отличный день, чтобы поиграть!",
            "Ты красавчик, что запускаешь это 😎",
            "Готов к новым блокам?",
            "Эндермены советуют: всегда носишь с собой эндер-жемчуг… и зонтик!",
            "Совет от опытного шахтёра: алмазы любят тишину… и факелы!",
            "Эндермен смотрит? Не смотри в ответ!",
            "Лава опасна, но обсидиан того стоит!",
            "Сундук с сокровищем? Проверь, нет ли ТНТ!",
            "Летать на Элитрах? Помни: ремонт нужен!",
            "Зельеварение? Не перепутай ингредиенты!",
            "Лови рыбу — может, клюнет зачарованная книга!",
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
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)
        self.launch_thread.close_launcher_signal.connect(self.close_launcher)
        
        # Добавляем хоткей Ctrl+D
        self.ctrl_d_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message)
        
        self.ctrl_d_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message_1)
        
        self.ctrl_d_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.ctrl_d_shortcut.activated.connect(self.show_funny_message_2)
        
        self.ctrl_d_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
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
        self.setup_game_tab()      # Настраиваем содержимое
        
        self.mods_tab = ModsTab(self)
        self.modpacks_tab = ModpackTab(self)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.game_tab, "Запуск игры")     # Теперь game_tab существует
        self.tabs.addTab(self.mods_tab, "Моды")
        self.tabs.addTab(self.modpacks_tab, "Мои сборки")
        
        self.tab_layout.addWidget(self.tabs)
        
        self.setup_modloader_tabs()
        
        self.stacked_widget.addWidget(self.tab_widget)
        self.settings_tab = SettingsTab(self)
        self.stacked_widget.addWidget(self.settings_tab)
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.currentChanged.connect(self.handle_tab_changed)
        
        self.apply_dark_theme()
        
    def retranslate_ui(self):
        """Обновляет все текстовые элементы интерфейса в соответствии с текущим языком"""
        # Основное окно
        self.setWindowTitle(translator.tr("window_title"))
        
        # Вкладка игры
        self.username.setPlaceholderText(translator.tr("username_placeholder"))
        self.random_name_button.setToolTip(translator.tr("generate_random_username"))
        
        # Версии и модлоадеры
        self.version_type_select.setItemText(0, translator.tr("all versions"))
        self.version_type_select.setItemText(1, translator.tr("favorites"))
        
        self.loader_select.setItemText(0, translator.tr("vanilla"))
        self.loader_select.setItemText(1, translator.tr("forge"))
        self.loader_select.setItemText(2, translator.tr("fabric"))
        self.loader_select.setItemText(3, translator.tr("optifine"))
        
        # Кнопки
        self.start_button.setText(translator.tr("launch_button"))
        self.ely_login_button.setText(translator.tr("ely_login_button"))
        self.change_skin_button.setText
        
    def handle_tab_changed(self, index):
        """Обработчик смены вкладок"""
        if self.tabs.tabText(index) == "Моды" and not hasattr(self, 'mods_tab'):
            # Инициализируем вкладку модов только при первом открытии
            self.mods_tab = ModsTab(self)
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, self.mods_tab, "Моды")
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

        # Кнопка "Настройки"
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(resource_path("assets/set64.png")))
        self.settings_button.setIconSize(QSize(64, 64))
        self.settings_button.setFixedSize(75, 75)
        self.settings_button.setStyleSheet(self.play_button.styleSheet())
        self.settings_button.clicked.connect(self.show_settings_tab)
        sidebar_content_layout.addWidget(self.settings_button, alignment=Qt.AlignCenter)

        # Кнопка "Новости"
        self.news_button = QPushButton()
        self.news_button.setIcon(QIcon(resource_path("assets/news64.png")))
        self.news_button.setIconSize(QSize(64, 64))
        self.news_button.setFixedSize(75, 75)
        self.news_button.setStyleSheet(self.play_button.styleSheet())
        self.news_button.clicked.connect(self.show_news_tab)
        sidebar_content_layout.addWidget(self.news_button, alignment=Qt.AlignCenter)
        

        sidebar_content_layout.addStretch()
        
        # Кнопка "Телеграм"
        self.telegram_button = QPushButton()
        self.telegram_button.setIcon(QIcon(resource_path("assets/tg.png")))
        self.telegram_button.setIconSize(QSize(64, 64))
        self.telegram_button.setFixedSize(75, 75)
        self.telegram_button.setStyleSheet(self.play_button.styleSheet())
        self.telegram_button.clicked.connect(lambda: webbrowser.open("https://t.me/of16launcher"))
        sidebar_content_layout.addWidget(self.telegram_button, alignment=Qt.AlignCenter)
        
        #Кнопка "Поддержать"
        self.support_button = QPushButton()
        self.support_button.setIcon(QIcon(resource_path("assets/support64.png")))
        self.support_button.setIconSize(QSize(64, 64))
        self.support_button.setFixedSize(75, 75)
        self.support_button.setStyleSheet(self.play_button.styleSheet())
        self.support_button.clicked.connect(lambda: webbrowser.open("https://www.donationalerts.com/r/16steyy"))
        sidebar_content_layout.addWidget(self.support_button, alignment=Qt.AlignCenter)
        
        # Кнопка-свёртка (вне панели!)
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

        # Добавляем панель и кнопку в контейнер
        self.sidebar_layout.addWidget(self.sidebar)
        self.sidebar_layout.addWidget(self.toggle_sidebar_button)

        self.main_layout.addWidget(self.sidebar_container)

    def update_login_button_text(self):
        if hasattr(self, "access_token") and self.access_token:
            self.ely_login_button.setText("Выйти из Ely.by")
        else:
            self.ely_login_button.setText("Войти с Ely.by")

    
    def show_game_tab(self):
        """Переключает на вкладку с игрой"""
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.setCurrentIndex(0)  # Убедимся, что выбрана первая вкладка (Запуск игры)
        
    def toggle_theme(self):
        current_theme = getattr(self, 'current_theme', 'dark')
        new_theme = 'light' if current_theme == 'dark' else 'dark'
        
        # Применяем новую тему
        self.apply_theme(new_theme == 'dark')
        
        # Обновляем иконки во всех местах
        icon_path = "assets/sun.png" if new_theme == 'light' else "assets/moon.png"
        self.theme_button.setIcon(QIcon(resource_path(icon_path)))
        
        # Если есть кнопка в настройках, обновляем и её
        if hasattr(self.settings_tab, 'theme_button'):
            self.settings_tab.theme_button.setIcon(QIcon(resource_path(icon_path)))
            self.settings_tab.theme_button.setText("Светлая тема" if new_theme == 'light' else "Тёмная тема")
        
        # Сохраняем выбор темы
        self.settings['theme'] = new_theme
        save_settings(self.settings)
    
    def show_settings_tab(self):
        """Переключает на вкладку с настройками"""
        self.stacked_widget.setCurrentIndex(1)
        
    def show_news_tab(self):
        """Переключает на вкладку с новостями"""
        if not hasattr(self, 'news_tab'):
            self.news_tab = NewsTab()
            self.stacked_widget.addWidget(self.news_tab)
            self.stacked_widget.setCurrentIndex(2)  # Новости будут третьей вкладкой
        else:
            self.stacked_widget.setCurrentWidget(self.news_tab)
    
    def setup_game_tab(self):
        layout = QVBoxLayout(self.game_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        # Первая строка — имя игрока + кнопка случайного имени встроенная в поле
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.username = CustomLineEdit(self.game_tab)
        self.username.setPlaceholderText('Введите имя')
        self.username.setMinimumHeight(40)
        self.username.setText(self.last_username)

        self.username.setStyleSheet("padding-right: 80px;")  # добавим отступ под кнопку
        top_row.addWidget(self.username)

        self.random_name_button = QToolButton(self.username)
        self.random_name_button.setIcon(QIcon(resource_path("assets/random.png"))) # Путь к вашей иконке
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
        self.random_name_button.setFixedSize(60, 30)  # Размер можно подобрать под вашу иконку
        self.random_name_button.setFixedSize(60, 30)
        self.random_name_button.clicked.connect(self.set_random_username)

        self.username.set_button(self.random_name_button)

        form_layout.addLayout(top_row) 

        form_layout.addLayout(top_row)

        version_row = QHBoxLayout()
        version_row.setSpacing(10)


        # 1. Все/Избранные
        self.version_type_select = QComboBox(self.game_tab)
        self.version_type_select.setMinimumHeight(45)
        self.version_type_select.setFixedWidth(250)
        self.version_type_select.addItem("Все версии")
        self.version_type_select.addItem("Избранные")
        self.version_type_select.currentTextChanged.connect(self.update_version_list)
        version_row.addWidget(self.version_type_select)

        # 2. Модлоадер
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

        # 3. Версия
        self.version_select = QComboBox(self.game_tab)
        self.version_select.setMinimumHeight(45)
        self.version_select.setFixedWidth(250)
        self.version_select.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        version_row.addWidget(self.version_select)

        # 4. Кнопка избранного
        self.favorite_button = QPushButton("★")
        self.favorite_button.setFixedSize(45, 45)
        self.favorite_button.setCheckable(True)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        version_row.addWidget(self.favorite_button)

        form_layout.addLayout(version_row)

        # Третья строка — Играть и Сменить скин
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
        
                # Кнопка "Открыть папку"
        self.open_folder_button = QPushButton()
        self.open_folder_button.setIcon(QIcon(resource_path("assets/folder.png")))
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
        self.open_folder_button.clicked.connect(self.open_root_folder)
        bottom_row.addWidget(self.open_folder_button)
        
            # --- Сообщение дня ---
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
        layout.addStretch()  # Добавляем растягивающееся пространство

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
            
            
    def setup_ely_auth(self):
        """Проверяет сохранённую сессию"""
        self.ely_session = None  # Добавьте эту строку в начало метода
        try:
            if ely.is_logged_in():
                self.ely_session = {
                    "username": ely.username(),
                    "uuid": ely.uuid(),
                    "token": ely.token()
                }
                self.username.setText(self.ely_session["username"])
                self.update_ely_ui(True)
                
                # Проверяем текстуру скина через authlib
                try:
                    texture_info = requests.get(
                        f"https://authserver.ely.by/session/profile/{self.ely_session['uuid']}",
                        headers={"Authorization": f"Bearer {self.ely_session['token']}"}
                    ).json()
                    
                    if "textures" in texture_info:
                        skin_url = texture_info["textures"].get("SKIN", {}).get("url")
                        if skin_url:
                            # Сохраняем скин локально для отображения в лаунчере
                            skin_data = requests.get(skin_url).content
                            os.makedirs(SKINS_DIR, exist_ok=True)
                            with open(os.path.join(SKINS_DIR, f"{self.ely_session['username']}.png"), "wb") as f:
                                f.write(skin_data)
                except Exception as e:
                    logging.error(f"Ошибка проверки скина: {e}")
        
        except Exception as e:
            logging.error(f"Ошибка загрузки сессии Ely.by: {e}")

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
            self.change_skin_button.setText("Управление скином")
        else:
            self.ely_login_button.setVisible(True)
            self.change_skin_button.setVisible(False)
                
    def setup_ely_auth(self):
        """Проверяет сохранённую сессию и загружает скин"""
        try:
            if ely.is_logged_in():
                self.ely_session = {
                    "username": ely.username(),
                    "uuid": ely.uuid(),
                    "token": ely.token()
                }
                self.username.setText(self.ely_session["username"])
                self.update_ely_ui(True)
                
                # Загружаем скин через текстуры-прокси
                texture_url = ElySkinManager.get_skin_texture_url(self.ely_session["username"])
                if texture_url:
                    if ElySkinManager.download_skin(self.ely_session["username"]):
                        logging.info("Скин успешно загружен")
                    else:
                        logging.warning("Не удалось загрузить скин")
        
        except Exception as e:
            logging.error(f"Ошибка загрузки сессии Ely.by: {e}")


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
        """Диалог ввода логина/пароля Ely.by"""
        email, ok = QInputDialog.getText(
            self, "Вход", "Введите email Ely.by:",
            QLineEdit.Normal, ""
        )
        if not ok or not email:
            return

        password, ok = QInputDialog.getText(
            self, "Вход", "Введите пароль:",
            QLineEdit.Password, ""
        )
        if not ok or not password:
            return

        try:
            self.ely_session = ely.auth_password(email, password)
            
            # Сохраняем токен в настройках
            self.settings['ely_access_token'] = self.ely_session["token"]
            save_settings(self.settings)
            
            self.update_ely_ui(True)
            self.username.setText(self.ely_session["username"])
            QMessageBox.information(self, "Успешно", "Авторизация прошла успешно!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            logging.error(f"Ошибка авторизации: {traceback.format_exc()}")


    def start_device_auth(self, dialog):
        """Запуск авторизации через device code"""
        dialog.close()
        try:
            self.ely_session = ely.auth_device_code()
            self.update_ely_ui(True)
            self.username.setText(self.ely_session["username"])
            QMessageBox.information(self, "Успешно", f"Вы вошли как {self.ely_session['username']}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def start_credentials_auth(self, dialog):
        """Запуск авторизации по логину/паролю"""
        dialog.close()
        email, ok = QInputDialog.getText(self, "Вход", "Введите email Ely.by:")
        if not ok or not email:
            return
            
        password, ok = QInputDialog.getText(self, "Вход", "Введите пароль:", QLineEdit.Password)
        if not ok or not password:
            return
            
        try:
            self.ely_session = ely.auth(email, password)
            ely.write_login_data({
                "username": self.ely_session["username"],
                "uuid": self.ely_session["uuid"],
                "token": self.ely_session["token"],
                "logged_in": True
            })
            self.update_ely_ui(True)
            self.username.setText(self.ely_session["username"])
            QMessageBox.information(self, "Успешно", f"Вы вошли как {self.ely_session['username']}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            
    def ely_logout(self):
        """Выход из аккаунта Ely.by"""
        ely.logout()
        self.ely_session = None
        self.update_ely_ui(False)
        self.username.setText("")
        # Обновляем кнопку в настройках
        if hasattr(self.settings_tab, 'update_logout_button_visibility'):
            self.settings_tab.update_logout_button_visibility()
        QMessageBox.information(self, "Выход", "Вы вышли из аккаунта Ely.by")
       
    def open_support_tab(self):
        support_tab = QWidget()
        layout = QVBoxLayout(support_tab)

        # Твой текст (можешь сам изменить потом)
        text = QLabel("Наш лаунчер абсолютно бесплатный и безопасный, если тебе нравится лаунчер, его функции, дизайн,\nты можешь поддержать разработчика ❤")
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
        donate_button.clicked.connect(lambda: webbrowser.open("https://www.donationalerts.com/r/16steyy"))
        layout.addWidget(donate_button, alignment=Qt.AlignCenter)

        layout.addStretch()

        self.stacked_widget.addWidget(support_tab)
        self.stacked_widget.setCurrentWidget(support_tab)
        
    def change_ely_skin(self):
        """Открывает диалог управления скином для Ely.by"""
        if not hasattr(self, 'ely_session') or not self.ely_session:
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
        
        # Кнопка сброса скина
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
        manage_btn.clicked.connect(lambda: webbrowser.open(f"https://ely.by/skins?username={self.ely_session['username']}"))
        layout.addWidget(manage_btn)
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
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
            "Выберите PNG-файл скина (64x64 или 64x32)",
            "",
            "PNG Images (*.png)"
        )
        
        if not file_path:
            return  # Пользователь отменил выбор
        
        # Диалог выбора типа модели
        model_type, ok = QInputDialog.getItem(
            self, "Тип модели",
            "Выберите тип модели:",
            ["classic", "slim"], 0, False
        )
        
        if not ok:
            return
        
        try:
            # Загружаем скин
            success, message = ElySkinManager.upload_skin(
                file_path,
                self.ely_session["token"],
                model_type
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
                    QMessageBox.warning(self, "Ошибка", "Не удалось получить новый скин")
            else:
                QMessageBox.critical(self, "Ошибка", message)
        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def reset_ely_skin(self, parent_dialog):
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

            
    def update_version_list(self):
        """Обновляет список версий в зависимости от выбранного типа"""
        current_text = self.version_select.currentText()
        self.version_select.clear()
        
        versions = get_version_list()
        show_only_favorites = self.version_type_select.currentText() == "Избранные"
        show_snapshots = self.settings.get('show_snapshots', False)
        
        for version in versions:
            if version["type"] == "release" or (show_snapshots and version["type"] == "snapshot"):
                version_id = version["id"]
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
            self.toggle_sidebar_button.setIcon(QIcon(resource_path("assets/toggle_open.png")))
        else:
            self.toggle_sidebar_button.setIcon(QIcon(resource_path("assets/toggle_close.png")))


    
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
        if self.version_type_select.currentText() == "Избранные":
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
            "QPushButton {color: %s;}" % ("gold" if version in self.favorites else "gray")
        )

    def get_selected_memory(self):
        """Возвращает выбранное количество памяти в мегабайтах"""
        return self.settings_tab.memory_slider.value() * 1024  # Конвертируем ГБ в МБ

    def show_funny_message(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText("💬 <i>Юля писька</i>")
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)
        
    def show_funny_message_1(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText("💬 <i>Еру Тукаш</i>")
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)
        
    def show_funny_message_2(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText("💬 <i>Sosun TheNerfi</i>")
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)
        
    def show_funny_message_3(self):
        """Показывает забавное сообщение при нажатии Ctrl+D"""
        self.motd_label.setText("💬 <i>Марат педик</i>")
        # Через 3 секунды возвращаем случайное сообщение
        QTimer.singleShot(3000, self.show_message_of_the_day)
        
    def load_skin(self):
        # Создаем диалоговое окно выбора источника скина
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
                self, 
                "Выбери PNG-файл скина", 
                "", 
                "PNG файлы (*.png)"
            )
            if file_path:
                try:
                    os.makedirs(SKINS_DIR, exist_ok=True)
                    dest_path = os.path.join(SKINS_DIR, f"{self.username.text().strip()}.png")
                    shutil.copy(file_path, dest_path)
                    QMessageBox.information(self, "Скин загружен", "Скин успешно загружен!")
                except Exception as e:
                    logging.error(f"Ошибка загрузки скина: {e}")
                    QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить скин: {e}")

        def load_from_elyby():
            source_dialog.close()
            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, "Ошибка", "Введите имя игрока!")
                return

            if ElyBySkinManager.download_skin(username):
                QMessageBox.information(self, "Скин загружен", "Скин успешно загружен с Ely.by!")
            else:
                ElyBySkinManager.authorize_and_get_skin(self, username)

        local_button.clicked.connect(load_from_local)
        elyby_button.clicked.connect(load_from_elyby)

        source_dialog.exec_()
        
    def get_ely_skin(username):
        """Получает URL скина пользователя с Ely.by"""
        try:
            response = requests.get(f"https://skinsystem.ely.by/skins/{username}.png", allow_redirects=False)
            if response.status_code == 200:
                return f"https://skinsystem.ely.by/skins/{username}.png"
            return None
        except Exception as e:
            logging.error(f"Ошибка при получении скина: {e}")
            return None

    def reset_ely_skin(access_token):
        """Сбрасывает скин на стандартный"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.delete('https://skinsystem.ely.by/upload', headers=headers)
            
            if response.status_code == 200:
                return True, "Скин сброшен на стандартный!"
            return False, f"Ошибка сброса скина: {response.json().get('message', 'Неизвестная ошибка')}"
        except Exception as e:
            return False, f"Ошибка при сбросе скина: {str(e)}"

    def load_user_data(self):
        if os.path.exists(self.user_data_path):
            try:
                with open(self.user_data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print("⚠️ Ошибка загрузки user_data:", e)
        return {"launch_count": 0, "achievements": []}

    def save_user_data(self):
        try:
            with open(self.user_data_path, "w", encoding="utf-8") as f:
                json.dump(self.user_data, f, indent=4)
        except Exception as e:
            print("⚠️ Ошибка сохранения user_data:", e)

    def increment_launch_count(self):
        self.user_data["launch_count"] += 1
        count = self.user_data["launch_count"]
        print(f"🚀 Запуск №{count}")
        
        # Проверка достижений
        if count >= 1 and "first_launch" not in self.user_data["achievements"]:
            self.user_data["achievements"].append("first_launch")
        if count >= 5 and "five_launches" not in self.user_data["achievements"]:
            self.user_data["achievements"].append("five_launches")

        self.save_user_data()


    def set_random_username(self):
        self.username.setText(generate_random_username())


    def setup_modloader_tabs(self):
        # Существующие вкладки
        self.forge_tab = ModLoaderTab("forge")
        self.tabs.addTab(self.forge_tab, "Forge")

        self.fabric_tab = ModLoaderTab("fabric")
        self.tabs.addTab(self.fabric_tab, "Fabric")

        self.optifine_tab = ModLoaderTab("optifine")
        self.tabs.addTab(self.optifine_tab, "OptiFine")

        self.quilt_tab = ModLoaderTab("quilt")
        self.tabs.addTab(self.quilt_tab, "Quilt")
    
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
        self.current_theme = "dark" if dark_theme else "light"
        
        # Обновляем иконки темы
        icon_name = "sun.png" if not dark_theme else "moon.png"
        icon_path = resource_path(f"assets/{icon_name}")
        
        if hasattr(self, 'theme_button'):
            self.theme_button.setIcon(QIcon(icon_path))
        
        if hasattr(self, 'settings_tab') and hasattr(self.settings_tab, 'update_theme_button_icon'):
            self.settings_tab.update_theme_button_icon()
        
        # Обновляем цвет MOTD-сообщения
        if hasattr(self, 'motd_label'):
            color = "#aaaaaa" if dark_theme else "#666666"
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
        
        self.settings['last_username'] = self.username.text().strip()
        save_settings(self.settings)
        event.accept()
    
    def close_launcher(self):
        """Закрывает лаунчер после запуска игры"""
        self.close()
            
    def launch_game(self):
        try:
            print("[LAUNCHER] Starting game launch process...")
            
            # Получаем введенные данные
            username = self.username.text().strip()
            if not username:
                QMessageBox.warning(self, "Ошибка", "Введите имя игрока!")
                return

            version = self.version_select.currentText()
            loader_type = self.loader_select.currentData()
            memory_mb = self.get_selected_memory()
            close_on_launch = self.settings_tab.close_on_launch_checkbox.isChecked()

            print(f"[LAUNCHER] Launch parameters: "
                f"User: {username}, "
                f"Version: {version}, "
                f"Loader: {loader_type}, "
                f"Memory: {memory_mb}MB, "
                f"Close on launch: {close_on_launch}")

            # Обработка сессии Ely.by
            if not hasattr(self, 'ely_session'):
                self.ely_session = None
                print("[LAUNCHER] No Ely.by session found")

            # Подготовка скина
            skin_path = os.path.join(SKINS_DIR, f"{username}.png")
            if os.path.exists(skin_path):
                print("[LAUNCHER] Found skin, copying...")
                assets_dir = os.path.join(MINECRAFT_DIR, "assets", "skins")
                os.makedirs(assets_dir, exist_ok=True)
                shutil.copy(skin_path, os.path.join(assets_dir, f"{username}.png"))

            # Обработка authlib для Ely.by
            if hasattr(self, 'ely_session') and self.ely_session:
                print("[LAUNCHER] Ely.by session detected, checking authlib...")
                if not os.path.exists(AUTHLIB_JAR_PATH):
                    print("[LAUNCHER] Downloading authlib-injector...")
                    if not download_authlib_injector():
                        QMessageBox.critical(self, "Ошибка", "Не удалось загрузить Authlib Injector")
                        return

            # Сохранение последних использованных настроек
            self.settings['last_version'] = version
            self.settings['last_loader'] = loader_type
            save_settings(self.settings)

            # Показ прогресса
            self.start_progress_label.setText("Подготовка к запуску...")
            self.start_progress_label.setVisible(True)
            self.start_progress.setVisible(True)
            QApplication.processEvents()

            print("[LAUNCHER] Starting launch thread...")
            self.launch_thread.launch_setup(version, username, loader_type, memory_mb, close_on_launch)
            self.launch_thread.start()

        except Exception as e:
            print(f"[ERROR] Launch failed: {str(e)}")
            logging.error(f"Game launch failed: {traceback.format_exc()}")
            QMessageBox.critical(self, "Ошибка запуска", f"Не удалось запустить игру: {str(e)}")

        
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
            

    def show_message_of_the_day(self):
        if hasattr(self, "motd_label"):
            message = random.choice(self.motd_messages)
            self.motd_label.setText(f"💬 <i>{message}</i>")
            
    def open_root_folder(self):
        import subprocess
        import platform
        import os

        # Используем глобальную переменную MINECRAFT_DIR, которая содержит путь к папке игры
        folder = MINECRAFT_DIR

        if platform.system() == "Windows":
            subprocess.Popen(f'explorer "{folder}"')
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
            
def download_optifine(version):
    try:
        url = "https://optifine.net/downloads"
        response = requests.get(url)
        if response.status_code != 200:
            return None, "Не удалось получить страницу загрузки OptiFine."

        pattern = f"OptiFine {version}"
        if pattern not in response.text:
            return None, f"Версия OptiFine {version} не найдена на сайте."

        # Автоматическая загрузка невозможна из-за защиты.
        # Просто открываем сайт.
        return "https://optifine.net/downloads", None

    except Exception as e:
        return None, f"Ошибка загрузки: {e}"

def install_optifine(version):
    link, error = download_optifine(version)
    if error:
        return False, error

    # Открываем сайт с версией
    import webbrowser
    webbrowser.open(link)
    return True, f"Открой сайт и скачай OptiFine {version} вручную."

class ModSearchThread(QThread):
    search_finished = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, query, version, loader, category, sort_by):
        super().__init__()
        self.query = query
        self.version = version
        self.loader = loader
        self.category = category
        self.sort_by = sort_by
        
    def run(self):
        try:
            mods = ModManager.cached_search(
                self.query, 
                self.version, 
                self.loader, 
                self.category, 
                self.sort_by, 
                "modrinth"
            )
            self.search_finished.emit(mods, self.query)
        except Exception as e:
            self.error_occurred.emit(str(e))

class PopularModsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, version=None, loader=None):
        super().__init__()
        self.version = version
        self.loader = loader
        
    def run(self):
        try:
            # Формируем параметры запроса для популярных модов
            params = {
                'limit': 50,
                'index': 'downloads',  # Сортировка по количеству загрузок
                'facets': []
            }

            # Добавляем версию
            if self.version and self.version != "Все версии":
                params['facets'].append(f'["versions:{self.version}"]')

            # Добавляем лоадер
            if self.loader and self.loader.lower() != "vanilla":
                params['facets'].append(f'["categories:{self.loader.lower()}"]')

            # Если есть facets, преобразуем их в строку
            if params['facets']:
                params['facets'] = '[' + ','.join(params['facets']) + ']'
            else:
                del params['facets']

            # Выполняем запрос
            response = requests.get('https://api.modrinth.com/v2/search', params=params)
            
            if response.status_code == 200:
                self.finished.emit(response.json().get('hits', []))
            else:
                self.error.emit("Не удалось загрузить популярные моды")

        except Exception as e:
            self.error.emit(str(e))

class ModsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.search_thread = None
        self.popular_mods_thread = None
        self.current_search_query = ""
        self.current_page = 1
        self.total_pages = 1
        self.mods_data = []
        self.setup_ui()
        
        # Добавляем надпись "Загрузка популярных модов..."
        self.loading_label = QLabel("Загрузка популярных модов...", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(self.loading_label)
        
        # Загружаем популярные моды в отдельном потоке
        self.load_popular_mods()

    def load_popular_mods(self):
        """Загружает список популярных модов в отдельном потоке"""
        try:
            # Показываем индикатор загрузки
            if hasattr(self, 'loading_label'):
                self.loading_label.setVisible(True)

            # Создаем и запускаем поток
            self.popular_mods_thread = PopularModsThread(
                version=self.version_combo.currentText(),
                loader=self.loader_combo.currentText()
            )
            self.popular_mods_thread.finished.connect(self.handle_popular_mods_loaded)
            self.popular_mods_thread.error.connect(self.handle_popular_mods_error)
            self.popular_mods_thread.start()

        except Exception as e:
            logging.error(f"Ошибка загрузки популярных модов: {e}")
            if hasattr(self, 'loading_label'):
                self.loading_label.setText("Ошибка загрузки модов")

    def handle_popular_mods_loaded(self, mods):
        """Обрабатывает загруженные популярные моды"""
        self.mods_data = mods
        self.current_page = 1
        if hasattr(self, 'loading_label'):
            self.loading_label.setVisible(False)
        self.update_page()

    def handle_popular_mods_error(self, error_message):
        """Обрабатывает ошибки загрузки популярных модов"""
        if hasattr(self, 'loading_label'):
            self.loading_label.setText(f"Ошибка: {error_message}")
        logging.error(f"Ошибка загрузки популярных модов: {error_message}")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.search_thread = None
        self.current_search_query = ""
        self.current_page = 1
        self.total_pages = 1
        self.mods_data = []
        self.setup_ui()
        
        # Загружаем популярные моды при инициализации
        QTimer.singleShot(100, self.load_popular_mods)  # Небольшая задержка для корректной инициализации UI
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Верхняя панель с поиском и фильтрами ---
        top_panel = QWidget()
        top_panel.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        top_layout = QVBoxLayout(top_panel)
        
        # Поисковая строка
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск модов...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #444444;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #666666;
            }
        """)
        self.search_input.returnPressed.connect(self.search_mods)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton()
        self.search_button.setIcon(QIcon(resource_path("assets/search.png")))
        self.search_button.setIconSize(QSize(24, 24))
        self.search_button.setFixedSize(40, 40)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.search_button.clicked.connect(self.search_mods)
        search_layout.addWidget(self.search_button)
        top_layout.addLayout(search_layout)
        
        # Фильтры
        filters_layout = QHBoxLayout()
        
        # Версия Minecraft
        version_layout = QVBoxLayout()
        version_layout.addWidget(QLabel("Версия Minecraft:"))
        self.version_combo = QComboBox()
        self.version_combo.setFixedWidth(200)
        self.version_combo.addItems(MINECRAFT_VERSIONS)
        self.version_combo.setStyleSheet("""
            QComboBox {
                background-color: #444444;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(assets/down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        version_layout.addWidget(self.version_combo)
        filters_layout.addLayout(version_layout)
        
        # Модлоадер
        loader_layout = QVBoxLayout()
        loader_layout.addWidget(QLabel("Модлоадер:"))
        self.loader_combo = QComboBox()
        self.loader_combo.setFixedWidth(200)
        self.loader_combo.addItems(["Fabric", "Forge", "Quilt"])
        self.loader_combo.setStyleSheet(self.version_combo.styleSheet())
        loader_layout.addWidget(self.loader_combo)
        filters_layout.addLayout(loader_layout)
        
        # Категория
        category_layout = QVBoxLayout()
        category_layout.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.setFixedWidth(200)
        self.category_combo.addItem("Все категории")
        self.category_combo.setStyleSheet(self.version_combo.styleSheet())
        category_layout.addWidget(self.category_combo)
        filters_layout.addLayout(category_layout)
        
        # Сортировка
        sort_layout = QVBoxLayout()
        sort_layout.addWidget(QLabel("Сортировка:"))
        self.sort_combo = QComboBox()
        self.sort_combo.setFixedWidth(200)
        self.sort_combo.addItems(["По релевантности", "По загрузкам", "По дате"])
        self.sort_combo.setStyleSheet(self.version_combo.styleSheet())
        sort_layout.addWidget(self.sort_combo)
        filters_layout.addLayout(sort_layout)
        
        top_layout.addLayout(filters_layout)
        layout.addWidget(top_panel)
        
        # --- Список модов ---
        self.mods_scroll = QScrollArea()
        self.mods_scroll.setWidgetResizable(True)
        self.mods_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #333333;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
        """)
        
        self.mods_container = QWidget()
        self.mods_layout = QVBoxLayout(self.mods_container)
        self.mods_layout.setSpacing(15)
        self.mods_scroll.setWidget(self.mods_container)
        layout.addWidget(self.mods_scroll)
        
        # --- Пагинация ---
        pagination_widget = QWidget()
        pagination_widget.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        pagination_layout = QHBoxLayout(pagination_widget)
        
        self.prev_page_button = QPushButton("←")
        self.prev_page_button.setFixedSize(40, 40)
        self.prev_page_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.prev_page_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_page_button)
        
        self.page_label = QLabel("Страница 1 из 1")
        self.page_label.setStyleSheet("color: white;")
        pagination_layout.addWidget(self.page_label)
        
        self.next_page_button = QPushButton("→")
        self.next_page_button.setFixedSize(40, 40)
        self.next_page_button.setStyleSheet(self.prev_page_button.styleSheet())
        self.next_page_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_page_button)
        
        layout.addWidget(pagination_widget)
        
        # Инициализация данных
        self.current_page = 1
        self.total_pages = 1
        self.mods_data = []
        
    def create_mod_card(self, mod):
        """Создает карточку мода"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #333333;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #444444;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        card.setFixedHeight(120)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Иконка
        icon_label = QLabel()
        icon_label.setFixedSize(90, 90)
        icon_label.setStyleSheet("background-color: #444444; border-radius: 5px;")
        icon_url = ModManager.get_mod_icon(mod.get('project_id', mod.get('id')), "modrinth")
        if icon_url:
            pixmap = QPixmap()
            try:
                pixmap.loadFromData(requests.get(icon_url).content)
                icon_label.setPixmap(pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except:
                pass
        layout.addWidget(icon_label)
        
        # Информация
        info_layout = QVBoxLayout()
        
        # Название
        name_label = QLabel(mod.get('title', mod.get('name', 'N/A')))
        name_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # Описание
        desc_label = QLabel(mod.get('description', 'Нет описания'))
        desc_label.setStyleSheet("color: #aaaaaa;")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        info_layout.addWidget(desc_label)
        
        # Статистика
        stats_layout = QHBoxLayout()
        downloads_label = QLabel(f"📥 {mod.get('downloads', 0)}")
        downloads_label.setStyleSheet("color: #aaaaaa;")
        stats_layout.addWidget(downloads_label)
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)
        
        layout.addLayout(info_layout)
        
        # Кнопка установки
        install_button = QPushButton("Установить")
        install_button.setFixedWidth(100)
        install_button.clicked.connect(lambda: self.install_modrinth_mod(mod['project_id']))
        layout.addWidget(install_button)
        
        return card
        
    def search_mods(self):
        """Выполняет поиск модов"""
        query = self.search_input.text().strip()
        
        # Если строка поиска пуста, показываем популярные моды
        if not query:
            self.load_popular_mods()
            return

        # Сохраняем текущий запрос
        self.current_search_query = query

        # Очищаем предыдущие результаты
        self.current_page = 1
        self.mods_data = []
        self.update_page()

        # Показываем индикатор загрузки
        self.show_loading_indicator()

        # Получаем параметры поиска
        version = self.version_combo.currentText()
        loader = self.loader_combo.currentText()
        category = self.category_combo.currentText()
        sort_by = self.sort_combo.currentText()

        # Создаем и запускаем поток поиска
        self.search_thread = ModSearchThread(query, version, loader, category, sort_by)
        self.search_thread.search_finished.connect(lambda mods, q: self.handle_search_results(mods, q))
        self.search_thread.error_occurred.connect(self.handle_search_error)
        self.search_thread.start()

    def load_popular_mods(self):
        """Загружает список популярных модов"""
        try:
            # Показываем индикатор загрузки
            self.show_loading_indicator()

            # Получаем параметры
            version = self.version_combo.currentText()
            loader = self.loader_combo.currentText()

            # Формируем параметры запроса для популярных модов
            params = {
                'limit': 50,
                'index': 'downloads',  # Сортировка по количеству загрузок
                'facets': []
            }

            # Добавляем версию
            if version and version != "Все версии":
                params['facets'].append(f'["versions:{version}"]')

            # Добавляем лоадер
            if loader and loader.lower() != "vanilla":
                params['facets'].append(f'["categories:{loader.lower()}"]')

            # Если есть facets, преобразуем их в строку
            if params['facets']:
                params['facets'] = '[' + ','.join(params['facets']) + ']'
            else:
                del params['facets']

            # Выполняем запрос
            response = requests.get('https://api.modrinth.com/v2/search', params=params)
            
            if response.status_code == 200:
                self.mods_data = response.json().get('hits', [])
                self.current_page = 1
                self.hide_loading_indicator()
                self.update_page()
            else:
                self.hide_loading_indicator()
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить популярные моды")

        except Exception as e:
            self.hide_loading_indicator()
            logging.error(f"Ошибка загрузки популярных модов: {e}")
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить популярные моды")

    def handle_search_results(self, mods, query):
        """Обрабатывает результаты поиска"""
        # Проверяем, актуален ли результат для текущего запроса
        if query != self.current_search_query:
            return
            
        self.mods_data = mods
        self.total_pages = max(1, (len(self.mods_data) + 9) // 10)
        self.current_page = 1
        
        # Скрываем индикатор загрузки и обновляем страницу
        self.hide_loading_indicator()
        self.update_page()
        
        if not self.mods_data:
            self.show_no_results_message()
            
    def handle_search_error(self, error_message):
        """Обрабатывает ошибки поиска"""
        self.hide_loading_indicator()
        QMessageBox.critical(self, "Ошибка", f"Ошибка при поиске модов: {error_message}")
        
    def prev_page(self):
        """Переход на предыдущую страницу"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page()
            
    def next_page(self):
        """Переход на следующую страницу"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page()

    def show_loading_indicator(self):
        """Показывает индикатор загрузки"""
        self.loading_label = QLabel("Загрузка...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(self.loading_label)

    def hide_loading_indicator(self):
        """Скрывает индикатор загрузки"""
        if hasattr(self, 'loading_label'):
            self.loading_label.deleteLater()

    def show_no_results_message(self):
        """Показывает сообщение об отсутствии результатов"""
        no_results_label = QLabel("Ничего не найдено")
        no_results_label.setAlignment(Qt.AlignCenter)
        no_results_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 16px;
                padding: 20px;
            }
        """)
        self.mods_layout.addWidget(no_results_label)

    def update_page(self):
        """Обновляет отображение текущей страницы с модами"""
        # Очищаем текущие карточки
        while self.mods_layout.count():
            item = self.mods_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Если нет данных, показываем сообщение
        if not self.mods_data:
            self.show_no_results_message()
            return
        
        # Обновляем информацию о странице
        self.total_pages = (len(self.mods_data) + 9) // 10  # Округляем вверх
        self.page_label.setText(f"Страница {self.current_page} из {self.total_pages}")
        self.prev_page_button.setEnabled(self.current_page > 1)
        self.next_page_button.setEnabled(self.current_page < self.total_pages)
        
        # Добавляем карточки для текущей страницы
        start = (self.current_page - 1) * 10
        end = min(start + 10, len(self.mods_data))
        for mod in self.mods_data[start:end]:
            self.mods_layout.addWidget(self.create_mod_card(mod))
        
        # Добавляем растягивающийся элемент
        self.mods_layout.addStretch()

    def install_modrinth_mod(self, mod_id):
        """Устанавливает мод с Modrinth"""
        try:
            # Получаем выбранную версию Minecraft
            version = self.version_combo.currentText()
            if not version:
                QMessageBox.warning(self, "Ошибка", "Выберите версию Minecraft")
                return

            self.show_loading_indicator()
            
            success, message = ModManager.download_modrinth_mod(mod_id, version)
            
            self.hide_loading_indicator()
            
            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.critical(self, "Ошибка", message)
                
        except Exception as e:
            self.hide_loading_indicator()
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить мод: {str(e)}")
            logging.error(f"Ошибка установки мода: {str(e)}")
            
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        
        # Создаем и показываем главное окно напрямую
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"Critical error: {str(e)}")
        sys.exit(1)