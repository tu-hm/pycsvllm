import string

import pandas as pd
import random
from decimal import Decimal
from typing import Callable, List

from num2words import num2words
from datetime import datetime


def _plain(n: float) -> str:                 # 1234.56
    return f"{n}"


def _commas(n: float) -> str:                # 1,234
    return f"{int(round(n)):,}"


def _scientific(n: float) -> str:            # 1.23e+03
    return f"{n:.2e}"


def _words(n: float) -> str:                 # one thousand two hundred…
    return num2words(int(round(n)))


def _eu_decimal(n: float) -> str:            # 1 234,560
    return f"{n:.3f}".replace(".", ",")


_FORMATTERS: List[Callable[[float], str]] = [
    _plain,
    _commas,
    _scientific,
    _words,
    _eu_decimal,
]


def format_number_random(value):
    """
    Format *value* using a randomly chosen numeric style.

    • Accepts int, float, or numeric string.
    • Non-numeric input is returned unchanged.
    • Never converts to str until **after** a formatter is chosen.
    """
    # --- keep it numeric ----------------------------------------------------
    try:
        num = float(value)
    except (TypeError, ValueError):
        return value                      # give back strings like "abc"

    # --- choose only formatters that can handle *num* -----------------------
    candidates = []
    for fmt in _FORMATTERS:
        try:
            fmt(num)                      # dry-run
            candidates.append(fmt)
        except Exception:
            pass

    if not candidates:                    # extremely unlikely
        return str(value)

    return random.choice(candidates)(num)

def mess_up_datetime_format_unknown_input(date_str):
    known_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%m-%d-%Y %I:%M %p",
        "%Y.%m.%d %H:%M",
        "%d %b %Y %H:%M:%S",
        "%Y%m%dT%H%M%S",
        "%b %d %Y %I:%M%p",
        "%d-%m-%y",
        "%I:%M:%S %p, %d/%m/%y",
        "%Y/%m/%d %H:%M:%S"
    ]

    output_formats = [
        "%d/%m/%Y",
        "%m-%d-%Y %I:%M %p",
        "%Y.%m.%d %H:%M",
        "%A, %B %d, %Y",
        "%d %b %Y %H:%M:%S",
        "%Y%m%dT%H%M%S",
        "%b %d %Y %I:%M%p",
        "%d-%m-%y",
        "%I:%M:%S %p, %d/%m/%y",
        "%Y/%m/%d %H:%M:%S"
    ]

    dt = None
    for fmt in known_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if dt is None:
        raise ValueError("Unknown datetime format: " + date_str)

    return dt.strftime(random.choice(output_formats))

def mess_up_string(s, noise_level=0.3):
    messy = []
    whitespace = [' ', '\t', '\n']
    all_chars = string.ascii_letters + string.digits + string.punctuation
    for char in s:
        if random.random() < noise_level:
            char = char.upper() if char.islower() else char.lower()
        messy.append(char)
        if random.random() < noise_level:
            messy.append(random.choice(whitespace))
        if random.random() < noise_level:
            messy.append(random.choice(all_chars))

    return ''.join(messy)

def make_messy_data_number(
    df: pd.DataFrame,
    columns: List[str],
) -> pd.DataFrame:
    df_out = df.copy(deep=True)

    for col in columns:
        if col not in df_out.columns:
            raise KeyError(f"Column '{col}' not found in DataFrame")

        # Apply only to non-null entries; leave NaN/None untouched
        df_out[col] = df_out[col].apply(
            lambda x: format_number_random(x) if pd.notna(x) else x
        )

    return df_out

def make_messy_data_string(df: pd.DataFrame, column: list[str]) -> pd.DataFrame:
    for col in column:
        for i in range(df.shape[0]):
            df.loc[i, col] = mess_up_string(df.loc[i, col])
    return df


        
