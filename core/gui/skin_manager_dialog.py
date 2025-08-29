from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QFileDialog

from ..ely_skin_manager import ElySkinManager


class SkinManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление скинами")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        # Кнопка для legacy-версий
        self.legacy_btn = QPushButton("Установить скин для старых версий")
        self.legacy_btn.clicked.connect(self.handle_legacy_skin)
        layout.addWidget(self.legacy_btn)

        # Кнопка для новых версий
        self.modern_btn = QPushButton("Установить через Ely.by")
        self.modern_btn.clicked.connect(self.handle_modern_skin)
        layout.addWidget(self.modern_btn)

        self.setLayout(layout)

    def handle_legacy_skin(self):
        file = QFileDialog.getOpenFileName(
            self, "Выберите PNG-скин", "", "Images (*.png)"
        )[0]
        if file:
            # Применяем скин для выбранной версии
            version = self.parent().version_select.currentText()
            ElySkinManager.inject_legacy_skin(file, version)
