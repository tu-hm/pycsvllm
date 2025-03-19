import json

import numpy as np
import pandas as pd
from jsonschema.validators import Draft202012Validator
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict

from file_processing.schema import (
    CSVJsonSchemaResponse,
    PotentialErrorQueryResponse,
    ImprovesItem
)
from llm import base_llm
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
        self.data = pd.read_csv(filepath, index_col=0)
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
        chain = chain_message | base_llm
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
        chain = chain_message | base_llm
        chain.bind(response_format="json_object")

        format_data = self.get_range_data(*range_query).to_csv(index=False)
        response = chain.invoke(input={
            "schema": str(schema),
            "data": format_data,
        })

        print(response.content)

        try:
            content_json = json.loads(response.content)
            if "improves" in content_json:
                return PotentialErrorQueryResponse(**content_json)
            else:
                raise ValueError("Invalid JSON format received from API.")
        except json.JSONDecodeError:
            raise ValueError("Response is not a valid JSON object.")

    def _update_index(self, left: int, items: List[ImprovesItem]):
        for item in items:
            item.position.row = left + item.position.row
        return items

    def scan_error(self, schema: dict, batch_size: int = 10) -> List[ImprovesItem]:
        """
        Scans the entire dataset for potential errors in batches.

        :param schema: JSON schema for validation.
        :param batch_size: Number of rows per scan.
        :return: List of detected improvement suggestions.
        """
        improvements: List[ImprovesItem] = []
        for start in range(0, self.get_length(), batch_size):
            end = min(start + batch_size, self.get_length())
            improvements.extend(
                self._update_index(start, self._scan_error_for_range(
                    schema, (start, end)).improves)
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

    @staticmethod
    def parse_value(value: str, type_or_dtype):
        """
        Parse a string value based on either a schema type string or a pandas dtype.

        :param value: The string value to parse (e.g., "42", "3.14", "true").
        :param type_or_dtype: Either a schema type (str) or pandas dtype (e.g., np.int64).
        :return: The parsed value (e.g., 42, 3.14, True).
        :raises ValueError: If parsing fails or the type/dtype is unsupported.
        """
        if isinstance(type_or_dtype, str):
            # Schema type string
            if type_or_dtype == "string":
                return value
            elif type_or_dtype == "integer":
                return int(value)
            elif type_or_dtype == "number":
                return float(value)
            elif type_or_dtype == "boolean":
                if value.lower() in ["true", "1", "yes", "t", "y"]:
                    return True
                elif value.lower() in ["false", "0", "no", "f", "n"]:
                    return False
                else:
                    raise ValueError(f"Cannot parse '{value}' as boolean.")
            else:
                raise ValueError(f"Unsupported schema type: {type_or_dtype}")
        else:
            # Pandas dtype
            dtype = type_or_dtype
            if np.issubdtype(dtype, np.integer):
                return int(value)
            elif np.issubdtype(dtype, np.floating):
                return float(value)
            elif np.issubdtype(dtype, np.bool_):
                if value.lower() in ["true", "1", "yes", "t", "y"]:
                    return True
                elif value.lower() in ["false", "0", "no", "f", "n"]:
                    return False
                else:
                    raise ValueError(f"Cannot parse '{value}' as boolean.")
            elif np.issubdtype(dtype, np.object_):
                return value
            else:
                raise ValueError(f"Unsupported pandas dtype: {dtype}")

    def apply_improvements(self, improvements: List[ImprovesItem]) -> None:
        """
        Apply improvements to the DataFrame, using schema types or inferred pandas types.

        :param improvements: List of improvements specifying row, column, and new value.
        :raises ValueError: If column/row is invalid or value cannot be parsed.
        """
        for item in improvements:
            column = item.position.column
            row = item.position.row
            value = item.position.value

            # Ensure column exists in DataFrame
            if column not in self.data.columns:
                raise ValueError(f"Column '{column}' not found in DataFrame.")

            # Decide whether to use schema or pandas dtype
            if self.schema:
                if column not in self.schema["properties"]:
                    raise ValueError(f"Column '{column}' not found in schema.")
                type_or_dtype = self.schema["properties"][column]["type"]
            else:
                type_or_dtype = self.data[column].dtype

            # Parse the value
            try:
                parsed_value = self.parse_value(value, type_or_dtype)
            except ValueError as e:
                raise ValueError(f"Failed to parse '{value}' for column '{column}': {e}")

            # Ensure row is valid
            if row < 0 or row >= len(self.data):
                raise ValueError(f"Row {row} is out of range (0 to {len(self.data) - 1}).")

            # Update the DataFrame
            column_index = self.data.columns.get_loc(column)
            self.data.iloc[row, column_index] = parsed_value
        return self.data