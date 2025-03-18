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
    row: int = Field(..., description="Row index")
    column: str = Field(..., description="Column name")
    value: str = Field(..., description="Cell value")


class ImprovesItem(BaseModel):
    """
    Model representing a suggested improvement for a dataset.
    """
    description: str = Field(..., description="Description of suggested improvement")
    position: CellInfo = Field(..., description="Location of the issue in the dataset")


class PotentialErrorQueryResponse(BaseModel):
    """
    Model representing a response containing potential errors in a dataset.
    """
    improves: List[ImprovesItem] = Field(..., description="List of suggested improvements")
