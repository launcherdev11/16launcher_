from PyQt5.QtWidgets import QLineEdit, QStyle


class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._button = None

    def set_button(self, button) -> None:
        self._button = button
        self.update_button_position()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_button_position()

    def update_button_position(self) -> None:
        if self._button:
            frame_width = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
            rect = self.rect()
            x = rect.right() - self._button.width() - frame_width - 2
            y = (rect.height() - self._button.height()) // 2
            self._button.move(x, y)
