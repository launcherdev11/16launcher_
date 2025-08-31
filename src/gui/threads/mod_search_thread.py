from PySide6.QtCore import QThread, Signal

from src.mod_manager import ModManager


class ModSearchThread(QThread):
    search_finished = Signal(list, str)
    error_occurred = Signal(str)

    def __init__(
        self,
        query: str,
        version: str,
        loader: str,
        category: str,
        sort_by: str,
    ) -> None:
        super().__init__()
        self.query = query
        self.version = version
        self.loader = loader
        self.category = category
        self.sort_by = sort_by

    def run(self) -> None:
        try:
            mods = ModManager.cached_search(
                self.query,
                self.version,
                self.loader,
                self.category,
                self.sort_by,
                'modrinth',
            )
            self.search_finished.emit(mods, self.query)
        except Exception as e:
            self.error_occurred.emit(str(e))
