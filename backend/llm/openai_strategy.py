from langchain_openai import ChatOpenAI
from utils import common
from .base import LLMStrategy

class OpenAIStrategy(LLMStrategy):
    def initialize(self):
        env_vars = common.get_required_env_vars(["OPENAI_KEY","OPENAI_MODEL"])
        return ChatOpenAI(
            temperature = 0,
            openai_api_key = env_vars["OPENAI_KEY"],
            model_name = env_vars["OPENAI_MODEL"],
            max_tokens = 4000
        )