from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

load_dotenv()

base_llm: BaseChatModel = ChatOpenAI(
    model='gpt-4o-mini',
    temperature=0,
)
