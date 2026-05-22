from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

metadata = MetaData()

prediction_jobs = Table(
    "prediction_jobs",
    metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    Column("smiles", Text, nullable=False),
    Column("dataset", String(16), nullable=False),
    Column("top_k", Integer, nullable=False),
    Column("return_sequence", Boolean, nullable=False),
    Column("model_version", String(64), nullable=False),
    Column("status", String(16), nullable=False),
    Column("result", JSONB, nullable=False, default=list),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
