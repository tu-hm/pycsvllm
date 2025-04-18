import pandas as pd
from typing import Dict, Any


def benchmark_data_cleaning(
        clean_path: str,
        messy_path: str,
        cleaned_path: str,
        id_column: str = None
) -> Dict[str, Any]:
    """
    Compare datasets to calculate data cleaning effectiveness

    Args:
        clean_path: Path to original clean CSV
        messy_path: Path to messy CSV
        cleaned_path: Path to cleaned CSV
        id_column: Optional name of ID column for row matching

    Returns:
        Dictionary with cleaning metrics and detailed statistics
    """
    clean_df = pd.read_csv(clean_path)
    messy_df = pd.read_csv(messy_path)
    cleaned_df = pd.read_csv(cleaned_path)

    if not clean_df.columns.equals(messy_df.columns) or not clean_df.columns.equals(cleaned_df.columns):
        raise ValueError("All datasets must have identical columns")

    if id_column:
        for df in [messy_df, cleaned_df]:
            if not clean_df[id_column].equals(df[id_column]):
                raise ValueError(f"ID column {id_column} mismatch between datasets")

    metrics = {
        'total_errors': 0,
        'corrected_errors': 0,
        'introduced_errors': 0,
        'remaining_errors': 0,
        'columns': {}
    }

    import re

    def is_equal(a, b):
        """
        Compare two values for equality, coercing between str, int/float, and bool when possible.
        Returns True if values are equivalent after coercion, False otherwise.
        """

        def try_bool(x):
            if isinstance(x, bool):
                return x
            if not isinstance(x, str):
                return None
            val = x.strip().lower()
            if val in ('true', '1', 'yes', 'y', 't'):
                return True
            if val in ('false', '0', 'no', 'n', 'f'):
                return False
            return None

        def try_number(x):
            # ints and floats stay as-is
            if isinstance(x, (int, float)) and not isinstance(x, bool):
                return x
            if not isinstance(x, str):
                return None
            x = x.strip()
            # integer?
            if re.fullmatch(r'[+-]?\d+', x):
                try:
                    return int(x)
                except ValueError:
                    pass
            # float?
            if re.fullmatch(r'[+-]?(\d*\.\d+|\d+\.\d*)([eE][+-]?\d+)?', x):
                try:
                    return float(x)
                except ValueError:
                    pass
            return None

        # 1) Try boolean comparison
        bool_a = try_bool(a)
        bool_b = try_bool(b)
        if bool_a is not None and bool_b is not None:
            return bool_a == bool_b

        # 2) Try numeric comparison
        num_a = try_number(a)
        num_b = try_number(b)
        if num_a is not None and num_b is not None:
            return num_a == num_b

        # 3) Fallback: compare as strings
        # Coerce everything to str and compare
        return str(a) == str(b)

    for col in clean_df.columns:
        col_metrics = {
            'dtype_match': cleaned_df[col].dtype == clean_df[col].dtype,
            'total_cells': len(clean_df),
            'original_errors': 0,
            'corrected': 0,
            'remaining': 0,
            'new_errors': 0
        }

        for idx in range(len(clean_df)):
            # Get values from all datasets
            clean_val = clean_df[col].iloc[idx]
            messy_val = messy_df[col].iloc[idx]
            cleaned_val = cleaned_df[col].iloc[idx]

            # Original error detection
            original_error = not is_equal(messy_val, clean_val)
            if original_error:
                metrics['total_errors'] += 1
                col_metrics['original_errors'] += 1

                # Check if error was fixed
                if is_equal(cleaned_val, clean_val):
                    metrics['corrected_errors'] += 1
                    col_metrics['corrected'] += 1
                else:
                    metrics['remaining_errors'] += 1
                    col_metrics['remaining'] += 1

            # Check for new errors introduced
            elif not is_equal(cleaned_val, clean_val):
                metrics['introduced_errors'] += 1
                col_metrics['new_errors'] += 1

        metrics['columns'][col] = col_metrics

    metrics['correction_rate'] = (
            metrics['corrected_errors'] / metrics['total_errors'] * 100
    ) if metrics['total_errors'] > 0 else 100.0

    metrics['error_introduction_rate'] = (
            metrics['introduced_errors'] / (len(clean_df) * len(clean_df.columns)) * 100
    )

    return metrics
