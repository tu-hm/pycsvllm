import string

import pandas as pd
import random
from typing import Callable, List, Iterable, Dict, Tuple
from dateutil import parser as _dateutil_parser

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
    # _eu_decimal,
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


KNOWN_INPUT_FORMATS = [
    "%Y-%m-%d",
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

DEFAULT_OUTPUT_FORMATS = [
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

def _extra_format_variants(dt: datetime) -> list[str]:
    sep = random.choice(["/", "-", ".", " "])
    v1 = dt.strftime(f"%-d{sep}%-m{sep}%y")
    v2 = dt.strftime(f"%m{sep}%d{sep}%y, %H:%M")
    v3 = dt.strftime("%Y-%m-%dT%I:%M %p").replace(" ", "")
    v4 = dt.strftime("%B %-d") + dt.strftime("%d").zfill(2)[-2:].translate(str.maketrans("0123", "tsnr")) + dt.strftime(" ’%y")
    return [v1, v2, v3, v4]

def mess_up_datetime_format(date_str: str,
                            output_formats: list[str] | None = None,
                            add_extra_variants: bool = True) -> str:
    dt = None
    for fmt in KNOWN_INPUT_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        if _dateutil_parser is None:
            raise ValueError(f"Unknown datetime format and python-dateutil not available: {date_str}")
        dt = _dateutil_parser.parse(date_str, fuzzy=True)
    formats_pool = list(output_formats or DEFAULT_OUTPUT_FORMATS)
    if add_extra_variants:
        formats_pool.extend(_extra_format_variants(dt))
    return dt.strftime(random.choice(formats_pool))

RAW_CONFUSIONS: Dict[str, List[Tuple[str, int]]] = {
    "0": [("O", 1), ("D", 2), ("Q", 3)],
    "1": [("I", 1), ("L", 1), ("7", 2), ("T", 3)],
    "2": [("Z", 1)],
    "3": [("E", 2)],
    "4": [("A", 2)],
    "5": [("S", 1)],
    "6": [("G", 2), ("9", 3)],
    "7": [("1", 2), ("T", 2)],
    "8": [("B", 1)],
    "9": [("G", 2), ("Q", 2)],
    "O": [("0", 1), ("D", 2), ("Q", 2)],
    "D": [("0", 2), ("O", 2)],
    "Q": [("0", 2), ("O", 2), ("9", 2)],
    "I": [("1", 1), ("L", 1)],
    "L": [("1", 1), ("I", 1)],
    "Z": [("2", 1)],
    "S": [("5", 1)],
    "B": [("8", 1)],
    "E": [("3", 2), ("F", 3)],
    "G": [("6", 2), ("9", 2)],
    "T": [("7", 2), ("1", 3)],
    "C": [("G", 3), ("O", 3)],
    "F": [("E", 3)],
    "M": [("N", 3)],
    "N": [("M", 3)],
}


def mess_up_string(
    text: str,
    operations: Iterable[str] = ("append", "delete", "replace"),
    alphabet: str = string.ascii_letters + string.digits,
    max_append: int = 1,
    rng: random.Random | None = None,
    confusion_map: Dict[str, List[Tuple[str, int]]] | None = RAW_CONFUSIONS,
) -> str:
    if rng is None:
        rng = random
    if confusion_map is None:
        confusion_map = RAW_CONFUSIONS
    if not text:
        return text

    op = rng.choice(tuple(operations))

    if op == "append":
        n = rng.randint(1, max_append)
        extra = "".join(rng.choice(alphabet) for _ in range(n))
        return text + extra

    if op in {"delete", "remove"}:
        if len(text) == 1:
            return ""
        idx = rng.randrange(len(text))
        return text[:idx] + text[idx + 1 :]

    if op == "replace":
        idx = rng.randrange(len(text))
        orig_char = text[idx]
        choices = confusion_map.get(orig_char, [])
        if choices:
            chars, weights = zip(*choices)
            new_char = rng.choices(chars, weights=weights, k=1)[0]
        else:
            new_char = orig_char
            while new_char == orig_char:
                new_char = rng.choice(alphabet)
        return text[:idx] + new_char + text[idx + 1 :]

    raise ValueError(f"Unsupported operation '{op}'")

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
    df_out = df.copy(deep=True)
    for col in column:
        for i in range(df.shape[0]):
            df_out.loc[i, col] = mess_up_string(df_out.loc[i, col])
    return df_out

def make_messy_data_datetime(df: pd.DataFrame, column: list[str]) -> pd.DataFrame:
    df_out = df.copy(deep=True)
    for col in column:
        for i in range(df.shape[0]):
            df_out.loc[i, col] = mess_up_datetime_format(df_out.loc[i, col])
    return df_out


        
