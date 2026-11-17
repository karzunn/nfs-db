from unittest.mock import patch

from tests.base_test_case import DatabaseTestCase


class TableUpdateTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.row_id = self.insert_row()
        self.row_path = self.table.rows_path / self.row_id

    def test_update_rejects_invalid_callbacks_and_rows(self):
        with self.assertRaisesRegex(TypeError, "edit must be a callable"):
            self.table.update(self.row_id, None)

        with self.assertRaisesRegex(TypeError, "return a row dictionary"):
            self.table.update(self.row_id, lambda row: None)

        with self.assertRaisesRegex(ValueError, "exactly the table's columns"):
            self.table.update(self.row_id, lambda row: {"id": self.row_id, "name": "Grace"})

        with self.assertRaisesRegex(TypeError, "Incorrect type for column 'number'"):
            self.table.update(
                self.row_id,
                lambda row: {**row, "number": "eight"},
            )

    def test_update_accepts_a_callback_returning_all_correct_fields(self):
        def edit(row):
            row.update(name="Grace", number=8, active=False)
            return row

        updated = self.table.update(self.row_id, edit)

        self.assertEqual(set(updated), set(self.spec.columns))
        self.assertEqual(updated["id"], self.row_id)
        self.assertEqual(updated["name"], "Grace")
        self.assertEqual(updated["number"], 8)
        self.assertFalse(updated["active"])
        self.assertEqual(self.table.get(self.row_id), updated)

    def test_failed_update_removes_new_indexes_and_transaction_files(self):
        old_transaction_id, old_row = self.table._get_row_snapshot(self.row_id)
        with patch(
            "nfs_db.table.transactions.update_transaction.execute",
            side_effect=OSError("simulated commit failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated commit failure"):
                self.table.update(
                    self.row_id,
                    lambda row: {**row, "name": "Grace", "number": 8},
                )

        self.assertEqual(self.table.get(self.row_id), old_row)
        self.assertEqual(
            {path.name for path in self.row_path.iterdir()},
            {old_transaction_id, f"{old_transaction_id}.current_transaction"},
        )
        self.assertFalse((self.table.indexes_path / "name" / "Grace").exists())
        self.assertFalse((self.table.indexes_path / "number" / "8").exists())

    def test_successful_update_removes_old_indexes_and_transaction_files(self):
        old_transaction_id, _ = self.table._get_row_snapshot(self.row_id)

        updated = self.table.update(
            self.row_id,
            lambda row: {**row, "name": "Grace", "number": 8},
        )

        self.assertFalse((self.table.indexes_path / "name" / "Ada").exists())
        self.assertFalse((self.table.indexes_path / "number" / "7").exists())
        self.assertFalse((self.row_path / old_transaction_id).exists())
        self.assertFalse(
            (self.row_path / f"{old_transaction_id}.current_transaction").exists()
        )
        self.assertEqual(len(list(self.row_path.glob("*.current_transaction"))), 1)
        self.assertEqual(
            len([path for path in self.row_path.iterdir() if path.is_dir()]), 1
        )
        self.assertEqual(updated, self.table.get(self.row_id))

    def test_update_retries_after_another_update_moves_the_marker(self):
        calls = 0

        def edit(row):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.table.update(
                    self.row_id,
                    lambda latest: {**latest, "number": latest["number"] + 10},
                )
            return {**row, "number": row["number"] + 1}

        updated = self.table.update(self.row_id, edit)

        self.assertEqual(calls, 2)
        self.assertEqual(updated["number"], 18)
        self.assertEqual(self.table.get(self.row_id), updated)

    def test_update_does_not_allow_changing_id(self):
        with self.assertRaisesRegex(ValueError, "cannot be modified"):
            self.table.update(self.row_id, lambda row: {**row, "id": "other"})

        self.assertEqual(self.table.get(self.row_id)["id"], self.row_id)
