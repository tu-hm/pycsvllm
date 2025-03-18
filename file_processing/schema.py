from pydantic import Field, BaseModel


class CSVJsonSchemaResponse(BaseModel):
    """
    The json schema response model.
    """

    json_schema: dict =  Field(...,
                  description="JSON schema output")
    other_info: str = Field(...,
                      description="other relation info in schema")
