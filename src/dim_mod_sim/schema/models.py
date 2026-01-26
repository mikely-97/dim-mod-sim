"""Schema submission models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class SCDType(str, Enum):
    """Slowly Changing Dimension strategy types."""

    TYPE_0 = "type_0"  # Fixed - no changes tracked
    TYPE_1 = "type_1"  # Overwrite - current value only
    TYPE_2 = "type_2"  # Add row - full history
    TYPE_3 = "type_3"  # Add column - previous + current
    TYPE_4 = "type_4"  # Mini-dimension - rapidly changing attributes
    TYPE_6 = "type_6"  # Hybrid (1+2+3)
    NONE = "none"  # No SCD handling


class AggregationType(str, Enum):
    """Types of aggregation for measures."""

    SUM = "sum"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    AVG = "avg"
    DISTINCT_COUNT = "distinct_count"


class Measure(BaseModel):
    """A measure in a fact table."""

    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str
    aggregation: AggregationType
    nullable: bool = False
    description: str | None = None


class GrainColumn(BaseModel):
    """A column that defines the grain of a fact table."""

    model_config = ConfigDict(frozen=True)

    name: str
    references_dimension: str | None = None
    is_degenerate: bool = False  # Degenerate dimension (e.g., transaction_id)


class FactTable(BaseModel):
    """A fact table in the dimensional model."""

    model_config = ConfigDict(frozen=True)

    name: str
    grain_description: str  # Human-readable grain declaration
    grain_columns: list[GrainColumn]
    measures: list[Measure]
    dimension_keys: list[str]  # Foreign keys to dimensions

    @field_validator("grain_columns")
    @classmethod
    def validate_grain_columns(cls, v: list[GrainColumn]) -> list[GrainColumn]:
        if not v:
            raise ValueError("Fact table must have at least one grain column")
        return v


class DimensionAttribute(BaseModel):
    """An attribute in a dimension table."""

    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str
    scd_tracked: bool = False  # Whether this attribute triggers SCD


class DimensionTable(BaseModel):
    """A dimension table in the dimensional model."""

    model_config = ConfigDict(frozen=True)

    name: str
    natural_key: list[str]  # Business key columns
    surrogate_key: str  # Surrogate key column name
    scd_strategy: SCDType
    attributes: list[DimensionAttribute]
    parent_dimension: str | None = None  # For snowflake schemas

    @field_validator("natural_key")
    @classmethod
    def validate_natural_key(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Dimension must have at least one natural key column")
        return v


class Relationship(BaseModel):
    """A relationship between fact and dimension tables."""

    model_config = ConfigDict(frozen=True)

    fact_table: str
    dimension_table: str
    fact_column: str
    dimension_column: str
    cardinality: str = "many-to-one"  # "many-to-one" or "many-to-many"
    is_role_playing: bool = False  # For role-playing dimensions
    role_name: str | None = None  # Role name if role-playing


class BridgeTable(BaseModel):
    """A bridge table for many-to-many relationships."""

    model_config = ConfigDict(frozen=True)

    name: str
    fact_table: str
    dimension_table: str
    group_key: str  # Groups related dimension members
    weighting_factor_column: str | None = None  # For allocation


class SchemaSubmission(BaseModel):
    """Complete schema submission for evaluation."""

    model_config = ConfigDict(frozen=True)

    fact_tables: list[FactTable]
    dimension_tables: list[DimensionTable]
    relationships: list[Relationship]
    bridge_tables: list[BridgeTable] = []

    @field_validator("fact_tables")
    @classmethod
    def validate_fact_tables(cls, v: list[FactTable]) -> list[FactTable]:
        if not v:
            raise ValueError("Schema must have at least one fact table")
        return v

    def get_fact_table(self, name: str) -> FactTable | None:
        """Get a fact table by name."""
        for ft in self.fact_tables:
            if ft.name == name:
                return ft
        return None

    def get_dimension_table(self, name: str) -> DimensionTable | None:
        """Get a dimension table by name."""
        for dt in self.dimension_tables:
            if dt.name == name:
                return dt
        return None

    def get_relationships_for_fact(self, fact_name: str) -> list[Relationship]:
        """Get all relationships for a fact table."""
        return [r for r in self.relationships if r.fact_table == fact_name]

    def get_dimensions_for_fact(self, fact_name: str) -> list[DimensionTable]:
        """Get all dimensions connected to a fact table."""
        dim_names = {r.dimension_table for r in self.get_relationships_for_fact(fact_name)}
        return [dt for dt in self.dimension_tables if dt.name in dim_names]
