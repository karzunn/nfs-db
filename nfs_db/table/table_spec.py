import enum
import hashlib
import json

from ..constants import ID_COLUMN_NAME


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


class table_spec:
    
    def __init__(self, name: str):
        self.name = name
        self.columns = {}
        self.columns[ID_COLUMN_NAME] = column(ID_COLUMN_NAME, column_type.STRING)

    def add_column(self, name: str, data_type: column_type) -> "table_info":
        if name in self.columns:
            raise ValueError(f"Column '{name}' already exists in table '{self.name}'")
        self.columns[name] = column(name, data_type)
        return self

    @property
    def identifier(self):
        definition = {
            "name": self.name,
            "columns": [
                (col.name, col.data_type.name) for col in self.columns.values()
            ],
        }
        serialized = json.dumps(
            definition, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()
