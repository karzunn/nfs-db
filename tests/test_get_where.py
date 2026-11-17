from tests.base_test_case import DatabaseTestCase


class TableGetWhereTests(DatabaseTestCase):
    def test_get_where_returns_every_matching_row(self):
        first_id = self.insert_row(name="Ada", row_id="first")
        second_id = self.insert_row(name="Ada", row_id="second")
        self.insert_row(name="Grace", row_id="third")

        matches = self.table.get_where("name", "Ada")

        self.assertEqual(
            {row["id"] for row in matches},
            {first_id, second_id},
        )
        self.assertTrue(all(row["name"] == "Ada" for row in matches))

    def test_get_where_tracks_insert_update_and_delete(self):
        first_id = self.insert_row(name="same", row_id="first")
        second_id = self.insert_row(name="same", row_id="second")
        third_id = self.insert_row(name="other", row_id="third")

        self.table.update(second_id, lambda row: {**row, "name": "other"})
        inserted_id = self.insert_row(name="same", row_id="inserted")
        self.table.delete(first_id)

        same_rows = self.table.get_where("name", "same")
        other_rows = self.table.get_where("name", "other")
        self.assertEqual({row["id"] for row in same_rows}, {inserted_id})
        self.assertEqual({row["id"] for row in other_rows}, {second_id, third_id})

    def test_get_where_rejects_an_unknown_column(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.table.get_where("missing", "value")
