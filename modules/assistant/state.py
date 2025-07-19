from typing import Literal
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState


class RouterSchema(BaseModel):
    """Schema for the triage router decision making."""
    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification decision."
    )
    classification: Literal["ignore", "respond"] = Field(
        description="Whether to ignore the input or respond to it."
    )


class AgentState(MessagesState):
    """State management for the ecommerce assistant agent.
    
    Extends MessagesState to include additional fields for user context
    and routing decisions.
    """
    user_input: str
    user_id: str
    classification_decision: Literal["ignore", "respond"]