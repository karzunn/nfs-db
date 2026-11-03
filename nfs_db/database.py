from pathlib import Path

from .constants import NFS_DB_PATH
from .table.table import table
from .table.table_info import table_info


class database:

    def __init__(self, nfs_path: Path, name: str):
        self.path = nfs_path / NFS_DB_PATH / name
        self.path.mkdir(parents=True, exist_ok=True)

    def table(self, table_info: table_info):
        return table(self.path, table_info)

