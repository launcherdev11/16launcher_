import logging

import requests
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.config import MINECRAFT_VERSIONS
from src.gui.threads.mod_search_thread import ModSearchThread
from src.gui.threads.popular_mods_thread import PopularModsThread
from src.mod_manager import ModManager
from src.util import resource_path


class ModsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.search_thread = None
        self.popular_mods_thread = None
        self.current_search_query = ''
        self.current_page = 1
        self.total_pages = 1
        self.mods_data = []
        self.minecraft_versions = []
        self.setup_ui()
        self.is_loaded = False  # Флаг загрузки данных

        # Добавляем надпись о загрузке
        self.loading_label = QLabel('Моды загружаются, подождите...')
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
        self.search_input.setPlaceholderText('Поиск модов...')
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
        self.search_button.setIcon(QIcon(resource_path('assets/search.png')))
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
        version_layout.addWidget(QLabel('Версия Minecraft:'))

        # Используем слайдер для выбора версии
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

        # Модлоадер
        loader_layout = QVBoxLayout()
        loader_layout.addWidget(QLabel('Модлоадер:'))
        self.loader_combo = QComboBox()
        self.loader_combo.setFixedWidth(200)
        self.loader_combo.addItems(['Любой', 'Fabric', 'Forge', 'Quilt'])
        combo_style = """
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
        """
        self.loader_combo.setStyleSheet(combo_style)
        loader_layout.addWidget(self.loader_combo)
        filters_layout.addLayout(loader_layout)

        # Категория
        category_layout = QVBoxLayout()
        category_layout.addWidget(QLabel('Категория:'))
        self.category_combo = QComboBox()
        self.category_combo.setFixedWidth(200)
        self.category_combo.addItem('Все категории')
        self.category_combo.setStyleSheet(combo_style)
        category_layout.addWidget(self.category_combo)
        filters_layout.addLayout(category_layout)

        # Сортировка
        sort_layout = QVBoxLayout()
        sort_layout.addWidget(QLabel('Сортировка:'))
        self.sort_combo = QComboBox()
        self.sort_combo.setFixedWidth(200)
        self.sort_combo.addItems(['По релевантности', 'По загрузкам', 'По дате'])
        self.sort_combo.setStyleSheet(combo_style)
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

        self.prev_page_button = QPushButton('←')
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

        self.page_label = QLabel('Страница 1 из 1')
        self.page_label.setStyleSheet('color: white;')
        pagination_layout.addWidget(self.page_label)

        self.next_page_button = QPushButton('→')
        self.next_page_button.setFixedSize(40, 40)
        self.next_page_button.setStyleSheet(self.prev_page_button.styleSheet())
        self.next_page_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_page_button)

        layout.addWidget(pagination_widget)

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
        icon_label.setStyleSheet('background-color: #444444; border-radius: 5px;')
        icon_url = ModManager.get_mod_icon(
            mod.get('project_id', mod.get('id')),
            'modrinth',
        )
        if icon_url:
            pixmap = QPixmap()
            try:
                pixmap.loadFromData(requests.get(icon_url).content)
                icon_label.setPixmap(
                    pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation),
                )
            except:
                pass
        layout.addWidget(icon_label)

        # Информация
        info_layout = QVBoxLayout()

        # Название
        name_label = QLabel(mod.get('title', mod.get('name', 'N/A')))
        name_label.setStyleSheet('color: white; font-size: 16px; font-weight: bold;')
        info_layout.addWidget(name_label)

        # Описание
        desc_label = QLabel(mod.get('description', 'Нет описания'))
        desc_label.setStyleSheet('color: #aaaaaa;')
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        info_layout.addWidget(desc_label)

        # Статистика
        stats_layout = QHBoxLayout()
        downloads_label = QLabel(f'📥 {mod.get("downloads", 0)}')
        downloads_label.setStyleSheet('color: #aaaaaa;')
        stats_layout.addWidget(downloads_label)
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)

        layout.addLayout(info_layout)

        # Кнопка установки
        install_button = QPushButton('Установить')
        install_button.setFixedWidth(100)
        install_button.clicked.connect(
            lambda: self.install_modrinth_mod(mod['project_id']),
        )
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
        version = self.get_selected_version()
        loader = self.loader_combo.currentText()
        if loader == 'Любой':
            loader = None
        category = self.category_combo.currentText()
        if category == 'Все категории':
            category = None
        sort_by = self.sort_combo.currentText()

        # Создаем и запускаем поток поиска
        self.search_thread = ModSearchThread(query, version, loader, category, sort_by)
        self.search_thread.search_finished.connect(
            lambda mods, q: self.handle_search_results(mods, q),
        )
        self.search_thread.error_occurred.connect(self.handle_search_error)
        self.search_thread.start()

    def load_popular_mods(self):
        """Загружает список популярных модов"""
        try:
            # Показываем индикатор загрузки
            self.loading_label.setVisible(True)
            self.mods_scroll.setVisible(False)

            # Получаем параметры
            version = self.get_selected_version()
            loader = self.loader_combo.currentText()
            if loader == 'Любой':
                loader = None

            # Создаем и запускаем поток
            self.popular_mods_thread = PopularModsThread(version, loader)
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
        self.loading_label.setText(f'Ошибка загрузки: {error_message}')
        QTimer.singleShot(5000, lambda: self.loading_label.setVisible(False))
        logging.error(f'Ошибка загрузки популярных модов: {error_message}')

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
        QMessageBox.critical(
            self,
            'Ошибка',
            f'Не удалось выполнить поиск: {error_message}',
        )

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
        self.loading_label = QLabel('Загрузка...')
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
        no_results_label = QLabel('Ничего не найдено')
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
        self.page_label.setText(f'Страница {self.current_page} из {self.total_pages}')
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
        self.minecraft_versions = MINECRAFT_VERSIONS[::-1]

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
            self.version_label.setText(f'Выбрано: {self.minecraft_versions[index]}')

    def get_selected_version(self):
        """Возвращает выбранную версию"""
        if self.minecraft_versions:
            return self.minecraft_versions[self.version_slider.value()]
        return None

    def install_modrinth_mod(self, mod_id):
        """Устанавливает мод с Modrinth"""
        try:
            # Получаем выбранную версию Minecraft
            version = self.get_selected_version()
            if not version:
                QMessageBox.warning(self, 'Ошибка', 'Выберите версию Minecraft')
                return

            # Показываем индикатор загрузки
            self.show_loading_indicator()

            # Устанавливаем мод
            success, message = ModManager.download_modrinth_mod(mod_id, version)

            # Скрываем индикатор загрузки
            self.hide_loading_indicator()

            # Показываем результат
            if success:
                QMessageBox.information(self, 'Успех', message)
            else:
                QMessageBox.critical(self, 'Ошибка', message)

        except Exception as e:
            self.hide_loading_indicator()
            QMessageBox.critical(self, 'Ошибка', f'Не удалось установить мод: {e!s}')
            logging.exception(f'Ошибка установки мода: {e!s}')
