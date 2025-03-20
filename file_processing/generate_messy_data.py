import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas.api.types as pd_types


def create_messy_dataset(
        input_filepath: str,
        output_filepath: str,
        change_percent: float = 0.04,
        **kwargs
) -> None:
    """
    Creates a messy dataset with controlled randomness and percentage of changes

    Args:
        input_filepath: Path to clean input CSV file
        output_filepath: Path to save messy output CSV file
        change_percent: Percentage of total cells to make messy (0-1)
        **kwargs: Additional arguments for pd.read_csv
    """
    clean_df = pd.read_csv(input_filepath, **kwargs)
    messy_df, change_log = make_dataset_messy(clean_df, change_percent)

    output_path = Path(output_filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    messy_df.to_csv(output_path, index=False)

    log_path = output_path.with_name(output_path.stem + "_CHANGELOG.csv")
    pd.DataFrame(change_log).to_csv(log_path, index=False)

    print(f"Messy dataset saved to {output_path}")
    print(f"Change log saved to {log_path}")


def make_dataset_messy(
        df: pd.DataFrame,
        change_percent: float
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    messy_df = df.copy()
    change_log = []
    rows, cols = messy_df.shape
    total_cells = rows * cols
    target_changes = int(total_cells * change_percent)

    # Generate and shuffle all possible cell indices
    cell_indices = [(r, c) for r in range(rows) for c in range(cols)]
    random.shuffle(cell_indices)

    # Define modifiers for different data types
    modifiers = {
        'numeric': [
            ('scale_value', lambda x: x * random.choice([0.1, 10])),
            ('add_noise', lambda x: x + random.uniform(-0.1, 0.1) * x),
            ('round_value', lambda x: round(x, random.randint(0, 3))),
            ('stringify', lambda x: f"{x}{random.choice(['', '%', ' units'])}")
        ],
        'string': [
            ('introduce_typo', lambda x: introduce_typos(x)),
            ('whitespace', lambda x: f"{' ' * random.randint(0, 2)}{x}{' ' * random.randint(0, 2)}"),
            ('change_case', lambda x: random.choice([x.upper(), x.lower(), x.title()])),
            ('truncate', lambda x: x[:random.randint(max(1, len(x) - 3), len(x))])
        ],
        'datetime': [
            ('shift_date', lambda x: x + timedelta(days=random.randint(-30, 30))),
            ('format_date', lambda x: x.strftime(random.choice([
                "%m/%d/%Y", "%d-%m-%Y", "%Y%m%d", "%b %d, %Y"
            ]))),
            ('corrupt_date', lambda x: x.replace(year=random.choice([x.year + 1, 9999])))
        ]
    }

    changed = 0
    for row_idx, col_idx in cell_indices:
        if changed >= target_changes:
            break

        col_name = messy_df.columns[col_idx]
        original = messy_df.iat[row_idx, col_idx]

        if pd.isna(original):
            continue

        dtype_category = get_dtype_category(messy_df[col_name].dtype, original)
        applicable_modifiers = modifiers.get(dtype_category, [])

        if not applicable_modifiers:
            continue

        mod_name, modifier = random.choice(applicable_modifiers)

        try:
            modified = modifier(original)
            if modified == original:
                continue
        except:
            continue

        messy_df.iat[row_idx, col_idx] = modified
        change_log.append({
            'row': row_idx + 1,  # Use 1-based indexing for user-friendliness
            'column': col_name,
            'original_value': original,
            'modified_value': modified,
            'error_type': mod_name,
            'data_type': dtype_category.upper(),
            'dtype': str(messy_df[col_name].dtype)
        })
        changed += 1

    return messy_df, change_log


def get_dtype_category(dtype: Any, value: Any) -> str:
    """Categorize data types for modifier selection"""
    if pd_types.is_numeric_dtype(dtype):
        return 'numeric'
    if pd_types.is_datetime64_any_dtype(dtype) or isinstance(value, (datetime, pd.Timestamp)):
        return 'datetime'
    if pd_types.is_string_dtype(dtype) or isinstance(value, str):
        return 'string'
    return 'other'


def introduce_typos(s: str) -> str:
    """Introduce realistic typos in string"""
    if len(s) < 1:
        return s

    typo_prob = 0.3
    chars = list(s)
    keyboard_adj = {
        'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'erfcxs',
        'e': 'rswd', 'f': 'rtgvcd', 'g': 'tyhbvf', 'h': 'yujnbg',
        'i': 'ujko', 'j': 'uikmnh', 'k': 'iolmj', 'l': 'opk',
        'm': 'njk', 'n': 'bhjm', 'o': 'iklp', 'p': 'ol',
        'q': 'wa', 'r': 'edft', 's': 'wedxza', 't': 'rfgy',
        'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
        'y': 'tghj', 'z': 'asx'
    }

    for i in range(len(chars)):
        if random.random() < typo_prob and chars[i].lower() in keyboard_adj:
            adj_chars = keyboard_adj[chars[i].lower()]
            chars[i] = random.choice(adj_chars).upper() if chars[i].isupper() else random.choice(adj_chars)

    return ''.join(chars)
