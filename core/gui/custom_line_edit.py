from PySide6.QtWidgets import QLineEdit


class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._button = None

    def set_button(self, button):
        self._button = button
        self.update_button_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_button_position()

    def update_button_position(self):
        if self._button:
            from PySide6.QtWidgets import QStyle

            frame_width = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
            rect = self.rect()
            x = (
                rect.right() - self._button.width() - frame_width - 2
            )  # Уменьшили отступ
            y = (rect.height() - self._button.height()) // 2
            self._button.move(x, y)
