from pydantic import Field, BaseModel
from typing import List, Dict


class CSVJsonSchemaResponse(BaseModel):
    """
    Model representing a JSON schema response.
    """
    json_schema: Dict = Field(..., description="JSON schema output")
    other_info: str = Field(..., description="Additional schema-related information")


class CreateQueryResponse(BaseModel):
    """
    Model representing the response for a create query.
    """
    statement: str = Field(..., description="SQL statement for creating a query")


class CellInfo(BaseModel):
    """
    Model representing information about a specific cell in a dataset.
    """
    name: str = Field(..., description="Column name")
    fixed_value: str | float = Field(..., description="Cell value")


class ImprovesItem(BaseModel):
    """
    Model representing a suggested improvement for a dataset.
    """
    row: int = Field(..., description="the row index")
    attribute: List[CellInfo] = Field(..., description="list of fixed cell positions")


class PotentialErrorQueryResponse(BaseModel):
    """
    Model representing a response containing potential errors in a dataset.
    """
    improves: List[ImprovesItem] | None = Field(..., description="List of suggested improvements")
