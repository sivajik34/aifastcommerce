from langgraph.prebuilt import create_react_agent
from typing import Any, List, Optional
import logging
from utils.log import Logger
logger = Logger(name="base_agent", log_file="Logs/app.log", level=logging.DEBUG)
def build_agent(
    llm: Any,
    tools: List[Any],
    prompt: str,
    name: str = "generic_agent",
    extra_tools: Optional[List[Any]] = None,
) -> Any:
    #logger.info(f"agent name:{name}")
    #logger.info(f"agent name:{prompt}")
    all_tools = tools + (extra_tools or [])
    return create_react_agent(
        llm,
        tools=all_tools,
        name=name,
        prompt=prompt
    )
