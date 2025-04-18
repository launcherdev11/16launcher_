import subprocess
import os
import sys
import logging
import json
import random
from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QComboBox, QProgressBar, QPushButton, QApplication, 
                            QMainWindow, QFileDialog, QDialog, QFormLayout, 
                            QSlider, QMessageBox, QTabWidget, QFrame, QStackedWidget, QCheckBox, QScrollArea, QTextEdit, QListWidget, QToolButton, QStyle)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QFontDatabase
from minecraft_launcher_lib.utils import get_minecraft_directory, get_version_list
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.forge import find_forge_version, install_forge_version
from minecraft_launcher_lib.fabric import get_all_minecraft_versions, install_fabric as fabric_install
from minecraft_launcher_lib.fabric import get_latest_loader_version
from minecraft_launcher_lib.command import get_minecraft_command
from random_username.generate import generate_username
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
            else:
                self.finished_signal.emit(False, f"Неизвестный тип модлоадера: {self.loader_type}")
        except Exception as e:
            self.finished_signal.emit(False, f"Критическая ошибка: {str(e)}")
            logging.error(f"Ошибка установки {self.loader_type}: {str(e)}", exc_info=True)

    def install_fabric(self):
        """Установка Fabric с расширенной обработкой ошибок и резервными методами"""
        try:
            # 1. Проверка интернет-соединения
            if not self._check_internet_connection():
                self.finished_signal.emit(False, "Требуется интернет-соединение для установки Fabric")
                return

            # 2. Получение списка версий (с резервными методами)
            fabric_versions = self._get_fabric_versions_with_fallback()
            if not fabric_versions:
                self.finished_signal.emit(False, "Не удалось получить список версий Fabric")
                return

            # 3. Проверка поддержки версии
            if self.mc_version not in fabric_versions:
                available = "\n".join(fabric_versions[:10])
                self.finished_signal.emit(False, 
                    f"Версия {self.mc_version} не поддерживается\nДоступные версии:\n{available}")
                return

            # 4. Установка Fabric
            self._perform_fabric_installation()
            
        except Exception as e:
            self.finished_signal.emit(False, f"Критическая ошибка: {str(e)}")
            logging.error(f"Fabric installation failed: {str(e)}", exc_info=True)

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

    def install_loader(self):
        mc_version = self.mc_version_combo.currentText()
        
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
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information if success else QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Результат установки")
        msg.exec_()

class LaunchThread(QThread):
    launch_setup_signal = pyqtSignal(str, str, str, int, bool)  # Добавили bool для close_on_launch
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)
    close_launcher_signal = pyqtSignal()  # Новый сигнал для закрытия лаунчера

    def __init__(self):
        super().__init__()
        self.launch_setup_signal.connect(self.launch_setup)
        self.loader_type = None
        self.memory_mb = 4096
        self.close_on_launch = False  # По умолчанию не закрываем

    def launch_setup(self, version_id, username, loader_type, memory_mb, close_on_launch):
        self.version_id = version_id
        self.username = username
        self.loader_type = loader_type
        self.memory_mb = memory_mb
        self.close_on_launch = close_on_launch
    
    def run(self):
        try:
            logging.debug(f"Запуск Minecraft {self.version_id} ({self.loader_type}) для {self.username} с памятью {self.memory_mb}MB")
            self.state_update_signal.emit(True)
            
            # Определяем фактическую версию для запуска
            if self.loader_type == "forge":
                forge_version = find_forge_version(self.version_id)
                if forge_version:
                    launch_version = f"{self.version_id}-forge-{forge_version.split('-')[-1]}"
                else:
                    launch_version = self.version_id
            elif self.loader_type == "fabric":
                try:
                    loader_version = get_latest_loader_version()
                    launch_version = f"fabric-loader-{loader_version}-{self.version_id}"
                except:
                    launch_version = self.version_id
            else:
                launch_version = self.version_id
                
            # Проверяем наличие скина
            skin_path = os.path.join(SKINS_DIR, f"{self.username}.png")
            if os.path.exists(skin_path):
                # Копируем скин в нужное место
                assets_dir = os.path.join(MINECRAFT_DIR, "assets", "skins")
                os.makedirs(assets_dir, exist_ok=True)
                shutil.copy(skin_path, os.path.join(assets_dir, f"{self.username}.png"))

            # Установка версии Minecraft
            install_minecraft_version(
                versionid=launch_version,
                minecraft_directory=MINECRAFT_DIR,
                callback={
                    'setStatus': lambda value: self.progress_update_signal.emit(0, 100, value),
                    'setProgress': lambda value: self.progress_update_signal.emit(value, 100, ''),
                    'setMax': lambda value: self.progress_update_signal.emit(0, value, '')
                }
            )
            
            if not self.username:
                self.username = generate_random_username()
            
            # Формируем JVM аргументы с выбранным количеством памяти
            options = {
                'username': self.username, 
                'uuid': str(uuid1()), 
                'token': '',
                'jvmArguments': [
                    f'-Xmx{self.memory_mb}M',  # Максимальная память
                    f'-Xms{min(self.memory_mb // 2, 2048)}M'  # Начальная память (не более 2ГБ)
                ]
            }
            
            # Запускаем Minecraft без ожидания завершения
            minecraft_process = subprocess.Popen(
                get_minecraft_command(
                    version=launch_version, 
                    minecraft_directory=MINECRAFT_DIR, 
                    options=options
                ),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # Если нужно закрыть лаунчер - отправляем сигнал
            if self.close_on_launch:
                self.close_launcher_signal.emit()
                
            self.state_update_signal.emit(False)
        except Exception as e:
            logging.error(f"Ошибка при запуске Minecraft: {e}")
            self.state_update_signal.emit(False)

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # Сохраняем ссылку на главное окно
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
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

        self.directory_edit = QLineEdit(self)
        self.directory_edit.setText(MINECRAFT_DIR)
        layout.addRow("Директория игры:", self.directory_edit)

        self.choose_directory_button = QPushButton("Выбрать папку", self)
        self.choose_directory_button.clicked.connect(self.choose_directory)
        layout.addRow(self.choose_directory_button)

        self.open_directory_button = QPushButton("Открыть корневую папку", self)
        self.open_directory_button.clicked.connect(self.open_directory)
        layout.addRow(self.open_directory_button)

        # Загружаем настройки один раз
        settings = self.parent_window.settings if self.parent_window else load_settings()
        if 'close_on_launch' in settings:
            self.close_on_launch_checkbox.setChecked(settings['close_on_launch'])
        if 'memory' in settings:
            self.memory_slider.setValue(settings['memory'])
        if 'minecraft_directory' in settings:
            self.directory_edit.setText(settings['minecraft_directory'])

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
                'minecraft_directory': self.directory_edit.text()
                # Убрали сохранение last_username здесь
            }
            save_settings(self.parent_window.settings)

def load_settings():
    default_settings = {
        'close_on_launch': False,
        'memory': 4,
        'minecraft_directory': MINECRAFT_DIR,
        'last_username': '',
        'favorites': [],  # Добавляем список избранных версий
        'last_version': '',  # Последняя выбранная версия
        'last_loader': 'vanilla',  # Последний выбранный загрузчик
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        setup_directories()
        self.setWindowTitle("16Launcher 1.0.1")
        self.setFixedSize(1000, 700)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        # Сначала загружаем настройки
        self.settings = load_settings()
        self.last_username = self.settings.get('last_username', '')
        self.favorites = self.settings.get('favorites', [])
        self.last_version = self.settings.get('last_version', '')
        self.last_loader = self.settings.get('last_loader', 'vanilla')

        # Затем создаем UI элементы
        self.launch_thread = LaunchThread()
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)
        self.launch_thread.close_launcher_signal.connect(self.close_launcher)

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
        
        self.tabs = QTabWidget()
        self.tab_layout.addWidget(self.tabs)

        self.game_tab = QWidget()
        self.setup_game_tab()
        self.tabs.addTab(self.game_tab, "Запуск игры")

        self.setup_modloader_tabs()
        
        self.stacked_widget.addWidget(self.tab_widget)
        self.settings_tab = SettingsTab(self)  # Передаем self как родителя
        self.stacked_widget.addWidget(self.settings_tab)
        self.stacked_widget.setCurrentIndex(0)
        
        self.apply_dark_theme()

    def setup_sidebar(self):
        """Настройка боковой панели с кнопками"""
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setFixedWidth(100)  # Увеличенная ширина боковой панели
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)  # Увеличенные отступы
        sidebar_layout.setSpacing(20)  # Увеличенное расстояние между кнопками
        
        # Увеличенные кнопки с иконками
        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon(resource_path("assets/play64.png")))
        self.play_button.setIconSize(QSize(64, 64))
        self.play_button.setFixedSize(75, 75)  # Увеличенный размер
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
        sidebar_layout.addWidget(self.play_button, alignment=Qt.AlignCenter)
        
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(resource_path("assets/set64.png")))
        self.settings_button.setIconSize(QSize(64, 64))
        self.settings_button.setFixedSize(75, 75)
        self.settings_button.setStyleSheet("""
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
        self.settings_button.clicked.connect(self.show_settings_tab)
        sidebar_layout.addWidget(self.settings_button, alignment=Qt.AlignCenter)
        
        self.news_button = QPushButton()
        self.news_button.setIcon(QIcon(resource_path("assets/news64.png")))
        self.news_button.setIconSize(QSize(64, 64))
        self.news_button.setFixedSize(75, 75)
        self.news_button.setStyleSheet("""
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
        self.news_button.clicked.connect(self.show_news_tab)
        sidebar_layout.addWidget(self.news_button, alignment=Qt.AlignCenter)
        
        sidebar_layout.addStretch()
        self.main_layout.addWidget(sidebar)
    
    def show_game_tab(self):
        """Переключает на вкладку с игрой"""
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.setCurrentIndex(0)  # Убедимся, что выбрана первая вкладка (Запуск игры)
    
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

        self.start_button = QPushButton("Играть")
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.launch_game)
        bottom_row.addWidget(self.start_button)

        self.load_skin_button = QPushButton("Сменить скин")
        self.load_skin_button.setMinimumHeight(50)
        self.load_skin_button.clicked.connect(self.load_skin)
        bottom_row.addWidget(self.load_skin_button)

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
            
    def update_version_list(self):
        """Обновляет список версий в зависимости от выбранного типа"""
        current_text = self.version_select.currentText()
        self.version_select.clear()
        
        versions = get_version_list()
        show_only_favorites = self.version_type_select.currentText() == "Избранные"
        
        for version in versions:
            if version["type"] == "release":
                version_id = version["id"]
                # Показываем только избранные или все версии
                if not show_only_favorites or version_id in self.favorites:
                    self.version_select.addItem(version_id)
        
        # Восстанавливаем текущий выбор, если он доступен
        if current_text and self.version_select.findText(current_text) >= 0:
            self.version_select.setCurrentText(current_text)
        
        # Обновляем состояние кнопки избранного
        self.update_favorite_button()
    
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

        
    def load_skin(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбери PNG-файл скина", "", "PNG файлы (*.png)")
        if file_path:
            try:
                # Создаем папку для скинов, если ее нет
                os.makedirs(SKINS_DIR, exist_ok=True)
                
                # Копируем скин в нужное место
                dest_path = os.path.join(SKINS_DIR, f"{self.username.text().strip()}.png")
                shutil.copy(file_path, dest_path)
                
                QMessageBox.information(self, "Скин загружен", "Скин успешно загружен!")
            except Exception as e:
                logging.error(f"Ошибка загрузки скина: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить скин: {e}")

    def set_random_username(self):
        self.username.setText(generate_username()[0])

    def setup_modloader_tabs(self):
        self.forge_tab = ModLoaderTab("forge")
        self.tabs.addTab(self.forge_tab, "Forge")

        self.fabric_tab = ModLoaderTab("fabric")
        self.tabs.addTab(self.fabric_tab, "Fabric")

        self.optifine_tab = ModLoaderTab("optifine")
        self.tabs.addTab(self.optifine_tab, "OptiFine")
    
    def apply_dark_theme(self):
        dark_theme = """
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
            padding: 10px 30px 10px 10px;  /* Добавлен правый отступ для иконки */
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

        /* Стиль для кнопки с иконкой внутри QLineEdit */
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

        QComboBox::down-arrow {
            width: 16px;
            height: 16px;
            image: url(:/assets/down-arrow.png);  /* или закомментируй, если нет иконки */
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
            background: #2d2d2d;
            height: 6px;
            border-radius: 3px;
            border: 1px solid #333;
        }

        QSlider::handle:horizontal {
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                    stop:0 #6e6e6e, stop:0.5 #505050, stop:1 #6e6e6e);
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
            border: 1px solid #444;
        }

        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #3a7bd5, stop:1 #00d2ff);
            border-radius: 3px;
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

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
            height: 0px;
            subcontrol-origin: margin;
        }

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        """
        self.setStyleSheet(dark_theme)

        
    def closeEvent(self, event):
        """Переопределяем метод закрытия окна для сохранения настроек"""
        # Сохраняем текущий выбор
        current_version = self.version_select.currentText()
        if current_version:
            self.settings['last_version'] = current_version
            self.settings['last_loader'] = self.loader_select.currentData()
        
        self.settings['last_username'] = self.username.text().strip()
        save_settings(self.settings)
        event.accept()

    
    def close_launcher(self):
        """Закрывает лаунчер после запуска игры"""
        self.close()
            
    def launch_game(self):
        username = self.username.text().strip()
        if not username:
            QMessageBox.warning(self, "Ошибка", "Введите имя игрока!")
            return

        version = self.version_select.currentText()
        loader_type = self.loader_select.currentData()
        memory_mb = self.get_selected_memory()
        close_on_launch = self.settings_tab.close_on_launch_checkbox.isChecked()

        # Сохраняем текущий выбор версии и загрузчика
        self.settings['last_version'] = version
        self.settings['last_loader'] = loader_type
        save_settings(self.settings)

        # Показываем прогресс
        self.start_progress_label.setText("Подготовка к запуску...")
        self.start_progress_label.setVisible(True)
        self.start_progress.setVisible(True)
        
        # Запускаем в отдельном потоке
        self.launch_thread.launch_setup_signal.emit(version, username, loader_type, memory_mb, close_on_launch)
        self.launch_thread.start()

        
    def update_progress(self, value):
        self.start_progress.setValue(value)

    def state_update(self, is_running):
        if is_running:
            self.start_button.setEnabled(False)
        else:
            self.start_button.setEnabled(True)
            self.start_progress_label.setVisible(False)
            self.start_progress.setVisible(False)


if __name__ == "__main__":
    try:
        setup_directories()
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Фатальная ошибка при запуске: {e}")
        sys.exit(1)