from langchain_core.messages import SystemMessage, HumanMessage

system_message = 'You are helpful assistant that expert in data analysis and data cleaning and find the data pattern smart'

find_json_schema_message = """
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

prompts_create_table_from_schema = """

"""

