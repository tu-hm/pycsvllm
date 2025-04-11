import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd
from jsonschema.validators import Draft202012Validator
from langchain_core.prompts import ChatPromptTemplate

from file_processing.schema import (
    CSVJsonSchemaResponse,
    PotentialErrorQueryResponse,
    ImprovesItem
)
from llm_providers import base_llm
from llm_providers.prompts import (
    FIND_JSON_SCHEMA_PROMPTS,
    SYSTEM_MESSAGE,
    GET_ISSUE_OF_DATA,
    FIX_JSON_SCHEMA_ERROR # Note: This wasn't used in the original fix_error_schema method
)

class CSVLoader:
    """
    Manages loading, processing, schema generation, validation, and error fixing
    for CSV data using pandas and an external LLM service.
    """

    def __init__(self, filepath: str, name: str = ''):
        """
        Initializes the CSVLoader with the path to a CSV file.

        Args:
            filepath: The path to the CSV file.
            name: An optional name for the dataset.
        """
        self.filepath: str = filepath
        self.name: str = name
        self.data: pd.DataFrame = pd.read_csv(filepath)
        self.schema: Dict[str, Any] = {}

    def read_data(self, filepath: str) -> None:
        """
        Reads data from a specified CSV file path, updating the internal DataFrame.

        Args:
            filepath: The path to the CSV file to load.
        """
        self.filepath = filepath
        self.data = pd.read_csv(filepath)
        # Reset schema if data changes? Consider if this is desired behavior.
        # self.schema = {}

    def to_str(self) -> str:
        """Returns the DataFrame content as a CSV formatted string (without index)."""
        return self.data.to_csv(index=False)

    def to_json(self) -> str:
        """Returns the DataFrame content as a JSON formatted string."""
        return self.data.to_json()

    def to_dict(self) -> Dict:
        """Returns the DataFrame content as a dictionary."""
        return self.data.to_dict()

    @property
    def num_rows(self) -> int:
        """Returns the number of rows in the DataFrame."""
        return self.data.shape[0]

    def get_sample_data(self, sample_size: int) -> pd.DataFrame:
        """
        Retrieves a random sample of rows from the DataFrame.

        Args:
            sample_size: The number of rows to include in the sample.

        Returns:
            A DataFrame containing the sampled rows.

        Raises:
            ValueError: If sample_size exceeds the total number of rows.
        """
        if not 0 < sample_size <= self.num_rows:
            raise ValueError(
                f"Sample size {sample_size} must be between 1 and "
                f"{self.num_rows} (inclusive)."
            )
        return self.data.sample(n=sample_size, random_state=42) # Keep random_state for reproducibility

    def get_range_data(self, start_index: int, end_index: int) -> pd.DataFrame:
        """
        Retrieves a slice of the DataFrame based on row index range (exclusive of end_index).

        Args:
            start_index: The starting row index (inclusive).
            end_index: The ending row index (exclusive).

        Returns:
            A DataFrame containing the specified rows.

        Raises:
            ValueError: If the range is invalid or out of bounds.
        """
        if not (0 <= start_index <= end_index <= self.num_rows):
            raise ValueError(
                f"Invalid index range [{start_index}:{end_index}]. "
                f"Must be within [0:{self.num_rows}]."
            )
        return self.data.iloc[start_index:end_index]

    @staticmethod
    def get_column_info(df: pd.DataFrame, unique_threshold: int = 20) -> List[Dict[str, Any]]:
        """
        Generates summary information for each column in the DataFrame.

        Args:
            df: The DataFrame to analyze.
            unique_threshold: The maximum number of unique values to list explicitly.
                              Above this, a sample is shown.

        Returns:
            A list of dictionaries, each describing a column's properties.
        """
        column_summaries = []

        for col_name in df.columns:
            col_series = df[col_name]
            total_count = len(col_series)
            null_count = col_series.isnull().sum()
            unique_count = col_series.nunique()

            summary = {
                'column_name': col_name,
                'dtype': str(col_series.dtype),
                'non_null_count': total_count - null_count,
                'null_count': null_count,
                'null_percentage': round((null_count / total_count) * 100, 2) if total_count > 0 else 0,
                'unique_count': unique_count,
            }

            # Determine type category
            if pd.api.types.is_numeric_dtype(col_series):
                summary['type_category'] = 'numerical'
            elif pd.api.types.is_datetime64_any_dtype(col_series):
                summary['type_category'] = 'datetime'
            elif pd.api.types.is_categorical_dtype(col_series):
                summary['type_category'] = 'categorical'
            elif pd.api.types.is_bool_dtype(col_series):
                summary['type_category'] = 'boolean'
                summary['value_distribution'] = col_series.value_counts().to_dict()
            else:
                summary['type_category'] = 'string/object'

            # Handle unique values display
            non_null_series = col_series.dropna()
            if unique_count <= unique_threshold:
                summary['unique_values'] = non_null_series.unique().tolist()
            else:
                sample_n = min(unique_threshold, unique_count)
                sample_n = min(sample_n, len(non_null_series))
                if sample_n > 0:
                     summary['unique_sample'] = non_null_series.sample(
                         n=sample_n,
                         random_state=42
                     ).tolist()
                else:
                    summary['unique_sample'] = []


            column_summaries.append(summary)

        return column_summaries

    def _invoke_llm_for_json(self, prompt_template: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to invoke the LLM and parse JSON response."""
        message = [('system', SYSTEM_MESSAGE), ('human', prompt_template)]
        chain_message = ChatPromptTemplate.from_messages(message)

        chain = chain_message | base_llm
        chain = chain.bind(response_format="json_object")

        response = chain.invoke(input=input_data)

        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM response is not valid JSON: {e}\nResponse content: {response.content}")
        except AttributeError:
             raise ValueError(f"LLM response object does not have 'content' attribute. Response: {response}")


    def generate_schema(self, context_info: str = '', prompt: str = FIND_JSON_SCHEMA_PROMPTS) -> Dict[str, Any]:
        """
        Generates a JSON schema for the current DataFrame using an LLM.

        Args:
            context_info: Additional textual context to provide to the LLM.
            prompt: The specific prompt template for schema generation.

        Returns:
            The generated JSON schema as a dictionary.

        Raises:
            ValueError: If the LLM response is not valid JSON or lacks the expected structure.
        """
        column_info = self.get_column_info(self.data)
        input_payload = {
            "data": self.to_str(),
            "context": context_info,
            "column_info": json.dumps(column_info, indent=2), # Provide structured info
        }

        content_json = self._invoke_llm_for_json(prompt, input_payload)

        try:

            schema_response = CSVJsonSchemaResponse(**content_json)
            if not isinstance(schema_response.json_schema, dict):
                 raise ValueError("The 'json_schema' field in the response is not a dictionary.")
            return schema_response.json_schema
        except (TypeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid JSON structure received from LLM for schema generation: {e}")


    def set_schema(self, prompt: str = FIND_JSON_SCHEMA_PROMPTS) -> None:
        """Generates and assigns the JSON schema to the instance's schema attribute."""
        self.schema = self.generate_schema(prompt=prompt)

    def _scan_error_for_range(self, schema: Dict[str, Any], row_range: Tuple[int, int]) -> PotentialErrorQueryResponse:
        """
        Invokes LLM to find potential data issues within a specific row range based on a schema.

        Args:
            schema: The JSON schema to validate against.
            row_range: A tuple (start_index, end_index) specifying the rows.

        Returns:
            A PotentialErrorQueryResponse object containing suggested improvements.

        Raises:
            ValueError: If the LLM response is invalid or lacks expected structure.
        """
        start_idx, end_idx = row_range
        range_data = self.get_range_data(start_idx, end_idx)
        input_payload = {
            "schema": json.dumps(schema, indent=2),
            "data": range_data.to_csv(index=False),
        }

        content_json = self._invoke_llm_for_json(GET_ISSUE_OF_DATA, input_payload)

        try:
            error_response = PotentialErrorQueryResponse(**content_json)
            if not isinstance(error_response.improves, list):
                raise ValueError("The 'improves' field in the response is not a list.")
            return error_response
        except (TypeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid JSON structure received from LLM for error scanning: {e}")
        except json.JSONDecodeError:
             print(f"Warning: Returning empty improvements due to JSON decode error during error scan for range {row_range}.")
             return PotentialErrorQueryResponse(improves=[]) # Graceful fallback


    def _adjust_improvement_row_indices(self, batch_start_index: int, items: List[ImprovesItem]) -> List[ImprovesItem]:
        """Adjusts the row index of improvement items relative to the global DataFrame index."""
        for item in items:
            if hasattr(item, 'position') and hasattr(item.position, 'row'):
                 item.position.row += batch_start_index
            if hasattr(item, 'row'):
                item.row += batch_start_index
        return items

    def scan_error(self, schema: Dict[str, Any], batch_size: int = 10) -> List[ImprovesItem]:
        """
        Scans the entire dataset in batches for potential errors using the LLM and a schema.

        Args:
            schema: The JSON schema to validate against.
            batch_size: The number of rows to process in each LLM call.

        Returns:
            A list of all suggested improvement items with corrected row indices.
        """
        all_improvements: List[ImprovesItem] = []
        total_rows = self.num_rows

        for start_index in range(0, total_rows, batch_size):
            end_index = min(start_index + batch_size, total_rows)
            if start_index == end_index: #
                continue

            try:
                batch_response = self._scan_error_for_range(schema, (start_index, end_index))
                adjusted_improvements = self._adjust_improvement_row_indices(
                    start_index, batch_response.improves
                )
                all_improvements.extend(adjusted_improvements)
            except ValueError as e:
                print(f"Warning: Skipping batch {start_index}-{end_index} due to error: {e}")

        return all_improvements

    @staticmethod
    def validate_row(row_data: Dict[str, Any], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validates a single data row (as a dictionary) against a JSON schema.

        Args:
            row_data: The row data to validate.
            schema: The JSON schema.

        Returns:
            A list of validation errors, each a dictionary with 'attribute' and 'message'.
            Returns an empty list if the row is valid.
        """
        validator = Draft202012Validator(schema)
        errors = []
        for error in validator.iter_errors(row_data):
            # Attempt to get the problematic attribute name
            attribute_name = error.path[0] if error.path else "Row Level"
            errors.append({"attribute": attribute_name, "message": error.message})
        return errors

    @classmethod
    def validate_dataset(cls, df: pd.DataFrame, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validates an entire DataFrame against a JSON schema row by row.

        Args:
            df: The DataFrame to validate.
            schema: The JSON schema.

        Returns:
            A list of validation results for rows with errors. Each item contains
            the 'row' index and a list of 'errors'.
        """
        validation_results = []
        for index, row in df.iterrows():

            row_dict = row.map(lambda x: x.item() if hasattr(x, 'item') else x).to_dict()
            errors = cls.validate_row(row_dict, schema)
            if errors:
                validation_results.append({
                    "row": index,
                    "errors": errors
                })
        return validation_results

    @staticmethod
    def _parse_boolean(value: str) -> bool:
        """Helper to parse string representations of booleans."""
        val_lower = value.strip().lower()
        if val_lower in ["true", "1", "yes", "t", "y"]:
            return True
        elif val_lower in ["false", "0", "no", "f", "n"]:
            return False
        else:
            raise ValueError(f"Cannot parse '{value}' as boolean.")

    @staticmethod
    def parse_value(value_str: str, target_type: Any) -> Any:
        """
        Parses a string value into a target type defined by schema or pandas dtype.

        Args:
            value_str: The string value to parse.
            target_type: The target type (e.g., "integer", "string", np.int64, float).

        Returns:
            The parsed value in the target type.

        Raises:
            ValueError: If parsing fails or the target type is unsupported.
        """
        if not isinstance(value_str, str):
             print(f"Warning: parse_value received non-string input '{value_str}' ({type(value_str)}). Attempting to use directly.")
             try:
                 if isinstance(target_type, str):
                     if target_type == "integer" and isinstance(value_str, int): return value_str
                     if target_type == "number" and isinstance(value_str, (int, float)): return float(value_str)
                     if target_type == "boolean" and isinstance(value_str, bool): return value_str
                     if target_type == "string": return str(value_str) # Ensure string if needed
                 elif np.issubdtype(target_type, np.integer) and isinstance(value_str, int): return value_str
                 elif np.issubdtype(target_type, np.floating) and isinstance(value_str, (int, float)): return float(value_str)
                 elif np.issubdtype(target_type, np.bool_) and isinstance(value_str, bool): return value_str
                 elif np.issubdtype(target_type, np.object_) or target_type == object : return value_str # Assume object type can take it
             except Exception:
                 pass # Fall through to parsing logic if direct use fails
             # If direct use doesn't match or fails, convert back to string for parsing attempt
             value_str = str(value_str)


        try:
            if isinstance(target_type, str):
                if target_type == "string":
                    return value_str
                elif target_type == "integer":
                    return int(value_str)
                elif target_type == "number":
                    return float(value_str)
                elif target_type == "boolean":
                    return CSVLoader._parse_boolean(value_str)
                elif target_type == "null":
                     return None
                else:
                    print(f"Warning: Unsupported schema type '{target_type}'. Returning as string.")
                    return value_str
            else:
                # Pandas dtype objects
                dtype = target_type
                if pd.api.types.is_integer_dtype(dtype):
                    return int(value_str)
                elif pd.api.types.is_float_dtype(dtype):
                    return float(value_str)
                elif pd.api.types.is_bool_dtype(dtype):
                    return CSVLoader._parse_boolean(value_str)
                elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
                     # Includes object, string, potentially others handled as strings
                    return value_str
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    return pd.to_datetime(value_str)
                elif pd.api.types.is_categorical_dtype(dtype):
                    # Returning the string value; category management is complex here.
                    # The DataFrame column should already be categorical if this dtype is inferred.
                    return value_str
                else:
                     print(f"Warning: Unsupported pandas dtype '{dtype}'. Returning as string.")
                     return value_str # Fallback for other dtypes

        except (ValueError, TypeError) as e:
            # Re-raise with more context
            raise ValueError(
                f"Failed to parse '{value_str}' into type '{target_type}'. Original error: {e}"
            ) from e


    def apply_improvements(self, improvements: List[ImprovesItem]) -> pd.DataFrame:
        """
        Applies suggested fixes from a list of improvement items to the DataFrame.

        Modifies the internal `self.data` DataFrame in place.

        Args:
            improvements: A list of `ImprovesItem` objects detailing the fixes.

        Returns:
            The modified DataFrame (`self.data`).

        Raises:
            ValueError: If an improvement targets an invalid row/column or
                        if a value cannot be parsed correctly for the target type.
            IndexError: If an improvement targets an invalid row index.
        """
        df_copy = self.data # Operate directly on the internal DataFrame

        for item in improvements:
            row_idx = getattr(item, 'row', getattr(getattr(item, 'position', None), 'row', None))
            if row_idx is None:
                print(f"Warning: Skipping improvement item - missing row index: {item}")
                continue

            try:
                row_idx = int(row_idx) # Ensure integer index
            except (ValueError, TypeError):
                 print(f"Warning: Skipping improvement item - invalid row index '{row_idx}': {item}")
                 continue

            if not (0 <= row_idx < self.num_rows):
                # Log or handle out-of-bounds rows gracefully if needed
                print(f"Warning: Skipping improvement for out-of-bounds row index {row_idx}.")
                continue

            for cell_fix in item.attribute: # Assuming attribute is a list of cell fixes
                col_name = cell_fix.name
                new_value_str = cell_fix.fixed_value # Assume this is string-like

                if col_name not in df_copy.columns:
                     print(f"Warning: Skipping fix for unknown column '{col_name}' at row {row_idx}.")
                     continue

                # Determine the target type for parsing
                target_type: Any
                if self.schema and 'properties' in self.schema and col_name in self.schema['properties']:
                    # Prefer schema type if available
                    target_type = self.schema['properties'][col_name].get('type', df_copy[col_name].dtype)
                    # Handle cases where schema might list multiple types (e.g., ["string", "null"])
                    if isinstance(target_type, list):
                        # Simple approach: prefer non-null type if available, otherwise first type
                        target_type = next((t for t in target_type if t != "null"), target_type[0])
                else:
                    target_type = df_copy[col_name].dtype

                try:
                    parsed_value = self.parse_value(new_value_str, target_type)
                    df_copy.loc[row_idx, col_name] = parsed_value
                except (ValueError, TypeError) as e:
                    print(f"Warning: Skipping fix for row {row_idx}, column '{col_name}'. "
                          f"Could not apply value '{new_value_str}'. Error: {e}")
                except Exception as e:
                     print(f"Warning: Unexpected error applying fix for row {row_idx}, col '{col_name}': {e}")


        self.data = df_copy # Update the instance data
        return self.data

    def _fix_errors_for_batch(self, schema: Dict[str, Any], batch_df: pd.DataFrame) -> List[ImprovesItem]:
        """
        Internal method to call the LLM for fixing errors in a specific batch DataFrame.

        Args:
            schema: The JSON schema.
            batch_df: The DataFrame slice representing the batch.

        Returns:
            A list of suggested improvement items for this batch. Returns empty list on error.
        """
        input_payload = {
            "schema": json.dumps(schema, indent=2),
            "data": batch_df.to_csv(index=False),
        }

        prompt_to_use = GET_ISSUE_OF_DATA # As used in original code

        try:
            content_json = self._invoke_llm_for_json(prompt_to_use, input_payload)

            response = PotentialErrorQueryResponse(**content_json)
            if not isinstance(response.improves, list):
                 print("Warning: LLM response for fixing batch has 'improves' field but it's not a list.")
                 return []
            return response.improves
        except (ValueError, TypeError, KeyError) as e:

            print(f"Warning: Failed to process batch for error fixing. Error: {e}")
            return []


    def fix_error_schema(self, schema: Dict[str, Any], batch_size: int = 20) -> List[ImprovesItem]:
        """
        Uses an LLM to identify and suggest fixes for data inconsistencies based on a schema,
        processing the data in parallel batches.

        Note: This method currently *identifies* potential fixes using the LLM.
              It returns the suggestions. Use `apply_improvements` to apply them.
              It uses the GET_ISSUE_OF_DATA prompt by default based on the original code,
              consider if FIX_JSON_SCHEMA_ERROR prompt is more suitable.

        Args:
            schema: The JSON schema to check against.
            batch_size: The number of rows per parallel processing batch.

        Returns:
            A list of `ImprovesItem` objects suggesting fixes across the dataset.
        """
        all_suggested_fixes: List[ImprovesItem] = []
        total_rows = self.num_rows


        batch_args = []
        for start_index in range(0, total_rows, batch_size):
            end_index = min(start_index + batch_size, total_rows)
            if start_index == end_index: continue
            batch_df = self.get_range_data(start_index, end_index)
            batch_args.append((schema, batch_df, start_index))

        def process_batch(args):
            batch_schema, df_batch, start_idx = args
            print(f"Processing batch for fixing: Rows {start_idx} to {start_idx + len(df_batch)}")
            items = self._fix_errors_for_batch(batch_schema, df_batch)
            corrected_items = self._adjust_improvement_row_indices(start_idx, items)
            return corrected_items

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_batch, batch_args))

        for batch_result in results:
            all_suggested_fixes.extend(batch_result)

        return all_suggested_fixes
