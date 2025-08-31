import io
import logging
import os
import re
import subprocess
import traceback
import zipfile
from uuid import uuid1

import requests
from PyQt5.QtCore import QThread, pyqtSignal
from minecraft_launcher_lib.command import get_minecraft_command
from minecraft_launcher_lib.fabric import get_latest_loader_version
from minecraft_launcher_lib.forge import find_forge_version
from minecraft_launcher_lib.install import install_minecraft_version

from ...config import AUTHLIB_JAR_PATH, MINECRAFT_DIR


class LaunchThread(QThread):
    launch_setup_signal = pyqtSignal(str, str, str, int, bool)
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)
    close_launcher_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.version_id = ""
        self.username = ""
        self.loader_type = "vanilla"
        self.memory_mb = 4096
        self.close_on_launch = False

    launch_setup_signal = pyqtSignal(str, str, str, int, bool)
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)
    log_signal = pyqtSignal(str)
    close_launcher_signal = pyqtSignal()

    def launch_setup(
        self, version_id, username, loader_type, memory_mb, close_on_launch
    ):
        self.version_id = version_id
        self.username = username
        self.loader_type = loader_type
        self.memory_mb = memory_mb
        self.close_on_launch = close_on_launch

    def run(self):
        try:
            self.log_signal.emit("[LAUNCH THREAD] Starting Minecraft launch process...")
            self.state_update_signal.emit(True)

            # 1. Определение базовых параметров
            launch_version = self.version_id
            is_legacy = self.is_legacy_version(self.version_id)
            options = {
                "username": self.username,
                "uuid": str(uuid1()),
                "token": "",
                "jvmArguments": [
                    f"-Xmx{self.memory_mb}M",
                    f"-Xms{min(self.memory_mb // 2, 2048)}M",
                ],
                "launcherName": "16Launcher",
                "launcherVersion": "1.0.2",
                "demo": False,
                "fullscreen": "false",
            }

            # 2. Обработка Ely.by сессии
            if hasattr(self.parent_window, "ely_session") and self.parent_window.ely_session:
                self.log_signal.emit("[LAUNCH THREAD] Applying Ely.by session...")
                options.update({
                    "username": self.parent_window.ely_session["username"],
                    "uuid": self.parent_window.ely_session["uuid"],
                    "token": self.parent_window.ely_session["token"],
                    "jvmArguments": options["jvmArguments"]
                        + [f"-javaagent:{AUTHLIB_JAR_PATH}=ely.by"],
                })

            # 3. Определение версии для модлоадеров
            if self.loader_type == "forge":
                self.log_signal.emit("[LAUNCH THREAD] Processing Forge version...")
                forge_version = find_forge_version(self.version_id)
                if not forge_version:
                    raise Exception(f"Forge версия {self.version_id} не найдена")
                launch_version = f"{self.version_id}-forge-{forge_version.split('-')[-1]}"
                self.log_signal.emit(f"[LAUNCH THREAD] Запускаемая версия Forge: {launch_version}")

            elif self.loader_type == "fabric":
                self.log_signal.emit("[LAUNCH THREAD] Processing Fabric version...")
                try:
                    loader_version = get_latest_loader_version()
                    launch_version = f"fabric-loader-{loader_version}-{self.version_id}"
                    self.log_signal.emit(f"[LAUNCH THREAD] Запускаемая версия Fabric: {launch_version}")
                except Exception as e:
                    raise Exception(f"Ошибка Fabric: {str(e)}")

            elif self.loader_type == "quilt":
                self.log_signal.emit("[LAUNCH THREAD] Processing Quilt version...")
                from minecraft_launcher_lib.quilt import get_quilt_profile

                profile = get_quilt_profile(self.version_id, MINECRAFT_DIR)
                launch_version = profile["version"]

            # 4. Патч для legacy версий
            if is_legacy:
                self.log_signal.emit("[LAUNCH THREAD] Применение Legacy патча...")
                self.apply_legacy_patch(launch_version)

            # 5. Установка версии если требуется
            self.log_signal.emit(f"[LAUNCH THREAD] Проверка версий {launch_version}...")
            if not os.path.exists(os.path.join(MINECRAFT_DIR, "versions", launch_version)):
                self.log_signal.emit("[LAUNCH THREAD] Установка версий...")
                install_minecraft_version(
                    versionid=launch_version,
                    minecraft_directory=MINECRAFT_DIR,
                    callback={
                        "setStatus": lambda text: (
                            self.log_signal.emit(f"[INSTALL] {text}"),
                            self.progress_update_signal.emit(0, 100, text),
                        ),
                        "setProgress": lambda value: (
                            self.log_signal.emit(f"[INSTALL] Progress: {value}%"),
                            self.progress_update_signal.emit(value, 100, ""),
                        ),
                        "setMax": lambda value: (
                            self.log_signal.emit(f"[INSTALL] Max progress set to: {value}"),
                            self.progress_update_signal.emit(0, value, ""),
                        ),
                    },
                )

            # 6. Формирование команды запуска
            self.log_signal.emit("[LAUNCH THREAD] Сборка комманд...")
            command = get_minecraft_command(
                version=launch_version,
                minecraft_directory=MINECRAFT_DIR,
                options=options,
            )
            self.log_signal.emit("[LAUNCH THREAD] Финальная команда: " + " ".join(command))

            # 7. Запуск процесса
            self.log_signal.emit("[LAUNCH THREAD] Старт майнкрафт...")
            minecraft_process = subprocess.Popen(
                command,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # 8. Закрытие лаунчера если нужно
            if self.close_on_launch:
                self.log_signal.emit("[LAUNCH THREAD] Закрытие лаунчера...")
                self.close_launcher_signal.emit()

            self.state_update_signal.emit(False)
            self.log_signal.emit("[LAUNCH THREAD] Успешный запуск")

        except Exception as e:
            self.log_signal.emit(f"[LAUNCH THREAD ERROR] {str(e)}")
            logging.error(f"Launch thread failed: {traceback.format_exc()}")
            self.state_update_signal.emit(False)


    def is_legacy_version(self, version):
        """Проверяет, является ли версия старой (до 1.7.5)"""
        try:
            major, minor, patch = re.match(r"(\d+)\.(\d+)\.?(\d+)?", version).groups()
            if int(major) == 1 and (
                int(minor) < 7 or (int(minor) == 7 and int(patch or 0) < 5)
            ):
                return True
            return False
        except Exception:
            return False

    def setup_authlib(self, options):
        """Настраивает authlib-injector для новых версий"""
        if not os.path.exists(AUTHLIB_JAR_PATH):
            if not self.download_authlib():
                raise Exception("Failed to download authlib-injector")

        options["jvmArguments"].append(f"-javaagent:{AUTHLIB_JAR_PATH}=ely.by")
        options["jvmArguments"].append(
            "-Dauthlibinjector.yggdrasil.prefetched={...}"
        )

    @staticmethod
    def download_authlib(self):
        """Скачивает authlib-injector"""
        try:
            response = requests.get(
                "https://maven.ely.by/releases/by/ely/authlib/1.2.0/authlib-1.2.0.jar"
            )  # Актуальная версия
            with open(AUTHLIB_JAR_PATH, "wb") as f:
                f.write(response.content)
            return True
        except Exception as e:
            logging.error(f"Authlib download failed: {str(e)}")
            return False

    @staticmethod
    def apply_legacy_patch(version: str):
        """Применяет патч для старых версий"""
        jar_path = os.path.join(MINECRAFT_DIR, "versions", version, f"{version}.jar")

        if not os.path.exists(jar_path):
            raise Exception("JAR file not found")

        patch_url = "https://ely.by/load/legacy-patch.jar"  # Пример URL
        patch_data = requests.get(patch_url).content

        with zipfile.ZipFile(jar_path, "a") as jar:
            with zipfile.ZipFile(io.BytesIO(patch_data)) as patch:
                for file in patch.namelist():
                    if file.endswith(".class"):
                        jar.writestr(file, patch.read(file))

    def _set_status(self, text):
        self.progress_update_signal.emit(self.current_step, self.total_steps, text)

    def _set_progress(self, sub_value: int):
        percent_of_stage = 20
        global_progress = self.progress_step * percent_of_stage + (
            sub_value * percent_of_stage // 100
        )
        self.current_step = global_progress
        self.progress_update_signal.emit(self.current_step, self.total_steps, "")

    def _set_max(self, _):  # не нужен для глобального прогресса
        pass
