import json
import logging
import os
import shutil
import time
from typing import Any, Callable
import zipfile

from PyQt5.QtCore import QSize, Qt, QEvent, QObject, QRegExp
from PyQt5.QtGui import QCursor, QDragEnterEvent, QDropEvent, QFont, QIcon, QPixmap, QRegExpValidator
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
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QMessageBox,
    QTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import (
    MINECRAFT_DIR,
    MINECRAFT_VERSIONS,
    MODS_DIR,
    RESOURCEPACKS_DIR,
    SHADERPACKS_DIR,
)
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
        )  
        self.banners_dir = os.path.join(
            MINECRAFT_DIR,
            'modpack_banners',
        )
        self.ICON_W, self.ICON_H = 96, 96
        self.BANNER_W, self.BANNER_H = 760, 200
        self.BANNER_THUMB_W = 480
        self.BANNER_THUMB_H = int(self.BANNER_H * (self.BANNER_THUMB_W / self.BANNER_W))
        os.makedirs(self.modpacks_dir, exist_ok=True)
        os.makedirs(self.icons_dir, exist_ok=True)
        os.makedirs(self.banners_dir, exist_ok=True)
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
            QPixmap(resource_path('assets/modpack_icon.png')).scaled(32, 32),
        )
        title_layout.addWidget(icon_label)

        self.title = QLabel('Мои сборки')
        self.title.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title_layout.addWidget(self.title)
        title_layout.addStretch()
        header.addLayout(title_layout)

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

        filter_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Поиск по названию...')
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.search_bar)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['Все', 'Forge', 'Fabric'])
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.currentIndexChanged.connect(self.filter_modpacks)
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet('color: #AAAAAA; font-size: 14px;')
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
            QTextEdit {
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
        qicon = QIcon(resource_path(f'assets/{icon}'))
        btn.setIcon(qicon)
        btn.setIconSize(QSize(24, 24))
        if not qicon.isNull():
            btn.setText('')
            btn.setToolTip(text)
        else:
            btn.setText(text)
        btn.setFixedSize(48, 48)
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

    def _safe_mod_count(self, mods_field: Any) -> int:
        """Возвращает корректное число модов при разных форматах данных."""
        try:
            if isinstance(mods_field, list):
                return len(mods_field)
            if isinstance(mods_field, str):
                parsed = json.loads(mods_field)
                return len(parsed) if isinstance(parsed, list) else 0
            return 0
        except Exception:
            return 0

    def _existing_mods_count(self, pack_data: dict[str, Any]) -> int:
        """Считает только реально существующие файлы модов в каталоге версии."""
        try:
            version = pack_data.get('version', '')
            mods_dir = os.path.join(MODS_DIR, version)
            mods_list: Any = pack_data.get('mods', [])
            if isinstance(mods_list, str):
                mods_list = json.loads(mods_list)
            if not isinstance(mods_list, list):
                return 0
            count = 0
            for name in mods_list:
                if os.path.exists(os.path.join(mods_dir, str(name))):
                    count += 1
            return count
        except Exception:
            return 0

    def create_modpack_card(self, pack_data: dict[str, Any]) -> QFrame:
        icon = QLabel()
        icon_name = pack_data.get('icon')
        icon_path = os.path.join(self.icons_dir, icon_name) if icon_name else ''
        # preview for icon
        icon.setFixedSize(self.ICON_W, self.ICON_H)
        icon.setStyleSheet('background-color: #3A3A3A; border-radius: 8px;')
        if icon_path and os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(self.ICON_W, self.ICON_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            icon.setPixmap(pix)

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
        header.setSpacing(12)
        header.addWidget(icon)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(8, 0, 0, 0)
        title = QLabel(pack_data['name'])
        title.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        title.setStyleSheet('color: #FFFFFF;')

        version = QLabel(f'· Minecraft {pack_data["version"]}')
        version.setStyleSheet('color: #AAAAAA; font-size: 11px;')

        title_layout.addWidget(title)
        title_layout.addWidget(version)
        header.addLayout(title_layout)
        layout.addLayout(header)

        details = QLabel(f"""
            <div style='color: #CCCCCC; font-size: 12px;'>
                <b>Тип:</b> {pack_data['loader']}<br>
                <b>Моды:</b> {self._existing_mods_count(pack_data)}<br>
                <b>Размер:</b> {self.get_modpack_size(pack_data)}
            </div>
        """)
        layout.addWidget(details)

        

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

        
        def on_card_click(event):
            child = card.childAt(event.pos())
            if isinstance(child, QPushButton):
                return QFrame.mousePressEvent(card, event)
            if event.button() == Qt.LeftButton:
                self.open_modpack_details(pack_data)
        card.mousePressEvent = on_card_click

        return card

    def open_modpack_details(self, pack_data: dict[str, Any]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(pack_data['name'])
        dialog.resize(820, 680)

        dialog.setStyleSheet(
            """
            QDialog { background-color: #2D2D2D; color: #FFFFFF; }
            QLabel { color: #FFFFFF; }
            QPushButton { background-color: #404040; color: #FFFFFF; border: 1px solid #555555; border-radius: 10px; padding: 8px 12px; }
            QPushButton:hover { background-color: #505050; }
            QTreeWidget { background-color: #373737; color: #FFFFFF; border: 1px solid #555555; border-radius: 10px; }
            QTreeWidget::item { color: #FFFFFF; padding: 6px 8px; }
            QScrollArea { background: transparent; border: none; }
            """
        )

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        
        banner = QLabel()
        banner.setFixedSize(self.BANNER_W, self.BANNER_H)
        banner.setStyleSheet('background-color: #3A3A3A; border: 1px solid #555555; border-radius: 12px;')
        banner.setScaledContents(True)
        icon_name = pack_data.get('icon')
        banner_name = pack_data.get('banner')
        
        if banner_name:
            banner_path = os.path.join(self.banners_dir, banner_name)
            if os.path.exists(banner_path):
                banner.setPixmap(QPixmap(banner_path))
        elif icon_name:
            icon_path = os.path.join(self.icons_dir, icon_name)
            if os.path.exists(icon_path):
                banner.setPixmap(QPixmap(icon_path))
        root_layout.addWidget(banner)

        
        title_row = QHBoxLayout()
        title_lbl = QLabel(f"{pack_data['name']}")
        title_lbl.setFont(QFont('Arial', 26, QFont.Weight.Bold))
        subtitle = QLabel(f"{pack_data['version']}")
        subtitle.setStyleSheet('color:#BBBBBB; font-size:18px; margin-left:8px;')
        title_row.addWidget(title_lbl)
        title_row.addWidget(subtitle)
        title_row.addStretch()
        root_layout.addLayout(title_row)

        
        badges = QHBoxLayout()
        def pill(text: str) -> QLabel:
            l = QLabel(text)
            l.setStyleSheet('background-color:#404040; border: 1px solid #555555; border-radius:12px; padding:6px 10px; font-size:13px;')
            return l
        mods_field = pack_data.get('mods', [])
        if isinstance(mods_field, list):
            mod_count = len(mods_field)
        elif isinstance(mods_field, str):
            
            try:
                parsed = json.loads(mods_field)
                mod_count = len(parsed) if isinstance(parsed, list) else 0
            except Exception:
                mod_count = 0
        else:
            mod_count = 0
        badges.addWidget(pill(f"{mod_count} модов"))
        badges.addWidget(pill(pack_data.get('loader', '')))
        badges.addWidget(pill(self.get_modpack_size(pack_data)))
        badges.addStretch()
        root_layout.addLayout(badges)

        
        switch_row = QHBoxLayout()
        btn_desc = QPushButton('Описание')
        btn_det = QPushButton('Детали')
        for b in (btn_desc, btn_det):
            b.setCheckable(True)
            b.setStyleSheet('QPushButton{background-color:#404040; border:1px solid #555555; border-radius:14px; padding:8px 16px;} QPushButton:checked{background-color:#505050;}')
        btn_desc.setChecked(True)
        switch_row.addWidget(btn_desc)
        switch_row.addWidget(btn_det)
        switch_row.addStretch()
        root_layout.addLayout(switch_row)

        stack = QStackedWidget()

        
        desc_page = QWidget()
        desc_layout = QVBoxLayout(desc_page)
        desc_box = QLabel((pack_data.get('description') or ''))
        desc_box.setWordWrap(True)
        desc_box.setStyleSheet('background-color:#404040; border:1px solid #555555; border-radius:12px; padding:14px; font-size:14px;')
        desc_layout.addWidget(desc_box)
        stack.addWidget(desc_page)

        
        det_page = QWidget()
        det_layout = QVBoxLayout(det_page)
        tree = QTreeWidget()
        tree.setColumnCount(1)
        tree.setHeaderHidden(True)
        root_item = QTreeWidgetItem([pack_data['name']])
        
        icon_suffix = ''
        try:
            if hasattr(self.parent_window, 'current_theme'):
                icon_suffix = '' if self.parent_window.current_theme == 'dark' else '_dark'
        except Exception:
            icon_suffix = ''
        folder_icon = QIcon(resource_path(f'assets/folder{icon_suffix}.png'))

        
        def to_list(value: Any) -> list[str]:
            
            try:
                if isinstance(value, list):
                    result: list[str] = []
                    for item in value:
                        if isinstance(item, dict):
                            name = item.get('file') or item.get('name') or ''
                            if name:
                                result.append(str(name))
                        elif item is not None:
                            result.append(str(item))
                    return result
                if isinstance(value, str):
                    s = value.strip()
                    if not s:
                        return []
                    
                    try:
                        parsed = json.loads(s)
                        if isinstance(parsed, list):
                            return to_list(parsed)
                    except Exception:
                        pass
                    
                    return [part.strip() for part in s.split(',') if part.strip()]
                return []
            except Exception:
                return []

        mods_list = to_list(pack_data.get('mods', []))
        textures_list = to_list(pack_data.get('textures', []))
        shaders_list = to_list(pack_data.get('shaders', []))

        mods_item = QTreeWidgetItem(['mods'])
        mods_item.setIcon(0, folder_icon)
        for m in mods_list:
            if not m:
                continue
            # показываем только то, что реально было выбрано/сохранено в сборке
            QTreeWidgetItem(mods_item, [m])
        textures_item = QTreeWidgetItem(['resourcepacks'])
        textures_item.setIcon(0, folder_icon)
        for t in textures_list:
            if not t:
                continue
            QTreeWidgetItem(textures_item, [t])
        shaders_item = QTreeWidgetItem(['shaders'])
        shaders_item.setIcon(0, folder_icon)
        for s in shaders_list:
            if not s:
                continue
            QTreeWidgetItem(shaders_item, [s])

        
        root_item.addChildren([mods_item, shaders_item, textures_item])
        tree.addTopLevelItem(root_item)
        tree.expandAll()
        tree.repaint()
        det_layout.addWidget(tree)
        stack.addWidget(det_page)

        def show_desc():
            stack.setCurrentIndex(0)
            btn_desc.setChecked(True)
            btn_det.setChecked(False)
        def show_det():
            stack.setCurrentIndex(1)
            btn_desc.setChecked(False)
            btn_det.setChecked(True)
        btn_desc.clicked.connect(show_desc)
        btn_det.clicked.connect(show_det)

        root_layout.addWidget(stack)

        
        action_btn = QPushButton('Запустить')
        action_btn.setFixedHeight(44)
        action_btn.setIcon(QIcon(resource_path('assets/play64.png')))
        action_btn.setIconSize(QSize(20, 20))
        
        action_btn.clicked.connect(lambda: (self.launch_modpack(pack_data), dialog.accept()))
        root_layout.addWidget(action_btn)

        dialog.setLayout(root_layout)
        dialog.exec_()

    def create_card_button(
        self,
        text: str,
        icon: str,
        callback: Callable[[], None],
    ) -> QPushButton:
        btn = QPushButton()
        qicon = QIcon(resource_path(f'assets/{icon}'))
        btn.setIcon(qicon)
        btn.setIconSize(QSize(16, 16))
        if not qicon.isNull():
            btn.setText('')
            btn.setToolTip(text)
        else:
            btn.setText(text)
        btn.setFixedSize(28, 28)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                color: #FFFFFF;
                border-radius: 5px;
                font-size: 0px;
                padding: 2px 2px;
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
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

        row, col = 0, 0
        for pack in sorted(modpacks, key=lambda x: x['name'].lower()):
            card = self.create_modpack_card(pack)
            card.setProperty('pack_name', pack['name'])
            card.setProperty('loader_type', pack['loader'])
            self.grid_layout.addWidget(card, row, col)

            col += 1
            if col > 2:
                col = 0
                row += 1

        self.status_label.setText(f'Загружено сборок: {len(modpacks)}')

    def get_modpack_size(self, pack_data: dict[str, Any]) -> str:
        total_size = 0
        version = pack_data.get('version', '')
        mods_dir = os.path.join(MODS_DIR, version)
        mods_list = pack_data.get('mods', [])
        
        if isinstance(mods_list, str):
            try:
                mods_list = json.loads(mods_list)
            except Exception:
                mods_list = []
        
        if os.path.exists(mods_dir) and isinstance(mods_list, list):
            for mod in mods_list:
                mod_path = os.path.join(mods_dir, str(mod))
                if os.path.exists(mod_path):
                    try:
                        total_size += os.path.getsize(mod_path)
                    except Exception:
                        pass
        
        for key, base_dir in (
            ('textures', RESOURCEPACKS_DIR),
            ('shaders', SHADERPACKS_DIR),
        ):
            items = pack_data.get(key, [])
            if isinstance(items, list):
                for name in items:
                    p = os.path.join(base_dir, str(name))
                    try:
                        if os.path.isdir(p):
                            for root, _dirs, files in os.walk(p):
                                for f in files:
                                    total_size += os.path.getsize(os.path.join(root, f))
                        elif os.path.exists(p):
                            total_size += os.path.getsize(p)
                    except Exception:
                        pass
        unit = 'MB'
        value = total_size / 1024 / 1024
        return f'{value:.1f} {unit}'

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

        name_layout = QHBoxLayout()
        name_label = QLabel('Название:')
        self.name_edit = QLineEdit(pack_data['name'])
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)

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
        self.loader_combo.addItems(['Forge', 'Fabric'])
        self.loader_combo.setCurrentText(pack_data['loader'])
        loader_layout.addWidget(loader_label)
        loader_layout.addWidget(self.loader_combo)

        desc_layout = QVBoxLayout()
        desc_label = QLabel('Описание:')
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText('Краткое описание сборки...')
        self.desc_edit.setFixedHeight(100)
        self.desc_edit.setText(pack_data.get('description', ''))
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.desc_edit)

        
        icon_row = QHBoxLayout()
        icon_lbl = QLabel('Иконка:')
        self.icon_preview_edit = QLabel()
        self.icon_preview_edit.setFixedSize(self.ICON_W, self.ICON_H)
        self.icon_preview_edit.setStyleSheet('background-color: #3A3A3A; border: 1px solid #555555; border-radius: 8px;')
        current_icon_name = pack_data.get('icon')
        if current_icon_name:
            current_icon_path = os.path.join(self.icons_dir, current_icon_name)
            if os.path.exists(current_icon_path):
                self.icon_preview_edit.setPixmap(QPixmap(current_icon_path).scaled(self.ICON_W, self.ICON_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        choose_icon_btn_edit = QPushButton('Выбрать')
        choose_icon_btn_edit.setIcon(QIcon(resource_path('assets/folder.png')))
        choose_icon_btn_edit.setIconSize(QSize(18, 18))
        choose_icon_btn_edit.clicked.connect(lambda: self.select_image('icon'))
        icon_row.addWidget(icon_lbl)
        icon_row.addWidget(self.icon_preview_edit)
        icon_row.addWidget(choose_icon_btn_edit)

        mods_layout = QVBoxLayout()
        mods_layout.setContentsMargins(0, 8, 0, 0)
        mods_layout.setSpacing(10)
        mods_label = QLabel('Моды в сборке:')
        self.mods_list = QListWidget()
        self.mods_list.addItems(pack_data['mods'])

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

        layout.addLayout(name_layout)
        layout.addLayout(version_layout)
        layout.addLayout(loader_layout)
        layout.addLayout(desc_layout)
        layout.addLayout(icon_row)
        layout.addLayout(mods_layout)

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
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter('Mod files (*.jar *.zip)')

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            mods_dir = os.path.join(MODS_DIR, pack_data['version'])

            for file_path in selected_files:
                mod_name = os.path.basename(file_path)
                dest_path = os.path.join(mods_dir, mod_name)

                if not os.path.exists(dest_path):
                    shutil.copyfile(file_path, dest_path)

                if not self.mods_list.findItems(mod_name, Qt.MatchExactly):
                    self.mods_list.addItem(mod_name)

            QMessageBox.information(self, 'Успех', 'Моды успешно добавлены!')

    def save_modpack_changes(self, old_pack: dict[str, Any], dialog: QDialog) -> None:
        new_name = self.name_edit.text()
        new_version = self.version_combo.currentText()
        new_loader = self.loader_combo.currentText()
        new_description = self.desc_edit.toPlainText().strip()

        new_mods = []
        for i in range(self.mods_list.count()):
            new_mods.append(self.mods_list.item(i).text())

        try:
            old_path = os.path.join(self.modpacks_dir, old_pack['filename'])
            os.remove(old_path)

            new_filename = f'{new_name}.json'

            
            icon_name = old_pack.get('icon')
            banner_name = old_pack.get('banner')
            if hasattr(self, 'selected_icon') and self.selected_icon:
                try:
                    icon_name = f'{new_name}_{int(time.time())}.png'
                    dest_path = os.path.join(self.icons_dir, icon_name)
                    shutil.copyfile(self.selected_icon, dest_path)
                except Exception as e:
                    logging.exception(f'Ошибка копирования иконки: {e}')
            if hasattr(self, 'selected_banner') and self.selected_banner:
                try:
                    banner_name = f'{new_name}_{int(time.time())}_banner.png'
                    dest_path = os.path.join(self.banners_dir, banner_name)
                    shutil.copyfile(self.selected_banner, dest_path)
                except Exception as e:
                    logging.exception(f'Ошибка копирования баннера: {e}')

            new_pack = {
                'name': new_name,
                'version': new_version,
                'loader': new_loader,
                'mods': new_mods,
                'description': new_description,
            }
            if icon_name:
                new_pack['icon'] = icon_name
            if banner_name:
                new_pack['banner'] = banner_name

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
            'Удаление сборки',  
            f"Вы уверены, что хотите удалить сборку '{pack_data['name']}'?",  
            QMessageBox.Yes | QMessageBox.No,  
            QMessageBox.No,
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
        dialog.setMinimumSize(750, 550)
        dialog.resize(900, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.steps = QStackedWidget()
        self._last_action_step2 = None 

        step1 = QWidget()
        form = QFormLayout()
        try:
            form.setHorizontalSpacing(14)
            form.setVerticalSpacing(10)
        except Exception:
            form.setSpacing(12)
        try:
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            form.setFormAlignment(Qt.AlignTop)
            form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        except Exception:
            pass
        self.pack_name = QLineEdit()
        self.pack_name.setMaxLength(32)
        self.pack_name.setValidator(QRegExpValidator(QRegExp('^[A-Za-z0-9()]{0,32}$'), self))
        self.pack_version = QComboBox()
        self.pack_loader = QComboBox()

        for v in MINECRAFT_VERSIONS:
            self.pack_version.addItem(v)
        self.pack_loader.addItems(['Forge', 'Fabric'])

        form.addRow('Название сборки:', self.pack_name)
        form.addRow('Версия Minecraft:', self.pack_version)
        form.addRow('Модлоадер:', self.pack_loader)

        from PyQt5.QtWidgets import QSizePolicy
        self.pack_description = QTextEdit()
        self.pack_description.setPlaceholderText('Краткое описание сборки...')
        self.pack_description.setFixedHeight(100)
        self.pack_description.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow('Описание:', self.pack_description)

        
        self.banner_preview = QLabel()
        self.banner_preview.setFixedSize(self.BANNER_THUMB_W, self.BANNER_THUMB_H)
        self.banner_preview.setStyleSheet('background-color: #3A3A3A; border: 1px solid #555555; border-radius: 12px;')
        banner_btn = QPushButton('Выбрать баннер')
        banner_btn.setIcon(QIcon(resource_path('assets/folder.png')))
        banner_btn.setIconSize(QSize(18, 18))
        banner_btn.clicked.connect(lambda: self.select_image('banner'))
        banner_row = QHBoxLayout()
        banner_row.setSpacing(12)
        banner_row.addWidget(self.banner_preview, 0, Qt.AlignLeft)
        banner_row.addStretch(1)
        banner_row.addWidget(banner_btn, 0, Qt.AlignRight)
        banner_container = QWidget()
        banner_container.setLayout(banner_row)
        form.addRow('Баннер:', banner_container)

        
        spacer = QWidget()
        spacer.setFixedHeight(12)
        form.addRow('', spacer)

        
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(self.ICON_W, self.ICON_H)
        self.icon_preview.setStyleSheet('background-color: #3A3A3A; border: 1px solid #555555; border-radius: 8px;')
        icon_btn = QPushButton('Выбрать иконку')
        icon_btn.setIcon(QIcon(resource_path('assets/folder.png')))
        icon_btn.setIconSize(QSize(18, 18))
        icon_btn.clicked.connect(lambda: self.select_image('icon'))
        icon_row = QHBoxLayout()
        icon_row.setSpacing(12)
        icon_row.addWidget(self.icon_preview, 0, Qt.AlignLeft)
        icon_row.addStretch(1)
        icon_row.addWidget(icon_btn, 0, Qt.AlignRight)
        icon_container = QWidget()
        icon_container.setLayout(icon_row)
        form.addRow('Иконка:', icon_container)

        
        spacer2 = QWidget()
        spacer2.setFixedHeight(10)
        form.addRow('', spacer2)

        from PyQt5.QtWidgets import QCheckBox
        self.use_all_cb = QCheckBox("Использовать все")
        self.use_textures_cb = QCheckBox("Использовать текстуры")
        self.use_shaders_cb = QCheckBox("Использовать шейдеры")

        def toggle_all(state):
            checked = state == Qt.Checked
            self.use_textures_cb.setChecked(checked)
            self.use_shaders_cb.setChecked(checked)

        self.use_all_cb.stateChanged.connect(toggle_all)

        form.addRow('', self.use_all_cb)
        form.addRow('', self.use_textures_cb)
        form.addRow('', self.use_shaders_cb)

        step1.setLayout(form)

        step2 = QWidget()
        mods_layout = QVBoxLayout()

        self.mods_selection = QListWidget()
        self.mods_selection.setSelectionMode(QListWidget.MultiSelection)
        self.mods_selection.setStyleSheet(
            """
            QListWidget { background-color: #373737; border: 1px solid #555; border-radius: 6px; }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:selected { background-color: #2f7d32; color: #fff; }
            """
        )
        mods_layout.addWidget(QLabel('Выберите моды:'))
        mods_layout.addWidget(self.mods_selection)

        mods_actions = QHBoxLayout()
        mods_actions.setSpacing(8)
        mods_add_btn = QPushButton('Добавить')
        mods_del_btn = QPushButton('Удалить')
        mods_undo_btn = QPushButton('Отменить')
        mods_actions.addWidget(mods_add_btn)
        mods_actions.addWidget(mods_del_btn)
        mods_actions.addWidget(mods_undo_btn)
        mods_layout.addLayout(mods_actions)

        self.textures_selection = QListWidget()
        self.textures_selection.setSelectionMode(QListWidget.MultiSelection)
        self.textures_selection.setVisible(False)
        self.textures_selection.setStyleSheet(
            """
            QListWidget { background-color: #373737; border: 1px solid #555; border-radius: 6px; }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:selected { background-color: #2f7d32; color: #fff; }
            """
        )
        self.textures_label = QLabel('Выберите текстуры:')
        self.textures_label.setVisible(False)
        mods_layout.addWidget(self.textures_label)
        mods_layout.addWidget(self.textures_selection)
        textures_actions = QHBoxLayout()
        textures_actions.setSpacing(8)
        textures_add_btn = QPushButton('Добавить')
        textures_del_btn = QPushButton('Удалить')
        textures_undo_btn = QPushButton('Отменить')
        textures_actions.addWidget(textures_add_btn)
        textures_actions.addWidget(textures_del_btn)
        textures_actions.addWidget(textures_undo_btn)
        self.textures_actions_container = QWidget()
        self.textures_actions_container.setLayout(textures_actions)
        self.textures_actions_container.setVisible(False)
        mods_layout.addWidget(self.textures_actions_container)

        self.shaders_selection = QListWidget()
        self.shaders_selection.setSelectionMode(QListWidget.MultiSelection)
        self.shaders_selection.setVisible(False)
        self.shaders_selection.setStyleSheet(
            """
            QListWidget { background-color: #373737; border: 1px solid #555; border-radius: 6px; }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:selected { background-color: #2f7d32; color: #fff; }
            """
        )
        self.shaders_label = QLabel('Выберите шейдеры:')
        self.shaders_label.setVisible(False)
        mods_layout.addWidget(self.shaders_label)
        mods_layout.addWidget(self.shaders_selection)
        shaders_actions = QHBoxLayout()
        shaders_actions.setSpacing(8)
        shaders_add_btn = QPushButton('Добавить')
        shaders_del_btn = QPushButton('Удалить')
        shaders_undo_btn = QPushButton('Отменить')
        shaders_actions.addWidget(shaders_add_btn)
        shaders_actions.addWidget(shaders_del_btn)
        shaders_actions.addWidget(shaders_undo_btn)
        self.shaders_actions_container = QWidget()
        self.shaders_actions_container.setLayout(shaders_actions)
        self.shaders_actions_container.setVisible(False)
        mods_layout.addWidget(self.shaders_actions_container)

        def adjust_dialog_size():
            base_w = 900
            base_h = 600
            extra_h = 140
            is_step2 = self.steps.currentIndex() == 1
            textures_on = self.use_textures_cb.isChecked()
            shaders_on = self.use_shaders_cb.isChecked()
            target_h = base_h
            if is_step2:
                if textures_on:
                    target_h += extra_h
                if shaders_on:
                    target_h += extra_h
            dialog.resize(base_w, target_h)

        def update_lists():
            version = self.pack_version.currentText()
            self.mods_selection.clear()
            self.mods_selection.addItems(ModManager.get_mods_list(version))

            self.textures_selection.clear()
            if self.use_textures_cb.isChecked():
                self.textures_label.setVisible(True)
                self.textures_selection.setVisible(True)
                self.textures_actions_container.setVisible(True)
                self.textures_selection.addItems(ModManager.get_textures_list(version))
            else:
                self.textures_label.setVisible(False)
                self.textures_selection.setVisible(False)
                self.textures_actions_container.setVisible(False)

            self.shaders_selection.clear()
            if self.use_shaders_cb.isChecked():
                self.shaders_label.setVisible(True)
                self.shaders_selection.setVisible(True)
                self.shaders_actions_container.setVisible(True)
                self.shaders_selection.addItems(ModManager.get_shaders_list(version))
            else:
                self.shaders_label.setVisible(False)
                self.shaders_selection.setVisible(False)
                self.shaders_actions_container.setVisible(False)

            adjust_dialog_size()

        self.pack_version.currentIndexChanged.connect(update_lists)
        self.use_textures_cb.stateChanged.connect(update_lists)
        self.use_shaders_cb.stateChanged.connect(update_lists)

        def ensure_dir(path: str) -> None:
            os.makedirs(path, exist_ok=True)

        def pick_files(caption: str, name_filter: str) -> list[str]:
            files, _ = QFileDialog.getOpenFileNames(self, caption, '', name_filter)
            return files

        def add_files_to(dir_path: str, files: list[str], list_widget: QListWidget) -> list[tuple[str, str]]:
            ensure_dir(dir_path)
            performed: list[tuple[str, str]] = []
            for src in files:
                try:
                    dest = os.path.join(dir_path, os.path.basename(src))
                    if not os.path.exists(dest):
                        shutil.copyfile(src, dest)
                        performed.append((dest, src))
                    names = [list_widget.item(i).text() for i in range(list_widget.count())]
                    base = os.path.basename(dest)
                    if base not in names:
                        list_widget.addItem(base)
                except Exception as e:
                    logging.exception(f'Ошибка копирования файла: {e}')
            return performed

        def trash_dir() -> str:
            td = os.path.join(MINECRAFT_DIR, '.trash')
            ensure_dir(td)
            return td

        def move_to_trash(path: str) -> str:
            base = os.path.basename(path)
            ts = str(int(time.time()))
            dest = os.path.join(trash_dir(), f'{ts}_{base}')
            try:
                shutil.move(path, dest)
                return dest
            except Exception as e:
                logging.exception(f'Не удалось переместить в корзину {path}: {e}')
                return ''

        def handle_delete(list_widget: QListWidget, base_dir: str) -> None:
            selected = list_widget.selectedItems()
            if not selected:
                return
            ops: list[tuple[str, str]] = []
            for it in selected:
                name = it.text()
                orig = os.path.join(base_dir, name)
                if os.path.exists(orig):
                    trashed = move_to_trash(orig)
                    if trashed:
                        ops.append((orig, trashed))
                row = list_widget.row(it)
                list_widget.takeItem(row)
            if ops:
                self._last_action_step2 = {
                    'type': 'delete',
                    'ops': ops,
                    'list_widget': list_widget,
                }

        def handle_undo() -> None:
            action = self._last_action_step2
            if not action:
                return
            if action.get('type') == 'delete':
                lw: QListWidget = action['list_widget']
                for orig, trashed in action['ops']:
                    try:
                        ensure_dir(os.path.dirname(orig))
                        shutil.move(trashed, orig)
                        base = os.path.basename(orig)
                        names = [lw.item(i).text() for i in range(lw.count())]
                        if base not in names:
                            lw.addItem(base)
                    except Exception as e:
                        logging.exception(f'Ошибка восстановления {orig}: {e}')
                self._last_action_step2 = None
            elif action.get('type') == 'add':
                lw: QListWidget = action['list_widget']
                for dest, _src in action['ops']:
                    try:
                        if os.path.exists(dest):
                            os.remove(dest)
                        base = os.path.basename(dest)
                        items = lw.findItems(base, Qt.MatchExactly)
                        for it in items:
                            lw.takeItem(lw.row(it))
                    except Exception as e:
                        logging.exception(f'Ошибка отката добавления {dest}: {e}')
                self._last_action_step2 = None

        def setup_dnd(list_widget: QListWidget, target_dir_getter: Callable[[], str], allowed_exts: tuple[str, ...]) -> None:
            list_widget.setAcceptDrops(True)

            def accepts(urls) -> bool:
                for url in urls:
                    path = url.toLocalFile()
                    low = path.lower()
                    if any(low.endswith(ext) for ext in allowed_exts):
                        return True
                return False

            class DnDFilter(QObject):
                def eventFilter(self, obj, event):
                    et = event.type()
                    if et in (QEvent.DragEnter, QEvent.DragMove):
                        md = event.mimeData()
                        if md.hasUrls() and accepts(md.urls()):
                            event.acceptProposedAction()
                            return True
                    if et == QEvent.Drop:
                        md = event.mimeData()
                        if md.hasUrls():
                            files = [u.toLocalFile() for u in md.urls()]
                            files = [f for f in files if any(f.lower().endswith(ext) for ext in allowed_exts)]
                            if files:
                                dir_path = target_dir_getter()
                                ops = add_files_to(dir_path, files, list_widget)
                                self._last_action_step2 = {
                                    'type': 'add',
                                    'ops': ops,
                                    'list_widget': list_widget,
                                }
                                event.acceptProposedAction()
                                return True
                    return QObject.eventFilter(self, obj, event)

            list_widget._dnd_filter = DnDFilter(list_widget)
            list_widget.installEventFilter(list_widget._dnd_filter)

        def set_asset_icon(button: QPushButton, asset_name: str, tooltip: str) -> None:
            icon = QIcon(resource_path(f'assets/{asset_name}'))
            button.setIcon(icon)
            button.setIconSize(QSize(20, 20))
            button.setText('')
            button.setToolTip(tooltip)

        set_asset_icon(mods_add_btn, 'folder.png', 'Добавить моды')
        set_asset_icon(mods_del_btn, 'delete.png', 'Удалить выбранные моды')
        set_asset_icon(mods_undo_btn, 'undo.png', 'Отменить последнее действие')
        set_asset_icon(textures_add_btn, 'folder.png', 'Добавить ресурспаки')
        set_asset_icon(textures_del_btn, 'delete.png', 'Удалить выбранные ресурспаки')
        set_asset_icon(textures_undo_btn, 'undo.png', 'Отменить последнее действие')
        set_asset_icon(shaders_add_btn, 'folder.png', 'Добавить шейдеры')
        set_asset_icon(shaders_del_btn, 'delete.png', 'Удалить выбранные шейдеры')
        set_asset_icon(shaders_undo_btn, 'undo.png', 'Отменить последнее действие')

        def on_mods_add() -> None:
            files = pick_files('Добавить моды', 'Mod files (*.jar *.zip)')
            if not files:
                return
            ops = add_files_to(os.path.join(MODS_DIR, self.pack_version.currentText()), files, self.mods_selection)
            self._last_action_step2 = {
                'type': 'add',
                'ops': ops,
                'list_widget': self.mods_selection,
            }

        mods_add_btn.clicked.connect(on_mods_add)
        mods_del_btn.clicked.connect(lambda: handle_delete(self.mods_selection, os.path.join(MODS_DIR, self.pack_version.currentText())))
        mods_undo_btn.clicked.connect(handle_undo)

        def on_textures_add() -> None:
            files = pick_files('Добавить ресурспаки', 'Zip files (*.zip)')
            if not files:
                return
            ops = add_files_to(RESOURCEPACKS_DIR, files, self.textures_selection)
            self._last_action_step2 = {
                'type': 'add',
                'ops': ops,
                'list_widget': self.textures_selection,
            }

        textures_add_btn.clicked.connect(on_textures_add)
        textures_del_btn.clicked.connect(lambda: handle_delete(self.textures_selection, RESOURCEPACKS_DIR))
        textures_undo_btn.clicked.connect(handle_undo)

        def on_shaders_add() -> None:
            files = pick_files('Добавить шейдеры', 'Zip files (*.zip)')
            if not files:
                return
            ops = add_files_to(SHADERPACKS_DIR, files, self.shaders_selection)
            self._last_action_step2 = {
                'type': 'add',
                'ops': ops,
                'list_widget': self.shaders_selection,
            }

        shaders_add_btn.clicked.connect(on_shaders_add)
        shaders_del_btn.clicked.connect(lambda: handle_delete(self.shaders_selection, SHADERPACKS_DIR))
        shaders_undo_btn.clicked.connect(handle_undo)

        setup_dnd(
            self.mods_selection,
            lambda: os.path.join(MODS_DIR, self.pack_version.currentText()),
            ('.jar', '.zip'),
        )
        setup_dnd(
            self.textures_selection,
            lambda: RESOURCEPACKS_DIR,
            ('.zip',),
        )
        setup_dnd(
            self.shaders_selection,
            lambda: SHADERPACKS_DIR,
            ('.zip',),
        )

        update_lists()
        adjust_dialog_size()

        step2.setLayout(mods_layout)

        self.steps.addWidget(step1)
        self.steps.addWidget(step2)

        nav_buttons = QHBoxLayout()
        self.prev_btn = QPushButton('Назад')
        self.next_btn = QPushButton('Далее')
        self.prev_btn.setIcon(QIcon(resource_path('assets/back.png')))
        self.prev_btn.setIconSize(QSize(20, 20))
        self.next_btn.setIcon(QIcon(resource_path('assets/next.png')))
        self.next_btn.setIconSize(QSize(20, 20))
        def go_step(idx: int) -> None:
            self.steps.setCurrentIndex(idx)
            adjust_dialog_size()
        self.prev_btn.clicked.connect(lambda: go_step(0))
        self.next_btn.clicked.connect(lambda: go_step(1))
        nav_buttons.addWidget(self.prev_btn)
        nav_buttons.addWidget(self.next_btn)

        save_btn = QPushButton('Сохранить')
        save_btn.setIcon(QIcon(resource_path('assets/save.png')))
        save_btn.setIconSize(QSize(20, 20))
        save_btn.clicked.connect(lambda: self.save_modpack(dialog))

        layout.addWidget(self.steps)
        layout.addLayout(nav_buttons)
        layout.addWidget(save_btn)
        dialog.setLayout(layout)
        dialog.exec_()


    def select_image(self, kind: str = 'icon'):
        caption = 'Выберите иконку' if kind == 'icon' else 'Выберите баннер'
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            caption,
            '',
            'Images (*.png *.jpg *.jpeg)',
        )
        if not file_path:
            return
        if kind == 'icon':
            self.selected_icon = file_path
            pix = QPixmap(file_path).scaled(self.ICON_W, self.ICON_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            if hasattr(self, 'icon_preview') and self.icon_preview is not None:
                self.icon_preview.setPixmap(pix)
            if hasattr(self, 'icon_preview_edit') and self.icon_preview_edit is not None:
                self.icon_preview_edit.setPixmap(pix)
        else:
            self.selected_banner = file_path
            pix = QPixmap(file_path).scaled(self.BANNER_THUMB_W, self.BANNER_THUMB_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            if hasattr(self, 'banner_preview') and self.banner_preview is not None:
                self.banner_preview.setPixmap(pix)

    def save_modpack(self, dialog):
        if not self.pack_name.hasAcceptableInput() or not self.pack_name.text():
            QMessageBox.warning(self, 'Неверное имя', 'Имя может содержать латинские буквы (A-Z, a-z), цифры и скобки () и быть не длиннее 32 символов.')
            return
        name = self.pack_name.text()
        version = self.pack_version.currentText()
        loader = self.pack_loader.currentText()
        description = self.pack_description.toPlainText().strip()
        selected_mods = [item.text() for item in self.mods_selection.selectedItems()]
        selected_textures = [item.text() for item in self.textures_selection.selectedItems()]
        selected_shaders = [item.text() for item in self.shaders_selection.selectedItems()]

        icon_name = None
        banner_name = None
        if hasattr(self, 'selected_icon') and self.selected_icon:
            try:
                icon_name = f'{name}_{int(time.time())}.png'
                dest_path = os.path.join(self.icons_dir, icon_name)
                shutil.copyfile(self.selected_icon, dest_path)
            except Exception as e:
                logging.exception(f'Ошибка копирования иконки: {e}')
                icon_name = None
        if hasattr(self, 'selected_banner') and self.selected_banner:
            try:
                banner_name = f'{name}_{int(time.time())}_banner.png'
                dest_path = os.path.join(self.banners_dir, banner_name)
                shutil.copyfile(self.selected_banner, dest_path)
            except Exception as e:
                logging.exception(f'Ошибка копирования баннера: {e}')
                banner_name = None

        pack_data = {
            'name': name,
            'version': version,
            'loader': loader,
            'mods': selected_mods,
            'textures': selected_textures,
            'shaders': selected_shaders,
            'description': description,
        }
        if icon_name:
            pack_data['icon'] = icon_name
        if banner_name:
            pack_data['banner'] = banner_name

        with open(os.path.join(self.modpacks_dir, f'{name}.json'), 'w') as f:
            json.dump(pack_data, f)

        self.load_modpacks()
        dialog.close()
