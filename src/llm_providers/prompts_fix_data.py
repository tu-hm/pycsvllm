PROMPT_FIX_NUMBER_FORMATION = """
I give you a dataset CSV, a schema information about the dataset, and information about the dataset. 
Also I give you the number formatting for each column in format list that I want you to apply for each data set.  
Also given you the few shot context in listing as pair that if I have as provided example that can help you solve the problem better.

Your response should follow the struct I provided, not other result or explanation or comment else.

Number Formatting Standardization Rules:
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
* **Preserve Integrity:** Maintain the original structure (rows and columns). Data in columns *not* listed in `{column_format_list}` must remain unchanged. 
Modify *only* the values within the specified columns according to the standardization rules.

{{
    "improves": [
      {{
        "row": <0-based row index>,
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
            "row": <0-based row index>,
            "attr": string[] # list of column names in this row that failed standardization
        }}
    ]
}}

Cases to handle:
-   **Concatenated Numbers:** Identify sequences of digits only as integers.
    * Example: `123456789` -> `123456789.00` (or the final standard decimal format)
-   **Numbers with Thousand Separators:** Remove common thousand separators (like `,` or `.`) before converting to a number.
    * Example: `1.234.567` -> `1234567`
    * Example: `1,234,567` -> `1234567`
-   **Decimal Numbers with Different Separators:** Convert the decimal separator (if not `.`) to a dot (`.`).
    * Example: `123,45` -> `123.45`
-   **Complex Formats or Numbers with Symbols:** Identify and remove non-numeric symbols before standardization. The LLM should use context to understand the true meaning of the number string.
    * Example: `$1,234.56` -> `1234.56`
    * Example: `95%` -> `0.95` (or `95.00` depending on how you want to represent percentages after standardization - clarify in specific instructions if needed)
    * Example: `€1000` -> `1000.00`
-   **Phone Number Format:** For fields identified as phone numbers in the schema or context, either retain the original format or standardize to a specific phone number format (clarify the desired standard format if standardization is needed). The LLM needs to distinguish phone numbers from other types of numbers.
    * Example: `(84) 90 123 4567` -> Keep as is, or standardize to `+84901234567` (clarify)
-   **Number that describe with text:** for some number can describe by text
    * Example: `2 hundreds` -> 200, `hai trăm mười năm` -> 215,
"""

