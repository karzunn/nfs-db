import errno
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nfs_db.constants import CURRENT_TRANSACTION_EXTENSION
from nfs_db.table.transactions import (
    _delete_index,
    delete_transaction,
    update_transaction,
)


class TransactionCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def test_delete_index_reraises_unexpected_directory_errors(self):
        index = self.root / "value" / "link"
        index.parent.mkdir()
        index.touch()

        with patch.object(Path, "rmdir", side_effect=OSError(errno.EACCES, "denied")):
            with self.assertRaises(PermissionError):
                _delete_index(index)

    def test_update_cleanup_handles_a_missing_previous_transaction(self):
        update = update_transaction(
            self.root,
            "row",
            "old-transaction",
            {"id": "row"},
        )
        update.executed = True

        update.cleanup()

        self.assertFalse(update.transaction_path.exists())

    def test_delete_indexes_rejects_missing_marker_and_fields(self):
        delete = delete_transaction(self.root, "row")
        with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
            delete._delete_indexes()

        transaction_id = "transaction"
        delete.deleted_path = self.root / "deleted"
        delete.deleted_path.mkdir()
        (delete.deleted_path / f"{transaction_id}{CURRENT_TRANSACTION_EXTENSION}").touch()
        with self.assertRaisesRegex(FileNotFoundError, "Fields for row"):
            delete._delete_indexes()
