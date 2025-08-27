import json
import logging
import os
import random
import shutil
import sys
from typing import Any

import requests

from .config import (
    MINECRAFT_DIR,
    SETTINGS_PATH,
    default_settings,
    adjectives,
    nouns,
    numbers,
    AUTHLIB_INJECTOR_URL,
    AUTHLIB_JAR_PATH,
)


def setup_directories():
    """Создает все необходимые директории при запуске"""
    try:
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
    except Exception as e:
        logging.error(f"Не удалось создать директорию: {e}")
        raise


def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                loaded_settings = json.load(f)
                return {**default_settings, **loaded_settings}
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек: {e}")
            return default_settings
    return default_settings


def save_settings(settings):
    try:
        os.makedirs(MINECRAFT_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        logging.debug("Настройки успешно сохранены")
    except Exception as e:
        logging.error(f"Ошибка при сохранении настроек: {e}")
    if "export_path" not in settings:
        settings["export_path"] = os.path.expanduser("~/Desktop")


def generate_random_username():
    """Генерирует случайное имя пользователя для Minecraft"""
    # Выбираем случайные элементы
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    num = random.choice(numbers) if random.random() > 0.5 else ""

    # Собираем имя
    if num:
        return f"{adj}{noun}{num}"
    return f"{adj}{noun}"


def download_authlib_injector():
    """Скачивает последнюю версию Authlib Injector"""
    try:
        response = requests.get(AUTHLIB_INJECTOR_URL)
        data = response.json()
        download_url = data["download_url"]

        response = requests.get(download_url, stream=True)
        with open(AUTHLIB_JAR_PATH, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        return True
    except Exception as e:
        logging.error(f"Ошибка загрузки Authlib Injector: {e}")
        return False


def download_optifine(version: str):
    try:
        url = "https://optifine.net/downloads"
        response = requests.get(url)
        if response.status_code != 200:
            return None, "Не удалось получить страницу загрузки OptiFine."

        pattern = f"OptiFine {version}"
        if pattern not in response.text:
            return None, f"Версия OptiFine {version} не найдена на сайте."

        return "https://optifine.net/downloads", None

    except Exception as e:
        return None, f"Ошибка загрузки: {e}"


def install_optifine(version: str):
    link, error = download_optifine(version)
    if error:
        return False, error

    import webbrowser

    webbrowser.open(link)
    return True, f"Открой сайт и скачай OptiFine {version} вручную."


def get_quilt_versions(mc_version: str) -> list[dict[str, Any]]:
    """Получает версии Quilt через официальное API"""
    try:
        response = requests.get(
            "https://meta.quiltmc.org/v3/versions/loader", timeout=15
        )
        data = response.json()
        return [
            {
                "version": loader["version"],
                "minecraft_version": loader["separator"],  # Исправлено с metadata
                "stable": not loader["version"].lower().startswith("beta"),
            }
            for loader in data
            if mc_version in loader["separator"]
        ]
    except Exception as e:
        logging.error(f"Quilt version fetch failed: {str(e)}")
        return []


def authenticate_ely_by(username, password) -> dict[str, Any] | None:
    url = "https://authserver.ely.by/authenticate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "agent": {"name": "Minecraft", "version": 1},
        "username": username,
        "password": password,
        "requestUser": True,
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return {
            "access_token": data["accessToken"],
            "client_token": data["clientToken"],
            "uuid": data["selectedProfile"]["id"],
            "username": data["selectedProfile"]["name"],
            "user": data.get("user", {}),
        }
    else:
        print("Ошибка авторизации:", response.text)
        return None


def resource_path(relative_path):
    """Универсальная функция для получения путей ресурсов"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    return os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')), relative_path)


def read(path):
    with open(path) as f:
        return json.load(f)


def write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
