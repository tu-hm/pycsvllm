import json
import pandas as pd
from jsonschema.validators import Draft202012Validator
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict

from file_processing.schema import (
    CSVJsonSchemaResponse,
    PotentialErrorQueryResponse,
    ImprovesItem
)
from llm import openai_llm
from llm.prompts import (
    FIND_JSON_SCHEMA_PROMPTS,
    SYSTEM_MESSAGE,
    GET_ISSUE_OF_DATA
)


class CSVLoader:
    """
    A class to load, process, and validate CSV files using JSON Schema.
    """

    def __init__(self, filepath: str, name: str = ''):
        """
        Initialize the CSVLoader instance.

        :param filepath: Path to the CSV file.
        :param name: Optional name for the dataset.
        """
        self.name = name
        self.filepath = filepath
        self.data = pd.read_csv(filepath)
        self.schema = {}

    def read_data(self, filepath: str) -> None:
        """
        Reads data from a CSV file and updates the internal DataFrame.

        :param filepath: Path to the new CSV file.
        """
        self.filepath = filepath
        self.data = pd.read_csv(filepath)

    def to_str(self) -> str:
        """Returns the CSV file as a string without index."""
        return self.data.to_csv(index=False)

    def to_json(self) -> str:
        """Returns the CSV file as a JSON string."""
        return self.data.to_json()

    def to_dict(self) -> Dict:
        """Returns the CSV file as a dictionary."""
        return self.data.to_dict()

    def get_length(self) -> int:
        """Returns the number of elements in the DataFrame."""
        return self.data.shape[0]

    def get_sample_data(self, sample_size: int) -> pd.DataFrame:
        """
        Returns a random sample of rows from the DataFrame.

        :param sample_size: Number of rows to sample.
        :return: Sampled DataFrame.
        """
        if sample_size > self.get_length():
            raise ValueError(f"Sample size {sample_size} exceeds available rows {self.get_length()}.")
        return self.data.sample(n=sample_size, random_state=42)

    def get_range_data(self, start: int, end: int) -> pd.DataFrame:
        """
        Returns a subset of the DataFrame based on row indices.

        :param start: Starting index.
        :param end: Ending index.
        :return: Sliced DataFrame.
        """
        if end < start or end > self.get_length() or start < 0:
            raise ValueError(f"Invalid range: {start}-{end}")
        return self.data.iloc[start:end]

    def generate_schema(self, other_info: str = '', prompt: str = FIND_JSON_SCHEMA_PROMPTS) -> dict:
        """
        Generates a JSON schema for the CSV dataset using an AI model.

        :param other_info: Additional context for the schema generation.
        :param prompt: Prompt template for the model.
        :return: Generated JSON schema.
        """
        message = [('system', SYSTEM_MESSAGE), ('human', prompt)]
        chain_message = ChatPromptTemplate.from_messages(message)
        chain = chain_message | openai_llm
        chain.bind(response_format="json_object")

        format_data = (self.get_sample_data(
            min(self.get_length(), 10))
                       .to_csv(index=False))
        response = chain.invoke(input={
            "data": format_data,
            "context": other_info
        })

        try:
            content_json = json.loads(response.content)
            if (isinstance(content_json, dict)
                    and "json_schema" in content_json):
                return CSVJsonSchemaResponse(**content_json).json_schema
            else:
                raise ValueError("Invalid JSON format received from API.")
        except json.JSONDecodeError:
            raise ValueError("Response is not a valid JSON object.")

    def set_schema(self, prompt: str = FIND_JSON_SCHEMA_PROMPTS) -> None:
        """Generates and sets the JSON schema for the dataset."""
        self.schema = self.generate_schema(prompt=prompt)

    def _scan_error_for_range(self, schema: dict, range_query: tuple[int, int]) -> PotentialErrorQueryResponse:
        """
        Scans for potential errors within a specific range of data.

        :param schema: JSON schema for validation.
        :param range_query: Tuple representing start and end row indices.
        :return: Potential error response object.
        """
        message = [('system', SYSTEM_MESSAGE), ('human', GET_ISSUE_OF_DATA)]
        chain_message = ChatPromptTemplate.from_messages(message)
        chain = chain_message | openai_llm
        chain.bind(response_format="json_object")

        format_data = self.get_range_data(*range_query).to_csv(index=False)
        response = chain.invoke(input={
            "schema": str(schema),
            "data": format_data,
            "range": str(range_query)
        })

        try:
            content_json = json.loads(response.content)
            if "improves" in content_json:
                return PotentialErrorQueryResponse(**content_json)
            else:
                raise ValueError("Invalid JSON format received from API.")
        except json.JSONDecodeError:
            raise ValueError("Response is not a valid JSON object.")

    def scan_error(self, schema: dict, batch_size: int = 5) -> List[ImprovesItem]:
        """
        Scans the entire dataset for potential errors in batches.

        :param schema: JSON schema for validation.
        :param batch_size: Number of rows per scan.
        :return: List of detected improvement suggestions.
        """
        improvements = []
        for start in range(0, self.get_length(), batch_size):
            end = min(start + batch_size, self.get_length())
            improvements.extend(
                self._scan_error_for_range(
                    schema, (start, end)).improves
            )
        return improvements

    @classmethod
    def validate_row(cls, row: dict, schema: dict) -> List[Dict]:
        """Validates a single row against the given schema."""
        validator = Draft202012Validator(schema)
        return [{"attribute": error.path[0] if error.path else "Unknown", "message": error.message}
                for error in validator.iter_errors(row)]

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