from pydantic import Field, BaseModel
from typing import List


class CSVJsonSchemaResponse(BaseModel):
    """
    The json schema response model.
    """

    json_schema: dict =  Field(...,
                  description="JSON schema output")
    other_info: str = Field(...,
                      description="other relation info in schema")

class CreateQueryResponse(BaseModel):
    """
    the define response type of create query response
    """
    statement: str = Field(...,
                            description="statement of create query")
class CellInfo(BaseModel):
    row: int = Field(..., description="row number")
    column: str = Field(..., description="column atrribute")
    value: str = Field(..., description="value")

class ImprovesItem(BaseModel):
    description: str = Field(..., description="description of how to improve")
    position: CellInfo = Field(..., description="cell position")

class PotentialErrorQueryResponse(BaseModel):
    improves: List[ImprovesItem] = Field(..., description="list of improves")