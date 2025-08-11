from langchain_core.tools import tool
import logging
from utils.log import Logger
logger=Logger(name="utility_tools", log_file="Logs/app.log", level=logging.DEBUG)

#it seems these tools not required, we can deprecate i think

@tool
def done():
    """Signal that the agent has completed all requested tasks successfully.
    
    Call this tool when you have fully completed the user's request and no further 
    actions are needed. This will end the conversation gracefully.
    """
    
   
    logger.info("✅ done() tool invoked.")
    return "Task completed successfully."



@tool
def ask_question(question: str):
    """Ask a clarifying question to the user when you need additional information.
    
    Args:
        question: The specific question you want to ask the user
        
    Use this when:
    - You need missing information to complete a task
    - The user's request is ambiguous
    - You need confirmation before taking an action
    """
    return f"I need some additional information: {question}"
tools=[ask_question,done]