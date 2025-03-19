import json

from langchain_core.prompts import ChatPromptTemplate

from file_processing.schema import CreateQueryResponse
from llm import base_llm
from llm.prompts import SYSTEM_MESSAGE, CREATE_TABLE_SCHEMA_PROMPTS

def generate_create_table(schema, table_name, columns):
    message = [('system', SYSTEM_MESSAGE), ('human', CREATE_TABLE_SCHEMA_PROMPTS)]
    chain_message = ChatPromptTemplate.from_messages(message)
    chain = chain_message | base_llm
    chain.bind(response_format="json_object")
    response = chain.invoke(input={
        "schema": str(schema),
        "table_name": table_name,
        "column_list": str(columns),
    })

    try:
        content_json = json.loads(response.content)

        if isinstance(content_json, dict) and "statement" in content_json:
            query_response = CreateQueryResponse(**content_json)
            return query_response.statement
        else:
            raise ValueError("Invalid JSON format received from API.")

    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format received from API.")



