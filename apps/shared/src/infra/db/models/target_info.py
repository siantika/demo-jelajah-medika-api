from __future__ import annotations

from sqlalchemy import Column, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY

from apps.shared.src.infra.db.models.jobs import metadata

target_info = Table(
    "target_info",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("pdb_id", String(255), nullable=True),
    Column("sequence", Text, nullable=True),
    Column("protein_name", Text, nullable=True),
    Column("protein_function", Text, nullable=True),
    Column("gene_name", String(50), nullable=True),
    Column("source_organism", Text, nullable=True),
    Column("ec_numbers", ARRAY(Text), nullable=True),
    Column("keywords", Text, nullable=True),
)
