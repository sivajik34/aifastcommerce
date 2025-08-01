import logging
from langgraph.store.memory import InMemoryStore
from utils.log import Logger

logger=Logger(name="util_memory", log_file="Logs/app.log", level=logging.DEBUG)

store = InMemoryStore()


