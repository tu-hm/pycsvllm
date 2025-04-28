PROMPT_FIX_NUMBER_FORMATION = """
I give you a dataset CSV, a schema information about the dataset, and information about the dataset. 
Also I give you the number formatting for column in format list that I want you to apply for each data set.  
**If I **not** provide the format** for some column in **column list**, then I will apply the default format given schema for that column.
Also given you the few shot context in listing as pair that if I have as provided example that can help you solve the problem better.

Your response should follow the struct I provided, not other result or explanation or comment else.


**Standardization Rules**
Plain integers: digit-only strings → integer → output with a fixed decimal portion if requested (123456 → 123456.00 when the desired format is decimal).

Thousands separators: strip , or . thousands marks before parsing (1.234.567 → 1234567).

Alternate decimal marks: convert a lone , acting as a decimal separator to . (123,45 → 123.45).

Decorated numbers: remove currency symbols, percent signs, or other non-numeric characters, then convert

$1,234.56 → 1234.56

95% → 0.95 or 95.00 ↪ choose according to the requested column format or schema.

Phone numbers (if identified as such by the schema or format list): do not treat as numeric; leave untouched or convert to your chosen canonical phone pattern (e.g. +84901234567).

Verbal numbers: resolve common textual or mixed expressions into numerals ("two hundred" → 200, "hai trăm mười năm" → 215).

Unresolvable values: if you cannot confidently standardize a cell, flag it as an error instead of guessing.


**Number Formatting Standardization Rules**:
Apply the following number formatting standardization rules to columns/data fields containing numerical values. The goal is to convert all numerical representations into a single, consistent standard format, using a dot (.) as the decimal separator and no thousand separators.

**Input:**
- Dataset: # the raw dataset csv file.
```csv
{data}
```

- Schema: # the json schema of each data in the dataset.
```json
{schema}
```

- Format list: # provided as pair of that column and format that I want to apply for that column.
```list
{format_list}
```

- Example: # provided as list of pairing as original data and changed data.
```list
{context}
```

**Output:**

Provide *only* the JSON structure below. No other text, explanations, or comments should be included before or after the JSON.
* **No Extra Content:** Do *not* include any explanations, comments, summaries, code, or any text other than the resulting CSV data.
* **Preserve Integrity:** Maintain the original structure (rows and columns). Data in columns *not* listed in `{{column_format_list}}` must remain unchanged. 
Modify *only* the values within the specified columns according to the standardization rules.

{{
    "improves": [
      {{
        "row": follow with the index in dataset csv file,
        "attr": [
            {{
                "name": string "<column_name>",
                "value": string "<corrected_value>"
            }}
        ]
      }}
    ] | [],
    "error": [ # cells that cannot be standardized according to the rules and format
        {{
            "row": follow with the index in dataset csv file,
            "attr": string[] # list of column names in this row that failed standardization
        }}
    ]
}}
"""

PROMPT_FIX_DATETIME_FORMATION = """
You are tasked with standardizing and reformatting date/time columns within a provided CSV dataset. 
Leverage advanced parsing capabilities to handle a wide variety of date/time representations, including standard formats (e.g., DD/MM/YYYY, MM-DD-YYYY, YYYY.MM.DD), different time formats (12/24 hour, AM/PM, with/without seconds), and importantly, natural language expressions (e.g., "ngày 3 tháng 12 năm 2020", "last Tuesday", "8 PM").

Instructions:

Instructions
Target only the listed columns
– Work on a column if, and only if, its name appears in {{format_list}}.

Parse intelligently
– Accept any reasonable date/time representation, including
• numeric formats (e.g. DD/MM/YYYY, MM-DD-YYYY, YYYY.MM.DD)
• 12- or 24-hour clock, with or without seconds / AM-PM markers
• natural-language phrases (e.g. “ngày 3 tháng 12 năm 2020”, “last Tuesday”, “8 PM”).

Re-format
– Convert each successfully parsed value to the column’s target_format.

Handle failures
– If a value cannot be parsed with high confidence, do not change it.
– Record the cell in the error list (row index + column name).

Preserve everything else
– Do not alter rows, column order, or data in untouched columns.

Key improvements:

Clearer Task Description: Explicitly mentions handling diverse formats and natural language, drawing from the source text.
Precise Input Descriptions: Clarifies the purpose and format of each input.
Structured Instructions: Breaks down the process into clear steps (Target, Parse, Apply, Handle Errors, Preserve).
Refined Output Specification: Reinforces the "JSON only" requirement and clarifies what goes into improves and error.
Implicit Handling of Cases: Instead of listing specific cases like YYYY-DD-MM, the instruction to "interpret diverse and potentially inconsistent date/time formats" covers this more broadly, trusting the LLM's capability (as described in the source text). The optional Examples input is the place for very specific edge cases.

**Input:**
- Dataset: # the raw dataset csv file.
```csv
{data}
```

- Schema: # the json schema of each data in the dataset.
```json
{schema}
```

- Format list: # provided as pair of that column and format that I want to apply for that column.
```list
{format_list}
```

- Example: # provided as list of pairing as original data and changed data.
```list
{context}
```

**Output:**

Provide *only* the JSON structure below. No other text, explanations, or comments should be included before or after the JSON.
* **No Extra Content:** Do *not* include any explanations, comments, summaries, code, or any text other than the resulting CSV data.
* **Preserve Integrity:** Maintain the original structure (rows and columns). Data in columns *not* listed in `{{column_format_list}}` must remain unchanged. 
Modify *only* the values within the specified columns according to the standardization rules.

{{
    "improves": [
      {{
        "row": follow with the index in dataset csv file,
        "attr": [
            {{
                "name": string "<column_name>",
                "value": string "<corrected_value>"
            }}
        ]
      }}
    ] | [],
    "error": [ # cells that cannot be standardized according to the rules and format
        {{
            "row": follow with the index in dataset csv file,
            "attr": string[] # list of column names in this row that failed standardization
        }}
    ]
}}
"""


FIX_GRAMMAR_PROMPTS = """
To meticulously review specified text columns within a provided CSV dataset, identify, and correct common textual errors such as misspellings, typographical errors, and misplaced/extra/missing characters. Your analysis and corrections must be applicable to both English and Vietnamese text.

Process Input: Receive the raw CSV dataset, a list of target column names (Columns to Check), and optionally, a list of example corrections (Examples).
Iterate and Analyze: Go through each row of the dataset. For each row, examine the text content within the cells belonging to the specified Columns to Check.
Detect Errors: Using advanced natural language processing (NLP) capabilities trained on both English and Vietnamese, analyze the structure of individual words or short phrases within these cells. Identify potential errors like:
Common typos (e.g., hte -> the, adress -> address).
Phonetic misspellings (e.g., fone -> phone).
Character insertion/deletion/substitution (e.g., Sepetember -> September, Hanoi. -> Hanoi).
Incorrect diacritics in Vietnamese (e.g., nghành -> ngành, kĩ thuật -> kỹ thuật).
Missing spaces in common phrases (e.g., NewYork -> New York, HoChiMinh -> Hồ Chí Minh) only if confidence is very high.
Suggest Corrections: For each detected potential error, determine the most probable correct spelling or form based on your language models.
Apply High-Confidence Corrections: Only apply a correction if you have high confidence that it is accurate and preserves the original meaning at the word/phrase level. If confidence is low, or if the word is ambiguous (e.g., proper nouns not in dictionaries, technical jargon, intentional stylistic spelling), leave the original text unchanged.
Generate Output: Compile a list of all the corrections made.
Scope Limitations (What NOT to do):

DO NOT correct grammatical errors (e.g., leave "he go store" as is).
DO NOT rephrase sentences or change sentence structure.
DO NOT attempt to interpret or alter the meaning of the text beyond simple spelling/typo correction.
DO NOT standardize formats like dates (e.g., 10/05/2023 vs May 10, 2023) or numbers unless it's a direct typo (e.g., 2O23 -> 2023).
DO NOT change regional spelling variations if they are valid (e.g., color vs colour).
DO NOT split or merge cells or modify the CSV structure itself.

**Output:**

Provide *only* the JSON structure below. No other text, explanations, or comments should be included before or after the JSON.
* **No Extra Content:** Do *not* include any explanations, comments, summaries, code, or any text other than the resulting CSV data.
* **Preserve Integrity:** Maintain the original structure (rows and columns). Data in columns *not* listed in `{{column_format_list}}` must remain unchanged. 
Modify *only* the values within the specified columns according to the standardization rules.

{{
    "improves": [
      {{
        "row": follow with the index in dataset csv file,
        "attr": [
            {{
                "name": string "<column_name>",
                "value": string "<corrected_value>"
            }}
        ]
      }}
    ] | [],
    "error": [ # cells that cannot be standardized according to the rules and format
        {{
            "row": follow with the index in dataset csv file,
            "attr": string[] # list of column names in this row that failed standardization
        }}
    ]
}}

**Input:**
- Dataset: # the raw dataset csv file.
```csv
{data}
```

- Example: # provided as list of pairing as original data and changed data.
```list
{context}
```
"""