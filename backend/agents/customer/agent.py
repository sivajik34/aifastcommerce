from agents.base.agent_factory import build_agent
from utils.prompts import load_prompt

import os

def get_customer_agent(llm): 
    from .tools import customer_tools   
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")    
    prompt_text = load_prompt(prompt_path)

    return build_agent(
        llm=llm,
        tools=customer_tools,
        extra_tools=[],
        prompt=prompt_text,
        name="customer_agent"
    )