import json
import random

import pandas
import pandas as pd
from jsonschema.validators import Draft202012Validator
from langchain_core.prompts import ChatPromptTemplate

from file_processing.schema import CSVJsonSchemaResponse
from llm import openai_llm
from llm.prompts import FIND_JSON_SCHEMA_PROMPTS, SYSTEM_MESSAGE, find_simple_json_schema_message


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

    def get_sample_data(self, sample_size: int, random_state: int = None):
        """
            Returns a random sample of the DataFrame.

            :param df: Pandas DataFrame to sample from
            :param sample_size: Number of rows to sample
            :param random_state: Random seed for reproducibility (default: None)
            :return: Sampled DataFrame
        """

        if sample_size > len(self.data):
            raise ValueError(f"Sample size cannot be greater than the number of rows in the DataFrame. {sample_size} > {self.data.shape[0]}")
        return self.data.sample(n=sample_size, random_state=random_state)

    def generate_schema(self, other_info: str = '', prompt: str = FIND_JSON_SCHEMA_PROMPTS) -> dict:
        message = [('system', SYSTEM_MESSAGE), ('human', prompt)]
        chain_message = ChatPromptTemplate.from_messages(message)
        chain = chain_message | openai_llm
        chain.bind(response_format="json_object")

        # get random format_data
        format_data = self.get_sample_data(min(self.data.length, 20), random_state=random.seed()).to_csv(index=False)

        response = chain.invoke(input={
            "data": format_data,
            "context": other_info,
        })

        try:
            content_json = json.loads(response.content)

            # Ensure correct structure
            if isinstance(content_json, dict) and "json_schema" in content_json and "other_info" in content_json:
                json_schema_response = CSVJsonSchemaResponse(**content_json)
                return json_schema_response.json_schema
            else:
                raise ValueError("Invalid JSON format received from API.")

        except json.JSONDecodeError:
            raise ValueError("Response is not a valid JSON object.")

    def set_schema(self, prompt: str = FIND_JSON_SCHEMA_PROMPTS):
        schema = self.generate_schema(prompt=prompt)
        self.schema = schema

    @classmethod
    def validate_row(cls, row, schema):
        validator = Draft202012Validator(schema)
        errors = []
        for error in validator.iter_errors(row):
            errors.append({
                "attribute": error.path[0] if error.path else "Unknown",
                "message": error.message
            })
        return errors

    @classmethod
    def validate_dataset(cls, df: pd.DataFrame, schema: dict):
        validation_results = []

        for index, row in df.iterrows():
            row_dict = row.to_dict()
            errors = cls.validate_row(row_dict, schema)

            if errors:
                validation_results.append({
                    "row": index,
                    "errors": errors
                })

        return validation_results