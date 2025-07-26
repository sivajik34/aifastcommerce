"""
Chat history management using PostgresChatMessageHistory
"""
import os
from typing import List
from langchain_postgres import PostgresChatMessageHistory
from langchain_core.messages import BaseMessage
import psycopg

class ChatHistoryManager:
    """Manages chat history using PostgreSQL storage."""
    
    def __init__(self):
        # Get database connection string from environment
        self.connection_string = os.getenv(
            "CON_STR"
        )
        self.sync_connection = psycopg.connect(self.connection_string )
        
    def get_session_history(self, session_id: str) -> PostgresChatMessageHistory:
        """
        Get chat history for a specific session/user.
        
        Args:
            session_id: Unique identifier for the chat session
            
        Returns:
            PostgresChatMessageHistory instance for the session
        """
        return PostgresChatMessageHistory("chat_message_history", session_id, sync_connection=self.sync_connection)
    
    async def get_messages(self, session_id: str) -> List[BaseMessage]:
        """
        Retrieve all messages for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            List of messages in chronological order
        """
        history = self.get_session_history(session_id)
        return history.messages
    
    async def add_message(self, session_id: str, message: BaseMessage):
        """
        Add a single message to the session history.
        
        Args:
            session_id: The session identifier  
            message: The message to add
        """
        history = self.get_session_history(session_id)
        history.add_message(message)
    
    async def add_messages(self, session_id: str, messages: List[BaseMessage]):
        """
        Add multiple messages to the session history.
        
        Args:
            session_id: The session identifier
            messages: List of messages to add
        """
        history = self.get_session_history(session_id)
        history.add_messages(messages)
    
    async def clear_session(self, session_id: str):
        """
        Clear all messages for a specific session.
        
        Args:
            session_id: The session identifier
        """
        history = self.get_session_history(session_id)
        history.clear()
    
    async def get_recent_messages(self, session_id: str, limit: int = 20) -> List[BaseMessage]:
        """
        Get the most recent messages for a session.
        
        Args:
            session_id: The session identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of recent messages
        """
        messages = await self.get_messages(session_id)
        return messages[-limit:] if len(messages) > limit else messages


# Global instance
chat_history_manager = ChatHistoryManager()