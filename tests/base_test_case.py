import tempfile
import unittest

from nfs_db import database, table_spec


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.db = database(self.temporary_directory.name)
        self.spec = table_spec("users", name=str, number=int, active=bool)
        self.table = self.db.table(self.spec)

    def insert_row(self, name="Ada", number=7, active=True, row_id=None):
        data = {"name": name, "number": number, "active": active}
        if row_id is not None:
            data["id"] = row_id
        return self.table.insert(data)
