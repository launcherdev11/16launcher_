import hashlib
import json
import logging
import os
from functools import lru_cache

import requests

from .config import MINECRAFT_DIR


class MinecraftNewsTranslator:
    @staticmethod
    @lru_cache(maxsize=100)  # Кэшируем последние 100 переводов
    def translate_text(text, source_lang="en", target_lang="ru"):
        """Переводит текст с помощью MyMemory API"""
        if not text.strip():
            return text

        try:
            # Создаем хэш для кэширования
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cache_file = os.path.join(MINECRAFT_DIR, f"translation_{text_hash}.json")

            # Проверяем кэш
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)["translation"]

            # Переводим через API
            params = {
                "q": text,
                "langpair": f"{source_lang}|{target_lang}",
                "de": "your-email@example.com",  # Укажите ваш email для бесплатного API
            }

            response = requests.get(
                "https://api.mymemory.translated.net/get", params=params, timeout=10
            )
            response.raise_for_status()

            translation = response.json()["responseData"]["translatedText"]

            # Сохраняем в кэш
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"translation": translation}, f, ensure_ascii=False)

            return translation
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            return text  # Возвращаем оригинальный текст при ошибке
