import json

import pandas
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate

from file_processing.schema import CSVJsonSchemaResponse
from llm import openai_llm
from llm.prompts import find_json_schema_message, system_message

class CSVLoader:
    name: str
    filepath: str
    data: pandas.DataFrame
    schema: dict

    def __init__(self, filepath: str, name: str = ''):
        self.name = name
        self.filepath = filepath
        self.data = pd.read_csv(filepath)
        self.schema = {}

    def read_data(self, filepath):
        self.filepath = filepath
        self.data = pd.read_csv(filepath)

    def to_str(self):
        return self.data.to_csv(index=False)

    def to_json(self):
        return self.data.to_json()

    def to_dict(self):
        return self.data.to_dict()

    def get_sample_data(self):
        pass

    def generate_schema(self, other_info: str = '') -> CSVJsonSchemaResponse:
        message = [('system', system_message), ('human', find_json_schema_message)]
        chain_message = ChatPromptTemplate.from_messages(message)
        chain = chain_message | openai_llm
        chain.bind(response_format="json_object")

        format_data = self.to_str()

        response = chain.invoke(input={
            "data": format_data,
            "context": other_info,
        })

        try:
            content_json = json.loads(response.content)

            # Ensure correct structure
            if isinstance(content_json, dict) and "json_schema" in content_json and "other_info" in content_json:
                json_schema_response = CSVJsonSchemaResponse(**content_json)
                schema = json_schema_response.json_schema
                self.schema = schema
                return json_schema_response
            else:
                raise ValueError("Invalid JSON format received from API.")

        except json.JSONDecodeError:
            raise ValueError("Response is not a valid JSON object.")
