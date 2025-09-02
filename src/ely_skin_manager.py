import logging
import os
import shutil

import requests

from .config import MINECRAFT_DIR, SKINS_DIR


class ElySkinManager:
    @staticmethod
    def apply_skin(username, version, is_legacy):
        """Применяет скин с учетом версии"""
        skin_url = ElySkinManager.get_skin_url(username)
        if not skin_url:
            return False

        # Для новых версий - через authlib
        if not is_legacy:
            return ElySkinManager.download_skin(username)

        # Для старых версий - напрямую в файлы игры
        skin_path = os.path.join(MINECRAFT_DIR, 'skins', f'{username}.png')
        ElySkinManager.download_skin_file(skin_url, skin_path)
        return ElySkinManager.inject_legacy_skin(skin_path, version)

    @staticmethod
    def inject_legacy_skin(skin_path, version):
        """Внедряет скин в файлы игры для legacy-версий"""
        try:
            assets_dir = os.path.join(MINECRAFT_DIR, 'assets', 'skins')
            os.makedirs(assets_dir, exist_ok=True)
            shutil.copy(skin_path, os.path.join(assets_dir, 'char.png'))
            return True
        except Exception as e:
            logging.exception(f'Legacy skin injection failed: {e!s}')
            return False

    @staticmethod
    def get_skin_texture_url(username):
        """Получаем URL текстуры скина через текстуры-прокси"""
        try:
            response = requests.get(f'https://skinsystem.ely.by/textures/{username}')
            if response.status_code == 200:
                data = response.json()
                return data.get('textures', {}).get('SKIN', {}).get('url')
            return None
        except Exception as e:
            logging.exception(f'Ошибка при получении текстуры скина: {e}')
            return None

    @staticmethod
    def get_skin_image_url(username):
        """Получаем URL изображения скина"""
        return f'https://skinsystem.ely.by/skins/{username}.png'

    @staticmethod
    def download_skin(username):
        """Скачиваем скин с Ely.by"""
        try:
            skin_url = ElySkinManager.get_skin_image_url(username)
            response = requests.get(skin_url, stream=True)
            if response.status_code == 200:
                os.makedirs(SKINS_DIR, exist_ok=True)
                dest_path = os.path.join(SKINS_DIR, f'{username}.png')
                with open(dest_path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                return True
        except Exception as e:
            logging.exception(f'Ошибка при загрузке скина: {e}')
        return False

    @staticmethod
    def upload_skin(file_path, access_token, variant='classic'):
        """
        Загружает скин на Ely.by
        :param file_path: путь к файлу скина
        :param access_token: токен доступа Ely.by
        :param variant: тип модели ("classic" или "slim")
        """
        try:
            url = 'https://account.ely.by/api/resources/skin'
            headers = {'Authorization': f'Bearer {access_token}'}

            with open(file_path, 'rb') as f:
                files = {
                    'file': ('skin.png', f, 'image/png'),
                    'variant': (None, variant),
                }

                response = requests.put(url, headers=headers, files=files)

                if response.status_code == 200:
                    return True, 'Скин успешно загружен!'
                return (
                    False,
                    f'Ошибка: {response.json().get("message", "Неизвестная ошибка")}',
                )
        except Exception as e:
            return False, f'Ошибка загрузки: {e!s}'

    @staticmethod
    def reset_skin(access_token):
        """Сбрасывает скин на стандартный"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.delete(
                'https://account.ely.by/api/resources/skin',
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
