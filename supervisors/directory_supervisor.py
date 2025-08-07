import os
from langgraph_supervisor import create_supervisor
from utils.prompts import load_prompt
def get_directory_supervisor(llm,agents):
    prompt_path = os.path.join(os.path.dirname(__file__), "directory_supervisor_prompt.md")
    prompt_text = load_prompt(prompt_path)
    return create_supervisor(
        agents,
        model=llm,
        supervisor_name="directory_supervisor",
        prompt=prompt_text,
        output_mode="full_history"
    ).compile(name="directory_supervisor")
