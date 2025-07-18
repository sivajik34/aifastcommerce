from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from config import DATABASE_URL
from typing import AsyncGenerator


if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment.")

async_engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)

metadata = MetaData()
Base = declarative_base(metadata=metadata)

# ✅ For FastAPI (used in Depends)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# ✅ For manual usage (tool functions or services)
@asynccontextmanager
async def get_db_session():
    async with async_session_maker() as session:
        yield session