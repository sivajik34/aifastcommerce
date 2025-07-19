import os
from utils import common
from .base import LLMStrategy
#from constant import GEMINI_CRED_FILES
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""
class GeminiStrategy(LLMStrategy):
    
    def initialize(self):
        from langchain_google_genai import ChatGoogleGenerativeAI
        env_vars = common.get_required_env_vars(["GEMINI-PROJECT-ID"])
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            project_id=env_vars["GEMINI-PROJECT-ID"]
        )