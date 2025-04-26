import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

base_llm: BaseChatModel = ChatOpenAI(
    model='o4-mini',
)

class LLMProvider:
    def __init__(self, model: BaseChatModel):
        self.model = model

    def generate(
        self,
        system_prompt: str,
        human_prompt: str,
        force_json: bool = False, # Added flag to force JSON output
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]

        model_to_invoke = self.model

        if force_json:
            if "json" not in system_prompt.lower():
                print("Warning: force_json=True but 'json' not mentioned in system_prompt. Consider instructing the model to output JSON in the system prompt for reliability.")
            try:
                 model_to_invoke = self.model.bind(
                     response_format={"type": "json_object"}
                 )
            except Exception as e:
                 print(f"Warning: Could not bind response_format for JSON. The model might not support it or the syntax changed. Error: {e}")

        chain = ChatPromptTemplate.from_messages(messages) | model_to_invoke

        try:
            response = chain.invoke(additional_data)
            content = str(response)
            if hasattr(response, 'content'):
                content = response.content

            if force_json:
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    print(f"Warning: Model output was not valid JSON despite force_json=True:\n{content}")

            return content

        except Exception as e:
            print(f"Error during model generation: {e}")
            raise
