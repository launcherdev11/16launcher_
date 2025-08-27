import requests
from PyQt5.QtCore import QThread, pyqtSignal


class PopularModsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, version=None, loader=None):
        super().__init__()
        self.version = version
        self.loader = loader

    def run(self):
        try:
            # Формируем параметры запроса для популярных модов
            params = {
                "limit": 50,
                "index": "downloads",  # Сортировка по количеству загрузок
                "facets": [],
            }

            # Добавляем версию
            if self.version and self.version != "Все версии":
                params["facets"].append(f'["versions:{self.version}"]')

            # Добавляем лоадер
            if self.loader and self.loader.lower() != "vanilla":
                params["facets"].append(f'["categories:{self.loader.lower()}"]')

            # Если есть facets, преобразуем их в строку
            if params["facets"]:
                params["facets"] = "[" + ",".join(params["facets"]) + "]"
            else:
                del params["facets"]

            # Выполняем запрос
            response = requests.get("https://api.modrinth.com/v2/search", params=params)

            if response.status_code == 200:
                self.finished.emit(response.json().get("hits", []))
            else:
                self.error.emit("Не удалось загрузить популярные моды")

        except Exception as e:
            self.error.emit(str(e))
