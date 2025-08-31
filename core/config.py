import os
from typing import Any

import requests
from minecraft_launcher_lib.types import MinecraftVersionInfo
from minecraft_launcher_lib.utils import get_minecraft_directory, get_version_list

host = "http://127.0.0.1:8000"
try:
    VERSIONS: list[MinecraftVersionInfo] = requests.get(f"{host}/minecraft/versions/vanilla").json()
    MINECRAFT_VERSIONS: list[str] = requests.get(f"{host}/minecraft/versions/vanilla/release").json()
except Exception:
    VERSIONS: list[MinecraftVersionInfo] = get_version_list()
    MINECRAFT_VERSIONS: list[str] = [version['id'] for version in VERSIONS if version['type'] == 'release']
MINECRAFT_DIR: str = os.path.join(get_minecraft_directory(), "16launcher")
SKINS_DIR: str = os.path.join(MINECRAFT_DIR, "skins")
SETTINGS_PATH: str = os.path.join(MINECRAFT_DIR, "settings.json")
LOG_FILE: str = os.path.join(MINECRAFT_DIR, "launcher_log.txt")
NEWS_FILE: str = os.path.join(MINECRAFT_DIR, "launcher_news.json")
AUTHLIB_JAR_PATH: str = os.path.join(MINECRAFT_DIR, "authlib-injector.jar")
MODS_DIR: str = os.path.join(MINECRAFT_DIR, "mods")
ELY_CLIENT_ID: str = "16Launcher"
CLIENT_ID: str = "16Launcher1"
ELY_BY_INJECT: str = "-javaagent:{}=ely.by"
versions: str = "versions"
ELY_BY_INJECT_URL: str = ("https://github.com/"
                          "yushijinhun/authlib-injector/releases/download/v1.2.5/authlib-injector-1.2.5.jar")
ELYBY_API_URL: str = "https://authserver.ely.by/api/"
ELYBY_SKINS_URL: str = "https://skinsystem.ely.by/skins/"
ELYBY_AUTH_URL: str = "https://account.ely.by/oauth2/v1"
AUTHLIB_INJECTOR_URL: str = "https://authlib-injector.ely.by/artifact/latest.json"
DEVICE_CODE_URL: str = "https://authserver.ely.by/oauth2/device"
TOKEN_URL: str = "https://authserver.ely.by/oauth2/token"
headers: dict[str, str] = {
    "Content-Type": "application/json",
    "User-Agent": "16Launcher/1.0"
}
RELEASE: bool = False
default_settings: dict[str, bool | str | int | list[Any]] = {
    "show_motd": True,
    "language": "ru",
    "close_on_launch": False,
    "memory": 4,
    "minecraft_directory": MINECRAFT_DIR,
    "last_username": "",
    "favorites": [],
    "last_version": "",
    "last_loader": "vanilla",
    "show_snapshots": False,
}
adjectives: list[str] = [
    "Cool",
    "Mighty",
    "Epic",
    "Crazy",
    "Wild",
    "Sneaky",
    "Happy",
    "Angry",
    "Funny",
    "Lucky",
    "Dark",
    "Light",
    "Red",
    "Blue",
    "Green",
    "Golden",
    "Silver",
    "Iron",
    "Diamond",
    "Emerald",
]
nouns: list[str] = [
    "Player",
    "Gamer",
    "Hero",
    "Villain",
    "Warrior",
    "Miner",
    "Builder",
    "Explorer",
    "Adventurer",
    "Hunter",
    "Wizard",
    "Knight",
    "Ninja",
    "Pirate",
    "Dragon",
    "Wolf",
    "Fox",
    "Bear",
    "Tiger",
    "Ender",
    "Sosun",
]
numbers: list[str] = ["123", "42", "99", "2023", "777", "1337", "69", "100", "1", "0"]
main_message: list[str] = [
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
dark_theme_css: str = """
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
vertical_slider_style: str = """
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
light_theme_css: str = """
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
