import os
import logging
from dotenv import load_dotenv

load_dotenv()
def get_required_env_vars(vars):
    try:
        missing_vars = [var for var in vars if os.getenv(var) is None]
        if missing_vars:
            logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return None
        return {var: os.getenv(var) for var in vars}
    except Exception as e:
        logging.error("Error in get_required_env_vars method:{}".format(e))
        raise ValueError("Error in get_required_env_vars method:{}".format(e))