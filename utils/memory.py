import logging
import os
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.postgres import PostgresSaver

from utils.log import Logger
logger=Logger(name="util_memory", log_file="Logs/app.log", level=logging.DEBUG)
checkpointer = InMemorySaver()
store = InMemoryStore()

# Create a reusable checkpointer instance with context management
def get_checkpointer():
    #DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
    DB_URI = os.getenv("DATABASE_URL_NEW")

    logger.debug(DB_URI)
    return PostgresSaver.from_conn_string(DB_URI)
