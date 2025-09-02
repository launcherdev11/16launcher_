import json
import logging
import os
import shutil
import time
from typing import Any, Callable
import zipfile

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QCursor, QDragEnterEvent, QDropEvent, QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import MINECRAFT_DIR, MINECRAFT_VERSIONS, MODS_DIR
from mod_manager import ModManager
from util import resource_path


class ModpackTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.modpacks_dir = os.path.join(MINECRAFT_DIR, 'modpacks')
        self.icons_dir = os.path.join(
            MINECRAFT_DIR,
            'modpack_icons',
        )  # Директория для иконок
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
        icon_label.setPixmap(
            QPixmap(resource_path('assets/modpack_icon.png')).scaled(32, 32),
        )
        title_layout.addWidget(icon_label)

        self.title = QLabel('Мои сборки')
        self.title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title_layout.addWidget(self.title)
        title_layout.addStretch()
        header.addLayout(title_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = self.create_tool_button(
            'Создать',
            'add.png',
            self.show_creation_dialog,
        )
        self.import_btn = self.create_tool_button(
            'Импорт',
            'import.png',
            self.import_modpack,
        )
        self.refresh_btn = self.create_tool_button(
            'Обновить',
            'refresh.png',
            self.load_modpacks,
        )

        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.refresh_btn)
        header.addLayout(btn_layout)

        layout.addLayout(header)

        # Filter Section
        filter_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Поиск по названию...')
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.search_bar)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Все', 'Forge', 'Fabric', 'OptiFine', 'Vanilla'])
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.currentIndexChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)

        # Modpacks Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        # Status Label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet('color: #AAAAAA; font-size: 14px;')
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

    def create_tool_button(
        self,
        text: str,
        icon: str,
        callback: Callable[[], None],
    ) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setIcon(QIcon(resource_path(f'assets/{icon}')))
        btn.setIconSize(QSize(24, 24))
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
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

    def create_modpack_card(self, pack_data: dict[str, Any]) -> QFrame:
        icon = QLabel()
        icon_name = pack_data.get('icon')
        icon_path = os.path.join(self.icons_dir, icon_name) if icon_name else ''

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
        title = QLabel(pack_data['name'])
        title.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        title.setStyleSheet('color: #FFFFFF;')

        version = QLabel(f'· Minecraft {pack_data["version"]}')
        version.setStyleSheet('color: #AAAAAA; font-size: 11px;')

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

        play_btn = self.create_card_button(
            'Запустить',
            'play.png',
            lambda: self.launch_modpack(pack_data),
        )
        edit_btn = self.create_card_button(
            'Изменить',
            'edit.png',
            lambda: self.edit_modpack(pack_data),
        )
        menu_btn = self.create_card_button(
            '⋮',
            'menu.png',
            lambda: self.show_context_menu(pack_data),
        )

        btn_layout.addWidget(play_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(menu_btn)
        layout.addLayout(btn_layout)

        return card

    def create_card_button(
        self,
        text: str,
        icon: str,
        callback: Callable[[], None],
    ) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(80, 28)
        btn.setIcon(QIcon(resource_path(f'assets/{icon}')))
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

    def filter_modpacks(self) -> None:
        search_text = self.search_bar.text().lower()
        filter_type = self.filter_combo.currentText()

        visible_count = 0
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                name_match = search_text in widget.property('pack_name').lower()
                type_match = (filter_type == 'Все') or (widget.property('loader_type') == filter_type)
                visible = name_match and type_match
                widget.setVisible(visible)
                if visible:
                    visible_count += 1

        self.status_label.setText(
            f'Найдено сборок: {visible_count}' if visible_count > 0 else 'Сборки не найдены',
        )

    def load_modpacks(self) -> None:
        # Clear existing cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load modpacks
        modpacks = []
        for file in os.listdir(self.modpacks_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(self.modpacks_dir, file)) as f:
                        pack = json.load(f)
                        pack['filename'] = file
                        modpacks.append(pack)
                except Exception as e:
                    logging.exception(f'Error loading modpack {file}: {e}')

        if not modpacks:
            self.status_label.setText('🎮 Создайте свою первую сборку!')
            return

        # Create cards
        row, col = 0, 0
        for pack in sorted(modpacks, key=lambda x: x['name'].lower()):
            card = self.create_modpack_card(pack)
            card.setProperty('pack_name', pack['name'])
            card.setProperty('loader_type', pack['loader'])
            self.grid_layout.addWidget(card, row, col)

            col += 1
            if col > 3:  # 4 columns
                col = 0
                row += 1

        self.status_label.setText(f'Загружено сборок: {len(modpacks)}')

    def get_modpack_size(self, pack_data: dict[str, Any]) -> str:
        total_size = 0
        mods_dir = os.path.join(MODS_DIR, pack_data['version'])
        if os.path.exists(mods_dir):
            for mod in pack_data['mods']:
                mod_path = os.path.join(mods_dir, mod)
                if os.path.exists(mod_path):
                    total_size += os.path.getsize(mod_path)
        return f'{total_size / 1024 / 1024:.1f} MB'

    def show_context_menu(self, pack_data: dict[str, Any]) -> None:
        menu = QMenu(self)

        export_action = QAction(
            QIcon(resource_path('assets/export.png')),
            'Экспорт',
            self,
        )
        export_action.triggered.connect(lambda: self.export_modpack(pack_data))

        duplicate_action = QAction(
            QIcon(resource_path('assets/copy.png')),
            'Дублировать',
            self,
        )
        duplicate_action.triggered.connect(lambda: self.duplicate_modpack(pack_data))

        delete_action = QAction(
            QIcon(resource_path('assets/delete.png')),
            'Удалить',
            self,
        )
        delete_action.triggered.connect(lambda: self.delete_modpack(pack_data))

        menu.addAction(export_action)
        menu.addAction(duplicate_action)
        menu.addAction(delete_action)
        menu.exec_(QCursor.pos())

    def duplicate_modpack(self, pack_data: dict[str, Any]) -> None:
        new_name, ok = QInputDialog.getText(
            self,
            'Дублирование сборки',
            'Введите новое название:',
            QLineEdit.EchoMode.Normal,
            f'{pack_data["name"]} - Копия',
        )

        if ok and new_name:
            new_filename = f'{new_name}.json'
            new_path = os.path.join(self.modpacks_dir, new_filename)

            if os.path.exists(new_path):
                QMessageBox.warning(
                    self,
                    'Ошибка',
                    'Сборка с таким именем уже существует!',
                )
                return

            try:
                shutil.copyfile(
                    os.path.join(self.modpacks_dir, pack_data['filename']),
                    new_path,
                )
                self.load_modpacks()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    'Ошибка',
                    f'Не удалось создать копию: {e!s}',
                )

    def launch_modpack(self, pack_data: dict[str, Any]) -> None:
        self.parent_window.version_select.setCurrentText(pack_data['version'])
        self.parent_window.loader_select.setCurrentText(pack_data['loader'])
        self.parent_window.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self,
            'Запуск сборки',
            f"Параметры сборки '{pack_data['name']}' установлены!\nНажмите 'Играть' для запуска.",
        )

    def edit_modpack(self, pack_data: dict[str, Any]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Редактирование: {pack_data["name"]}')
        dialog.setFixedSize(800, 600)

        layout = QVBoxLayout()

        # Существующие поля
        name_layout = QHBoxLayout()
        name_label = QLabel('Название:')
        self.name_edit = QLineEdit(pack_data['name'])
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)

        # Поля версии и лоадера
        version_layout = QHBoxLayout()
        version_label = QLabel('Версия:')
        self.version_combo = QComboBox()
        self.version_combo.addItems(MINECRAFT_VERSIONS)
        self.version_combo.setCurrentText(pack_data['version'])
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_combo)

        loader_layout = QHBoxLayout()
        loader_label = QLabel('Модлоадер:')
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(['Vanilla', 'Forge', 'Fabric', 'OptiFine'])
        self.loader_combo.setCurrentText(pack_data['loader'])
        loader_layout.addWidget(loader_label)
        loader_layout.addWidget(self.loader_combo)

        # Секция модов
        mods_layout = QVBoxLayout()
        mods_label = QLabel('Моды в сборке:')
        self.mods_list = QListWidget()
        self.mods_list.addItems(pack_data['mods'])

        # Кнопки управления модами
        mod_buttons = QHBoxLayout()
        self.remove_mod_btn = QPushButton('Удалить выбранное')
        self.remove_mod_btn.clicked.connect(lambda: self.remove_selected_mods())
        self.add_mod_btn = QPushButton('Добавить моды')
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
        button_box.accepted.connect(
            lambda: self.save_modpack_changes(pack_data, dialog),
        )
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        dialog.exec_()

    def remove_selected_mods(self) -> None:
        selected_items = self.mods_list.selectedItems()
        for item in selected_items:
            row = self.mods_list.row(item)
            self.mods_list.takeItem(row)

    def add_mods_to_pack(self, pack_data: dict[str, Any]) -> None:
        # Диалог выбора модов
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter('Mod files (*.jar *.zip)')

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            mods_dir = os.path.join(MODS_DIR, pack_data['version'])

            for file_path in selected_files:
                mod_name = os.path.basename(file_path)
                dest_path = os.path.join(mods_dir, mod_name)

                # Копируем мод в папку сборки
                if not os.path.exists(dest_path):
                    shutil.copyfile(file_path, dest_path)

                # Добавляем в список, если еще нет
                if not self.mods_list.findItems(mod_name, Qt.MatchExactly):
                    self.mods_list.addItem(mod_name)

            QMessageBox.information(self, 'Успех', 'Моды успешно добавлены!')

    def save_modpack_changes(self, old_pack: dict[str, Any], dialog: QDialog) -> None:
        new_name = self.name_edit.text()
        new_version = self.version_combo.currentText()
        new_loader = self.loader_combo.currentText()

        # Получаем обновленный список модов
        new_mods = []
        for i in range(self.mods_list.count()):
            new_mods.append(self.mods_list.item(i).text())

        try:
            # Удаляем старый файл
            old_path = os.path.join(self.modpacks_dir, old_pack['filename'])
            os.remove(old_path)

            # Создаем новый
            new_filename = f'{new_name}.json'
            new_pack = {
                'name': new_name,
                'version': new_version,
                'loader': new_loader,
                'mods': new_mods,
            }

            with open(os.path.join(self.modpacks_dir, new_filename), 'w') as f:
                json.dump(new_pack, f)

            self.load_modpacks()
            dialog.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                'Ошибка',
                f'Не удалось сохранить изменения: {e!s}',
            )

    def delete_modpack(self, pack_data: dict[str, Any]) -> None:
        confirm = QMessageBox.question(
            self,
            'Удаление сборки',  # Исправлен заголовок
            f"Вы уверены, что хотите удалить сборку '{pack_data['name']}'?",  # Исправлен текст
            QMessageBox.Yes | QMessageBox.No,  # Правильные константы кнопок
            QMessageBox.No,  # Кнопка по умолчанию
        )

        if confirm == QMessageBox.Yes:
            try:
                os.remove(os.path.join(self.modpacks_dir, pack_data['filename']))
                self.load_modpacks()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    'Ошибка',
                    f'Не удалось удалить сборку: {e!s}',
                )

    def setup_drag_drop(self):
        self.setAcceptDrops(True)
        self.scroll_area.setAcceptDrops(True)
        self.scroll_area.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith('.zip') for url in urls):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip'):
                self.handle_dropped_file(file_path)
        event.acceptProposedAction()

    def handle_dropped_file(self, file_path: str) -> None:
        try:
            loading_indicator = QLabel('Импорт сборки...', self)
            loading_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            loading_indicator.setStyleSheet("""
                QLabel {
                    background-color: #454545;
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    font-size: 16px;
                }
            """)
            loading_indicator.setGeometry(
                self.width() // 2 - 150,
                self.height() // 2 - 50,
                300,
                100,
            )
            loading_indicator.show()
            QApplication.processEvents()

            self.import_modpack(file_path)
            self.load_modpacks()

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка импорта: {e!s}')
        finally:
            loading_indicator.hide()

    def import_modpack(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                'Выберите файл сборки',
                '',
                'ZIP файлы (*.zip)',
            )
            if not file_path:
                return

        try:
            with zipfile.ZipFile(file_path, 'r') as zipf:
                if 'modpack.json' not in zipf.namelist():
                    raise ValueError('Отсутствует файл modpack.json в архиве')

                pack_data = json.loads(zipf.read('modpack.json'))
                mods_dir = os.path.join(MODS_DIR, pack_data['version'])
                os.makedirs(mods_dir, exist_ok=True)

                for mod in pack_data['mods']:
                    try:
                        zipf.extract(f'mods/{mod}', mods_dir)
                    except KeyError:
                        logging.warning(f'Мод {mod} отсутствует в архиве')

                with open(
                    os.path.join(self.modpacks_dir, f'{pack_data["name"]}.json'),
                    'w',
                ) as f:
                    json.dump(pack_data, f)

            self.load_modpacks()
            QMessageBox.information(self, 'Успех', 'Сборка успешно импортирована!')

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка импорта: {e!s}')

    def export_modpack(self, pack_data):
        try:
            export_path = self.parent_window.settings.get(
                'export_path',
                os.path.expanduser('~/Desktop'),
            )
            os.makedirs(export_path, exist_ok=True)

            with open(os.path.join(self.modpacks_dir, pack_data['filename'])) as f:
                pack_data = json.load(f)

            zip_path = os.path.join(export_path, f'{pack_data["name"]}.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                mods_dir = os.path.join(MODS_DIR, pack_data['version'])
                for mod in pack_data['mods']:
                    mod_path = os.path.join(mods_dir, mod)
                    if os.path.exists(mod_path):
                        zipf.write(mod_path, arcname=f'mods/{mod}')

                zipf.writestr('modpack.json', json.dumps(pack_data))

            QMessageBox.information(
                self,
                'Успех',
                f'Сборка экспортирована в:\n{zip_path}',
            )
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка экспорта: {e!s}')

    def show_creation_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Создание сборки')
        dialog.setFixedSize(500, 400)

        layout = QVBoxLayout()
        self.steps = QStackedWidget()

        # Шаг 1: Основная информация
        step1 = QWidget()
        form = QFormLayout()
        self.pack_name = QLineEdit()
        self.pack_version = QComboBox()
        self.pack_loader = QComboBox()

        for v in MINECRAFT_VERSIONS:
            self.pack_version.addItem(v)
        self.pack_loader.addItems(['Vanilla', 'Forge', 'Fabric', 'OptiFine'])

        form.addRow('Название сборки:', self.pack_name)
        form.addRow('Версия Minecraft:', self.pack_version)
        form.addRow('Модлоадер:', self.pack_loader)
        step1.setLayout(form)

        # Шаг 2: Выбор модов
        step2 = QWidget()
        mods_layout = QVBoxLayout()
        self.mods_selection = QListWidget()
        self.mods_selection.setSelectionMode(QListWidget.MultiSelection)

        version = self.pack_version.currentText()
        mods = ModManager.get_mods_list(version)
        self.mods_selection.addItems(mods)

        mods_layout.addWidget(QLabel('Выберите моды:'))
        mods_layout.addWidget(self.mods_selection)
        step2.setLayout(mods_layout)

        self.steps.addWidget(step1)
        self.steps.addWidget(step2)

        # Навигация
        nav_buttons = QHBoxLayout()
        self.prev_btn = QPushButton('Назад')
        self.next_btn = QPushButton('Далее')
        self.prev_btn.clicked.connect(lambda: self.steps.setCurrentIndex(0))
        self.next_btn.clicked.connect(lambda: self.steps.setCurrentIndex(1))
        nav_buttons.addWidget(self.prev_btn)
        nav_buttons.addWidget(self.next_btn)

        # Сохранение
        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(lambda: self.save_modpack(dialog))

        layout.addWidget(self.steps)
        layout.addLayout(nav_buttons)
        layout.addWidget(save_btn)
        dialog.setLayout(layout)
        dialog.exec_()

    def select_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Выберите иконку',
            '',
            'Images (*.png *.jpg *.jpeg)',
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
                icon_name = f'{name}_{int(time.time())}.png'
                dest_path = os.path.join(self.icons_dir, icon_name)
                shutil.copyfile(self.selected_icon, dest_path)
            except Exception as e:
                logging.exception(f'Ошибка копирования иконки: {e}')
                icon_name = None

        pack_data = {
            'name': name,
            'version': version,
            'loader': loader,
            'mods': selected_mods,
        }
        # Добавляем иконку, только если она есть
        if icon_name:
            pack_data['icon'] = icon_name

        with open(os.path.join(self.modpacks_dir, f'{name}.json'), 'w') as f:
            json.dump(pack_data, f)

        self.load_modpacks()
        dialog.close()
