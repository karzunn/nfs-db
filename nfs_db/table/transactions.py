from uuid import uuid4
from pathlib import Path
import errno
import os
from abc import ABC, abstractmethod
import shutil
from nfs_db.constants import (
    CURRENT_TRANSACTION_EXTENSION,
    STAGING_PATH,
    INDEXES_PATH,
    ROWS_PATH,
    FIELDS_PATH,
    ID_COLUMN_NAME,
)


def _delete_index(index_path: Path):
    index_path.unlink(missing_ok=True)
    try:
        index_path.parent.rmdir()
    except OSError as error:
        if error.errno not in (errno.ENOENT, errno.ENOTEMPTY, errno.EEXIST):
            raise


class transaction(ABC):

    @abstractmethod
    def stage(self): ...

    @abstractmethod
    def execute(self): ...

    @abstractmethod
    def cleanup(self): ...


class insert_transaction(transaction):

    def __init__(self, table_path: Path, data: dict):
        self.id = str(uuid4())
        self.data = data
        self.row_id = data[ID_COLUMN_NAME]
        self.table_path = table_path
        self.staging_path = self.table_path / STAGING_PATH
        self.indexes_path = self.table_path / INDEXES_PATH
        self.rows_path = self.table_path / ROWS_PATH
        self.staging_row_path = self.staging_path / self.id / self.row_id
        self.future_row_path = self.rows_path / self.row_id
        self.executed = False

    def _create_indexes(self):
        for name, value in self.data.items():
            symlink_path = (self.indexes_path / name / str(value) / self.id)
            symlink_path.parent.mkdir(parents=True, exist_ok=True)
            symlink_path.symlink_to(self.future_row_path, target_is_directory=True)

    def _delete_indexes(self):
        for name, value in self.data.items():
            _delete_index(self.indexes_path / name / str(value) / self.id)

    def _create_current_transaction_marker(self):
        (self.staging_row_path / (self.id + CURRENT_TRANSACTION_EXTENSION)).touch(exist_ok=True)

    def _create_transaction_contents(self):
        fields_path = self.staging_row_path / self.id / FIELDS_PATH
        for name, value in self.data.items():
            (fields_path / name / str(value)).mkdir(parents=True, exist_ok=True)

    def stage(self):
        self._create_transaction_contents()
        self._create_current_transaction_marker()
        self._create_indexes()

    def execute(self):
        self.executed = False
        try: 
            os.rename(self.staging_row_path, self.future_row_path)
            self.executed = True
        except OSError as error:
            if error.errno in (errno.EEXIST, errno.ENOTEMPTY):
                raise FileExistsError() from None
            raise

    def cleanup(self):
        if not self.executed:
            self._delete_indexes()
        shutil.rmtree(self.staging_row_path, ignore_errors=True)
        self.staging_row_path.parent.rmdir()


class update_transaction(transaction):

    def __init__(
        self,
        table_path: Path,
        row_id: str,
        existing_transaction_id: str,
        data: dict,
    ):
        self.id = str(uuid4())
        self.data = data
        self.row_id = row_id
        self.existing_transaction_id = existing_transaction_id
        self.table_path = table_path
        self.indexes_path = self.table_path / INDEXES_PATH
        self.rows_path = self.table_path / ROWS_PATH
        self.row_path = self.rows_path / self.row_id
        self.transaction_path = self.row_path / self.id
        self.executed = False

    def _create_transaction_contents(self):
        fields_path = self.transaction_path / FIELDS_PATH
        for name, value in self.data.items():
            (fields_path / name / str(value)).mkdir(parents=True, exist_ok=True)

    def _delete_transaction_contents(self):
        shutil.rmtree(self.transaction_path, ignore_errors=True)

    def _create_new_indexes(self):
        for name, value in self.data.items():
            symlink_path = (self.indexes_path / name / str(value) / self.id)
            symlink_path.parent.mkdir(parents=True, exist_ok=True)
            symlink_path.symlink_to(self.row_path, target_is_directory=True)

    def _delete_new_indexes(self):
        for name, value in self.data.items():
            _delete_index(self.indexes_path / name / str(value) / self.id)

    def _delete_previous_indexes(self):
        fields_path = (
            self.row_path / self.existing_transaction_id / FIELDS_PATH
        )
        if not fields_path.is_dir():
            return

        for column_path in fields_path.iterdir():
            for value_path in column_path.iterdir():
                _delete_index(
                    self.indexes_path
                    / column_path.name
                    / value_path.name
                    / self.existing_transaction_id
                )

    def stage(self):
        self._create_transaction_contents()
        self._create_new_indexes()

    def execute(self):
        existing_transaction_marker = (
            self.row_path
            / f"{self.existing_transaction_id}{CURRENT_TRANSACTION_EXTENSION}"
        )
        new_transaction_marker = (
            self.row_path / f"{self.id}{CURRENT_TRANSACTION_EXTENSION}"
        )
        os.rename(existing_transaction_marker, new_transaction_marker)
        self.executed = True

    def cleanup(self):
        if self.executed:
            self._delete_previous_indexes()
            shutil.rmtree(
                self.row_path / self.existing_transaction_id,
                ignore_errors=True,
            )
        else:
            self._delete_new_indexes()
            self._delete_transaction_contents()


class delete_transaction(transaction):

    def __init__(self, table_path: Path, row_id: str):
        self.id = str(uuid4())
        self.row_id = row_id
        self.table_path = table_path
        self.staging_path = self.table_path / STAGING_PATH
        self.indexes_path = self.table_path / INDEXES_PATH
        self.rows_path = self.table_path / ROWS_PATH
        self.row_path = self.rows_path / self.row_id
        self.deleted_path = self.staging_path / self.id
        self.executed = False

    def stage(self): ...

    def execute(self):
        try: 
            os.rename(self.row_path, self.deleted_path)
            self.executed = True
        except OSError as error:
            if error.errno in (errno.ENOENT, errno.ENOTEMPTY):
                raise FileNotFoundError() from None
            raise

    def _delete_indexes(self):
        current_marker = next(
            self.deleted_path.glob(f"*{CURRENT_TRANSACTION_EXTENSION}"),
            None,
        )
        if current_marker is None:
            raise FileNotFoundError(f"Row with ID {self.row_id} does not exist")
        current_transaction = current_marker.name.removesuffix(CURRENT_TRANSACTION_EXTENSION)
        fields_path = self.deleted_path / current_transaction / FIELDS_PATH
        if not fields_path.is_dir():
            raise FileNotFoundError(f"Fields for row with ID {self.row_id} do not exist")
        for column_path in fields_path.iterdir():
            for value_path in column_path.iterdir():
                _delete_index(
                    self.indexes_path
                    / column_path.name
                    / value_path.name
                    / current_transaction
                )

    def cleanup(self):
        if not self.executed:
            return
        self._delete_indexes()
        shutil.rmtree(self.deleted_path, ignore_errors=True)
