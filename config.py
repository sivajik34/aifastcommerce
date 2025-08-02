import os
from dotenv import load_dotenv

load_dotenv()

SECRET = os.getenv("SECRET")
DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC")
JWT_LIFETIME_SECONDS = int(os.getenv("JWT_LIFETIME_SECONDS", 3600))
