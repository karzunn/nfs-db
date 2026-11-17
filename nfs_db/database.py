from pathlib import Path

from .constants import NFS_DB_PATH
from .table.table import table
from .table.table_spec import table_spec


class database:

    def __init__(self, path: str):
        self.path = Path(path) / Path(NFS_DB_PATH)
        self.path.mkdir(parents=True, exist_ok=True)

    def table(self, table_spec: table_spec):
        return table(self.path, table_spec)
