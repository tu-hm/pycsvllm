import json

from langchain_core.prompts import ChatPromptTemplate

from file_processing.csv import CSVLoader
from file_processing.schema import CreateQueryResponse
from llm import openai_llm
from llm.prompts import system_message, prompts_create_table_from_schema

def generate_create_table(file: CSVLoader):
    schema = file.schema
    table_name = file.name

    columns = file.data.columns

    message = [('system', system_message), ('human', prompts_create_table_from_schema)]
    chain_message = ChatPromptTemplate.from_messages(message)
    chain = chain_message | openai_llm
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



