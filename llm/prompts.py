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

Provide a summary of the data analysis, cleaning, and normalization procedures in a structured format such as a bulleted list or a short report. Include key steps, visualizations (examples as text descriptions or summary), and reasoning where applicable.

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
Given the CSV dataset below and any optional context provided, generate a **strict and valid JSON Schema** that adheres to the following requirements:

1. **Accurate Data Typing** – Infer and enforce the correct data types (e.g., `string`, `number`, `integer`, `boolean`, `array`, `object`).
2. **Format Specification** – Apply appropriate formats where relevant (e.g., `date-time`, `email`, `uuid`, `uri`).
3. **Pattern Validation** – Derive and enforce regex patterns for fields that contain structured or constrained values.
4. **Value Constraints** – Extract and apply min/max values, string length constraints, and enumerated values where applicable.
5. **Field Descriptions** – Provide meaningful descriptions based on the field names, values, and context.
6. **Intelligent Schema Generation** – Ensure the schema is precise, comprehensive, and avoids unnecessary generalization.

Your response **must** strictly follow this JSON format:
{{
    "json_schema": {{ ... }},  
    "other_info": "Additional details about the schema"
}}
**Do not** return anything outside this format.

---
**CSV Dataset:**
{data}

**Additional Context (if any):**
{context}
---
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

Your response **must strictly** follow this JSON format:

```
{{
    "json_schema": {{ ... }},
    "other_info": "Additional details about the schema"
}}
```

**Do not** return anything outside this format.

### Input Data:  
CSV Dataset:  
{data}  

Optional Context:  
{context}  

Ensure that the generated JSON Schema is **valid**, accurately represents the CSV structure, and reflects inferred data types.
"""

get_issues_of_data = """
You are given a **strict schema** for a dataset and a **partial dataset** extracted within a specified range [l, r]. Your task is to **identify and correct errors** in the dataset while strictly adhering to the schema and real-world context.

#### Possible Issues to Detect & Fix:
1. **Wrong Format:**  
   - Example: The correct date format is **DD-MM-YYYY**, but some data uses **MM:DD:YYYY**.  
   - Example: A serial number should follow **ABC-123**, but an incorrect entry is **AB1-123**.  

2. **Incorrect Number Format:**  
   - Example: The expected decimal separator is **comma (1,35)**, but some entries use a **dot (1.35)** instead.  

3. **Unit Inconsistency:**  
   - Example: The dataset mixes units (e.g., **1 cm** and **2 meters**), causing inconsistencies.  

4. **Spelling or Typographical Errors:**  
   - Example: **"Itally"** instead of **"Italy"**.  

Your **response** must strictly follow this JSON format**:  

```json
{
    "improves": [
        {
            "description": "Explain why the data needs correction in simple terms.",
            "position": {
                "row": <row_number>,
                "column": <column_number>,
                "new_values": "<corrected_value>"
            }
        }
    ]
}
```

---
### **Input Structure:**  
#### **Schema:**  
```
{schema}
```
#### **Data (Partial Range from Dataset):**  
```
{data}
```
#### **Range for Processing:**  
```
{range}
```
---
### **Expected Behavior:**  
- **Ensure all corrections align with the schema** (e.g., expected formats, constraints, regex patterns).  
- **Explain the reasoning for each fix clearly and concisely.**  
- **Preserve the integrity of real-world context** while updating values.  
- **Strictly return only the required JSON format.**  
"""