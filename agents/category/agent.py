from agents.base.agent_factory import build_agent
from utils.prompts import load_prompt
import os

def get_category_agent(llm):
    from .tools import category_tools, get_category_seo_by_name_tool
    seo_update_tool = get_category_seo_by_name_tool(llm)
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
    prompt_text = load_prompt(prompt_path)

    return build_agent(
        llm=llm,
        tools=category_tools,
        extra_tools=[seo_update_tool],
        prompt=prompt_text,
        name="category_agent"
    )
