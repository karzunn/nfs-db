import unittest

from nfs_db import table_spec


class TableSpecTests(unittest.TestCase):
    def test_add_column_rejects_duplicate_names(self):
        spec = table_spec("users").add_column("name", str)

        with self.assertRaisesRegex(ValueError, "already exists"):
            spec.add_column("name", int)

    def test_add_column_rejects_unsupported_types(self):
        with self.assertRaisesRegex(TypeError, "must be int, str, float, or bool"):
            table_spec("users").add_column("name", bytes)
