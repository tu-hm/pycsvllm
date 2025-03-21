# system_message = 'You are helpful assistant that expert in data analysis and data cleaning and find the data pattern smart'

SYSTEM_MESSAGE = """
Provide detailed instructions on data analysis and data cleaning/normalization, outlining key concepts and techniques.

# Steps

1. **Data Analysis**:
   - Define the objectives of the data analysis.
   - Collect relevant data from primary and secondary sources.
   - Use statistical methods to summarize the data (descriptive statistics).
   - Visualize the data using plots and graphs to identify patterns and trends.
   - Perform exploratory data analysis to generate hypotheses.

2. **Data Cleaning**:
   - Identify and handle missing values.
   - Remove duplicates and inconsistencies in the data.
   - Correct structural errors such as incorrect data types or misplaced entries.
   - Filter out irrelevant data that does not contribute to the analysis goals.

3. **Data Normalization**:
   - Identify the need for data normalization based on the analysis requirements.
   - Choose an appropriate normalization technique (e.g., Min-Max Scaling, Z-score Normalization, Decimal Scaling).
   - Apply the normalization method to scale the data within the desired range or distribution.

# Output Format

- You should given the json format that user have defined. No ```json``` like this, only the data, no other comment or explain.

# Examples

**Example 1**:
- **Objective**: Analyze sales data to identify trends.
- **Data Analysis**:
  - Summarized sales data to calculate average monthly sales.
  - Used line graphs to visualize monthly sales trends.
- **Data Cleaning**:
  - Addressed missing values in the sales column by filling in the median sales value.
  - Removed duplicate transaction records.
- **Data Normalization**:
  - Applied Min-Max Scaling to the sales figures to normalize data between 0 and 1.

**Example 2**:
- **Objective**: Prepare customer data for machine learning model.
- **Data Analysis**:
  - Conducted descriptive statistics on customer demographics.
  - Visualized age distribution using a histogram.
- **Data Cleaning**:
  - Corrected categorical errors in the 'Gender' field.
  - Filtered out entries with unrealistic ages.
- **Data Normalization**:
  - Utilized Z-score Normalization on numerical fields for model readiness. 

# Notes

- Ensure the selection of data cleaning and normalization methods suits the context and objectives.
- Consider potential biases introduced during normalization, especially when preparing data for machine learning models.
"""

FIND_JSON_SCHEMA_PROMPTS = """
**Task:**  
Generate a **strict and valid JSON Schema** in **Draft 2020-12** for the given CSV dataset, adhering to the following requirements:  

### **Schema Requirements:**  
1. **Accurate Data Typing** – Infer and enforce the correct data types (`string`, `number`, `boolean`, `array`, `object`, 'null').  Prefer type number because python not support integer type.
2. **Format Specification** – Apply relevant formats (`date-time`, `email`, `uuid`, `uri`, etc.) where applicable.  
3. **Pattern Validation** – Derive and enforce regex patterns for fields with structured or constrained values.   
5. **Field Descriptions** – Generate meaningful descriptions based on field names, sample values, and any provided context.  
6. **Strictness & Precision** – The schema must be precise, avoiding unnecessary generalization while ensuring validity.  

### **Response Format (Strictly Follow This Structure):**  
{{
    "json_schema": {{ ... }},  
    "other_info": "Additional details about the schema"
}}
```  
- **Do NOT** include extra explanations or any content outside this JSON structure, not ```json```.  
- Ensure the output schema is complete, consistent, and strictly adheres to **Draft 2020-12** specifications.  

---

### **Input Data:**  
**CSV Dataset:**  
```
{data}
```  

**Column Metadata:**  
```
{column_info}
```  

**Additional Context (if provided):**  
```
{context}
```
"""

CREATE_TABLE_SCHEMA_PROMPTS = """
Given the database schema, table name, and list of columns, generate a SQLite CREATE TABLE statement that accurately defines the table structure. 

- Ensure the statement follows SQLite syntax, including appropriate data types, constraints (e.g., PRIMARY KEY, NOT NULL, UNIQUE), and any relevant attributes inferred from the provided schema.  
- The table definition should be as strict as possible, correctly enforcing constraints based on the given schema and column list.  
- Use appropriate SQLite data types (e.g., INTEGER, TEXT, REAL, BLOB) and constraints where applicable.  

Your response **must** strictly follow this JSON format:  

{{
    "statement": "<SQLite CREATE TABLE statement>"
}}

**Do not** return anything outside this format.

### Input Data:  
Schema:  
{schema}  

Table Name:  
{table_name}  

Column List:  
{column_list}  
"""

find_simple_json_schema_message = """
Given the following CSV dataset and any optional context provided, generate a JSON Schema that meets the following requirement:

- **Accurate Data Typing**: Infer and enforce the correct data types (`string`, `number`, `integer`, `boolean`, `array`, `object`) for each field.  
- **All fields are optional** (i.e., not required).  

Your response **must** strictly follow this JSON format:

{{
    "json_schema": {{ ... }},
    "other_info": "Additional details about the schema"
}}

**Do not** return anything outside this format.

### Input Data:  
CSV Dataset:  
{data}  

Optional Context:  
{context}  

Ensure that the generated JSON Schema is **valid**, accurately represents the CSV structure, and reflects inferred data types.
"""

GET_ISSUE_OF_DATA = """
You are given a **strict schema** for a CSV dataset along with a **partial dataset**. Your task is to **detect and correct errors** in the dataset while conforming rigorously to the schema and preserving the real-world meaning of the data. The corrections should be as precise as possible—if a valid alternative exists, adjust the value rather than reverting to a default.

---

### **Issues to Detect & Correct**

1. **Incorrect Formatting:**  
   - **Dates:** Ensure dates follow the **DD-MM-YYYY** format. For example, if a date is provided as **MM-DD-YYYY** or **MM:DD:YYYY**, convert it to the correct format.  
   - **Serial Numbers:** Validate entries against the expected pattern (e.g., **ABC-123**); if a serial number appears as **AB1-123**, correct the format.  
   - **General Consistency:** All entries in a given column should adhere to a single, uniform format.
   - Not correct white space, you can remove it.

2. **Number Formatting Errors:**  
   - Correct the decimal and thousand separators. For example, if the expected format uses a comma (e.g., **1,35** for decimals), convert any numbers using a dot (e.g., **1.35**) accordingly.  
   - Adjust number formatting without defaulting to a generic value.

3. **Unit Inconsistencies:**  
   - If the dataset uses mixed units (e.g., **1 cm** vs. **2 meters**), standardize units to maintain consistency across the dataset.

4. **Spelling and Typographical Errors:**  
   - Fix misspellings and typographical errors while respecting contextual clues. For instance, correct **"Itally"** to **"Italy"**.

5. **Contextual and Logical Corrections:**  
   - For any invalid value, decide on the best correction by considering the time, type, description, and overall column meaning.  
   - Use logical substitutions (e.g., change **"midnight"** to **"00:00:00"**).

6. **Intelligent Spelling Adjustments:**  
   - Use context to remove extra characters or typos. For example:  
     - "italy111" should be corrected to "Italy"  
     - "sun?light" should become "Sunlight"  
     - "9taly" should be corrected to "Italy"

---

### **Input Structure**

- **Schema:**  
  ```
  {schema}
  ```

- **Data (Partial Range from Dataset):**  
  ```
  {data}
  ```


---

### **Output Requirements**

Your response **must** strictly follow this JSON format:

{{
    "improves": list[  
        {{
            "description": "Explain why the data needs correction in simple terms.", 
            "row": <<row_number>>, row is base 0 start at 0,   
            "attribute": list[
                {{
                    "name": <<column_headername>>,  
                    "fixed_value": "<<corrected_value>>, default type is str that I can format"  
                }} #list fixed items in one row.
            ]
        }}  
    ] || can be none  
}}

**Important:**  
- Return **only** the required JSON structure—do not include any additional text or formatting outside this structure.  
- Provide a clear, concise explanation for each correction that ties back to the schema rules and real-world context.  
- Ensure every change is aligned with the expected formats, constraints, and regex patterns defined in the schema.

---

### **Expected Behavior**

- **Strict Schema Adherence:**  
  Every correction must align with the provided schema specifications.

- **Context-Aware Corrections:**  
  Corrections should respect the real-world context of the data (e.g., maintaining appropriate units and logical time values).

- **Minimal Disruption:**  
  Only change values that are in error. If a better correction exists, do not resort to default values.

- **Clear Justification:**  
  For every corrected value, provide a brief explanation that is easily understandable.

---

This prompt is designed to guide you through a careful, context-aware data cleaning process while strictly adhering to the schema and returning your findings in the required JSON format.

"""

FIX_JSON_SCHEMA_ERROR = """
I have a list of errors detected by JSON Schema validation and right JSON Schma of it.. 
Each error corresponds to a row in my dataset and specifies an attribute that has an issue. 
I need you to suggest fixes in the following structured format:

```json
[
  {{
    "row": number,
    "attribute": [{{
      "name": string,
      "fixed_value": string
    }}] # list of fixed values in one row
  }}
]
```

### Output:
Your response **must** strictly follow this JSON format, no ```json```:


{{
    "improves": list[
      {{
        "description": "Explain why the data needs correction in simple terms.",
        "row": number,
        "attribute": list[ 
            {{
                "name": string,
                "fixed_value": string
            }}
        ]
      }}]
    ]
}}
**Important:**  
- Return **only** the required JSON structure—do not include any additional text or formatting outside this structure.  
- Ensure every change is aligned with the expected formats, constraints, and regex patterns defined in the schema.

Ensure that:
- Dates are formatted correctly.
- Numbers follow the expected constraints.
- Text values match required patterns.
- Any other JSON Schema validation issues are fixed accordingly.

***Now, I give you the JSON Schema of the right data***
{schema}

**Now, here is the list of errors I need you to fix:**
{errors}

"""