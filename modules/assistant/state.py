from pydantic import BaseModel, Field
from langgraph.graph import MessagesState
from typing import Dict, List, Optional, Any, Literal, TypedDict
from langchain_core.messages import BaseMessage
from enum import Enum


class ClassificationType(str, Enum):
    """Classification types for triage"""
    RESPOND = "respond"
    IGNORE = "ignore"

class RouterSchema(BaseModel):
    """Schema for routing decisions"""
    classification: ClassificationType = Field(
        description="Whether to respond to or ignore the user input"
    )
    reasoning: str = Field(
        description="Explanation for the classification decision"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence level of the classification (0-1)"
    )     



class AgentState(TypedDict, total=False):
    """Enhanced state for the ecommerce agent"""
    # Core conversation
    user_input: str
    messages: List[BaseMessage]    
    session_id: Optional[str]
    
    # Classification and routing
    classification_decision: Optional[str]
    classification_reasoning: Optional[str]

    
    
    







__all__ = [
    "AgentState",
    "RouterSchema" 
]        