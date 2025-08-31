import json
import logging
import os
import random
import shutil
import webbrowser
from typing import Any

import requests

from .config import (
    AUTHLIB_INJECTOR_URL,
    AUTHLIB_JAR_PATH,
    MINECRAFT_DIR,
    SETTINGS_PATH,
    adjectives,
    default_settings,
    nouns,
)


def setup_directories() -> None:
    """Создает все необходимые директории при запуске"""
    os.makedirs(MINECRAFT_DIR, exist_ok=True)


def load_settings() -> dict[str | Any, bool | str | int | list[str] | Any] | dict[str, bool | str | int | list[str]]:
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, encoding='utf-8') as f:
                loaded_settings = json.load(f)
                return {**default_settings, **loaded_settings}
        except Exception as e:
            logging.exception(f'Ошибка загрузки настроек: {e}')
            return default_settings
    return default_settings


def save_settings(settings: dict[str, Any]) -> None:
    os.makedirs(MINECRAFT_DIR, exist_ok=True)

    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.exception(f'Ошибка при сохранении настроек: {e}')
        return

    logging.debug('Настройки успешно сохранены')

    if 'export_path' not in settings:
        settings['export_path'] = os.path.expanduser('~/Desktop')


def generate_random_username() -> str:
    """Генерирует случайное имя пользователя для Minecraft"""
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    num = random.randint(1, 999)

    return f'{adj}{noun}{num}'


def download_authlib_injector() -> bool:
    """Скачивает последнюю версию Authlib Injector"""
    try:
        response = requests.get(AUTHLIB_INJECTOR_URL)
        data = response.json()
        download_url = data['download_url']

        response = requests.get(download_url, stream=True)
        with open(AUTHLIB_JAR_PATH, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        return True
    except Exception as e:
        logging.exception(f'Ошибка загрузки Authlib Injector: {e}')
        return False


def download_optifine(version: str) -> tuple[str | None, str | None]:
    try:
        url = 'https://optifine.net/downloads'
        response = requests.get(url)
        if response.status_code != 200:
            return None, 'Не удалось получить страницу загрузки OptiFine.'

        pattern = f'OptiFine {version}'
        if pattern not in response.text:
            return None, f'Версия OptiFine {version} не найдена на сайте.'

        return 'https://optifine.net/downloads', None

    except Exception as e:
        return None, f'Ошибка загрузки: {e}'


def install_optifine(version: str) -> tuple[bool, str | None]:
    link, error = download_optifine(version)
    if error:
        return False, error

    if link is not None:
        webbrowser.open(link)
        return True, f'Открой сайт и скачай OptiFine {version} вручную.'
    else:
        return False, 'Ссылка для загрузки OptiFine не найдена.'


def get_quilt_versions(mc_version: str) -> list[dict[str, Any]]:
    """Получает версии Quilt через официальное API"""
    try:
        response = requests.get(
            'https://meta.quiltmc.org/v3/versions/loader',
            timeout=15,
        )
        data = response.json()
        return [
            {
                'version': loader['version'],
                'minecraft_version': loader['separator'],
                'stable': not loader['version'].lower().startswith('beta'),
            }
            for loader in data
            if mc_version in loader['separator']
        ]
    except Exception as e:
        logging.exception(f'Quilt version fetch failed: {e!s}')
        return []


def authenticate_ely_by(username: str, password: str) -> dict[str, Any] | None:
    url = 'https://authserver.ely.by/authenticate'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'agent': {'name': 'Minecraft', 'version': 1},
        'username': username,
        'password': password,
        'requestUser': True,
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return {
            'access_token': data['accessToken'],
            'client_token': data['clientToken'],
            'uuid': data['selectedProfile']['id'],
            'username': data['selectedProfile']['name'],
            'user': data.get('user', {}),
        }
    print('Ошибка авторизации:', response.text)
    return None


def resource_path(relative_path: str) -> str:
    """Универсальная функция для получения путей ресурсов"""
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    print(os.path.join(base_path, relative_path))
    return os.path.join(base_path, relative_path)


def read(path: str) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def write(path: str, data: dict[str, Any]) -> None:
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
