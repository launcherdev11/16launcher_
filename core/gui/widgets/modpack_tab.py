import json
import logging
import os
import shutil
import time
import zipfile

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QIcon, QCursor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QScrollArea,
    QGridLayout,
    QToolButton,
    QFrame,
    QPushButton,
    QAction,
    QMenu,
    QInputDialog,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QFileDialog,
    QApplication,
    QFormLayout,
    QStackedWidget,
    QCheckBox,
    QGroupBox,
    QTabWidget,
)
from ...config import MINECRAFT_DIR, MINECRAFT_VERSIONS, MODS_DIR
from ...mod_manager import ModManager
from ...util import resource_path


class ModpackTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.modpacks_dir = os.path.join(MINECRAFT_DIR, "modpacks")
        self.icons_dir = os.path.join(
            MINECRAFT_DIR, "modpack_icons"
        ) 
        os.makedirs(self.modpacks_dir, exist_ok=True)
        os.makedirs(self.icons_dir, exist_ok=True)
        self.setup_ui()
        self.load_modpacks()
        self.setup_drag_drop()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        header = QHBoxLayout()

        title_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(
            QPixmap(resource_path("assets/modpack_icon.png")).scaled(32, 32)
        )
        title_layout.addWidget(icon_label)

        self.title = QLabel("Мои сборки")
        self.title.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(self.title)
        title_layout.addStretch()
        header.addLayout(title_layout)

        btn_layout = QHBoxLayout()
        self.create_btn = self.create_tool_button(
            "Создать", "add.png", self.show_creation_dialog
        )
        self.import_btn = self.create_tool_button(
            "Импорт", "import.png", self.import_modpack
        )
        self.refresh_btn = self.create_tool_button(
            "Обновить", "refresh.png", self.load_modpacks
        )

        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.refresh_btn)
        header.addLayout(btn_layout)

        layout.addLayout(header)

        filter_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Поиск по названию...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.search_bar)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "Forge", "Fabric"])
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.currentIndexChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #AAAAAA; font-size: 14px;")
        layout.addWidget(self.status_label)

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

    def create_tool_button(self, text: str, icon: str, callback):
        btn = QToolButton()
        btn.setText(text)
        btn.setIcon(QIcon(resource_path(f"assets/{icon}")))
        btn.setIconSize(QSize(24, 24))
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
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

    def create_modpack_card(self, pack_data):
        icon = QLabel()
        icon_name = pack_data.get("icon")
        icon_path = os.path.join(self.icons_dir, icon_name) if icon_name else ""

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

        header = QHBoxLayout()
        header.addWidget(icon)

        title_layout = QVBoxLayout()
        title = QLabel(pack_data["name"])
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")

        version = QLabel(f"· Minecraft {pack_data['version']}")
        version.setStyleSheet("color: #AAAAAA; font-size: 11px;")

        title_layout.addWidget(title)
        title_layout.addWidget(version)
        header.addLayout(title_layout)
        layout.addLayout(header)

        details = QLabel(f"""
            <div style='color: #CCCCCC; font-size: 12px;'>
                <b>Тип:</b> {pack_data["loader"]}<br>
                <b>Моды:</b> {len(pack_data["mods"])}<br>
                <b>Размер:</b> {self.get_modpack_size(pack_data)}
            </div>
        """)
        layout.addWidget(details)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        play_btn = self.create_card_button(
            "Запустить", "play.png", lambda: self.launch_modpack(pack_data)
        )
        edit_btn = self.create_card_button(
            "Изменить", "edit.png", lambda: self.edit_modpack(pack_data)
        )
        menu_btn = self.create_card_button(
            "⋮", "menu.png", lambda: self.show_context_menu(pack_data)
        )

        btn_layout.addWidget(play_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(menu_btn)
        layout.addLayout(btn_layout)

        return card

    def create_card_button(self, text, icon, callback):
        btn = QPushButton(text)
        btn.setFixedSize(80, 28)
        btn.setIcon(QIcon(resource_path(f"assets/{icon}")))
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

    def filter_modpacks(self):
        search_text = self.search_bar.text().lower()
        filter_type = self.filter_combo.currentText()

        visible_count = 0
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                name_match = search_text in widget.property("pack_name").lower()
                type_match = (filter_type == "Все") or (
                    widget.property("loader_type") == filter_type
                )
                visible = name_match and type_match
                widget.setVisible(visible)
                if visible:
                    visible_count += 1

        self.status_label.setText(
            f"Найдено сборок: {visible_count}"
            if visible_count > 0
            else "Сборки не найдены"
        )

    def load_modpacks(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        modpacks = []
        for file in os.listdir(self.modpacks_dir):
            if file.endswith(".json"):
                try:
                    with open(os.path.join(self.modpacks_dir, file), "r") as f:
                        pack = json.load(f)
                        pack["filename"] = file
                        modpacks.append(pack)
                except Exception as e:
                    logging.error(f"Error loading modpack {file}: {e}")

        if not modpacks:
            self.status_label.setText("🎮 Создайте свою первую сборку!")
            return

        row, col = 0, 0
        for pack in sorted(modpacks, key=lambda x: x["name"].lower()):
            card = self.create_modpack_card(pack)
            card.setProperty("pack_name", pack["name"])
            card.setProperty("loader_type", pack["loader"])
            self.grid_layout.addWidget(card, row, col)

            col += 1
            if col > 3: 
                col = 0
                row += 1

        self.status_label.setText(f"Загружено сборок: {len(modpacks)}")

    def get_modpack_size(self, pack_data):
        total_size = 0
        mods_dir = os.path.join(MODS_DIR, pack_data["version"])
        if os.path.exists(mods_dir):
            for mod in pack_data["mods"]:
                mod_path = os.path.join(mods_dir, mod)
                if os.path.exists(mod_path):
                    total_size += os.path.getsize(mod_path)
        return f"{total_size / 1024 / 1024:.1f} MB"

    def show_context_menu(self, pack_data):
        menu = QMenu(self)

        export_action = QAction(
            QIcon(resource_path("assets/export.png")), "Экспорт", self
        )
        export_action.triggered.connect(lambda: self.export_modpack(pack_data))

        duplicate_action = QAction(
            QIcon(resource_path("assets/copy.png")), "Дублировать", self
        )
        duplicate_action.triggered.connect(lambda: self.duplicate_modpack(pack_data))

        delete_action = QAction(
            QIcon(resource_path("assets/delete.png")), "Удалить", self
        )
        delete_action.triggered.connect(lambda: self.delete_modpack(pack_data))

        menu.addAction(export_action)
        menu.addAction(duplicate_action)
        menu.addAction(delete_action)
        menu.exec_(QCursor.pos())

    def duplicate_modpack(self, pack_data):
        new_name, ok = QInputDialog.getText(
            self,
            "Дублирование сборки",
            "Введите новое название:",
            QLineEdit.Normal,
            f"{pack_data['name']} - Копия",
        )

        if ok and new_name:
            new_filename = f"{new_name}.json"
            new_path = os.path.join(self.modpacks_dir, new_filename)

            if os.path.exists(new_path):
                QMessageBox.warning(
                    self, "Ошибка", "Сборка с таким именем уже существует!"
                )
                return

            try:
                shutil.copyfile(
                    os.path.join(self.modpacks_dir, pack_data["filename"]), new_path
                )
                self.load_modpacks()
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось создать копию: {str(e)}"
                )

    def launch_modpack(self, pack_data):
        self.parent_window.version_select.setCurrentText(pack_data["version"])
        self.parent_window.loader_select.setCurrentText(pack_data["loader"])
        self.parent_window.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self,
            "Запуск сборки",
            f"Параметры сборки '{pack_data['name']}' установлены!\nНажмите 'Играть' для запуска.",
        )

    def edit_modpack(self, pack_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Редактирование: {pack_data['name']}")
        dialog.setFixedSize(800, 600)

        layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_label = QLabel("Название:")
        self.name_edit = QLineEdit(pack_data["name"])
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)

        version_layout = QHBoxLayout()
        version_label = QLabel("Версия:")
        self.version_combo = QComboBox()
        self.version_combo.addItems(MINECRAFT_VERSIONS)
        self.version_combo.setCurrentText(pack_data["version"])
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_combo)

        loader_layout = QHBoxLayout()
        loader_label = QLabel("Модлоадер:")
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["Forge", "Fabric"])
        self.loader_combo.setCurrentText(pack_data["loader"])
        loader_layout.addWidget(loader_label)
        loader_layout.addWidget(self.loader_combo)

        # Секция модов
        mods_layout = QVBoxLayout()
        mods_label = QLabel("Моды в сборке:")
        self.mods_list = QListWidget()
        self.mods_list.addItems(pack_data["mods"])

        # Кнопки управления модами
        mod_buttons = QHBoxLayout()
        self.remove_mod_btn = QPushButton("Удалить выбранное")
        self.remove_mod_btn.clicked.connect(lambda: self.remove_selected_mods())
        self.add_mod_btn = QPushButton("Добавить моды")
        self.add_mod_btn.clicked.connect(lambda: self.add_mods_to_pack(pack_data))

        mod_buttons.addWidget(self.remove_mod_btn)
        mod_buttons.addWidget(self.add_mod_btn)

        mods_layout.addWidget(mods_label)
        mods_layout.addWidget(self.mods_list)
        mods_layout.addLayout(mod_buttons)

        #  layout
        layout.addLayout(name_layout)
        layout.addLayout(version_layout)
        layout.addLayout(loader_layout)
        layout.addLayout(mods_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(
            lambda: self.save_modpack_changes(pack_data, dialog)
        )
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        dialog.exec_()

    def remove_selected_mods(self):
        selected_items = self.mods_list.selectedItems()
        for item in selected_items:
            row = self.mods_list.row(item)
            self.mods_list.takeItem(row)

    def add_mods_to_pack(self, pack_data):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Mod files (*.jar *.zip)")

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            mods_dir = os.path.join(MODS_DIR, pack_data["version"])

            for file_path in selected_files:
                mod_name = os.path.basename(file_path)
                dest_path = os.path.join(mods_dir, mod_name)

                if not os.path.exists(dest_path):
                    shutil.copyfile(file_path, dest_path)

                if not self.mods_list.findItems(mod_name, Qt.MatchExactly):
                    self.mods_list.addItem(mod_name)

            QMessageBox.information(self, "Успех", "Моды успешно добавлены!")

    def save_modpack_changes(self, old_pack, dialog):
        new_name = self.name_edit.text()
        new_version = self.version_combo.currentText()
        new_loader = self.loader_combo.currentText()

        new_mods = []
        for i in range(self.mods_list.count()):
            new_mods.append(self.mods_list.item(i).text())

        try:
            old_path = os.path.join(self.modpacks_dir, old_pack["filename"])
            os.remove(old_path)

            new_filename = f"{new_name}.json"
            new_pack = {
                "name": new_name,
                "version": new_version,
                "loader": new_loader,
                "mods": new_mods,
            }

            with open(os.path.join(self.modpacks_dir, new_filename), "w") as f:
                json.dump(new_pack, f)

            self.load_modpacks()
            dialog.accept()

        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сохранить изменения: {str(e)}"
            )

    def delete_modpack(self, pack_data):
        confirm = QMessageBox.question(
            self,
            "Удаление сборки", 
            f"Вы уверены, что хотите удалить сборку '{pack_data['name']}'?",
            QMessageBox.Yes | QMessageBox.No,  
            QMessageBox.No,  
        )

        if confirm == QMessageBox.Yes:
            try:
                os.remove(os.path.join(self.modpacks_dir, pack_data["filename"]))
                self.load_modpacks()
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось удалить сборку: {str(e)}"
                )

    def setup_drag_drop(self):
        self.setAcceptDrops(True)
        self.scroll_area.setAcceptDrops(True)
        self.scroll_content.setAcceptDrops(True)
        self.scroll_area.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith(".zip") for url in urls):
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if file_path.lower().endswith(".zip"):
                self.handle_dropped_file(file_path)
        event.acceptProposedAction()

    def handle_dropped_file(self, file_path):
        try:
            loading_indicator = QLabel("Импорт сборки...", self)
            loading_indicator.setAlignment(Qt.AlignCenter)
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
                self.width() // 2 - 150, self.height() // 2 - 50, 300, 100
            )
            loading_indicator.show()
            QApplication.processEvents()

            self.import_modpack(file_path)
            self.load_modpacks()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {str(e)}")
        finally:
            loading_indicator.hide()

    def import_modpack(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Выберите файл сборки", "", "ZIP файлы (*.zip)"
            )
            if not file_path:
                return

        try:
            with zipfile.ZipFile(file_path, "r") as zipf:
                if "modpack.json" not in zipf.namelist():
                    raise ValueError("Отсутствует файл modpack.json в архиве")

                pack_data = json.loads(zipf.read("modpack.json"))
                mods_dir = os.path.join(MODS_DIR, pack_data["version"])
                os.makedirs(mods_dir, exist_ok=True)

                for mod in pack_data["mods"]:
                    try:
                        zipf.extract(f"mods/{mod}", mods_dir)
                    except KeyError:
                        logging.warning(f"Мод {mod} отсутствует в архиве")

                with open(
                    os.path.join(self.modpacks_dir, f"{pack_data['name']}.json"), "w"
                ) as f:
                    json.dump(pack_data, f)

            self.load_modpacks()
            QMessageBox.information(self, "Успех", "Сборка успешно импортирована!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {str(e)}")

    def export_modpack(self, pack_data):
        try:
            export_path = self.parent_window.settings.get(
                "export_path", os.path.expanduser("~/Desktop")
            )
            os.makedirs(export_path, exist_ok=True)

            with open(os.path.join(self.modpacks_dir, pack_data["filename"]), "r") as f:
                pack_data = json.load(f)

            zip_path = os.path.join(export_path, f"{pack_data['name']}.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                mods_dir = os.path.join(MODS_DIR, pack_data["version"])
                for mod in pack_data["mods"]:
                    mod_path = os.path.join(mods_dir, mod)
                    if os.path.exists(mod_path):
                        zipf.write(mod_path, arcname=f"mods/{mod}")

                zipf.writestr("modpack.json", json.dumps(pack_data))

            QMessageBox.information(
                self, "Успех", f"Сборка экспортирована в:\n{zip_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {str(e)}")

    def show_creation_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Создание сборки")
        dialog.setFixedSize(900, 750)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Создание новой сборки")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title_label)

        info_group = QGroupBox("Основная информация")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #CCCCCC;
            }
        """)
        
        info_layout = QFormLayout()
        info_layout.setSpacing(10)

        self.pack_name = QLineEdit()
        self.pack_name.setPlaceholderText("Введите название сборки")
        self.pack_name.setStyleSheet("""
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
        """)

        self.pack_version = QComboBox()
        self.pack_loader = QComboBox()

        versions = get_version_list()
        for v in versions:
            if v["type"] == "release":
                self.pack_version.addItem(v["id"])
        self.pack_loader.addItems(["Vanilla", "Forge", "Fabric", "OptiFine"])

        info_layout.addRow("Название сборки:", self.pack_name)
        info_layout.addRow("Версия Minecraft:", self.pack_version)
        info_layout.addRow("Модлоадер:", self.pack_loader)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555555;
                border-radius: 5px;
                background-color: #2D2D2D;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #CCCCCC;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #505050;
                color: #FFFFFF;
            }
        """)

        # Вкладка модов
        mods_dir = os.path.join(MODS_DIR, self.pack_version.currentText())
        self.mods_tab = ContentTab(mods_dir, [".jar"], self)
        tabs.addTab(self.mods_tab, "Моды")

        # Вкладка текстур
        textures_dir = os.path.join(MINECRAFT_DIR, "resourcepacks")
        self.textures_tab = ContentTab(textures_dir, [".zip"], self)
        tabs.addTab(self.textures_tab, "Текстуры")

        # Вкладка шейдеров
        shaders_dir = os.path.join(MINECRAFT_DIR, "shaderpacks")
        self.shaders_tab = ContentTab(shaders_dir, [".zip"], self)
        tabs.addTab(self.shaders_tab, "Шейдеры")

        layout.addWidget(tabs)

        # Кнопки
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedSize(100, 35)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                color: white;
                border-radius: 4px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        
        save_btn = QPushButton("Создать сборку")
        save_btn.setFixedSize(150, 40)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(lambda: self.save_new_modpack(dialog))
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)

        self.pack_version.currentTextChanged.connect(self.update_content_tabs)

        dialog.exec_()

    def update_content_tabs(self, version):
        mods_dir = os.path.join(MODS_DIR, version)
        self.mods_tab.target_dir = mods_dir
        self.mods_tab.refresh_list()

    def save_new_modpack(self, dialog):
        name = self.pack_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название сборки!")
            return

        version = self.pack_version.currentText()
        loader = self.pack_loader.currentText()
        
        all_mods = [self.mods_tab.file_list.item(i).text() for i in range(self.mods_tab.file_list.count())]
        all_textures = [self.textures_tab.file_list.item(i).text() for i in range(self.textures_tab.file_list.count())]
        all_shaders = [self.shaders_tab.file_list.item(i).text() for i in range(self.shaders_tab.file_list.count())]

        pack_data = {
            "name": name,
            "version": version,
            "loader": loader,
            "mods": all_mods,
            "textures": all_textures,
            "shaders": all_shaders,
        }

        try:
            os.makedirs(self.modpacks_dir, exist_ok=True)
            pack_path = os.path.join(self.modpacks_dir, f"{name}.json")
            
            if os.path.exists(pack_path):
                reply = QMessageBox.question(
                    self,
                    "Сборка уже существует",
                    f"Сборка с именем '{name}' уже существует. Перезаписать?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            with open(pack_path, "w", encoding="utf-8") as f:
                json.dump(pack_data, f, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "Успех", f"Сборка '{name}' успешно создана!")
            self.load_modpacks()
            dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать сборку: {str(e)}")

    def select_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите иконку", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.selected_icon = file_path
            self.icon_label.setText(os.path.basename(file_path))

    def save_modpack(self, dialog):
        name = self.pack_name.text()
        version = self.pack_version.currentText()
        loader = self.pack_loader.currentText()
        selected_mods = [item.text() for item in self.mods_selection.selectedItems()]

        selected_textures = []
        selected_shaders = []
        if hasattr(self, "textures_selection") and self.use_textures_cb.isChecked():
            selected_textures = [item.text() for item in self.textures_selection.selectedItems()]
        if hasattr(self, "shaders_selection") and self.use_shaders_cb.isChecked():
            selected_shaders = [item.text() for item in self.shaders_selection.selectedItems()]

        icon_name = None
        if hasattr(self, "selected_icon") and self.selected_icon:
            try:
                icon_name = f"{name}_{int(time.time())}.png"
                dest_path = os.path.join(self.icons_dir, icon_name)
                shutil.copyfile(self.selected_icon, dest_path)
            except Exception as e:
                logging.error(f"Ошибка копирования иконки: {e}")
                icon_name = None

        pack_data = {
            "name": name,
            "version": version,
            "loader": loader,
            "mods": selected_mods,
            "textures": selected_textures,
            "shaders": selected_shaders,
        }
        if icon_name:
            pack_data["icon"] = icon_name

        try:
            with open(os.path.join(self.modpacks_dir, f"{name}.json"), "w") as f:
                json.dump(pack_data, f, indent=4, ensure_ascii=False)

            self.load_modpacks()
            dialog.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить сборку: {str(e)}")
            
class ContentTab(QWidget):
    def __init__(self, target_dir, file_exts, parent=None):
        super().__init__(parent)
        self.target_dir = target_dir
        self.file_exts = file_exts
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Область drag&drop
        self.drag_drop = DragDropArea("Перетащите файлы сюда или выберите ниже")
        self.drag_drop.browse_btn.clicked.connect(self.browse_files)
        self.drag_drop.filesDropped.connect(self.handle_dropped_files)
        layout.addWidget(self.drag_drop)
        
        # Заголовок списка файлов
        list_header = QHBoxLayout()
        list_label = QLabel("Добавленные файлы:")
        list_label.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        
        self.select_all_btn = QPushButton("Выделить все")
        self.select_all_btn.setFixedSize(105, 35)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                color: white;
                border-radius: 7px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)
        self.select_all_btn.clicked.connect(self.select_all_files)
        
        list_header.addWidget(list_label)
        list_header.addStretch()
        list_header.addWidget(self.select_all_btn)
        layout.addLayout(list_header)
        
        # Список файлов
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.MultiSelection)
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 5px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #505050;
            }
        """)
        
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_list_context_menu)
        
        layout.addWidget(self.file_list)
        
        # Кнопка открытия папки
        self.open_folder_btn = QPushButton("Выбрать файлы")
        self.open_folder_btn.setFixedSize(150, 40)
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                border-radius: 5px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)
        self.open_folder_btn.clicked.connect(self.browse_files)
        layout.addWidget(self.open_folder_btn, 0, Qt.AlignCenter)
        
        self.refresh_list()

    def show_list_context_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Удалить выбранное")
        delete_action.triggered.connect(self.delete_selected_files)
        menu.exec_(self.file_list.mapToGlobal(position))

    def delete_selected_files(self):
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
            
        reply = QMessageBox.question(
            self, 
            "Подтверждение удаления", 
            f"Удалить {len(selected_items)} выбранных файлов?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for item in selected_items:
                file_name = item.text()
                file_path = os.path.join(self.target_dir, file_name)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить файл {file_name}: {str(e)}")
            
            self.refresh_list()

    def select_all_files(self):
        self.file_list.selectAll()

    def handle_dropped_files(self, file_paths):
        for file_path in file_paths:
            self.add_file(file_path)
        self.refresh_list()

    def browse_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_filter = "Файлы (" + " ".join([f"*{ext}" for ext in self.file_exts]) + ")"
        file_dialog.setNameFilter(file_filter)
        
        if file_dialog.exec_():
            for file_path in file_dialog.selectedFiles():
                self.add_file(file_path)
            self.refresh_list()

    def add_file(self, file_path):
        try:
            os.makedirs(self.target_dir, exist_ok=True)
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(self.target_dir, file_name)
            
            if os.path.exists(dest_path):
                reply = QMessageBox.question(
                    self, 
                    "Файл уже существует", 
                    f"Файл {file_name} уже существует. Заменить?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            shutil.copy2(file_path, dest_path)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить файл: {str(e)}")

    def refresh_list(self):
        self.file_list.clear()
        if os.path.exists(self.target_dir):
            for file in os.listdir(self.target_dir):
                if any(file.lower().endswith(ext.lower()) for ext in self.file_exts):
                    self.file_list.addItem(file)

    def get_selected_files(self):
        return [item.text() for item in self.file_list.selectedItems()]
            
class DragDropArea(QFrame):
    filesDropped = pyqtSignal(list)
    
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(150)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap(resource_path("assets/upload.png")).scaled(48, 48))
        icon_label.setAlignment(Qt.AlignCenter)
        
        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("color: #CCCCCC; font-size: 14px; margin: 10px;")
        
        self.browse_btn = QPushButton("Выбрать файлы")
        self.browse_btn.setFixedSize(120, 35)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                color: white;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addWidget(self.browse_btn, 0, Qt.AlignCenter)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            DragDropArea {
                background-color: #404040;
                border: 2px dashed #666666;
                border-radius: 10px;
            }
            DragDropArea:hover {
                border-color: #888888;
                background-color: #484848;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DragDropArea {
                    background-color: #484848;
                    border: 2px dashed #888888;
                    border-radius: 10px;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DragDropArea {
                background-color: #404040;
                border: 2px dashed #666666;
                border-radius: 10px;
            }
        """)

    def dropEvent(self, event):
        self.setStyleSheet("""
            DragDropArea {
                background-color: #404040;
                border: 2px dashed #666666;
                border-radius: 10px;
            }
        """)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            file_paths = []
            for url in event.mimeData().urls():
                file_paths.append(url.toLocalFile())
            self.filesDropped.emit(file_paths)  

class DraggableListWidget(QListWidget):
    def __init__(self, target_dir, file_exts, parent=None):
        super().__init__(parent)
        self.target_dir = target_dir
        self.file_exts = file_exts
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.MultiSelection)
        os.makedirs(target_dir, exist_ok=True)
        self.refresh_list()  
        
    def refresh_list(self):
        self.clear()
        if os.path.exists(self.target_dir):
            for file in os.listdir(self.target_dir):
                if any(file.lower().endswith(ext) for ext in self.file_exts):
                    self.addItem(file)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith(tuple(self.file_exts)) for url in urls):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(tuple(self.file_exts)):
                    try:
                        os.makedirs(self.target_dir, exist_ok=True)
                        file_name = os.path.basename(file_path)
                        dest_path = os.path.join(self.target_dir, file_name)

                        if not os.path.exists(dest_path):
                            shutil.copyfile(file_path, dest_path)

                    except Exception as e:
                        QMessageBox.critical(self, "Ошибка", f"Не удалось добавить файл: {str(e)}")
            
            self.refresh_list()  
            event.acceptProposedAction()
        else:
            event.ignore()

