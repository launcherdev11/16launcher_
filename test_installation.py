#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый файл для проверки отмены установки модлоадеров
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QProgressBar, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal
import time

class TestModLoaderInstaller(QThread):
    """Тестовый класс для имитации установки модлоадера"""
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(bool, str)
    cancelled_signal = pyqtSignal()
    
    def __init__(self, loader_type, version, mc_version):
        super().__init__()
        self.loader_type = loader_type
        self.version = version
        self.mc_version = mc_version
        self.is_cancelled = False
    
    def run(self):
        try:
            # Имитируем процесс установки
            total_steps = 10
            for i in range(total_steps):
                if self.is_cancelled:
                    self.cancelled_signal.emit()
                    return
                
                # Имитируем загрузку
                self.progress_signal.emit(i + 1, total_steps, f"Установка {self.loader_type}... Шаг {i + 1}/{total_steps}")
                time.sleep(0.5)  # Имитируем задержку
            
            if not self.is_cancelled:
                self.finished_signal.emit(True, f"{self.loader_type} успешно установлен!")
                
        except Exception as e:
            if not self.is_cancelled:
                self.finished_signal.emit(False, f"Ошибка установки: {str(e)}")
    
    def cancel(self):
        """Отменяет установку"""
        self.is_cancelled = True
        self.cancelled_signal.emit()

class TestInstallationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.install_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Тест отмены установки модлоадеров")
        self.setFixedSize(400, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Выбор модлоадера
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["Fabric", "Forge", "OptiFine", "Quilt"])
        layout.addWidget(QLabel("Выберите модлоадер:"))
        layout.addWidget(self.loader_combo)
        
        # Выбор версии Minecraft
        self.mc_combo = QComboBox()
        self.mc_combo.addItems(["1.20.1", "1.19.4", "1.18.2", "1.17.1"])
        layout.addWidget(QLabel("Выберите версию Minecraft:"))
        layout.addWidget(self.mc_combo)
        
        # Кнопки
        button_layout = QVBoxLayout()
        
        self.install_button = QPushButton("Начать установку")
        self.install_button.clicked.connect(self.start_installation)
        button_layout.addWidget(self.install_button)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.cancel_installation)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Статус
        self.status_label = QLabel("Готов к установке")
        layout.addWidget(self.status_label)
        
    def start_installation(self):
        if self.install_thread and self.install_thread.isRunning():
            return
            
        loader_type = self.loader_combo.currentText()
        mc_version = self.mc_combo.currentText()
        
        self.install_thread = TestModLoaderInstaller(loader_type, None, mc_version)
        self.install_thread.progress_signal.connect(self.update_progress)
        self.install_thread.finished_signal.connect(self.installation_finished)
        self.install_thread.cancelled_signal.connect(self.installation_cancelled)
        
        self.install_thread.start()
        
        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Установка началась...")
    
    def cancel_installation(self):
        if self.install_thread:
            self.install_thread.cancel()
            self.status_label.setText("Отмена установки...")
    
    def update_progress(self, current, total, text):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(text)
    
    def installation_finished(self, success, message):
        self.install_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
    
    def installation_cancelled(self):
        self.install_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Установка отменена")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestInstallationWindow()
    window.show()
    sys.exit(app.exec_())
