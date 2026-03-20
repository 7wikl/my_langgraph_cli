"""Database types - Pydantic models corresponding to TypeScript interfaces."""

from typing import Any, Optional
from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: Optional[str] = None
    timezone: Optional[str] = None


class ColumnInfo(BaseModel):
    column_name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str] = None
    column_comment: str
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None


class TableSchema(BaseModel):
    table_name: str
    table_comment: str
    columns: list[ColumnInfo]


class SqlQueryResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time: float


class GeneratedSql(BaseModel):
    sql: str
    explanation: str
    tables_used: list[str]
    confidence: float
