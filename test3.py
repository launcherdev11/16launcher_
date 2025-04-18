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
                            QSlider, QMessageBox, QTabWidget, QFrame, QStackedWidget)
from PyQt5.QtGui import QPixmap, QIcon
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

# Глобальные константы
MINECRAFT_DIR = os.path.join(get_minecraft_directory(), "16launcher")
SKINS_DIR = os.path.join(MINECRAFT_DIR, "skins")
SETTINGS_PATH = os.path.join(MINECRAFT_DIR, "settings.json")
LOG_FILE = os.path.join(MINECRAFT_DIR, "launcher_log.txt")

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
    launch_setup_signal = pyqtSignal(str, str, str)
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.launch_setup_signal.connect(self.launch_setup)
        self.loader_type = None

    def launch_setup(self, version_id, username, loader_type):
        self.version_id = version_id
        self.username = username
        self.loader_type = loader_type
    
    def run(self):
        try:
            logging.debug(f"Запуск Minecraft {self.version_id} ({self.loader_type}) для {self.username}")
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
            
            options = {
                'username': self.username, 
                'uuid': str(uuid1()), 
                'token': '',
                'jvmArguments': ['-Xmx4G', '-Xms2G']
            }
            
            call(get_minecraft_command(
                version=launch_version, 
                minecraft_directory=MINECRAFT_DIR, 
                options=options
            ))
            
            self.state_update_signal.emit(False)
        except Exception as e:
            logging.error(f"Ошибка при запуске Minecraft: {e}")
            self.state_update_signal.emit(False)

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)

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

        settings = load_settings()
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
                # Обновляем пути после изменения директории
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
        settings = {
            'memory': self.memory_slider.value(),
            'minecraft_directory': self.directory_edit.text()
        }
        save_settings(settings)

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка при загрузке настроек: {e}")
    return {}

def save_settings(settings):
    try:
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=4)
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Создаем директорию при запуске
        setup_directories()
        self.setWindowTitle("16Launcher 1.0.1")
        self.setFixedSize(800, 600)
        self.setWindowIcon(QIcon("assets/icon.ico"))

        # Главный контейнер с боковой панелью и содержимым
        self.main_container = QWidget(self)
        self.setCentralWidget(self.main_container)
        
        # Основной горизонтальный layout
        self.main_layout = QHBoxLayout(self.main_container)
        self.main_container.setLayout(self.main_layout)
        
        # Создаем боковую панель
        self.setup_sidebar()
        
        # Основное содержимое - StackedWidget для переключения между вкладками и настройками
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # Создаем виджет с вкладками
        self.tab_widget = QWidget()
        self.tab_layout = QVBoxLayout(self.tab_widget)
        
        self.tabs = QTabWidget()
        self.tab_layout.addWidget(self.tabs)

        self.game_tab = QWidget()
        self.setup_game_tab()
        self.tabs.addTab(self.game_tab, "Запуск игры")

        self.setup_modloader_tabs()
        
        # Добавляем виджет с вкладками в stacked widget
        self.stacked_widget.addWidget(self.tab_widget)
        
        # Создаем виджет настроек
        self.settings_tab = SettingsTab()
        self.stacked_widget.addWidget(self.settings_tab)
        
        # По умолчанию показываем вкладки
        self.stacked_widget.setCurrentIndex(0)
        
        self.launch_thread = LaunchThread()
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)

        self.apply_dark_theme()
    
    def setup_sidebar(self):
        """Настройка боковой панели с кнопками"""
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setFixedWidth(75)  # Уменьшили ширину с 150 до 100
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        
        # Кнопка "Играть"
        self.play_button = QPushButton("")
        self.play_button.setIcon(QIcon("assets/play64.png"))
        self.play_button.setIconSize(QSize(46, 46))  # Уменьшили размер иконки
        self.play_button.setFixedSize(60, 60)  # Фиксированный размер кнопки
        self.play_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #444444;
                border-radius: 5px;
            }
        """)
        self.play_button.clicked.connect(self.show_game_tab)
        sidebar_layout.addWidget(self.play_button, alignment=Qt.AlignCenter)
        
        # Кнопка "Настройки"
        self.settings_button = QPushButton("")
        self.settings_button.setIcon(QIcon("assets/set64.png"))
        self.settings_button.setIconSize(QSize(46, 46))  # Уменьшили размер иконки
        self.settings_button.setFixedSize(60, 60)  # Фиксированный размер кнопки
        self.settings_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #444444;
                border-radius: 5px;
            }
        """)
        self.settings_button.clicked.connect(self.show_settings_tab)
        sidebar_layout.addWidget(self.settings_button, alignment=Qt.AlignCenter)
        
        # Добавляем растяжку внизу
        sidebar_layout.addStretch()
        
        # Добавляем боковую панель в основной layout
        self.main_layout.addWidget(sidebar)
    
    def show_game_tab(self):
        """Переключает на вкладку с игрой"""
        self.stacked_widget.setCurrentIndex(0)
        self.tabs.setCurrentIndex(0)  # Убедимся, что выбрана первая вкладка (Запуск игры)
    
    def show_settings_tab(self):
        """Переключает на вкладку с настройками"""
        self.stacked_widget.setCurrentIndex(1)
    
    def setup_game_tab(self):
        layout = QVBoxLayout(self.game_tab)
        logo_label = QLabel(self.game_tab)
        logo_pixmap = QPixmap("assets/logo.png").scaled(200, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        layout = QVBoxLayout(self.game_tab)

        form_layout = QVBoxLayout()

        top_row = QHBoxLayout()
        self.username = QLineEdit(self.game_tab)
        self.username.setPlaceholderText('Введите имя')
        top_row.addWidget(self.username)

        self.random_name_button = QPushButton("Случ. имя")
        self.random_name_button.clicked.connect(self.set_random_username)
        top_row.addWidget(self.random_name_button)

        form_layout.addLayout(top_row)

        second_row = QHBoxLayout()
        self.version_select = QComboBox(self.game_tab)
        for version in get_version_list():
            if version["type"] == "release":
                self.version_select.addItem(version['id'])
        second_row.addWidget(self.version_select)

        self.loader_select = QComboBox(self.game_tab)
        self.loader_select.addItem("Vanilla", "vanilla")
        self.loader_select.addItem("Forge", "forge")
        self.loader_select.addItem("Fabric", "fabric")
        self.loader_select.addItem("OptiFine", "optifine")
        second_row.addWidget(self.loader_select)

        form_layout.addLayout(second_row)

        third_row = QHBoxLayout()
        self.start_button = QPushButton("Играть")
        self.start_button.clicked.connect(self.launch_game)
        third_row.addWidget(self.start_button)

        self.load_skin_button = QPushButton("Сменить скин")
        self.load_skin_button.clicked.connect(self.load_skin)
        third_row.addWidget(self.load_skin_button)

        form_layout.addLayout(third_row)

        layout.addLayout(form_layout)

        self.start_progress_label = QLabel(self.game_tab)
        self.start_progress_label.setVisible(False)
        layout.addWidget(self.start_progress_label)

        self.start_progress = QProgressBar(self.game_tab)
        self.start_progress.setVisible(False)
        layout.addWidget(self.start_progress)

        
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
        /* Основной фон окна */
        QMainWindow {
            background-color: #212121;
        }

        /* Основной фон виджетов */
        QWidget {
            background-color: #212121;
            color: #E0E0E0;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }

        /* Поля ввода */
        QLineEdit {
            background-color: #2D2D2D;
            color: #E0E0E0;
            border: 1px solid #424242;
            border-radius: 8px;
            padding: 8px;
            selection-background-color: #4CAF50;
            selection-color: #FFFFFF;
        }
        QLineEdit:focus {
            border: 1px solid #4CAF50;
            background-color: #333333;
        }
        QLineEdit:hover {
            border: 1px solid #616161;
        }

        /* Выпадающие списки */
        QComboBox {
            background-color: #2D2D2D;
            color: #E0E0E0;
            border: 1px solid #424242;
            border-radius: 8px;
            padding: 8px;
            min-height: 34px;
        }
        QComboBox:hover {
            border: 1px solid #616161;
        }
        QComboBox:focus {
            border: 1px solid #4CAF50;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: url(assets/down_arrow.png); /* Добавьте иконку стрелки */
            width: 12px;
            height: 12px;
        }
        QComboBox QAbstractItemView {
            background-color: #2D2D2D;
            color: #E0E0E0;
            border: 1px solid #424242;
            selection-background-color: #4CAF50;
            selection-color: #FFFFFF;
            border-radius: 8px;
        }

        /* Кнопки */
        QPushButton {
            background-color: #4CAF50;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
            font-weight: 500;
            min-height: 36px;
        }
        QPushButton:hover {
            background-color: #45A049;
            transform: scale(1.02); /* Не поддерживается в PyQt, см. примечание */
        }
        QPushButton:pressed {
            background-color: #3D8B40;
        }
        QPushButton:disabled {
            background-color: #616161;
            color: #9E9E9E;
        }

        /* Боковая панель */
        QFrame {
            background-color: #1A1A1A;
            border-right: 1px solid #333333;
        }
        QPushButton#play_button, QPushButton#settings_button {
            background-color: transparent;
            border: none;
            border-radius: 12px;
            padding: 8px;
        }
        QPushButton#play_button:hover, QPushButton#settings_button:hover {
            background-color: #333333;
        }

        /* Вкладки */
        QTabWidget::pane {
            border: none;
            background: #212121;
            margin-top: 0px;
        }
        QTabBar::tab {
            background: #2D2D2D;
            color: #B0B0B0;
            padding: 12px 20px;
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 2px;
            font-size: 13px;
            font-weight: 500;
        }
        QTabBar::tab:selected {
            background: #4CAF50;
            color: #FFFFFF;
        }
        QTabBar::tab:hover:!selected {
            background: #424242;
            color: #E0E0E0;
        }

        /* Прогресс-бар */
        QProgressBar {
            background-color: #2D2D2D;
            color: #E0E0E0;
            border: 1px solid #424242;
            border-radius: 8px;
            text-align: center;
            font-size: 12px;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 6px;
        }

        /* Слайдер */
        QSlider::groove:horizontal {
            height: 8px;
            background: #424242;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #4CAF50;
            border: 1px solid #3D8B40;
            width: 18px;
            height: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }
        QSlider::handle:horizontal:hover {
            background: #45A049;
        }
        QSlider::sub-page:horizontal {
            background: #4CAF50;
            border-radius: 4px;
        }

        /* Метки */
        QLabel {
            color: #E0E0E0;
            font-size: 13px;
        }

        /* Диалоговые окна */
        QMessageBox {
            background-color: #212121;
            color: #E0E0E0;
        }
        QMessageBox QPushButton {
            background-color: #4CAF50;
            color: #FFFFFF;
            border-radius: 8px;
            padding: 8px;
            min-width: 80px;
        }
        QMessageBox QPushButton:hover {
            background-color: #45A049;
        }
        """
        self.setStyleSheet(dark_theme)
        pixmap = QPixmap("assets/background.png")  # Файл с текстурой
        palette = self.palette()
        palette.setBrush(self.backgroundRole(), pixmap)
        self.setPalette(palette)
        self.setStyleSheet(dark_theme)
    
    def launch_game(self):
        username = self.username.text().strip()
        if not username:
            QMessageBox.warning(self, "Ошибка", "Введите имя игрока!")
            return

        version = self.version_select.currentText()
        loader_type = self.loader_select.currentData()

        # Показываем прогресс
        self.start_progress_label.setText("Подготовка к запуску...")
        self.start_progress_label.setVisible(True)
        self.start_progress.setVisible(True)
        
        # Запускаем в отдельном потоке
        self.launch_thread.launch_setup_signal.emit(version, username, loader_type)
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