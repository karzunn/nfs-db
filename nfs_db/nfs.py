import shutil
from pathlib import Path

from .database import database


class nfs:

    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"NFS path '{path}' does not exist.")

    def db(self, name: str):
        return database(self.path, name)
