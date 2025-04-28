import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd
from jsonschema.validators import Draft202012Validator
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from thefuzz import fuzz

from src.file_processing.regex import correct_to_pattern
from src.file_processing.schema import (
    CSVJsonSchemaResponse,
    PotentialErrorQueryResponse,
    ImprovesItem, NotImprovesItem
)
from src.llm_providers import base_llm
from src.llm_providers.prompts import (
    FIND_JSON_SCHEMA_PROMPTS,
    SYSTEM_MESSAGE,
    GET_ISSUE_OF_DATA,
    GET_DIRTY_DATA_ISSUE  # Note: This wasn't used in the original fix_error_schema method
)
from src.llm_providers.prompts_fix_data import PROMPT_FIX_NUMBER_FORMATION, PROMPT_FIX_DATETIME_FORMATION, \
    FIX_GRAMMAR_PROMPTS


class CSVLoader:
    def __init__(self, filepath: str, name: str = '', model: BaseChatModel = base_llm):
        self.filepath: str = filepath
        self.name: str = name
        self.data: pd.DataFrame = pd.read_csv(filepath)
        self.schema: Dict[str, Any] = {}
        self.model: BaseChatModel = model
        self.list_improvements: List[ImprovesItem] = []

    def read_data(self, filepath: str) -> None:
        self.filepath = filepath
        self.data = pd.read_csv(filepath)
        self.schema = {}

    def to_str(self) -> str:
        return self.data.to_csv(index=False)

    def to_json(self) -> str:
        return self.data.to_json()

    def to_dict(self) -> Dict:
        return self.data.to_dict()

    def filter_with_column_names(self, column_names: List[str]) -> pd.DataFrame:
        return self.data[column_names]

    @property
    def num_rows(self) -> int:
        return self.data.shape[0]

    def get_sample_data(self, sample_size: int) -> pd.DataFrame:
        sample_size = min(sample_size, self.data.num_rows)
        return self.data.sample(n=sample_size, random_state=42) # Keep random_state for reproducibility

    def get_range_data(self, start_index: int, end_index: int) -> pd.DataFrame:
        if not (0 <= start_index <= end_index <= self.num_rows):
            raise ValueError(
                f"Invalid index range [{start_index}:{end_index}]. "
                f"Must be within [0:{self.num_rows}]."
            )
        return self.data.iloc[start_index:end_index]

    @staticmethod
    def get_column_info(df: pd.DataFrame, unique_threshold: int = 20) -> List[Dict[str, Any]]:
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
        message = [('system', SYSTEM_MESSAGE), ('human', prompt_template)]
        chain_message = ChatPromptTemplate.from_messages(message)
        chain = chain_message | self.model
        chain = chain.bind(response_format="json_object")
        response = chain.invoke(input=input_data)

        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM response is not valid JSON: {e}\nResponse content: {response.content}")
        except AttributeError:
             raise ValueError(f"LLM response object does not have 'content' attribute. Response: {response}")


    def valid_column_info(self, column_info: Dict[str, Any]) -> bool:
        list_column = self.data.columns.to_list()
        for key in column_info:
            if key not in list_column:
                return False
        return True

    def _get_representative_sample(
        self,
        sample_size: int = 50,
        per_column_quota: int = 2,
        null_fraction: float = 0.30,
        random_state: int | None = None
    ) -> pd.DataFrame:
        rng = np.random.default_rng(random_state)
        df = self.data
        selected: set[int] = set()

        for col in df.columns:
            null_idx = df.index[df[col].isna()]
            non_idx = df.index[df[col].notna()]
            if len(null_idx):
                selected.update(rng.choice(null_idx, min(per_column_quota, len(null_idx)), replace=False))
            if len(non_idx):
                selected.update(rng.choice(non_idx, min(per_column_quota, len(non_idx)), replace=False))

        null_rows = df.index[df.isna().any(axis=1)]
        non_rows = df.index.difference(null_rows)
        need_null = min(int(sample_size * null_fraction), len(null_rows))
        need_non = min(sample_size - need_null, len(non_rows))
        selected.update(rng.choice(null_rows, need_null, replace=False))
        selected.update(rng.choice(non_rows, need_non, replace=False))

        selected = list(selected)
        if len(selected) > sample_size:
            selected = rng.choice(selected, sample_size, replace=False)
        elif len(selected) < sample_size:
            remaining = df.index.difference(selected)
            extra = rng.choice(remaining, sample_size - len(selected), replace=False)
            selected = np.concatenate([selected, extra])

        return df.loc[selected].sample(frac=1, random_state=random_state)

    def generate_schema(
            self,
            reference_data: pd.DataFrame = pd.DataFrame(),
            other_column_info: dict[str, Any] = {},
            sample_size: int = 50
        ) -> CSVJsonSchemaResponse:
        if not self.valid_column_info(other_column_info):
            raise ValueError("The 'other_column_info' parameter must not contain column names that are not in the reference data.")

        sample_data = self._get_representative_sample(sample_size)

        input_payload = {
            "data": sample_data.to_csv(index=True),
            "ref_data": reference_data.to_json(),
            "column_info": str(other_column_info), # Provide structured info
        }

        prompt = FIND_JSON_SCHEMA_PROMPTS
        content_json = self._invoke_llm_for_json(prompt, input_payload)

        try:

            schema_response = CSVJsonSchemaResponse(**content_json)
            return schema_response
        except (TypeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid JSON structure received from LLM for schema generation: {e}")


    def set_schema(self, schema) -> None:
        """Generates and assigns the JSON schema to the instance's schema attribute."""
        self.schema = schema

    def _scan_error_for_range(
            self,
            schema: Dict[str, Any],
            row_range: Tuple[int, int],
            prompt: str = GET_ISSUE_OF_DATA,
            other_context: str = ''
    ) -> PotentialErrorQueryResponse:
        start_idx, end_idx = row_range
        range_data = self.get_range_data(start_idx, end_idx)
        input_payload = {
            "schema": json.dumps(schema, indent=2),
            "data": range_data.to_csv(index=False),
            "context": other_context,
        }

        content_json = self._invoke_llm_for_json(prompt, input_payload)

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

    def scan_error(self, schema: Dict[str, Any], batch_size: int = 10, prompt: str = GET_ISSUE_OF_DATA, other_context: str = '') -> List[ImprovesItem]:
        all_improvements: List[ImprovesItem] = []
        total_rows = self.num_rows

        for start_index in range(0, total_rows, batch_size):
            end_index = min(start_index + batch_size, total_rows)
            if start_index == end_index: #
                continue

            try:
                batch_response = self._scan_error_for_range(schema=schema, row_range=(start_index, end_index), prompt=prompt, other_context=other_context)
                all_improvements.extend(batch_response.improves)
            except ValueError as e:
                print(f"Warning: Skipping batch {start_index}-{end_index} due to error: {e}")

        return all_improvements

    @staticmethod
    def validate_row(row_data: Dict[str, Any], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        validator = Draft202012Validator(schema)
        errors = []
        for error in validator.iter_errors(row_data):
            attribute_name = error.path[0] if error.path else "Row Level"
            errors.append({"attribute": attribute_name, "message": error.message})
        return errors

    @classmethod
    def validate_dataset(cls, df: pd.DataFrame, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
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
    def parse_value(value_str: Any, target_type: Any) -> Any:
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
                 pass
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
                    return value_str
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    return pd.to_datetime(value_str)
                elif pd.api.types.is_categorical_dtype(dtype):
                    return value_str
                else:
                     print(f"Warning: Unsupported pandas dtype '{dtype}'. Returning as string.")
                     return value_str

        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Failed to parse '{value_str}' into type '{target_type}'. Original error: {e}"
            ) from e


    def apply_improvements(self, improvements: List[ImprovesItem]) -> pd.DataFrame:
        df_copy = self.data # Operate directly on the internal DataFrame

        for item in improvements:
            row_idx = getattr(item, 'row', getattr(getattr(item, 'position', None), 'row', None))
            if row_idx is None:
                print(f"Warning: Skipping improvement item - missing row index: {item}")
                continue

            try:
                row_idx = int(row_idx)
            except (ValueError, TypeError):
                 print(f"Warning: Skipping improvement item - invalid row index '{row_idx}': {item}")
                 continue

            if not (0 <= row_idx < self.num_rows):
                print(f"Warning: Skipping improvement for out-of-bounds row index {row_idx}.")
                continue

            for cell_fix in item.attr:
                col_name = cell_fix.name
                new_value_str = cell_fix.value

                if col_name not in df_copy.columns:
                     print(f"Warning: Skipping fix for unknown column '{col_name}' at row {row_idx}.")
                     continue

                # Determine the target type for parsing
                target_type: Any
                if self.schema and 'properties' in self.schema and col_name in self.schema['properties']:
                    # Prefer schema type if available
                    target_type = self.schema['properties'][col_name].get('type', df_copy[col_name].dtype)
                    if isinstance(target_type, list):
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


        self.data = df_copy
        return self.data

    def _fix_errors_for_batch(self, schema: Dict[str, Any], batch_df: pd.DataFrame, prompt: str = GET_DIRTY_DATA_ISSUE, other_context: str = '') -> List[ImprovesItem]:
        input_payload = {
            "schema": json.dumps(schema, indent=2),
            "data": batch_df.to_csv(index=False),
            "context": other_context,
        }

        prompt_to_use =  prompt

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

    @staticmethod
    def extract_column_schema(full_schema: dict, columns_to_extract):
        extracted_schema = {
            "type": "object",
            "properties": {}
        }

        full_properties = full_schema.get('properties', {})

        for column_name in columns_to_extract:
            if column_name in full_properties:
                extracted_schema["properties"][column_name] = full_properties[column_name]

        if 'required' in full_schema and isinstance(full_schema['required'], list):
            extracted_required = [
                col for col in full_schema['required']
                if col in extracted_schema["properties"]
            ]
            if extracted_required:
                extracted_schema['required'] = extracted_required

        return extracted_schema

    def _fix_error_with_prompt(
            self,
            df: pd.DataFrame,
            schema: Dict[str, Any],
            formation: List[Tuple[str, str]] = None,
            few_shot_context: List[Tuple[str, str]] = None,
            prompt: str = PROMPT_FIX_NUMBER_FORMATION,
        ) -> PotentialErrorQueryResponse:
        formation_str = str(formation)
        few_shot_context = str(few_shot_context)

        input_payload = {
            "data": df.to_csv(index=True),
            "schema": schema,
            "format_list": formation_str,
            "context": few_shot_context,
        }

        try:
            content = self._invoke_llm_for_json(prompt, input_payload)
            response = PotentialErrorQueryResponse(**content)
            return response
        except (ValueError, TypeError, KeyError) as e:
            raise ValueError(f"Failed to process batch for error fixing. Error: {e}")

    def _fix_error(
            self,
            column_list: list[str] | None = None,
            batch_size: int = 50,
            prompt: str = PROMPT_FIX_NUMBER_FORMATION,
            formation: List[Tuple[str, str]] | None = None,
            few_shot_context: List[Tuple[str, str]] | None = None,
    ) -> Tuple[List[ImprovesItem], List[NotImprovesItem]]:
        """
        Run the LLM fixer on the selected columns, batch the calls,
        and **wait for every batch to finish** before returning.
        """
        # ------------- setup -------------
        if not column_list:
            column_list = self.data.columns.tolist()

        schema_str = str(self.extract_column_schema(self.schema, column_list))
        total_rows = self.num_rows
        data_subset = self.data[column_list]

        # Build argument list first (important if num_rows changes later)
        batch_args: list[tuple[pd.DataFrame, int]] = []
        for start in range(0, total_rows, batch_size):
            end = min(start + batch_size, total_rows)
            if start == end:
                continue
            batch_df = data_subset.iloc[start:end]
            batch_args.append((batch_df, start))

        # ------------- worker -------------
        def _process_batch(batch_df: pd.DataFrame, batch_start: int):
            """Call the LLM once for this batch and shift indices."""
            resp = self._fix_error_with_prompt(
                batch_df,
                schema=schema_str,
                formation=formation,
                few_shot_context=few_shot_context,
                prompt=prompt,
            )
            return resp.improves, resp.error

        # ------------- execute in parallel -------------
        improvements: list[ImprovesItem] = []
        cant_improvements: list[NotImprovesItem] = []

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_process_batch, df, start) for df, start in batch_args]
            for fut in as_completed(futures):
                try:
                    ok, ko = fut.result()
                    improvements.extend(ok)
                    cant_improvements.extend(ko)
                except Exception as exc:
                    print(f"⚠️  A batch failed but was skipped: {exc}")
        return improvements, cant_improvements

    def fix_number_error(self, column_list: list[str], batch_size: int = 50, formation: List[Tuple[str, str]] = None, few_shot_context: List[Tuple[str, str]] = None):
        improvements, cant_improvements = self._fix_error(column_list, batch_size, PROMPT_FIX_NUMBER_FORMATION, formation, few_shot_context)
        return improvements, cant_improvements

    def fix_datetime_error(self, column_list: list[str], batch_size: int = 50, formation: List[Tuple[str, str]] = None, few_shot_context: List[Tuple[str, str]] = None):
        improvements, cant_improvements = self._fix_error(column_list, batch_size, PROMPT_FIX_DATETIME_FORMATION, formation, few_shot_context)
        return improvements, cant_improvements

    def fix_regex_pattern_error(self, column: str, pattern: str = ''):
        if pattern == '':
            pattern = self.schema['properties'][column]['pattern']

        improvements = []
        cant_improvements = []

        for i in range(self.num_rows):
            improvements.append(ImprovesItem(
                row=i,
                attr=[{
                        "name": column,
                        "value" : correct_to_pattern(pattern,  self.data.loc[i, column])}]
                ))

        return improvements, cant_improvements

    def fix_reference_value_error(self, column: str, reference_values: list[str]):
        improvements = []
        cant_improvements = []

        for i in range(self.num_rows):
            best_value = ''
            best_ratio = 0
            for ref_value in reference_values:
                ratio = fuzz.ratio(self.data.loc[i, column], ref_value)
                if ratio > best_ratio and ratio >= 50:
                    best_ratio = ratio
                    best_value = ref_value

            if best_ratio > 0:
                improvements.append(ImprovesItem(
                    row=i,
                    attr=[{
                        "name": column,
                        "value" : best_value}]
                    ))
            else:
                cant_improvements.append(NotImprovesItem(
                    row=i,
                    attr=[column]
                ))

        return improvements, cant_improvements

    def _fix_typography_data_segment(self, segment_data: pd.DataFrame, few_shot_context: List[Tuple[str, str]]):
        input_payload = {
            "data": segment_data.to_csv(index=True),
            "context": str(few_shot_context),
        }

        try:
            content = self._invoke_llm_for_json(FIX_GRAMMAR_PROMPTS, input_payload)
            response = PotentialErrorQueryResponse(**content)
            return response
        except (ValueError, TypeError, KeyError) as e:
            raise ValueError(f"Failed to process batch for error fixing. Error: {e}")

    def fix_typography_data(self, column_list: List[str], few_shot_context: List[Tuple[str, str]] = None, batch_size: int = 50):
        improvements = []
        cant_improvements = []

        if column_list is None or len(column_list) == 0:
            column_list = self.data.columns.tolist()

        for start_index in range(0, self.num_rows, batch_size):
            end_index = min(start_index + batch_size, self.num_rows)
            segment_data = self.data[column_list].iloc[start_index:end_index]
            response = self._fix_typography_data_segment(segment_data, few_shot_context)
            if response:
                improvements.extend(response.improves)
                cant_improvements.extend(response.error)

        return improvements, cant_improvements



