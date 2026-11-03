import errno
import os
import shutil
from uuid import uuid4
from pathlib import Path

from ..constants import (
    STAGING_PATH,
    INDEXES_PATH,
    ROWS_PATH,
    ID_COLUMN_NAME,
    CURRENT_TRANSACTION_EXTENSION,
    FIELDS_PATH
)
from .table_info import table_info
from ..utils import exec


class table:

    def __init__(self, db_path: Path, table_info: table_info):
        self.info = table_info
        self.path = db_path / table_info.identifier

        self.staging_path = self.path / STAGING_PATH
        self.staging_path.mkdir(parents=True, exist_ok=True)

        self.indexes_path = self.path / INDEXES_PATH
        self.indexes_path.mkdir(parents=True, exist_ok=True)

        self.rows_path = self.path / ROWS_PATH
        self.rows_path.mkdir(parents=True, exist_ok=True)

    def _validate_data(self, data: dict):
        if ID_COLUMN_NAME not in data:
            data[ID_COLUMN_NAME] = str(uuid4())
        for col in self.info.columns.values():
            if col.name not in data:
                raise ValueError(f"Missing value for column '{col.name}'")
            if not isinstance(data[col.name], col.data_type.value):
                raise TypeError(
                    f"Incorrect type for column '{col.name}'. "
                    f"Expected {col.data_type.value.__name__}, got {type(data[col.name]).__name__}"
                )

    def _stage_insert(self, data: dict) -> tuple[Path, Path]:
        row_id = data[ID_COLUMN_NAME]
        transaction_id = str(uuid4())
        staging_transaction_path = self.staging_path / transaction_id
        staging_row_path = staging_transaction_path / row_id
        (staging_row_path / transaction_id).mkdir(parents=True, exist_ok=True)

        (staging_row_path / (transaction_id + "." + CURRENT_TRANSACTION_EXTENSION)).touch(exist_ok=True)

        fields_path = staging_row_path / transaction_id / FIELDS_PATH
        fields_path.mkdir(parents=True, exist_ok=True)

        future_row_path = self.rows_path / row_id
        for name, value in data.items():
            (fields_path / name / str(value)).mkdir(parents=True, exist_ok=True)
            symlink_path = (self.indexes_path / name / str(value) / transaction_id)
            symlink_path.parent.mkdir(parents=True, exist_ok=True)
            symlink_path.symlink_to(future_row_path, target_is_directory=True)

        return staging_row_path, future_row_path

    def _clean_up_staging(self, staging_path: Path, data: dict):
        staging_parent = staging_path.parent
        transaction_id = staging_parent.name
        shutil.rmtree(staging_parent, ignore_errors=True)
        for name, value in data.items():
            (self.indexes_path / name / str(value) / transaction_id).unlink()

    def insert(self, data: dict) -> str:
        self._validate_data(data)
        staging_path, future_path = self._stage_insert(data)

        try: os.rename(staging_path, future_path)
        except OSError as error:
            self._clean_up_staging(staging_path, data)
            if error.errno in (errno.EEXIST, errno.ENOTEMPTY):
                raise FileExistsError(
                    f"Row with ID '{data[ID_COLUMN_NAME]}' already exists in table '{self.info.table_name}'"
                ) from None
            raise

        staging_path.parent.rmdir()
        return data[ID_COLUMN_NAME]

    def _stage_delete(self) -> Path:
        transaction_id = str(uuid4())
        return self.staging_path / transaction_id

    def delete(self, row_id: str):
        deleted_path = self._stage_delete()
        try: os.rename(self.rows_path / row_id, deleted_path)
        except OSError as error:
            if error.errno in (errno.ENOENT, errno.ENOTEMPTY):
                raise FileNotFoundError(
                    f"Row with ID '{row_id}' does not exist in table '{self.info.table_name}'"
                ) from None
            raise

        # TODO: remove symlink indexes

    def get(self, row_id: str) -> dict:
        row_path = self.rows_path / row_id
        lines, _, _ = exec("find", row_path)
        paths = lines.splitlines()

        data = {}
        for path in paths:
            relative_path = Path(path).relative_to(row_path)
            if len(relative_path.parts) == 4:
                _, _, column_name, column_value = relative_path.parts
                column = self.info.columns[column_name]
                if column.data_type.value == bool:
                    data[column_name] = column_value.lower() == "true"
                else:
                    data[column_name] = column.data_type.value(column_value)

        return data
        
        
