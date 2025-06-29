from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from config import DATABASE_URL

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment.")

async_engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)

metadata = MetaData()
Base = declarative_base(metadata=metadata)

@asynccontextmanager
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

@asynccontextmanager
async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
