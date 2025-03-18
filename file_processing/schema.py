from pydantic import Field, BaseModel


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

class PotentialErrorQueryResponse(BaseModel):
    issue_list: list[str] = Field(...,
                                  description="list of issue list")