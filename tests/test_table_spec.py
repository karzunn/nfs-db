import unittest

from nfs_db import column_type, table_spec


class TableSpecTests(unittest.TestCase):
    def test_add_column_rejects_duplicate_names(self):
        spec = table_spec("users").add_column("name", column_type.STRING)

        with self.assertRaisesRegex(ValueError, "already exists"):
            spec.add_column("name", column_type.INTEGER)
