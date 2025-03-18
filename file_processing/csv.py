import json
import random

import pandas
import pandas as pd
from jsonschema.validators import Draft202012Validator
from langchain_core.prompts import ChatPromptTemplate
from typing import List

from file_processing.schema import CSVJsonSchemaResponse, PotentialErrorQueryResponse, ImprovesItem
from llm import openai_llm
from llm.prompts import FIND_JSON_SCHEMA_PROMPTS, SYSTEM_MESSAGE, GET_ISSUE_OF_DATA


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

    def get_length(self):
        return self.data.size

    def get_sample_data(self, sample_size: int):
        """
            Returns a random sample of the DataFrame.

            :param sample_size: Number of rows to sample
            :return: Sampled DataFrame
        """

        if sample_size > self.get_length():
            raise ValueError(f"Sample size cannot be greater than the number of rows in the DataFrame. {sample_size} > {self.data.shape[0]}")
        return self.data.sample(n=sample_size, replace=True, random_state=42)

    def get_range_date(self, left: int, right: int):
        if right < left or right > self.data.size or left < 0:
            raise ValueError(f"Range not valid. {left}, {right}")
        return self.data.loc[left:right]

    def generate_schema(self, other_info: str = '', prompt: str = FIND_JSON_SCHEMA_PROMPTS) -> dict:
        message = [('system', SYSTEM_MESSAGE), ('human', prompt)]
        chain_message = ChatPromptTemplate.from_messages(message)
        chain = chain_message | openai_llm
        chain.bind(response_format="json_object")

        # get random format_data
        format_data = self.get_sample_data(sample_size=min(self.data.size, 10)).to_csv(index=False)

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

    def _scan_error_for_range(self, schema: dict, range_query: tuple[int, int]) -> PotentialErrorQueryResponse:
        message = [('system', SYSTEM_MESSAGE), ('human', GET_ISSUE_OF_DATA)]
        chain_message = ChatPromptTemplate.from_messages(message)
        chain = chain_message | openai_llm
        chain.bind(response_format="json_object")

        format_data = self.get_range_date(range_query[0], range_query[1])

        response = chain.invoke(input={
            "schema": str(schema),
            "data": format_data.to_csv(index=False),
            "range": str(range_query),
        })

        try:
            content_json = json.loads(response.content)
            if isinstance(content_json, dict) and "improves" in content_json:
                improves_response = PotentialErrorQueryResponse(**content_json)
                return improves_response
            else:
                raise ValueError("Invalid JSON format received from API.")
        except json.JSONDecodeError:
            raise ValueError("Response is not a valid JSON object.")

    def scan_error(self, schema: dict, batch_size: int = 5) -> List[ImprovesItem]:
        list_improves: List[ImprovesItem] = []
        for left in range(0, self.data.size, batch_size):
            right = min(left + batch_size, self.data.size)
            improves = self._scan_error_for_range(schema=schema, range_query=(left, right))
            list_improves.extend(improves.improves)
        return list_improves

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