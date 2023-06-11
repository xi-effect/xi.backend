from __future__ import annotations

from sqlalchemy import Enum


class EnumUpdater:
    def __init__(self, old_enum_name: str, *new_options: str) -> None:
        self.old_enum = Enum(name=old_enum_name)
        self.new_enum = Enum(*new_options, name=old_enum_name)
        self.tmp_enum = Enum(*new_options, name=f"_{old_enum_name}")

    def upgrade(self, op, table_name: str, column_name: str) -> None:
        self.tmp_enum.create(op.get_bind())
        op.execute(
            f"ALTER TABLE {table_name}"
            f" ALTER COLUMN {column_name}"
            f" TYPE {self.tmp_enum.name}"
            f" USING {column_name}::text::{self.tmp_enum.name}"
        )
        self.old_enum.drop(op.get_bind())
        self.new_enum.create(op.get_bind())
        op.execute(
            f"ALTER TABLE {table_name}"
            f" ALTER COLUMN {column_name}"
            f" TYPE {self.new_enum.name}"
            f" USING {column_name}::text::{self.new_enum.name}"
        )
        self.tmp_enum.drop(op.get_bind())

    def downgrade(self, op, table_name: str, column_name: str) -> None:
        pass
