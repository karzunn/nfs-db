import unittest

from nfs_db import table_spec


class TableSpecTests(unittest.TestCase):
    def test_name_keyword_can_define_a_column(self):
        spec = table_spec("users", name=str)

        self.assertIs(spec.columns["name"].data_type, str)

    def test_reserved_id_column_cannot_be_redefined(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            table_spec("users", id=str)

    def test_unsupported_column_types_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "must be int, str, float, or bool"):
            table_spec("users", payload=bytes)
