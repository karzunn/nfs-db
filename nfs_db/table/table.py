from collections.abc import Callable
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
from .table_spec import table_spec
from .transactions import insert_transaction, update_transaction, delete_transaction
from ..utils import exec


class table:

    def __init__(self, db_path: Path, table_spec: table_spec):
        self.spec = table_spec
        self.path = db_path / table_spec.identifier

        self.staging_path = self.path / STAGING_PATH
        self.staging_path.mkdir(parents=True, exist_ok=True)

        self.indexes_path = self.path / INDEXES_PATH
        self.indexes_path.mkdir(parents=True, exist_ok=True)

        self.rows_path = self.path / ROWS_PATH
        self.rows_path.mkdir(parents=True, exist_ok=True)


    def _validate(self, data: dict):
        if ID_COLUMN_NAME not in data:
            data[ID_COLUMN_NAME] = str(uuid4())

        for col in self.spec.columns.values():
            if col.name not in data:
                raise ValueError(f"Missing value for column '{col.name}'")
            if type(data[col.name]) is not col.data_type:
                raise TypeError(
                    f"Incorrect type for column '{col.name}'. "
                    f"Expected {col.data_type.__name__}, got {type(data[col.name]).__name__}"
                )


    def insert(self, data: dict) -> str:
        self._validate(data)
        insert_trans = insert_transaction(self.path, data)
        try:
            insert_trans.stage()
            insert_trans.execute()
            return data[ID_COLUMN_NAME]
        except FileExistsError:
            raise FileExistsError(
                f"Row with ID {data[ID_COLUMN_NAME]} already exists in table {self.spec.name}"
            ) from None
        finally:
            insert_trans.cleanup()


    def update(self, row_id: str, edit: Callable[[dict], dict]) -> dict:
        if not callable(edit):
            raise TypeError("edit must be a callable that accepts and returns a row")

        while True:
            existing_transaction_id, row = self._get_row_snapshot(row_id)
            updated_row = edit(row.copy())
            if not isinstance(updated_row, dict):
                raise TypeError("edit must return a row dictionary")
            if updated_row.get(ID_COLUMN_NAME) != row_id:
                raise ValueError(f"Row ID '{ID_COLUMN_NAME}' cannot be modified")
            if set(updated_row) != set(self.spec.columns):
                raise ValueError("Updated row must contain exactly the table's columns")
            self._validate(updated_row)

            update_trans = update_transaction(
                self.path,
                row_id,
                existing_transaction_id,
                updated_row,
            )
            try:
                update_trans.stage()
                try:
                    update_trans.execute()
                except FileNotFoundError:
                    continue
            finally:
                update_trans.cleanup()

            return updated_row


    def delete(self, row_id: str):
        delete_trans = delete_transaction(self.path, row_id)
        try:
            delete_trans.execute()
        except FileNotFoundError:
            raise KeyError(
                f"Row with ID {row_id} does not exist in table {self.spec.name}"
            ) from None
        finally:
            delete_trans.cleanup()


    def _convert_value(self, column_name: str, value: str):
        column = self.spec.columns[column_name]
        if column.data_type is bool:
            return value.lower() == "true"
        return column.data_type(value)


    def get(self, row_id: str) -> dict:
        _, row = self._get_row_snapshot(row_id)
        return row


    def _get_row_snapshot(self, row_id: str) -> tuple[str, dict]:
        row_path = self.rows_path / row_id
        lines, _, _ = exec(
            "find",
            row_path,
            "(",
            "-type",
            "d",
            "-o",
            "-type",
            "f",
            "-name",
            f"*{CURRENT_TRANSACTION_EXTENSION}",
            ")",
        )
        paths = lines.splitlines()

        if not paths:
            raise KeyError(f"Row with ID '{row_id}' does not exist")

        transaction_ids = {
            relative[0]
            for path in paths
            if len(relative := Path(path).relative_to(row_path).parts) == 1
        }
        current_transaction_id = next(
            (
                Path(path).name.removesuffix(CURRENT_TRANSACTION_EXTENSION)
                for path in paths
                if path.endswith(CURRENT_TRANSACTION_EXTENSION)
                and Path(path).name.removesuffix(CURRENT_TRANSACTION_EXTENSION)
                in transaction_ids
            ),
            None,
        )
        if current_transaction_id is None:
            raise RuntimeError(
                f"Row with ID '{row_id}' is missing a current transaction marker."
            )

        data = {}
        for path in paths:
            relative_path = Path(path).relative_to(row_path)
            parts = relative_path.parts
            if len(parts) == 4 and parts[0] == current_transaction_id:
                _, _, column_name, column_value = parts
                data[column_name] = self._convert_value(column_name, column_value)

        return current_transaction_id, data

    def get_where(self, column_name: str, value) -> list[dict]:
        if column_name not in self.spec.columns:
            raise ValueError(
                f"Column '{column_name}' does not exist in table '{self.spec.name}'"
            )

        index_path = self.indexes_path / column_name / str(value)
        lines, _, _ = exec(
            "find",
            "-L",
            str(index_path),
            "(",
            "-type",
            "d",
            "-o",
            "-type",
            "f",
            "-name",
            f"*{CURRENT_TRANSACTION_EXTENSION}",
            ")",
        )
        matching_transactions = set()
        rows = {}
        for path in lines.splitlines():
            relative_path = Path(path).relative_to(index_path)
            parts = relative_path.parts
            if (
                len(parts) == 2
                and parts[1].endswith(CURRENT_TRANSACTION_EXTENSION)
                and parts[0] == parts[1][:-len(CURRENT_TRANSACTION_EXTENSION)]
            ):
                matching_transactions.add(parts[0])
            elif len(parts) == 5 and parts[1] == parts[0] and parts[2] == FIELDS_PATH:
                index_transaction_id, _, _, field_name, field_value = parts
                rows.setdefault(index_transaction_id, {})[field_name] = self._convert_value(
                    field_name, field_value
                )
        return [
            row
            for index_transaction_id, row in rows.items()
            if index_transaction_id in matching_transactions
        ]
