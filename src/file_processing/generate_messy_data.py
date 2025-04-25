import string

import pandas
import random
from num2words import num2words
from datetime import datetime

def format_number_random(num):
    num = str(num)
    formats = [
        lambda n: f"{n}",  # Default
        lambda n: f"{n:,}",  # With commas
        lambda n: f"{n:.2e}",  # Scientific notation
        lambda n: num2words(int(n)),  # In words (English)
        lambda n: f"{n:.3f}".replace('.', ','),  # Decimal with comma (EU-style)
    ]

    formatter = random.choice(formats)
    try:
        return formatter(num)
    except Exception as e:
        return f"Error formatting number: {e}"

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

def make_messy_data_number(df: pandas.DataFrame, column: list[str]) -> pandas.DataFrame:
    for col in column:
        df[col].apply(format_number_random)
    return df

def make_messy_data_string(df: pandas.DataFrame, column: list[str]) -> pandas.DataFrame:
    for col in column:
        df[col] = df[col].apply(mess_up_string)
    return df


        
