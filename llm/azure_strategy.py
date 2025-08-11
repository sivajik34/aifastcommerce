
from utils import common
from .base import LLMStrategy

class AzureOpenAIStrategy(LLMStrategy):
    
    def initialize(self):
        from langchain_openai import AzureChatOpenAI
        env_vars = common.get_required_env_vars(["AZURE-DEPLOYMENT-NAME","OPENAI-API-VERSION","AZURE-OPENAI-API-KEY","AZURE-OPENAI-ENDPOINT"])
        return AzureChatOpenAI(
            deployment_name=env_vars["AZURE-DEPLOYMENT-NAME"],
            openai_api_version=env_vars["OPENAI-API-VERSION"],           
            openai_api_key=env_vars["AZURE-OPENAI-API-KEY"],         
            azure_endpoint=env_vars["AZURE-OPENAI-ENDPOINT"],
            max_tokens=4000
        )
