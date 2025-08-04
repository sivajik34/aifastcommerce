from langgraph.prebuilt import create_react_agent
from typing import Any, List, Optional

def build_agent(
    llm: Any,
    tools: List[Any],
    prompt: str,
    name: str = "generic_agent",
    extra_tools: Optional[List[Any]] = None,
) -> Any:
    all_tools = tools + (extra_tools or [])
    return create_react_agent(
        llm,
        tools=all_tools,
        name=name,
        prompt=prompt
    )
