import hashlib
import json

from ..constants import ID_COLUMN_NAME


_COLUMN_TYPE_NAMES = {
    int: "INTEGER",
    str: "STRING",
    float: "FLOAT",
    bool: "BOOLEAN",
}


class column:

    def __init__(
        self,
        name: str,
        data_type: type,
    ):
        self.name = name
        self.data_type = data_type


class table_spec:

    def __init__(self, name: str, /, **columns: type):
        self.name = name
        self.columns = {}
        self.columns[ID_COLUMN_NAME] = column(ID_COLUMN_NAME, str)

        for column_name, data_type in columns.items():
            if column_name in self.columns:
                raise ValueError(
                    f"Column '{column_name}' already exists in table '{self.name}'"
                )
            if data_type not in _COLUMN_TYPE_NAMES:
                raise TypeError("Column type must be int, str, float, or bool")
            self.columns[column_name] = column(column_name, data_type)

    @property
    def identifier(self):
        definition = {
            "name": self.name,
            "columns": [
                (col.name, _COLUMN_TYPE_NAMES[col.data_type])
                for col in self.columns.values()
            ],
        }
        serialized = json.dumps(
            definition, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()
