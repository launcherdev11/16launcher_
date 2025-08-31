import logging
import logging
import os
import shutil
import subprocess
import traceback

import requests
from PyQt5.QtCore import QThread, pyqtSignal
from minecraft_launcher_lib.fabric import get_latest_loader_version as last_fabric
from minecraft_launcher_lib.fabric import install_fabric
from minecraft_launcher_lib.forge import find_forge_version, install_forge_version
from minecraft_launcher_lib.quilt import get_latest_loader_version as last_quilt, install_quilt

from ...config import MINECRAFT_DIR


class ModLoaderInstaller(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, loader_type, version, mc_version=None):
        super().__init__()
        self.loader_type = loader_type.lower()
        self.version = version
        self.mc_version = mc_version

    def run(self):
        try:
            loaders = {
                "fabric": self.install_fabric,
                "forge": self.install_forge,
                "optifine": self.install_optifine,
                "quilt": self.install_quilt
            }
            loader = loaders.get(self.loader_type)
            if loader:
                loader()
                return
            self.finished_signal.emit(
                False, f"Неизвестный тип модлоадера: {self.loader_type}"
            )
        except Exception as e:
            self.finished_signal.emit(False, f"Критическая ошибка: {str(e)}")
            logging.error(
                f"Ошибка установки {self.loader_type}: {str(e)}", exc_info=True
            )

    def install_optifine(self):
        """Установка OptiFine"""
        try:
            download_url = f"https://optifine.net/adloadx?f=OptiFine_{self.mc_version}.jar"
            optifine_path = os.path.join(MINECRAFT_DIR, "OptiFine.jar")

            with requests.get(download_url, stream=True) as r:
                with open(optifine_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)

            command = ["java", "-jar", optifine_path, "--install", MINECRAFT_DIR]
            subprocess.run(command, check=True)

            self.finished_signal.emit(
                True, f"OptiFine для {self.mc_version} установлен!"
            )

        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки OptiFine: {str(e)}")

    def install_quilt(self):
        try:
            loader_version = last_quilt()
            install_quilt(
                minecraft_version=self.mc_version,
                loader_version=loader_version,
                minecraft_directory=MINECRAFT_DIR,
                callback=self.get_callback(),
            )
            self.finished_signal.emit(
                True, f"Quilt {loader_version} для {self.mc_version} установлен!"
            )

        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки Quilt: {str(e)}")

    def install_fabric(self):
        try:
            loader_version = last_fabric()
            install_fabric(
                minecraft_version=self.mc_version,
                minecraft_directory=MINECRAFT_DIR,
                loader_version=loader_version,
                callback=self.get_callback()
            )

            self.finished_signal.emit(
                True, f"Fabric {loader_version} для {self.mc_version} установлен!"
            )

        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки Fabric: {str(e)}")
            logging.error(f"Fabric install error: {traceback.format_exc()}")

    def install_forge(self):
        """Установка Forge"""
        try:
            forge_version = find_forge_version(self.mc_version)
            if not forge_version:
                self.finished_signal.emit(
                    False, f"Forge для {self.mc_version} не найден"
                )
                return

            install_forge_version(
                forge_version,
                path=MINECRAFT_DIR,
                callback=self.get_callback()
            )
            self.finished_signal.emit(True, f"Forge {forge_version} установлен!")

        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка установки Forge: {str(e)}")
            logging.error(f"Forge install failed: {str(e)}", exc_info=True)

    def get_callback(self):
        """Генератор callback-функций для отслеживания прогресса"""
        return {
            "setStatus": lambda text: self.progress_signal.emit(0, 100, text),
            "setProgress": lambda value: self.progress_signal.emit(value, 100, ""),
            "setMax": lambda value: self.progress_signal.emit(0, value, ""),
        }
