import errno
import os
import shutil
from uuid import uuid4
from pathlib import Path
from collections import defaultdict

from ..constants import (
    STAGING_PATH,
    INDEXES_PATH,
    ROWS_PATH,
    ID_COLUMN_NAME,
    CURRENT_TRANSACTION_EXTENSION,
    FIELDS_PATH
)
from .table_info import table_info
from .transactions import insert_transaction, delete_transaction
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


    def _validate(self, data: dict):
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


    def insert(self, data: dict) -> str:
        self._validate(data)
        insert_trans = insert_transaction(self.path, data)
        try:
            insert_trans.stage()
            insert_trans.execute()
            return data[ID_COLUMN_NAME]
        except FileExistsError as err:
            raise Exception(
                f"Row with ID {data[ID_COLUMN_NAME]} already exists in table {self.table_info.table_name}"
            ) from None
        finally:
            insert_trans.cleanup()


    def delete(self, row_id: str):
        delete_trans = delete_transaction(self.path, row_id)
        try:
            delete_trans.execute()
        except FileNotFoundError as err:
            raise Exception(
                f"Row with ID {row_id} does not exist in table {self.table_info.table_name}"
            ) from None
        finally:
            delete_trans.cleanup()


    def get(self, row_id: str) -> dict:
        row_path = self.rows_path / row_id
        lines, _, _ = exec("find", row_path)
        paths = lines.splitlines()

        data = {}
        current_transaction_id = None
        for path in paths:
            if path.endswith(CURRENT_TRANSACTION_EXTENSION):
                current_transaction_id = Path(path).name.replace(CURRENT_TRANSACTION_EXTENSION, "")
                break
        else:
            raise RuntimeError(f"Row with ID '{row_id}' is missing a current transaction marker.")
        for path in paths:
            relative_path = Path(path).relative_to(row_path)
            is_value_dir = len(relative_path.parts) == 4
            is_current_transaction = str(relative_path).startswith(current_transaction_id)
            if is_value_dir and is_current_transaction:
                _, _, column_name, column_value = relative_path.parts
                column = self.info.columns[column_name]
                if column.data_type.value == bool:
                    data[column_name] = column_value.lower() == "true"
                else:
                    data[column_name] = column.data_type.value(column_value)

        return data

    def get_where(self, column_name: str, value) -> list[dict]:
        if column_name not in self.info.columns:
            raise ValueError(f"Column '{column_name}' does not exist in table '{self.info.table_name}'")

        index_path = self.indexes_path / column_name / str(value)
        lines, _, _ = exec("find", index_path, "-ls")
        paths = lines.splitlines()

        rows = defaultdict(dict)
        for path in paths:
            relative_path = Path(path).relative_to(index_path)
            print(relative_path.parts)
            is_value_dir = len(relative_path.parts) == 5
            if is_value_dir:
                is_current_transaction = relative_path.parts[0] == relative_path.parts[1]
                if is_current_transaction:
                    if relative_path.parts[0] == relative_path.parts[1]:
                        _, _, _, column_name, column_value = relative_path.parts
                        column = self.info.columns[column_name]
                        if column.data_type.value == bool:
                            rows[relative_path.parts[0]][column_name] = column_value.lower() == "true"
                        else:
                            rows[relative_path.parts[0]][column_name] = column.data_type.value(column_value)
        return list(rows.values())
