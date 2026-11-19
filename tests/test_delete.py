from tests.base_test_case import DatabaseTestCase


class TableDeleteTests(DatabaseTestCase):
    def test_delete_rejects_a_missing_row(self):
        with self.assertRaisesRegex(KeyError, "does not exist"):
            self.table.delete("missing")

        self.assertEqual(list(self.table.staging_path.iterdir()), [])

    def test_delete_removes_row_indexes_and_staging_files(self):
        row_id = self.insert_row()
        transaction_id, _ = self.table._get_row_snapshot(row_id)
        row_path = self.table.rows_path / row_id
        fields_path = row_path / transaction_id / "fields"
        (fields_path / "._name").touch()
        (fields_path / "name" / "._Ada").touch()
        (row_path / f"._{transaction_id}").touch()
        (row_path / f"._{transaction_id}.current_transaction").touch()

        self.table.delete(row_id)

        self.assertFalse((self.table.rows_path / row_id).exists())
        self.assertFalse((self.table.indexes_path / "name" / "Ada").exists())
        self.assertFalse((self.table.indexes_path / "number" / "7").exists())
        self.assertEqual(list(self.table.staging_path.iterdir()), [])
