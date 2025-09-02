import logging
import threading

import requests
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...minecraft_news_translator import MinecraftNewsTranslator


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
        self.tabs.addTab(self.minecraft_news_tab, 'Minecraft')

        # Launcher News Tab
        self.launcher_news_tab = QWidget()
        self.setup_launcher_news_tab()
        self.tabs.addTab(self.launcher_news_tab, 'Лаунчер')

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

        self.refresh_button = QPushButton('Обновить')
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
        thread = threading.Thread(target=self.load_minecraft_news)
        thread.start()
        thread = threading.Thread(target=self.load_launcher_news)
        thread.start()

    def load_minecraft_news(self):
        try:
            news = requests.get(
                'https://launchercontent.mojang.com/news.json',
                timeout=10,
            ).json()

            html_content = """
            <h1 style="color: #FFAA00;">Последние новости Minecraft</h1>
            <p><small>Автоматический перевод с английского</small></p>
            """

            for item in news['entries'][:50]:  # Берем 50 последних новостей (меньше для скорости)
                try:
                    # Обработка даты
                    date = item['date'][:10] if 'date' in item else 'Дата не указана'

                    # Переводим заголовок и текст
                    title = MinecraftNewsTranslator.translate_text(
                        item.get('title', ''),
                    )
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
                    logging.exception(f'Ошибка обработки новости: {e!s}')
                    continue

            self.minecraft_news_list.setText(html_content)
        except Exception as e:
            self.minecraft_news_list.setText(f"""
                <h1 style="color: #FF5555;">Ошибка загрузки новостей</h1>
                <p>Не удалось загрузить новости Minecraft: {e!s}</p>
                <p>Попробуйте позже или проверьте интернет-соединение.</p>
            """)
            logging.exception(f'Ошибка загрузки новостей Minecraft: {e!s}')

    def load_launcher_news(self):
        try:
            response = requests.get(
                'https://raw.githubusercontent.com/16steyy/launcher-news/refs/heads/main/launcher_news.json',
                timeout=10,
            )
            news = response.json()

            html_content = '<h1>Новости лаунчера</h1>'

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
                <p>Не удалось загрузить новости лаунчера: {e!s}</p>
            """)
            logging.exception(f'Ошибка загрузки новостей лаунчера: {e!s}')
