#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import requests
import time

class DownloadManager(QThread):
    progress_signal = pyqtSignal(int, int, str)  # current, total, filename
    status_signal = pyqtSignal(str)  # статус загрузки
    finished_signal = pyqtSignal(bool, str)  # success, message
    download_paused = pyqtSignal()
    download_resumed = pyqtSignal()
    
    def __init__(self, url, filepath, filename="", resume_support=True):
        super().__init__()
        self.url = url
        self.filepath = filepath
        self.filename = filename or os.path.basename(filepath)
        self.resume_support = resume_support
        self.is_cancelled = False
        self.is_paused = False
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.session = requests.Session()
        
    def run(self):
        try:
            self.status_signal.emit("Подготовка к загрузке...")
            
            # Проверяем, можно ли продолжить загрузку
            resume_pos = 0
            if self.resume_support and os.path.exists(self.filepath):
                resume_pos = os.path.getsize(self.filepath)
                if resume_pos > 0:
                    self.downloaded_bytes = resume_pos
                    self.status_signal.emit(f"Продолжение загрузки с позиции {resume_pos} байт")
            
            # Настраиваем заголовки для продолжения загрузки
            headers = {}
            if resume_pos > 0 and self.resume_support:
                headers['Range'] = f'bytes={resume_pos}-'
            
            # Отправляем запрос
            response = self.session.get(self.url, headers=headers, stream=True)
            
            if response.status_code == 206:  # Partial Content - поддержка продолжения
                self.total_bytes = int(response.headers.get('content-range', '').split('/')[-1])
            elif response.status_code == 200:
                self.total_bytes = int(response.headers.get('content-length', 0))
                if resume_pos > 0:
                    # Сервер не поддерживает продолжение, начинаем заново
                    resume_pos = 0
                    self.downloaded_bytes = 0
            else:
                raise Exception(f"HTTP {response.status_code}: {response.reason}")
            
            # Открываем файл для записи
            mode = 'ab' if resume_pos > 0 else 'wb'
            with open(self.filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.is_cancelled:
                        self.status_signal.emit("Загрузка отменена")
                        return
                    
                    while self.is_paused:
                        if self.is_cancelled:
                            return
                        self.download_paused.emit()
                        time.sleep(0.1)
                    
                    if chunk:
                        f.write(chunk)
                        self.downloaded_bytes += len(chunk)
                        
                        if self.total_bytes > 0:
                            progress = int((self.downloaded_bytes / self.total_bytes) * 100)
                            self.progress_signal.emit(self.downloaded_bytes, self.total_bytes, self.filename)
                            
                            # Обновляем статус каждые 5%
                            if progress % 5 == 0:
                                self.status_signal.emit(f"Загружено {progress}%")
            
            if self.is_cancelled:
                return
                
            self.status_signal.emit("Загрузка завершена")
            self.finished_signal.emit(True, f"Файл {self.filename} успешно загружен")
            
        except Exception as e:
            if not self.is_cancelled:
                self.finished_signal.emit(False, f"Ошибка загрузки: {str(e)}")
                print(f"Download error: {str(e)}")
    
    def cancel(self):
        #Отменяет загрузку
        self.is_cancelled = True
        self.status_signal.emit("Отмена загрузки...")
    
    def pause(self):
        self.is_paused = True
    
    def resume(self):
        self.is_paused = False
        self.download_resumed.emit()
        self.status_signal.emit("Загрузка возобновлена")

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_manager = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Тест системы загрузки")
        self.setFixedSize(400, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Статус
        self.status_label = QLabel("Готов к загрузке")
        layout.addWidget(self.status_label)
        
        # Прогресс
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)
        
        # Кнопки
        self.start_button = QPushButton("Начать загрузку")
        self.start_button.clicked.connect(self.start_download)
        layout.addWidget(self.start_button)
        
        self.pause_button = QPushButton("Пауза")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        layout.addWidget(self.pause_button)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        layout.addWidget(self.cancel_button)
        
        # Тестовая загрузка
        self.test_url = "https://speed.hetzner.de/100MB.bin"  # Тестовый файл 100MB
        self.test_file = "test_download.bin"
        
    def start_download(self):
        if self.download_manager and self.download_manager.isRunning():
            return
            
        self.download_manager = DownloadManager(self.test_url, self.test_file, "test_download.bin")
        self.download_manager.progress_signal.connect(self.update_progress)
        self.download_manager.status_signal.connect(self.update_status)
        self.download_manager.finished_signal.connect(self.download_finished)
        self.download_manager.download_paused.connect(self.on_paused)
        self.download_manager.download_resumed.connect(self.on_resumed)
        
        self.download_manager.start()
        
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
    def update_progress(self, current, total, filename):
        if total > 0:
            progress = int((current / total) * 100)
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.progress_label.setText(f"{current_mb:.1f} MB / {total_mb:.1f} MB ({progress}%)")
    
    def update_status(self, status):
        self.status_label.setText(status)
    
    def toggle_pause(self):
        if self.download_manager:
            if self.download_manager.is_paused:
                self.download_manager.resume()
                self.pause_button.setText("Пауза")
            else:
                self.download_manager.pause()
                self.pause_button.setText("Продолжить")
    
    def on_paused(self):
        self.pause_button.setText("Продолжить")
    
    def on_resumed(self):
        self.pause_button.setText("Пауза")
    
    def cancel_download(self):
        if self.download_manager:
            self.download_manager.cancel()
    
    def download_finished(self, success, message):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.pause_button.setText("Пауза")
        
        if success:
            self.status_label.setText("Загрузка завершена успешно!")
        else:
            self.status_label.setText(f"Ошибка: {message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
