import enum
import errno
import hashlib
import json
import os
import shutil
from uuid import uuid4
from pathlib import Path

from .constants import (
    INSERT_STAGING_PATH,
    INDEXES_PATH,
    ROWS_PATH,
    DELETED_ROWS_PATH,
    ID_COLUMN_NAME,
    CURRENT_TRANSACTION_EXTENSION,
    FIELDS_PATH
)


class column_type(enum.Enum):
    INTEGER = int
    STRING = str
    FLOAT = float
    BOOLEAN = bool


class column:

    def __init__(
        self,
        name: str,
        data_type: column_type,
    ):
        self.name = name
        self.data_type = data_type


class table_info:
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.columns = {}
        self.columns[ID_COLUMN_NAME] = column(ID_COLUMN_NAME, column_type.STRING)

    def add_column(self, name: str, data_type: column_type) -> "table_info":
        if name in self.columns:
            raise ValueError(f"Column '{name}' already exists in table '{self.table_name}'")
        self.columns[name] = column(name, data_type)
        return self

    @property
    def identifier(self):
        definition = {
            "table_name": self.table_name,
            "columns": [
                (col.name, col.data_type.name) for col in self.columns.values()
            ],
        }
        serialized = json.dumps(
            definition, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


class table:

    def __init__(self, db_path: Path, table_info: table_info):
        self.info = table_info
        self.path = db_path / table_info.identifier

        self.staging_path = self.path / INSERT_STAGING_PATH
        self.staging_path.mkdir(parents=True, exist_ok=True)

        self.indexes_path = self.path / INDEXES_PATH
        self.indexes_path.mkdir(parents=True, exist_ok=True)

        self.rows_path = self.path / ROWS_PATH
        self.rows_path.mkdir(parents=True, exist_ok=True)

        self.deleted_rows_path = self.path / DELETED_ROWS_PATH
        self.deleted_rows_path.mkdir(parents=True, exist_ok=True)

    def insert(self, data: dict):
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

        try:
            os.rename(staging_row_path, future_row_path)
        except OSError as error:
            if error.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                raise
            shutil.rmtree(staging_transaction_path)
            for name, value in data.items():
                (self.indexes_path / name / str(value) / transaction_id).unlink()
            raise FileExistsError(
                f"Row with ID '{row_id}' already exists in table '{self.info.table_name}'"
            )

        staging_transaction_path.rmdir()
