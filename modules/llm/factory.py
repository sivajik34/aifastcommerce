from .openai_strategy import OpenAIStrategy
from .gemini_strategy import GeminiStrategy
from .llama_strategy import LlamaStrategy
from .azure_strategy import AzureOpenAIStrategy

def get_llm_strategy(service_name: str, config):
    strategies = {
        "openai": OpenAIStrategy,
        "gemini": GeminiStrategy,
        "llama": LlamaStrategy,
        "azure_openai": AzureOpenAIStrategy,
    }

    strategy_cls = strategies.get(service_name.lower())
    if not strategy_cls:
        raise ValueError(f"Unsupported LLM service: {service_name}")
    return strategy_cls(config)
