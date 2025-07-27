"""
Main agent workflow for the ecommerce assistant
"""
import logging
import traceback
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage

from .state import AgentState, RouterSchema
from modules.magento_tools import tools, tools_by_name
from .prompts import (
    TRIAGE_SYSTEM_PROMPT, 
    TRIAGE_USER_PROMPT,
    ASSISTANT_SYSTEM_PROMPT
)
from modules.llm.factory import get_llm_strategy
from utils.log import Logger
logger=Logger(name="agent", log_file="Logs/app.log", level=logging.DEBUG)
# ---- LLM Setup ----
strategy = get_llm_strategy("openai", "")
llm = strategy.initialize()
tool_names = list(tools_by_name.keys())
print(tool_names)
llm_with_tools = llm.bind_tools(tools, tool_choice="auto", parallel_tool_calls=False)
llm_router = llm.with_structured_output(RouterSchema)


def triage_router(state: AgentState) -> Command:
    """
    Route user input based on whether it should be handled or ignored.
    
    This node classifies the user input and decides whether to proceed
    with the response agent or end the conversation.
    """
    user_msg = state["user_input"]
    user_prompt = TRIAGE_USER_PROMPT.format(user_input=user_msg)
    messages = state.get("messages", [])
    result = llm_router.invoke([
        {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},*messages,
        {"role": "user", "content": user_prompt},
    ])

    if result.classification == "respond":
        logger.info(f"📧 Classification: respond - {result.reasoning}")
        return Command(
            goto="response_agent",
            update={                
                "classification_decision": result.classification,
                "classification_reasoning": result.reasoning
            },
        )
    elif result.classification == "ignore":
        logger.info(f"🚫 Classification: ignore - {result.reasoning}")
        return Command(
            goto=END,
            update={"classification_decision": result.classification},
        )
    else:
        raise ValueError(f"Invalid classification: {result.classification}")    


def llm_call(state: AgentState):
    """
    Main LLM reasoning node that decides what tool to call next.
    
    This node processes the conversation history and determines
    the appropriate tool to use based on the user's request.
    """
    logger.info("🧠 LLM reasoning and tool selection...")

    response = llm_with_tools.invoke(
        [
            SystemMessage(content=ASSISTANT_SYSTEM_PROMPT),
            *state["messages"]
        ]
    )
    
    # Log what tool was selected
    if hasattr(response, 'tool_calls') and response.tool_calls:
        tool_names = [tc.get("name") or getattr(tc, "name", "unknown") for tc in response.tool_calls]
        logger.info(f"🔧 Selected tools: {tool_names}")
    
    return {"messages": state["messages"] + [response]}


async def tool_handler(state: AgentState):
    """
    Execute the tools requested by the LLM.
    
    This node handles the actual execution of tools and manages
    any errors that might occur during tool execution.
    """
    logger.info("⚙️ Executing tools...")
    last_message = state["messages"][-1]
    
    # Ensure we have an AIMessage with tool_calls
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        logger.info("⚠️ No tool calls found in last message")
        return {"messages": state["messages"]}
    
    tool_messages = []

    for idx, tool_call in enumerate(last_message.tool_calls):
        try:
            logger.info(f"\n--- Executing Tool [{idx + 1}] ---")

            # Safe access to tool call properties
            tool_name = getattr(tool_call, "name", tool_call.get("name"))
            tool_args = getattr(tool_call, "arguments", None)
            if tool_args is None and isinstance(tool_call, dict):
                tool_args = tool_call.get("arguments") or tool_call.get("args")

            tool_id = getattr(tool_call, "id", tool_call.get("id"))

            logger.info(f"🔧 Tool: {tool_name}")
            logger.info(f"📝 Args: {tool_args}")

            # Validate tool exists
            if tool_name not in tools_by_name:
                error_msg = f"Tool '{tool_name}' not found"
                logger.info(f"❌ {error_msg}")
                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tool_id or f"unknown-{idx}",
                        content=error_msg
                    )
                )
                continue

            # Execute tool
            tool = tools_by_name[tool_name]
            result = await tool.ainvoke(tool_args)
            
            # Convert result to string if needed
            if not isinstance(result, str):
                result = str(result)
                
            logger.info(f"✅ Result: {result[:100]}{'...' if len(result) > 100 else ''}")
            
            tool_messages.append(ToolMessage(tool_call_id=tool_id, content=result))

        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"❌ Error during tool_call [{idx + 1}]: {error_msg}")
            #traceback.logger.info_exc()
            tool_messages.append(
                ToolMessage(
                    tool_call_id=tool_id or f"unknown-{idx}",
                    content=error_msg
                )
            )

    return {"messages": state["messages"] + tool_messages}


def should_continue(state: AgentState) -> Literal["tool_handler", "__end__"]:
    """
    Determine whether to continue with tool execution or end the workflow.
    
    The workflow continues if there are tools to execute, and ends when
    the 'done' tool has been executed or no more tools are needed.
    """
    last_message = state["messages"][-1]
    
    # Check if it's an AIMessage with tool_calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Check if any of the tool calls is "done"
        for tool_call in last_message.tool_calls:
            tool_name = getattr(tool_call, "name", None)
            if tool_name is None and isinstance(tool_call, dict):
                tool_name = tool_call.get("name")
            if tool_name == "done":
                logger.info("🏁 Done tool detected - will end after execution")
                return "tool_handler"  # Execute the done tool, then end
        return "tool_handler"  # Execute other tools
    
    # Check if the last message is a ToolMessage from the "done" tool
    if isinstance(last_message, ToolMessage):
        # Look for the corresponding AIMessage with tool_calls
        for i in range(len(state["messages"]) - 1, -1, -1):
            msg = state["messages"][i]
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = getattr(tool_call, "name", None)
                    if tool_name is None and isinstance(tool_call, dict):
                        tool_name = tool_call.get("name")
                    if tool_name == "done" and getattr(tool_call, "id", tool_call.get("id")) == last_message.tool_call_id:
                        logger.info("🏁 Workflow complete - ending")
                        return "__end__"
                break
    
    return "__end__"


# ---- Response Agent Workflow ----
agent_workflow = StateGraph(AgentState)
agent_workflow.add_node("llm_call", llm_call)
agent_workflow.add_node("tool_handler", tool_handler)
agent_workflow.set_entry_point("llm_call")
agent_workflow.add_conditional_edges(
    "llm_call", 
    should_continue, 
    {"tool_handler": "tool_handler", "__end__": END}
)
agent_workflow.add_edge("tool_handler", "llm_call")
response_agent = agent_workflow.compile()

# ---- Overall Workflow ----
overall_workflow = (
    StateGraph(AgentState)
    .add_node("triage_router", triage_router)
    .add_node("response_agent", response_agent)
    .set_entry_point("triage_router")
    .add_conditional_edges(
        "triage_router",
        lambda state: "response_agent" if state.get("classification_decision") == "respond" else END,
        {"response_agent": "response_agent", END: END}
    )
    .compile()
)