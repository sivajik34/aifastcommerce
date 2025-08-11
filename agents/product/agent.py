from agents.base.agent_factory import build_agent
from utils.prompts import load_prompt
import os

def get_product_agent(llm):
    from .tools import tools,enhance_product_description_tool,suggest_product_links_tool
    enhance_product_description = enhance_product_description_tool(llm)
    suggest_related_products = suggest_product_links_tool(llm,relation_type="related")
    suggest_upsell_products = suggest_product_links_tool(llm, relation_type="upsell")
    suggest_crosssell_products = suggest_product_links_tool(llm, relation_type="crosssell")    
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
    prompt_text = load_prompt(prompt_path)

    return build_agent(
        llm=llm,
        tools=tools,
        extra_tools=[enhance_product_description,suggest_related_products,suggest_upsell_products,suggest_crosssell_products],
        prompt=prompt_text,
        name="product_agent"
    )
