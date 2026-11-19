from pathlib import Path

from tests.base_test_case import DatabaseTestCase


class TableGetTests(DatabaseTestCase):
    def test_get_returns_all_fields_with_expected_types(self):
        row_id = self.insert_row(name="Ada", number=7, active=True)

        self.assertEqual(
            self.table.get(row_id),
            {"id": row_id, "name": "Ada", "number": 7, "active": True},
        )

    def test_get_ignores_nfs_metadata_files(self):
        row_id = self.insert_row()
        transaction_id, _ = self.table._get_row_snapshot(row_id)
        metadata_path = (
            self.table.rows_path
            / row_id
            / transaction_id
            / "fields"
            / "number"
            / "._7"
        )
        metadata_path.touch()
        row_path = self.table.rows_path / row_id
        (row_path / f"._{transaction_id}").touch()
        (row_path / f"._{transaction_id}.current_transaction").touch()

        self.assertEqual(self.table.get(row_id)["number"], 7)

    def test_get_rejects_a_missing_row(self):
        with self.assertRaisesRegex(KeyError, "does not exist"):
            self.table.get("missing")

    def test_get_rejects_a_row_without_a_current_marker(self):
        row_path = self.table.rows_path / "corrupt"
        row_path.mkdir()

        with self.assertRaisesRegex(RuntimeError, "missing a current transaction marker"):
            self.table.get("corrupt")
