from tests.base_test_case import DatabaseTestCase


class TableInsertTests(DatabaseTestCase):
    def test_insert_rejects_missing_and_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "Missing value for column 'active'"):
            self.table.insert({"name": "Ada", "number": 7})

        with self.assertRaisesRegex(TypeError, "Incorrect type for column 'number'"):
            self.table.insert({"name": "Ada", "number": "seven", "active": True})

        with self.assertRaisesRegex(TypeError, "Expected int, got bool"):
            self.table.insert({"name": "Ada", "number": True, "active": True})

        self.assertEqual(list(self.table.staging_path.iterdir()), [])
        self.assertEqual(list(self.table.rows_path.iterdir()), [])

    def test_insert_rejects_an_existing_id(self):
        self.insert_row(row_id="duplicate")

        with self.assertRaisesRegex(FileExistsError, "already exists"):
            self.table.insert(
                {
                    "id": "duplicate",
                    "name": "Different",
                    "number": 99,
                    "active": False,
                }
            )

    def test_failed_insert_removes_new_indexes_and_staging_files(self):
        self.insert_row(row_id="duplicate")
        conflicting_values = ("Different", "99", "False")

        with self.assertRaises(FileExistsError):
            self.table.insert(
                {
                    "id": "duplicate",
                    "name": conflicting_values[0],
                    "number": int(conflicting_values[1]),
                    "active": False,
                }
            )

        for column, value in zip(("name", "number", "active"), conflicting_values):
            self.assertFalse((self.table.indexes_path / column / value).exists())
        self.assertEqual(list(self.table.staging_path.iterdir()), [])
        current_markers = list(
            (self.table.rows_path / "duplicate").glob("*.current_transaction")
        )
        self.assertEqual(len(current_markers), 1)
