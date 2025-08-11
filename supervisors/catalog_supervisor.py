import os
from langgraph_supervisor import create_supervisor
from utils.prompts import load_prompt

def get_catalog_supervisor(llm, agents):
    from langgraph_supervisor.handoff import create_forward_message_tool
    forwarding_tool = create_forward_message_tool("catalog_supervisor")
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"prompts", "catalog_supervisor_prompt.md")
    prompt_text = load_prompt(prompt_path)
    return create_supervisor(
        agents,
        model=llm,
        supervisor_name="catalog_supervisor",
        prompt=prompt_text,
        output_mode="full_history",
        tools=[forwarding_tool]
    ).compile(name="catalog_supervisor")
